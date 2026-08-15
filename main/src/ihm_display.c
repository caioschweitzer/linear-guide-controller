#include "ihm_display.h"
#include <math.h>
#include <stdio.h>
#include <string.h>

#define LCD_RS (1 << 0)
#define LCD_RW (0 << 1)
#define LCD_EN (1 << 2)
#define LCD_BL (1 << 3)

#ifndef HOST_TEST
#include "driver/gpio.h"
#include "driver/i2c_master.h"
#include "esp_log.h"

static const char *TAG = "IHM_DISPLAY";
#endif

const char *ihm_state_to_str(machine_state_t state) {
  switch (state) {
  case MACHINE_STATE_IDLE:
    return "IDLE  ";
  case MACHINE_STATE_MOVING:
    return "MOVING";
  case MACHINE_STATE_EMERGENCY:
    return "EMERG ";
  default:
    return "UNK   ";
  }
}

void ihm_format_lines(float position_mm, float velocity_mm_s,
                      machine_state_t state, char *line1, char *line2) {
  if (!line1 || !line2)
    return;

  // Fail-safe protection for NaN / INF
  if (isnan(position_mm) || isinf(position_mm))
    position_mm = 0.0f;
  if (isnan(velocity_mm_s) || isinf(velocity_mm_s))
    velocity_mm_s = 0.0f;

  const char *state_str = ihm_state_to_str(state);

  // Format Line 1 strictly to 16 characters ("P:%7.2f mm    ")
  snprintf(line1, 17, "P:%7.2f mm    ", position_mm);

  // Format Line 2 strictly to 16 characters ("V:%5.1f S:%-6s")
  snprintf(line2, 17, "V:%5.1f S:%-6s", velocity_mm_s, state_str);

  // Ensure exact 16-character string termination
  line1[16] = '\0';
  line2[16] = '\0';
}

bool ihm_update_led(ihm_display_t *ihm, machine_state_t state,
                    uint32_t current_time_ms) {
  if (!ihm)
    return false;

  bool prev_state = ihm->led_state;

  switch (state) {
  case MACHINE_STATE_IDLE:
    // Solid ON in IDLE state to signal system readiness
    ihm->led_state = true;
    break;

  case MACHINE_STATE_MOVING:
    // 1 Hz blink (500 ms toggle interval)
    if (current_time_ms - ihm->last_led_toggle_ms >= 500) {
      ihm->led_state = !ihm->led_state;
      ihm->last_led_toggle_ms = current_time_ms;
    }
    break;

  case MACHINE_STATE_EMERGENCY:
    // 5 Hz blink (100 ms toggle interval)
    if (current_time_ms - ihm->last_led_toggle_ms >= 100) {
      ihm->led_state = !ihm->led_state;
      ihm->last_led_toggle_ms = current_time_ms;
    }
    break;

  default:
    ihm->led_state = false;
    break;
  }

#ifndef HOST_TEST
  gpio_set_level((gpio_num_t)ihm->config.led_gpio, ihm->led_state ? 1 : 0);
#endif

  return (ihm->led_state != prev_state);
}

#ifndef HOST_TEST
static esp_err_t pcf8574_write_byte(ihm_display_t *ihm, uint8_t data) {
  if (!ihm || !ihm->i2c_dev_handle)
    return ESP_FAIL;
  i2c_master_dev_handle_t dev = (i2c_master_dev_handle_t)ihm->i2c_dev_handle;
  return i2c_master_transmit(dev, &data, 1, 50);
}

static void lcd_strobe(ihm_display_t *ihm, uint8_t data) {
  pcf8574_write_byte(ihm, data | LCD_EN);
  pcf8574_write_byte(ihm, data & ~LCD_EN);
}

static void lcd_write_nibble(ihm_display_t *ihm, uint8_t nibble, uint8_t rs) {
  uint8_t data = (nibble & 0xF0) | rs | LCD_BL;
  pcf8574_write_byte(ihm, data);
  lcd_strobe(ihm, data);
}

static void lcd_send_cmd(ihm_display_t *ihm, uint8_t cmd) {
  lcd_write_nibble(ihm, cmd & 0xF0, 0);
  lcd_write_nibble(ihm, (cmd << 4) & 0xF0, 0);
}

static void lcd_send_data(ihm_display_t *ihm, uint8_t data) {
  lcd_write_nibble(ihm, data & 0xF0, LCD_RS);
  lcd_write_nibble(ihm, (data << 4) & 0xF0, LCD_RS);
}
#endif

