#include "gpio_safety.h"
#include <stddef.h>

#ifndef HOST_TEST
#include "driver/gpio.h"
#include "esp_attr.h"
#include "esp_log.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#else
#define IRAM_ATTR
static int s_simulated_emergency_gpio = 0;
#endif

static TaskHandle_t s_control_task_handle = NULL;

void gpio_safety_set_control_task_handle(TaskHandle_t task_handle) {
    s_control_task_handle = task_handle;
}

// Emergency ISR running directly from IRAM for minimum latency
static void IRAM_ATTR gpio12_emergency_isr(void *arg) {
#ifndef HOST_TEST
    // Glitch rejection: Ignore transient crosstalk pulses (e.g. from GPIO 13 toggling)
    // Only enforce hardware level check if triggered by physical interrupt (arg != NULL)
    if (arg != NULL && gpio_get_level(GPIO_EMERGENCY_PIN) == 0) {
        return;
    }
    // 1. Immediate Physical Hardware Cutoff (Disable motor enable / PWM outputs)
    gpio_set_level(GPIO_NUM_13, 0);
#else
    (void)arg;
    s_simulated_emergency_gpio = 1;
#endif

    // 2. Atomic state transition to EMERGENCY (No mutex lock inside ISR)
    shared_data_set_state_atomic(MACHINE_STATE_EMERGENCY);

#ifndef HOST_TEST
    // 3. Notify Core 1 Control Task immediately
    BaseType_t xHigherPriorityTaskWoken = pdFALSE;
    if (s_control_task_handle != NULL) {
        vTaskNotifyGiveFromISR(s_control_task_handle, &xHigherPriorityTaskWoken);
        portYIELD_FROM_ISR(xHigherPriorityTaskWoken);
    }
#endif
}

#ifndef HOST_TEST
// Core 0 Task to monitor GPIO 11 (Start Button) with software debounce
static void start_button_debounce_task(void *pvParameters) {
    (void)pvParameters;
    int last_state = 0;
    int current_state = 0;
    TickType_t last_debounce_time = 0;
    const TickType_t debounce_delay = pdMS_TO_TICKS(50); // 50ms debounce

    while (1) {
        int reading = gpio_get_level(GPIO_START_PIN);

        if (reading != last_state) {
            last_debounce_time = xTaskGetTickCount();
        }

        if ((xTaskGetTickCount() - last_debounce_time) > debounce_delay) {
            if (reading != current_state) {
                current_state = reading;
                // Rising edge detected (button pressed: LOW -> HIGH, Active-HIGH)
                if (current_state != 0) {
                    // Toggle between IDLE and MOVING
                    machine_state_t state = shared_data_get_state();
                    if (state == MACHINE_STATE_MOVING) {
                        shared_data_request_state_change(MACHINE_STATE_IDLE);
                    } else if (state == MACHINE_STATE_IDLE) {
                        shared_data_request_state_change(MACHINE_STATE_MOVING);
                    }
                }
            }
        }

        last_state = reading;
        vTaskDelay(pdMS_TO_TICKS(10));
    }
}
#endif

esp_err_t gpio_safety_init(void) {
#ifndef HOST_TEST
    // 1. Configure GPIO 11 (Start Button) - Input with Internal Pull-down (Active-HIGH)
    gpio_config_t io_conf_start = {
        .pin_bit_mask = (1ULL << GPIO_START_PIN),
        .mode = GPIO_MODE_INPUT,
        .pull_up_en = GPIO_PULLUP_DISABLE,
        .pull_down_en = GPIO_PULLDOWN_ENABLE,
        .intr_type = GPIO_INTR_DISABLE
    };
    gpio_config(&io_conf_start);

    // 1b. Configure GPIO 37 (Home Sensor) - Input with Internal Pull-up
    // NC (NF) sensor wired to GND: closed (not home) = LOW (0), open (home/broken wire) = HIGH (1)
    gpio_config_t io_conf_home = {
        .pin_bit_mask = (1ULL << GPIO_HOME_PIN),
        .mode = GPIO_MODE_INPUT,
        .pull_up_en = GPIO_PULLUP_ENABLE,
        .pull_down_en = GPIO_PULLDOWN_DISABLE,
        .intr_type = GPIO_INTR_DISABLE
    };
    gpio_config(&io_conf_home);

    // 2. Configure GPIO 12 (Emergency Button) - Input with Pull-down & Rising Edge Interrupt (Active-HIGH)
    gpio_config_t io_conf_emerg = {
        .pin_bit_mask = (1ULL << GPIO_EMERGENCY_PIN),
        .mode = GPIO_MODE_INPUT,
        .pull_up_en = GPIO_PULLUP_DISABLE,
        .pull_down_en = GPIO_PULLDOWN_ENABLE,
        .intr_type = GPIO_INTR_POSEDGE
    };
    gpio_config(&io_conf_emerg);

    // 3. Configure GPIO 13 (Motor Enable / Driver Safety Cutoff Pin)
    gpio_config_t io_conf_motor = {
        .pin_bit_mask = (1ULL << GPIO_NUM_13),
        .mode = GPIO_MODE_INPUT,
        .pull_up_en = GPIO_PULLUP_DISABLE,
        .pull_down_en = GPIO_PULLDOWN_ENABLE,
        .intr_type = GPIO_INTR_DISABLE
    };
    gpio_config(&io_conf_motor);

    // 4. Install ISR Service & Add Handler for GPIO 12
    esp_err_t err = gpio_install_isr_service(ESP_INTR_FLAG_IRAM);
    if (err != ESP_OK && err != ESP_ERR_INVALID_STATE) {
        return err;
    }
    gpio_isr_handler_add(GPIO_EMERGENCY_PIN, gpio12_emergency_isr, (void *)1);

    // 5. Create Start Button Debounce Task on Core 0
    xTaskCreatePinnedToCore(
        start_button_debounce_task,
        "StartDebounceTask",
        2048,
        NULL,
        4,
        NULL,
        0 // Core 0
    );
#else
    s_simulated_emergency_gpio = 0;
#endif
    return ESP_OK;
}

void gpio_safety_trigger_emergency_software(void) {
    gpio12_emergency_isr(NULL);
}

void gpio_safety_reset_simulation(void) {
#ifdef HOST_TEST
    s_simulated_emergency_gpio = 0;
#endif
}

bool gpio_safety_is_emergency_active(void) {
    if (shared_data_get_state() == MACHINE_STATE_EMERGENCY) {
        return true;
    }
#ifndef HOST_TEST
    return (gpio_get_level(GPIO_EMERGENCY_PIN) != 0);
#else
    return (s_simulated_emergency_gpio != 0);
#endif
}
