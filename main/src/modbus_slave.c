#include "modbus_slave.h"
#include "gpio_safety.h"
#include "shared_data.h"
#include <math.h>
#include <string.h>

#ifndef HOST_TEST
#include "driver/gpio.h"
#include "driver/spi_master.h"
#include "esp_eth.h"
#include "esp_eth_mac_w5500.h"
#include "esp_eth_phy_w5500.h"
#include "esp_event.h"
#include "esp_log.h"
#include "esp_netif.h"
#include "mbcontroller.h"

#define MB_TCP_PORT_NUMBER 502
#define MB_SLAVE_ADDR 1

#define ETH_SPI_HOST SPI2_HOST
#define ETH_SPI_SCLK_GPIO 18
#define ETH_SPI_MOSI_GPIO 8
#define ETH_SPI_MISO_GPIO 10
#define ETH_SPI_CS_GPIO 21
#define ETH_SPI_RST_GPIO 9
#define ETH_SPI_INT_GPIO 17
#define ETH_SPI_CLOCK_MHZ 5

// Static IP configuration (disables DHCP client)
#define STATIC_IP "192.168.1.100"
#define STATIC_NETMASK "255.255.255.0"
#define STATIC_GW "192.168.1.1"
#endif

// Internal buffers mapped to Modbus stack
holding_reg_params_t g_modbus_holding_reg = {0};
input_reg_params_t g_modbus_input_reg = {0};
discrete_reg_params_t g_modbus_discrete_reg = {0};
coil_reg_params_t g_modbus_coil_reg = {0};

static void *s_mbc_handle = NULL;

// Helper to convert float to 2 x uint16 (Big-Endian IEEE 754)
static void float_to_registers(float src, uint16_t *hi, uint16_t *lo) {
  uint32_t val;
  memcpy(&val, &src, sizeof(float));
  *hi = (uint16_t)((val >> 16) & 0xFFFF);
  *lo = (uint16_t)(val & 0xFFFF);
}

// Helper to convert 2 x uint16 (Big-Endian IEEE 754) to float
static float registers_to_float(uint16_t hi, uint16_t lo) {
  uint32_t val = ((uint32_t)hi << 16) | lo;
  float result;
  memcpy(&result, &val, sizeof(float));
  return result;
}

#ifndef HOST_TEST
static void eth_event_handler(void *arg, esp_event_base_t event_base,
                              int32_t event_id, void *event_data) {
  if (event_base == ETH_EVENT) {
    if (event_id == ETHERNET_EVENT_CONNECTED) {
      ESP_LOGI("ETH", "Ethernet Link Up");
    } else if (event_id == ETHERNET_EVENT_DISCONNECTED) {
      ESP_LOGI("ETH", "Ethernet Link Down");
    }
  } else if (event_base == IP_EVENT) {
    if (event_id == IP_EVENT_ETH_GOT_IP) {
      ip_event_got_ip_t *event = (ip_event_got_ip_t *)event_data;
      ESP_LOGI("ETH",
               "Static IP assigned: " IPSTR " (Netmask: " IPSTR ", GW: " IPSTR
               ")",
               IP2STR(&event->ip_info.ip), IP2STR(&event->ip_info.netmask),
               IP2STR(&event->ip_info.gw));
    }
  }
}
#endif

