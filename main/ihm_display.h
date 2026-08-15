#ifndef IHM_DISPLAY_H
#define IHM_DISPLAY_H

#include <stdbool.h>
#include <stdint.h>
#include "shared_data.h"

#ifdef __cplusplus
extern "C" {
#endif

#define IHM_DEFAULT_SDA_GPIO    1
#define IHM_DEFAULT_SCL_GPIO    2
#define IHM_DEFAULT_LED_GPIO    7
#define IHM_DEFAULT_I2C_ADDR    0x27
#define IHM_DEFAULT_I2C_FREQ    100000

typedef struct {
    int sda_gpio;
    int scl_gpio;
    int led_gpio;
    uint8_t i2c_address;
    uint32_t i2c_clk_speed;
} ihm_config_t;

typedef struct {
    ihm_config_t config;
    bool is_connected;
    bool led_state;
    uint32_t last_led_toggle_ms;
    uint32_t last_reconnect_attempt_ms;
#ifndef HOST_TEST
    void *i2c_bus_handle;
    void *i2c_dev_handle;
#endif
} ihm_display_t;

/**
 * @brief Initialize IHM Display manager and hardware pins (I2C Master & GPIO LED).
 * 
 * @param ihm Pointer to ihm_display_t context
 * @param config Pointer to configuration struct (NULL for defaults)
 */
void ihm_init(ihm_display_t *ihm, const ihm_config_t *config);

/**
 * @brief Convert machine_state_t enum to concise 6-character string representation.
 * 
 * @param state Machine state enum
 * @return const char* String representation ("IDLE  ", "MOVING", "EMERG ")
 */
const char* ihm_state_to_str(machine_state_t state);

/**
 * @brief Strictly format 16-character Line 1 and Line 2 buffers for HD44780 16x2 LCD.
 * 
 * Line 1 format: "P:%7.2f mm   " (16 chars)
 * Line 2 format: "V:%5.1f S:%-6s" (16 chars)
 * 
 * @param position_mm Measured position in mm
 * @param velocity_mm_s Measured velocity in mm/s
 * @param state Machine state enum
 * @param line1 Buffer for Line 1 (must be at least 17 bytes)
 * @param line2 Buffer for Line 2 (must be at least 17 bytes)
 */
void ihm_format_lines(float position_mm, float velocity_mm_s, machine_state_t state, char *line1, char *line2);

/**
 * @brief Non-blocking GPIO status LED logic.
 * 
 * IDLE: Solid ON / OFF
 * MOVING: 1 Hz blink (500 ms toggle)
 * EMERGENCY: 5 Hz blink (100 ms toggle)
 * 
 * @param ihm Pointer to ihm_display_t context
 * @param state Machine state enum
 * @param current_time_ms Current time in milliseconds
 * @return bool True if LED state toggled/changed
 */
bool ihm_update_led(ihm_display_t *ihm, machine_state_t state, uint32_t current_time_ms);

/**
 * @brief Update LCD display lines over PCF8574 I2C.
 * 
 * @param ihm Pointer to ihm_display_t context
 * @param line1 16-character string for line 1
 * @param line2 16-character string for line 2
 * @return bool True if I2C transmission succeeded, False if NACK/Timeout
 */
bool ihm_write_lcd(ihm_display_t *ihm, const char *line1, const char *line2);

/**
 * @brief Periodic IHM update routine (called from Task loop).
 * 
 * @param ihm Pointer to ihm_display_t context
 * @param position_mm Current position
 * @param velocity_mm_s Current velocity
 * @param state Current machine state
 * @param current_time_ms Current timestamp in ms
 */
void ihm_update(ihm_display_t *ihm, float position_mm, float velocity_mm_s, machine_state_t state, uint32_t current_time_ms);

#ifdef __cplusplus
}
#endif

#endif // IHM_DISPLAY_H
