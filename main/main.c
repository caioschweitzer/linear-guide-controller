#include <stdio.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "shared_data.h"
#include "modbus_slave.h"
#include "gpio_safety.h"

static TaskHandle_t s_control_task_handle = NULL;

// Control Task pinned to Core 1 (100Hz / 10ms period)
static void control_loop_task(void *pvParameters) {
    (void)pvParameters;
    TickType_t last_wake_time = xTaskGetTickCount();
    const TickType_t period = pdMS_TO_TICKS(10); // 100 Hz

    while (1) {
        // Check for direct Emergency ISR notification
        if (ulTaskNotifyTake(pdTRUE, 0) > 0) {
            // Immediate handling of Emergency ISR signal on Core 1
            shared_data_set_state_atomic(MACHINE_STATE_EMERGENCY);
        }

        machine_state_t state = shared_data_get_state();

        if (state == MACHINE_STATE_MOVING) {
            // Control loop active (Placeholder for PID, PCNT read, MCPWM update)
        } else if (state == MACHINE_STATE_EMERGENCY) {
            // Emergency lockout mode - ensure drive outputs remain disabled
        }

        vTaskDelayUntil(&last_wake_time, period);
    }
}

void app_main(void) {
    // 1. Initialize Shared IPC Data & Mutex
    shared_data_init();

    // 2. Initialize GPIO Safety Subsystem (Start Debounce & Emergency ISR)
    gpio_safety_init();

    // 3. Initialize Modbus RTU Slave
    if (modbus_slave_init() == ESP_OK) {
        modbus_slave_start_task();
    }

    // 4. Create Control Task on Core 1 & Link Task Handle for ISR Notifications
    xTaskCreatePinnedToCore(
        control_loop_task,
        "ControlLoopTask",
        4096,
        NULL,
        5, // Priority 5
        &s_control_task_handle,
        1  // Core 1
    );

    gpio_safety_set_control_task_handle(s_control_task_handle);
}