esp_err_t modbus_slave_init(void) {
  // Populate default holding register values
  float_to_registers(0.0f, &g_modbus_holding_reg.setpoint_hi,
                     &g_modbus_holding_reg.setpoint_lo);
  g_modbus_holding_reg.command = CMD_NONE;
  float_to_registers(2.0f, &g_modbus_holding_reg.kp_hi,
                     &g_modbus_holding_reg.kp_lo);
  float_to_registers(0.5f, &g_modbus_holding_reg.ki_hi,
                     &g_modbus_holding_reg.ki_lo);
  float_to_registers(0.05f, &g_modbus_holding_reg.kd_hi,
                     &g_modbus_holding_reg.kd_lo);
  g_modbus_holding_reg.burst_read_index = 0;
#ifndef HOST_TEST

  // 1. Re-enable console ASCII logging on UART0 / USB-C
  esp_log_level_set("*", ESP_LOG_INFO);

  // 2. Hardware Reset WIZ550io and allow 500ms for internal MCU auto-config
  gpio_config_t rst_gpio_conf = {
      .pin_bit_mask = (1ULL << ETH_SPI_RST_GPIO),
      .mode = GPIO_MODE_OUTPUT,
      .pull_up_en = GPIO_PULLUP_DISABLE,
      .pull_down_en = GPIO_PULLDOWN_DISABLE,
      .intr_type = GPIO_INTR_DISABLE,
  };
  gpio_config(&rst_gpio_conf);
  gpio_set_level(ETH_SPI_RST_GPIO, 0); // Assert reset (LOW)
  vTaskDelay(pdMS_TO_TICKS(50));
  gpio_set_level(ETH_SPI_RST_GPIO, 1); // De-assert reset (HIGH)
  vTaskDelay(pdMS_TO_TICKS(500));      // Wait 500ms for WIZ550io RDY

  // 3. Initialize SPI Bus for WIZ550io (W5500)
  spi_bus_config_t buscfg = {
      .miso_io_num = ETH_SPI_MISO_GPIO,
      .mosi_io_num = ETH_SPI_MOSI_GPIO,
      .sclk_io_num = ETH_SPI_SCLK_GPIO,
      .quadwp_io_num = -1,
      .quadhd_io_num = -1,
  };
  esp_err_t err = spi_bus_initialize(ETH_SPI_HOST, &buscfg, SPI_DMA_CH_AUTO);
  // 4. Configure W5500 MAC/PHY Driver
  spi_device_interface_config_t devcfg = {
      .command_bits = 16,
      .address_bits = 8,
      .mode = 0,
      .clock_speed_hz = ETH_SPI_CLOCK_MHZ * 1000 * 1000,
      .spics_io_num = ETH_SPI_CS_GPIO,
      .queue_size = 20,
  };

  eth_w5500_config_t w5500_config =
      ETH_W5500_DEFAULT_CONFIG(ETH_SPI_HOST, &devcfg);
  w5500_config.base.int_gpio_num = ETH_SPI_INT_GPIO;

  eth_mac_config_t mac_config = ETH_MAC_DEFAULT_CONFIG();
  esp_eth_mac_t *mac = esp_eth_mac_new_w5500(&w5500_config, &mac_config);

  eth_phy_config_t phy_config = ETH_PHY_DEFAULT_CONFIG();
  phy_config.reset_gpio_num = -1; // Reset managed manually above
  esp_eth_phy_t *phy = esp_eth_phy_new_w5500(&phy_config);

  esp_eth_config_t eth_config = ETH_DEFAULT_CONFIG(mac, phy);
  esp_eth_handle_t eth_handle = NULL;
  err = esp_eth_driver_install(&eth_config, &eth_handle);
  if (err != ESP_OK)
    return err;

  // 4. Attach Ethernet to esp_netif TCP/IP stack
  esp_netif_init();
  esp_event_loop_create_default();
  esp_netif_config_t netif_cfg = ESP_NETIF_DEFAULT_ETH();
  esp_netif_t *eth_netif = esp_netif_new(&netif_cfg);

  esp_eth_netif_glue_handle_t glue = esp_eth_new_netif_glue(eth_handle);
  err = esp_netif_attach(eth_netif, glue);
  if (err != ESP_OK)
    return err;

  // 4a. Stop DHCP client and apply static IP configuration
  err = esp_netif_dhcpc_stop(eth_netif);
  if (err != ESP_OK && err != ESP_ERR_ESP_NETIF_DHCP_ALREADY_STOPPED) {
    ESP_LOGE("ETH", "Failed to stop DHCP client: %s", esp_err_to_name(err));
    return err;
  }
  esp_netif_ip_info_t ip_info;
  memset(&ip_info, 0, sizeof(ip_info));
  ip_info.ip.addr = esp_ip4addr_aton(STATIC_IP);
  ip_info.netmask.addr = esp_ip4addr_aton(STATIC_NETMASK);
  ip_info.gw.addr = esp_ip4addr_aton(STATIC_GW);
  err = esp_netif_set_ip_info(eth_netif, &ip_info);
  if (err != ESP_OK) {
    ESP_LOGE("ETH", "Failed to set static IP: %s", esp_err_to_name(err));
    return err;
  }
  ESP_LOGI("ETH", "Static IP configured: %s / %s (GW: %s)", STATIC_IP,
           STATIC_NETMASK, STATIC_GW);

  esp_event_handler_instance_register(ETH_EVENT, ESP_EVENT_ANY_ID,
                                      &eth_event_handler, NULL, NULL);
  esp_event_handler_instance_register(IP_EVENT, IP_EVENT_ETH_GOT_IP,
                                      &eth_event_handler, NULL, NULL);

  err = esp_eth_start(eth_handle);
  if (err != ESP_OK)
    return err;

  // 5. Initialize Modbus TCP Slave Controller
  mb_communication_info_t comm_info = {.tcp_opts = {.port = MB_TCP_PORT_NUMBER,
                                                    .mode = MB_TCP,
                                                    .addr_type = MB_IPV4,
                                                    .ip_addr_table = NULL,
                                                    .ip_netif_ptr = eth_netif,
                                                    .uid = MB_SLAVE_ADDR}};

  err = mbc_slave_create_tcp(&comm_info, &s_mbc_handle);
  if (err != ESP_OK)
    return err;

  // 6. Register holding area
  mb_register_area_descriptor_t reg_area_holding = {
      .type = MB_PARAM_HOLDING,
      .start_offset = HOLDING_REG_START_ADDR,
      .address = (void *)&g_modbus_holding_reg,
      .size = sizeof(g_modbus_holding_reg)};
  err = mbc_slave_set_descriptor(s_mbc_handle, reg_area_holding);
  if (err != ESP_OK)
    return err;

  // 7. Register input area
  mb_register_area_descriptor_t reg_area_input = {
      .type = MB_PARAM_INPUT,
      .start_offset = INPUT_REG_START_ADDR,
      .address = (void *)&g_modbus_input_reg,
      .size = sizeof(g_modbus_input_reg)};
  err = mbc_slave_set_descriptor(s_mbc_handle, reg_area_input);
  if (err != ESP_OK)
    return err;

  // 8. Register discrete input area
  mb_register_area_descriptor_t reg_area_discrete = {
      .type = MB_PARAM_DISCRETE,
      .start_offset = DISCRETE_REG_START_ADDR,
      .address = (void *)&g_modbus_discrete_reg,
      .size = sizeof(g_modbus_discrete_reg)};
  err = mbc_slave_set_descriptor(s_mbc_handle, reg_area_discrete);
  if (err != ESP_OK)
    return err;

  // 9. Register coil area
  mb_register_area_descriptor_t reg_area_coil = {
      .type = MB_PARAM_COIL,
      .start_offset = COIL_REG_START_ADDR,
      .address = (void *)&g_modbus_coil_reg,
      .size = sizeof(g_modbus_coil_reg)};
  err = mbc_slave_set_descriptor(s_mbc_handle, reg_area_coil);
  if (err != ESP_OK)
    return err;

  // 10. Start Modbus slave
  err = mbc_slave_start(s_mbc_handle);
  return err;
#else
  return ESP_OK;
#endif
}

