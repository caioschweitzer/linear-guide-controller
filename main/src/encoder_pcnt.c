#include "encoder_pcnt.h"
#include <stddef.h>

#ifndef HOST_TEST
#include "esp_log.h"

static const char *TAG = "ENCODER_PCNT";

static bool IRAM_ATTR encoder_on_reach(pcnt_unit_handle_t unit, const pcnt_watch_event_data_t *edata, void *user_ctx) {
    encoder_driver_t *driver = (encoder_driver_t *)user_ctx;
    if (!driver) return false;

    portENTER_CRITICAL_ISR(&driver->spinlock);
    if (edata->watch_point_value == ENCODER_WATCH_POINT_MAX) {
        driver->accumulated_overflows++;
        pcnt_unit_clear_count(unit);
    } else if (edata->watch_point_value == ENCODER_WATCH_POINT_MIN) {
        driver->accumulated_overflows--;
        pcnt_unit_clear_count(unit);
    }
    portEXIT_CRITICAL_ISR(&driver->spinlock);

    return false;
}

esp_err_t encoder_init(encoder_driver_t *driver, const encoder_config_t *config) {
    if (!driver) return ESP_ERR_INVALID_ARG;

    encoder_config_t cfg;
    if (config) {
        cfg = *config;
    } else {
        cfg.gpio_a = ENCODER_DEFAULT_GPIO_A;
        cfg.gpio_b = ENCODER_DEFAULT_GPIO_B;
        cfg.max_glitch_ns = ENCODER_DEFAULT_GLITCH_NS;
    }

    // Configure GPIO Pull-Ups
    gpio_pullup_en((gpio_num_t)cfg.gpio_a);
    gpio_pullup_en((gpio_num_t)cfg.gpio_b);

    // Create PCNT Unit
    pcnt_unit_config_t unit_config = {
        .low_limit = -32768,
        .high_limit = 32767,
    };
    esp_err_t ret = pcnt_new_unit(&unit_config, &driver->pcnt_unit);
    if (ret != ESP_OK) return ret;

    // Glitch Filter
    pcnt_glitch_filter_config_t filter_config = {
        .max_glitch_ns = cfg.max_glitch_ns,
    };
    ret = pcnt_unit_set_glitch_filter(driver->pcnt_unit, &filter_config);
    if (ret != ESP_OK) return ret;

    // Channel A Config
    pcnt_chan_config_t chan_a_config = {
        .edge_gpio_num = cfg.gpio_a,
        .level_gpio_num = cfg.gpio_b,
    };
    ret = pcnt_new_channel(driver->pcnt_unit, &chan_a_config, &driver->pcnt_chan_a);
    if (ret != ESP_OK) return ret;

    // Channel B Config
    pcnt_chan_config_t chan_b_config = {
        .edge_gpio_num = cfg.gpio_b,
        .level_gpio_num = cfg.gpio_a,
    };
    ret = pcnt_new_channel(driver->pcnt_unit, &chan_b_config, &driver->pcnt_chan_b);
    if (ret != ESP_OK) return ret;

    // Set Quadrature Actions
    pcnt_channel_set_edge_action(driver->pcnt_chan_a, PCNT_CHANNEL_EDGE_ACTION_INCREASE, PCNT_CHANNEL_EDGE_ACTION_DECREASE);
    pcnt_channel_set_level_action(driver->pcnt_chan_a, PCNT_CHANNEL_LEVEL_ACTION_KEEP, PCNT_CHANNEL_LEVEL_ACTION_INVERSE);

    pcnt_channel_set_edge_action(driver->pcnt_chan_b, PCNT_CHANNEL_EDGE_ACTION_INCREASE, PCNT_CHANNEL_EDGE_ACTION_DECREASE);
    pcnt_channel_set_level_action(driver->pcnt_chan_b, PCNT_CHANNEL_LEVEL_ACTION_INVERSE, PCNT_CHANNEL_LEVEL_ACTION_KEEP);

    // Watch points
    pcnt_unit_add_watch_point(driver->pcnt_unit, ENCODER_WATCH_POINT_MAX);
    pcnt_unit_add_watch_point(driver->pcnt_unit, ENCODER_WATCH_POINT_MIN);

    // Event callbacks
    pcnt_event_callbacks_t cbs = {
        .on_reach = encoder_on_reach,
    };
    ret = pcnt_unit_register_event_callbacks(driver->pcnt_unit, &cbs, driver);
    if (ret != ESP_OK) return ret;

    driver->spinlock = (portMUX_TYPE)portMUX_INITIALIZER_UNLOCKED;
    driver->accumulated_overflows = 0;

    ret = pcnt_unit_enable(driver->pcnt_unit);
    if (ret != ESP_OK) return ret;

    ret = pcnt_unit_clear_count(driver->pcnt_unit);
    if (ret != ESP_OK) return ret;

    ret = pcnt_unit_start(driver->pcnt_unit);
    if (ret != ESP_OK) return ret;

    driver->is_initialized = true;
    ESP_LOGI(TAG, "PCNT Encoder initialized on GPIO %d and %d", cfg.gpio_a, cfg.gpio_b);
    return ESP_OK;
}