void ihm_init(ihm_display_t *ihm, const ihm_config_t *config) {
  if (!ihm)
    return;

  if (config) {
    ihm->config = *config;
  } else {
    ihm->config.sda_gpio = IHM_DEFAULT_SDA_GPIO;
    ihm->config.scl_gpio = IHM_DEFAULT_SCL_GPIO;
    ihm->config.led_gpio = IHM_DEFAULT_LED_GPIO;
    ihm->config.i2c_address = IHM_DEFAULT_I2C_ADDR;
    ihm->config.i2c_clk_speed = IHM_DEFAULT_I2C_FREQ;
  }

  ihm->is_connected = false;
  ihm->led_state = false;
  ihm->last_led_toggle_ms = 0;
  ihm->last_reconnect_attempt_ms = 0;

#ifndef HOST_TEST
  // Configure GPIO LED Pin
  gpio_config_t io_conf = {
      .pin_bit_mask = (1ULL << ihm->config.led_gpio),
      .mode = GPIO_MODE_OUTPUT,
      .pull_up_en = GPIO_PULLUP_DISABLE,
      .pull_down_en = GPIO_PULLDOWN_ENABLE,
      .intr_type = GPIO_INTR_DISABLE,
  };
  gpio_config(&io_conf);
  gpio_set_level((gpio_num_t)ihm->config.led_gpio, 0);

  // Configure I2C Master Bus using ESP-IDF v5.x driver
  i2c_master_bus_config_t bus_config = {
      .i2c_port = I2C_NUM_0,
      .sda_io_num = (gpio_num_t)ihm->config.sda_gpio,
      .scl_io_num = (gpio_num_t)ihm->config.scl_gpio,
      .clk_source = I2C_CLK_SRC_DEFAULT,
      .glitch_ignore_cnt = 7,
      .flags.enable_internal_pullup = true,
  };

  i2c_master_bus_handle_t bus_handle;
  if (i2c_new_master_bus(&bus_config, &bus_handle) == ESP_OK) {
    ihm->i2c_bus_handle = (void *)bus_handle;

    i2c_device_config_t dev_config = {
        .dev_addr_length = I2C_ADDR_BIT_LEN_7,
        .device_address = ihm->config.i2c_address,
        .scl_speed_hz = ihm->config.i2c_clk_speed,
    };

    i2c_master_dev_handle_t dev_handle;
    if (i2c_master_bus_add_device(bus_handle, &dev_config, &dev_handle) ==
        ESP_OK) {
      ihm->i2c_dev_handle = (void *)dev_handle;

      // Initialize LCD in 4-bit mode (HD44780 init sequence)
      lcd_write_nibble(ihm, 0x30, 0);
      lcd_write_nibble(ihm, 0x30, 0);
      lcd_write_nibble(ihm, 0x30, 0);
      lcd_write_nibble(ihm, 0x20, 0); // Set 4-bit mode

      lcd_send_cmd(ihm, 0x28); // 2 lines, 5x8 font
      lcd_send_cmd(ihm, 0x0C); // Display ON, Cursor OFF
      lcd_send_cmd(ihm, 0x01); // Clear Display
      lcd_send_cmd(ihm, 0x06); // Entry Mode Set

      ihm->is_connected = true;
      ESP_LOGI(TAG, "IHM LCD I2C connected successfully at 0x%02X",
               ihm->config.i2c_address);
    }
  }
#else
  ihm->is_connected = true;
#endif
}

bool ihm_write_lcd(ihm_display_t *ihm, const char *line1, const char *line2) {
  if (!ihm || !line1 || !line2)
    return false;

  if (!ihm->is_connected) {
    return false;
  }

#ifndef HOST_TEST
  // Set cursor to Row 0, Col 0
  lcd_send_cmd(ihm, 0x80);
  for (int i = 0; i < 16 && line1[i] != '\0'; i++) {
    lcd_send_data(ihm, (uint8_t)line1[i]);
  }

  // Set cursor to Row 1, Col 0
  lcd_send_cmd(ihm, 0xC0);
  for (int i = 0; i < 16 && line2[i] != '\0'; i++) {
    lcd_send_data(ihm, (uint8_t)line2[i]);
  }
#endif

  return true;
}

void ihm_update(ihm_display_t *ihm, float position_mm, float velocity_mm_s,
                machine_state_t state, uint32_t current_time_ms) {
  if (!ihm)
    return;

  char line1[17];
  char line2[17];

  ihm_format_lines(position_mm, velocity_mm_s, state, line1, line2);
  ihm_update_led(ihm, state, current_time_ms);
  ihm_write_lcd(ihm, line1, line2);
}