void modbus_slave_sync_buffers(void) {
  // Process Command Register if set
  uint16_t cmd = g_modbus_holding_reg.command;
  if (cmd != CMD_NONE) {
    g_modbus_holding_reg.command = CMD_NONE; // Reset command register after reading
    if (cmd == CMD_START) {
      shared_data_request_state_change(MACHINE_STATE_MOVING);
    } else if (cmd == CMD_STOP) {
      shared_data_request_state_change(MACHINE_STATE_IDLE);
    } else if (cmd == CMD_RESET) {
      shared_data_request_state_change(MACHINE_STATE_IDLE);
    } else if (cmd == CMD_HOME) {
      shared_data_request_state_change(MACHINE_STATE_HOMING);
    } else if (cmd == CMD_OPEN_LOOP_TEST) {
      shared_data_request_state_change(MACHINE_STATE_OPEN_LOOP_TEST);
    } else if (cmd == CMD_SIMULATE_EMERGENCY) {
      gpio_safety_trigger_emergency_software();
    }
  }

  // Process Coil Triggers (Bit 1: Remote Emergency, Bit 2: Remote Start)
  if (g_modbus_coil_reg.coils & (1 << 1)) {
    g_modbus_coil_reg.coils &= ~(1 << 1); // Clear remote emergency trigger coil
    gpio_safety_trigger_emergency_software();
  }
  if (g_modbus_coil_reg.coils & (1 << 2)) {
    g_modbus_coil_reg.coils &= ~(1 << 2); // Clear remote start trigger coil
    shared_data_request_state_change(MACHINE_STATE_MOVING);
  }

  if (shared_data_lock(pdMS_TO_TICKS(10))) {
    // Read setpoint from Modbus holding registers
    g_system_data.position_setpoint = registers_to_float(
        g_modbus_holding_reg.setpoint_hi, g_modbus_holding_reg.setpoint_lo);

    // Synchronize PID gains with Modbus holding registers
    float mb_kp = registers_to_float(g_modbus_holding_reg.kp_hi,
                                     g_modbus_holding_reg.kp_lo);
    float mb_ki = registers_to_float(g_modbus_holding_reg.ki_hi,
                                     g_modbus_holding_reg.ki_lo);
    float mb_kd = registers_to_float(g_modbus_holding_reg.kd_hi,
                                     g_modbus_holding_reg.kd_lo);

    if (!isnan(mb_kp) && !isinf(mb_kp) && mb_kp >= 0.0f)
      g_system_data.kp = mb_kp;
    if (!isnan(mb_ki) && !isinf(mb_ki) && mb_ki >= 0.0f)
      g_system_data.ki = mb_ki;
    if (!isnan(mb_kd) && !isinf(mb_kd) && mb_kd >= 0.0f)
      g_system_data.kd = mb_kd;

    float_to_registers(g_system_data.kp, &g_modbus_holding_reg.kp_hi,
                       &g_modbus_holding_reg.kp_lo);
    float_to_registers(g_system_data.ki, &g_modbus_holding_reg.ki_hi,
                       &g_modbus_holding_reg.ki_lo);
    float_to_registers(g_system_data.kd, &g_modbus_holding_reg.kd_hi,
                       &g_modbus_holding_reg.kd_lo);

    // Write current position, velocity, duty cycle, state to Modbus input registers
    float_to_registers(g_system_data.current_position,
                       &g_modbus_input_reg.pos_hi,
                       &g_modbus_input_reg.pos_lo);
    float_to_registers(g_system_data.current_velocity,
                       &g_modbus_input_reg.vel_hi,
                       &g_modbus_input_reg.vel_lo);
    float_to_registers(g_system_data.duty_cycle,
                       &g_modbus_input_reg.duty_hi,
                       &g_modbus_input_reg.duty_lo);
    g_modbus_input_reg.state = (uint16_t)shared_data_get_state();

    // Burst Buffer synchronization
    g_burst_buffer.read_index = g_modbus_holding_reg.burst_read_index;
    g_modbus_input_reg.burst_status = g_burst_buffer.status;
    g_modbus_input_reg.burst_sample_count = g_burst_buffer.sample_count;

    uint16_t r_idx = g_modbus_holding_reg.burst_read_index;
    if (r_idx < g_burst_buffer.sample_count && r_idx < BURST_BUFFER_MAX_SAMPLES) {
      uint32_t t_ms = g_burst_buffer.samples[r_idx].time_ms;
      g_modbus_input_reg.sample_time_hi = (uint16_t)((t_ms >> 16) & 0xFFFF);
      g_modbus_input_reg.sample_time_lo = (uint16_t)(t_ms & 0xFFFF);
      float_to_registers(g_burst_buffer.samples[r_idx].position,
                         &g_modbus_input_reg.sample_pos_hi,
                         &g_modbus_input_reg.sample_pos_lo);
      float_to_registers(g_burst_buffer.samples[r_idx].velocity,
                         &g_modbus_input_reg.sample_vel_hi,
                         &g_modbus_input_reg.sample_vel_lo);
    } else {
      g_modbus_input_reg.sample_time_hi = 0;
      g_modbus_input_reg.sample_time_lo = 0;
      float_to_registers(0.0f, &g_modbus_input_reg.sample_pos_hi,
                         &g_modbus_input_reg.sample_pos_lo);
      float_to_registers(0.0f, &g_modbus_input_reg.sample_vel_hi,
                         &g_modbus_input_reg.sample_vel_lo);
    }

    // Update Discrete Inputs register (Bit 0: E-Stop, Bit 1: Start, Bit 2: Safety Enable, Bit 3: Home Sensor)
    uint8_t discrete_bits = 0;
    if (g_system_data.button_estop)
      discrete_bits |= (1 << 0);
    if (g_system_data.button_start)
      discrete_bits |= (1 << 1);
    if (g_system_data.safety_enable)
      discrete_bits |= (1 << 2);
#ifndef HOST_TEST
    if (gpio_get_level(GPIO_HOME_PIN) == 0) // 0V = Magnet detected (1: Active)
      discrete_bits |= (1 << 3);
#endif
    g_modbus_discrete_reg.discrete_inputs = discrete_bits;

    // Reflect LED status coil (Bit 0)
    g_system_data.led_status = (g_modbus_coil_reg.coils & (1 << 0)) != 0;

    shared_data_unlock();
  }
}

#ifndef HOST_TEST
static void modbus_slave_task(void *pvParameters) {
  (void)pvParameters;

  while (1) {
    if (s_mbc_handle) {
      mb_event_group_t event = mbc_slave_check_event(
          s_mbc_handle,
          MB_EVENT_HOLDING_REG_WR | MB_EVENT_INPUT_REG_RD | MB_EVENT_COILS_WR);
      (void)event;
    }

    modbus_slave_sync_buffers();

    vTaskDelay(pdMS_TO_TICKS(20));
  }
}
#endif

void modbus_slave_start_task(void) {
#ifndef HOST_TEST
  xTaskCreatePinnedToCore(modbus_slave_task, "ModbusSlaveTask", 4096, NULL, 4,
                          NULL,
                          0 // Core 0
  );
#endif
}
