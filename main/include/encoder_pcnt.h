#ifndef ENCODER_PCNT_H
#define ENCODER_PCNT_H

#include <stdint.h>
#include <stdbool.h>

#ifndef HOST_TEST
#include "esp_err.h"
#include "driver/pulse_cnt.h"
#include "driver/gpio.h"
#include "freertos/FreeRTOS.h"
#else
// Host simulation types
typedef int esp_err_t;
#define ESP_OK          0
#define ESP_FAIL        -1
#define ESP_ERR_INVALID_ARG -2
#endif

#ifdef __cplusplus
extern "C" {
#endif

#define ENCODER_DEFAULT_GPIO_A     14
#define ENCODER_DEFAULT_GPIO_B     15
#define ENCODER_WATCH_POINT_MAX    30000
#define ENCODER_WATCH_POINT_MIN    (-30000)
#define ENCODER_DEFAULT_GLITCH_NS  1000

typedef struct {
    int gpio_a;
    int gpio_b;
    uint32_t max_glitch_ns;
} encoder_config_t;

typedef struct {
#ifndef HOST_TEST
    pcnt_unit_handle_t pcnt_unit;
    pcnt_channel_handle_t pcnt_chan_a;
    pcnt_channel_handle_t pcnt_chan_b;
    portMUX_TYPE spinlock;
#endif
    volatile int32_t accumulated_overflows;
    bool is_initialized;
#ifdef HOST_TEST
    int32_t simulated_raw_count;
#endif
} encoder_driver_t;

/**
 * @brief Initialize encoder PCNT unit, channels, pull-ups, glitch filter, and watch points.
 * 
 * @param driver Pointer to encoder driver context
 * @param config Pointer to configuration struct (NULL for defaults)
 * @return esp_err_t ESP_OK on success
 */
esp_err_t encoder_init(encoder_driver_t *driver, const encoder_config_t *config);

/**
 * @brief De-initialize encoder driver and free PCNT resources.
 * 
 * @param driver Pointer to encoder driver context
 * @return esp_err_t ESP_OK on success
 */
esp_err_t encoder_deinit(encoder_driver_t *driver);

/**
 * @brief Get current 32-bit accumulated encoder count.
 * 
 * Total Count = (accumulated_overflows * 30000) + hardware_count
 * 
 * @param driver Pointer to encoder driver context
 * @param out_count Pointer to receive 32-bit count
 * @return esp_err_t ESP_OK on success
 */
esp_err_t encoder_get_count(encoder_driver_t *driver, int32_t *out_count);

/**
 * @brief Atomically reset hardware PCNT counter and 32-bit software overflow accumulator to zero.
 * 
 * @param driver Pointer to encoder driver context
 * @return esp_err_t ESP_OK on success
 */
esp_err_t encoder_clear_count(encoder_driver_t *driver);

#ifdef HOST_TEST
/**
 * @brief Host simulation helper: inject count changes into driver context.
 * 
 * @param driver Pointer to encoder driver context
 * @param delta Incremental pulse count (can be positive or negative)
 */
void encoder_sim_add_count(encoder_driver_t *driver, int32_t delta);
#endif

#ifdef __cplusplus
}
#endif

#endif // ENCODER_PCNT_H
