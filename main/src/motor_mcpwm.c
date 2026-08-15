#include "motor_mcpwm.h"
#include <stddef.h>
#include <math.h>

#ifndef HOST_TEST
#include "esp_log.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

static const char *TAG = "MOTOR_MCPWM";

esp_err_t motor_init(motor_driver_t *driver, const motor_config_t *config) {
    if (!driver) return ESP_ERR_INVALID_ARG;

    motor_config_t cfg;
    if (config) {
        cfg = *config;
    } else {
        cfg.gpio_pwm = MOTOR_DEFAULT_GPIO_PWM;
        cfg.gpio_in1 = MOTOR_DEFAULT_GPIO_IN1;
        cfg.gpio_in2 = MOTOR_DEFAULT_GPIO_IN2;
        cfg.pwm_freq_hz = MOTOR_PWM_FREQ_HZ;
    }

    // Configure GPIOs IN1 & IN2
    gpio_config_t io_conf = {
        .pin_bit_mask = (1ULL << cfg.gpio_in1) | (1ULL << cfg.gpio_in2),
        .mode = GPIO_MODE_OUTPUT,
        .pull_down_en = GPIO_PULLDOWN_DISABLE,
        .pull_up_en = GPIO_PULLUP_DISABLE,
        .intr_type = GPIO_INTR_DISABLE,
    };
    esp_err_t ret = gpio_config(&io_conf);
    if (ret != ESP_OK) return ret;

    gpio_set_level((gpio_num_t)cfg.gpio_in1, 0);
    gpio_set_level((gpio_num_t)cfg.gpio_in2, 0);

    // MCPWM Timer
    uint32_t period_ticks = MOTOR_PWM_RESOLUTION_HZ / cfg.pwm_freq_hz;
    mcpwm_timer_config_t timer_conf = {
        .group_id = 0,
        .clk_src = MCPWM_TIMER_CLK_SRC_DEFAULT,
        .resolution_hz = MOTOR_PWM_RESOLUTION_HZ,
        .period_ticks = period_ticks,
        .count_mode = MCPWM_TIMER_COUNT_MODE_UP,
    };
    ret = mcpwm_new_timer(&timer_conf, &driver->timer);
    if (ret != ESP_OK) return ret;

    // MCPWM Operator
    mcpwm_operator_config_t oper_conf = {
        .group_id = 0,
    };
    ret = mcpwm_new_operator(&oper_conf, &driver->oper);
    if (ret != ESP_OK) return ret;

    ret = mcpwm_operator_connect_timer(driver->oper, driver->timer);
    if (ret != ESP_OK) return ret;

    // MCPWM Comparator
    mcpwm_comparator_config_t cmpr_conf = {
        .flags = {
            .update_cmp_on_tez = true,
        },
    };
    ret = mcpwm_new_comparator(driver->oper, &cmpr_conf, &driver->cmpr);
    if (ret != ESP_OK) return ret;

    mcpwm_comparator_set_compare_value(driver->cmpr, 0);

    // MCPWM Generator
    mcpwm_generator_config_t gen_conf = {
        .gen_gpio_num = cfg.gpio_pwm,
    };
    ret = mcpwm_new_generator(driver->oper, &gen_conf, &driver->gen);
    if (ret != ESP_OK) return ret;

    mcpwm_generator_set_action_on_timer_event(driver->gen, MCPWM_GEN_TIMER_EVENT_ACTION(MCPWM_TIMER_DIRECTION_UP, MCPWM_TIMER_EVENT_EMPTY, MCPWM_GEN_ACTION_HIGH));
    mcpwm_generator_set_action_on_compare_event(driver->gen, MCPWM_GEN_COMPARE_EVENT_ACTION(MCPWM_TIMER_DIRECTION_UP, driver->cmpr, MCPWM_GEN_ACTION_LOW));

    ret = mcpwm_timer_enable(driver->timer);
    if (ret != ESP_OK) return ret;

    ret = mcpwm_timer_start_stop(driver->timer, MCPWM_TIMER_START_NO_STOP);
    if (ret != ESP_OK) return ret;

    driver->gpio_in1 = cfg.gpio_in1;
    driver->gpio_in2 = cfg.gpio_in2;
    driver->current_effort = 0.0f;
    driver->last_direction = 0;
    driver->is_initialized = true;

    ESP_LOGI(TAG, "MCPWM Motor initialized on PWM GPIO %d, IN1 %d, IN2 %d at %lu Hz", cfg.gpio_pwm, cfg.gpio_in1, cfg.gpio_in2, (unsigned long)cfg.pwm_freq_hz);
    return ESP_OK;
}

esp_err_t motor_deinit(motor_driver_t *driver) {
    if (!driver || !driver->is_initialized) return ESP_ERR_INVALID_ARG;

    motor_brake(driver);
    mcpwm_timer_start_stop(driver->timer, MCPWM_TIMER_STOP_EMPTY);
    mcpwm_timer_disable(driver->timer);
    mcpwm_del_generator(driver->gen);
    mcpwm_del_comparator(driver->cmpr);
    mcpwm_del_operator(driver->oper);
    mcpwm_del_timer(driver->timer);
    driver->is_initialized = false;
    return ESP_OK;
}