esp_err_t encoder_deinit(encoder_driver_t *driver) {
    if (!driver || !driver->is_initialized) return ESP_ERR_INVALID_ARG;

    pcnt_unit_stop(driver->pcnt_unit);
    pcnt_unit_disable(driver->pcnt_unit);
    pcnt_del_channel(driver->pcnt_chan_a);
    pcnt_del_channel(driver->pcnt_chan_b);
    pcnt_del_unit(driver->pcnt_unit);
    driver->is_initialized = false;
    return ESP_OK;
}

esp_err_t encoder_get_count(encoder_driver_t *driver, int32_t *out_count) {
    if (!driver || !driver->is_initialized || !out_count) return ESP_ERR_INVALID_ARG;

    int hw_count = 0;
    esp_err_t ret = pcnt_unit_get_count(driver->pcnt_unit, &hw_count);
    if (ret != ESP_OK) return ret;

    portENTER_CRITICAL(&driver->spinlock);
    int32_t overflow = driver->accumulated_overflows;
    portEXIT_CRITICAL(&driver->spinlock);

    *out_count = (overflow * ENCODER_WATCH_POINT_MAX) + (int32_t)hw_count;
    return ESP_OK;
}

esp_err_t encoder_clear_count(encoder_driver_t *driver) {
    if (!driver || !driver->is_initialized) return ESP_ERR_INVALID_ARG;

    portENTER_CRITICAL(&driver->spinlock);
    driver->accumulated_overflows = 0;
    esp_err_t ret = pcnt_unit_clear_count(driver->pcnt_unit);
    portEXIT_CRITICAL(&driver->spinlock);

    return ret;
}

#else

// Host Simulation Implementation
esp_err_t encoder_init(encoder_driver_t *driver, const encoder_config_t *config) {
    if (!driver) return ESP_ERR_INVALID_ARG;
    driver->accumulated_overflows = 0;
    driver->simulated_raw_count = 0;
    driver->is_initialized = true;
    return ESP_OK;
}

esp_err_t encoder_deinit(encoder_driver_t *driver) {
    if (!driver) return ESP_ERR_INVALID_ARG;
    driver->is_initialized = false;
    return ESP_OK;
}

esp_err_t encoder_get_count(encoder_driver_t *driver, int32_t *out_count) {
    if (!driver || !driver->is_initialized || !out_count) return ESP_ERR_INVALID_ARG;
    *out_count = (driver->accumulated_overflows * ENCODER_WATCH_POINT_MAX) + driver->simulated_raw_count;
    return ESP_OK;
}

esp_err_t encoder_clear_count(encoder_driver_t *driver) {
    if (!driver || !driver->is_initialized) return ESP_ERR_INVALID_ARG;
    driver->accumulated_overflows = 0;
    driver->simulated_raw_count = 0;
    return ESP_OK;
}

void encoder_sim_add_count(encoder_driver_t *driver, int32_t delta) {
    if (!driver || !driver->is_initialized) return;

    driver->simulated_raw_count += delta;

    while (driver->simulated_raw_count >= ENCODER_WATCH_POINT_MAX) {
        driver->accumulated_overflows++;
        driver->simulated_raw_count -= ENCODER_WATCH_POINT_MAX;
    }

    while (driver->simulated_raw_count <= ENCODER_WATCH_POINT_MIN) {
        driver->accumulated_overflows--;
        driver->simulated_raw_count -= ENCODER_WATCH_POINT_MIN;
    }
}

#endif
