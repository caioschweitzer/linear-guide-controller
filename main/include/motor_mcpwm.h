#ifndef MOTOR_MCPWM_H
#define MOTOR_MCPWM_H

#include <stdint.h>
#include <stdbool.h>

#ifndef HOST_TEST
#include "esp_err.h"
#include "driver/mcpwm_prelude.h"
#include "driver/gpio.h"
#else
// Host simulation types
typedef int esp_err_t;
#define ESP_OK              0
#define ESP_FAIL            -1
#define ESP_ERR_INVALID_ARG -2
#endif

#ifdef __cplusplus
extern "C" {
#endif

#define MOTOR_DEFAULT_GPIO_PWM    4
#define MOTOR_DEFAULT_GPIO_IN1    5
#define MOTOR_DEFAULT_GPIO_IN2    6
#define MOTOR_PWM_FREQ_HZ         20000
#define MOTOR_PWM_RESOLUTION_HZ   10000000
#define MOTOR_PWM_PERIOD_TICKS    (MOTOR_PWM_RESOLUTION_HZ / MOTOR_PWM_FREQ_HZ)

typedef struct {
    int gpio_pwm;
    int gpio_in1;
    int gpio_in2;
    uint32_t pwm_freq_hz;
} motor_config_t;

typedef struct {
#ifndef HOST_TEST
    mcpwm_timer_handle_t timer;
    mcpwm_oper_handle_t oper;
    mcpwm_cmpr_handle_t cmpr;
    mcpwm_gen_handle_t gen;
    int gpio_in1;
    int gpio_in2;
#endif
    float current_effort;
    int last_direction; // +1: forward, -1: reverse, 0: brake
    bool is_initialized;

#ifdef HOST_TEST
    int sim_in1;
    int sim_in2;
    float sim_duty_percent;
    int sim_brake_transitions;
#endif
} motor_driver_t;

/**
 * @brief Initialize motor driver, MCPWM timer/operator/comparator/generator, and direction GPIOs.
 * 
 * @param driver Pointer to motor driver context
 * @param config Pointer to configuration struct (NULL for defaults)
 * @return esp_err_t ESP_OK on success
 */
esp_err_t motor_init(motor_driver_t *driver, const motor_config_t *config);

/**
 * @brief De-initialize motor driver and free MCPWM/GPIO resources.
 * 
 * @param driver Pointer to motor driver context
 * @return esp_err_t ESP_OK on success
 */
esp_err_t motor_deinit(motor_driver_t *driver);

/**
 * @brief Set motor effort percent (-100.0% to +100.0%).
 * 
 * Automatically handles direction pins (IN1/IN2), PWM duty cycle on GPIO 4,
 * effort clamping, NaN/INF protection, and short brake transitions on direction reversals.
 * 
 * @param driver Pointer to motor driver context
 * @param effort_percent Input effort in percentage (-100.0f to +100.0f)
 * @return esp_err_t ESP_OK on success
 */
esp_err_t motor_set_effort(motor_driver_t *driver, float effort_percent);

/**
 * @brief Apply passive short brake (IN1=0, IN2=0, PWM duty=0%).
 * 
 * @param driver Pointer to motor driver context
 * @return esp_err_t ESP_OK on success
 */
esp_err_t motor_brake(motor_driver_t *driver);

#ifdef __cplusplus
}
#endif

#endif // MOTOR_MCPWM_H