esp_err_t motor_brake(motor_driver_t *driver) {
    if (!driver || !driver->is_initialized) return ESP_ERR_INVALID_ARG;

    mcpwm_comparator_set_compare_value(driver->cmpr, 0);
    gpio_set_level((gpio_num_t)driver->gpio_in1, 0);
    gpio_set_level((gpio_num_t)driver->gpio_in2, 0);
    driver->last_direction = 0;
    driver->current_effort = 0.0f;
    return ESP_OK;
}

esp_err_t motor_set_effort(motor_driver_t *driver, float effort_percent) {
    if (!driver || !driver->is_initialized) return ESP_ERR_INVALID_ARG;

    // Fail-safe protection against NaN and INF
    if (isnan(effort_percent) || isinf(effort_percent)) {
        return motor_brake(driver);
    }

    // Effort Clamping
    if (effort_percent > 100.0f) effort_percent = 100.0f;
    if (effort_percent < -100.0f) effort_percent = -100.0f;

    int target_dir = 0;
    if (effort_percent > 0.0f) target_dir = 1;
    else if (effort_percent < 0.0f) target_dir = -1;

    // Shoot-through / Back-EMF Direction Reversal Protection
    if (driver->last_direction != 0 && target_dir != 0 && driver->last_direction != target_dir) {
        motor_brake(driver);
        vTaskDelay(pdMS_TO_TICKS(1)); // Brief 1ms brake transition
    }

    float abs_effort = fabsf(effort_percent);
    uint32_t cmp_val = (uint32_t)((abs_effort / 100.0f) * MOTOR_PWM_PERIOD_TICKS);
    mcpwm_comparator_set_compare_value(driver->cmpr, cmp_val);

    if (target_dir == 1) {
        gpio_set_level((gpio_num_t)driver->gpio_in1, 1);
        gpio_set_level((gpio_num_t)driver->gpio_in2, 0);
    } else if (target_dir == -1) {
        gpio_set_level((gpio_num_t)driver->gpio_in1, 0);
        gpio_set_level((gpio_num_t)driver->gpio_in2, 1);
    } else {
        gpio_set_level((gpio_num_t)driver->gpio_in1, 0);
        gpio_set_level((gpio_num_t)driver->gpio_in2, 0);
    }

    driver->last_direction = target_dir;
    driver->current_effort = effort_percent;
    return ESP_OK;
}

#else

// Host Simulation Implementation
esp_err_t motor_init(motor_driver_t *driver, const motor_config_t *config) {
    if (!driver) return ESP_ERR_INVALID_ARG;
    driver->sim_in1 = 0;
    driver->sim_in2 = 0;
    driver->sim_duty_percent = 0.0f;
    driver->sim_brake_transitions = 0;
    driver->current_effort = 0.0f;
    driver->last_direction = 0;
    driver->is_initialized = true;
    return ESP_OK;
}

esp_err_t motor_deinit(motor_driver_t *driver) {
    if (!driver) return ESP_ERR_INVALID_ARG;
    driver->is_initialized = false;
    return ESP_OK;
}

esp_err_t motor_brake(motor_driver_t *driver) {
    if (!driver || !driver->is_initialized) return ESP_ERR_INVALID_ARG;
    driver->sim_in1 = 0;
    driver->sim_in2 = 0;
    driver->sim_duty_percent = 0.0f;
    driver->last_direction = 0;
    driver->current_effort = 0.0f;
    return ESP_OK;
}

esp_err_t motor_set_effort(motor_driver_t *driver, float effort_percent) {
    if (!driver || !driver->is_initialized) return ESP_ERR_INVALID_ARG;

    // Fail-safe for NaN / INF
    if (isnan(effort_percent) || isinf(effort_percent)) {
        return motor_brake(driver);
    }

    // Clamping
    if (effort_percent > 100.0f) effort_percent = 100.0f;
    if (effort_percent < -100.0f) effort_percent = -100.0f;

    int target_dir = 0;
    if (effort_percent > 0.0f) target_dir = 1;
    else if (effort_percent < 0.0f) target_dir = -1;

    // Direction reversal protection
    if (driver->last_direction != 0 && target_dir != 0 && driver->last_direction != target_dir) {
        motor_brake(driver);
        driver->sim_brake_transitions++;
    }

    if (target_dir == 1) {
        driver->sim_in1 = 1;
        driver->sim_in2 = 0;
        driver->sim_duty_percent = effort_percent;
    } else if (target_dir == -1) {
        driver->sim_in1 = 0;
        driver->sim_in2 = 1;
        driver->sim_duty_percent = fabsf(effort_percent);
    } else {
        driver->sim_in1 = 0;
        driver->sim_in2 = 0;
        driver->sim_duty_percent = 0.0f;
    }

    driver->last_direction = target_dir;
    driver->current_effort = effort_percent;
    return ESP_OK;
}

#endif
