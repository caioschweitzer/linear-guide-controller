#include <stdio.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "shared_data.h"
#include "modbus_slave.h"

// Placeholder Control Task pinned to Core 1 (100Hz / 10ms period)
static void control_loop_task(void *pvParameters) {
    (void)pvParameters;
    TickType_t last_wake_time = xTaskGetTickCount();
    const TickType_t period = pdMS_TO_TICKS(10); // 100 Hz

    while (1) {
        // Placeholder for future PID control loop, PCNT encoder read, and MCPWM update
        if (shared_data_lock(pdMS_TO_TICKS(2))) {
            // Read setpoint or update state for placeholder
            shared_data_unlock();
        }

        vTaskDelayUntil(&last_wake_time, period);
    }
}

void app_main(void) {
    // 1. Initialize Shared IPC Data & Mutex
    shared_data_init();

    // 2. Initialize Modbus RTU Slave
    if (modbus_slave_init() == ESP_OK) {
        modbus_slave_start_task();
    }

    // 3. Create Placeholder Control Task on Core 1
    xTaskCreatePinnedToCore(
        control_loop_task,
        "ControlLoopTask",
        4096,
        NULL,
        5, // Priority 5
        NULL,
        1  // Core 1
    );
}
