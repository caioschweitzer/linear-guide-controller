#include <stdio.h>
#include <math.h>

#ifndef HOST_TEST
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_log.h"
#endif

#include "shared_data.h"
#include "gpio_safety.h"
#include "linear_kinematics.h"
#include "encoder_pcnt.h"
#include "motor_mcpwm.h"
#include "pid_controller.h"
#include "ihm_display.h"
#include "modbus_slave.h"

#define SYSTEM_MAX_TRAVEL_MM 424.115f

static TaskHandle_t s_control_task_handle = NULL;
static pid_controller_t g_pid;
static ihm_display_t g_ihm;
static kinematics_t g_kinematics;
static encoder_driver_t g_encoder;
static motor_driver_t g_motor;

#ifndef HOST_TEST
static const char *TAG = "MAIN_SYSTEM";

// Deterministic Control Loop Task Pinned to Core 1 (100 Hz / 10 ms period)
static void control_loop_task(void *pvParameters) {
    (void)pvParameters;
    TickType_t last_wake_time = xTaskGetTickCount();
    const TickType_t period = pdMS_TO_TICKS(10); // 100 Hz

    int32_t raw_counts = 0;
    float current_pos_mm = 0.0f;
    float current_vel_mm_s = 0.0f;
    float position_setpoint = 0.0f;
    machine_state_t state = MACHINE_STATE_IDLE;

    while (1) {
        // 1. Direct Emergency ISR Notification Handling
        if (ulTaskNotifyTake(pdTRUE, 0) > 0) {
            shared_data_set_state_atomic(MACHINE_STATE_EMERGENCY);
        }

        // 2. Read PCNT Encoder Hardware
        encoder_get_count(&g_encoder, &raw_counts);

        // 3. Compute Linear Kinematics (Position & Velocity)
        current_pos_mm = kinematics_update(&g_kinematics, raw_counts, 0.01f, &current_vel_mm_s);

        // 4. Fast Snapshot Mutex Lock (< 1 ms hold)
        if (shared_data_lock(pdMS_TO_TICKS(1))) {
            position_setpoint = g_system_data.position_setpoint;
            state = (machine_state_t)g_system_data.machine_state;

            // Publish telemetry to shared structure for Core 0 (IHM & Modbus)
            g_system_data.current_position = current_pos_mm;
            g_system_data.current_velocity = current_vel_mm_s;
            shared_data_unlock();
        }

        // 5. Mechanical Boundary Clamping
        if (position_setpoint < 0.0f) position_setpoint = 0.0f;
        if (position_setpoint > SYSTEM_MAX_TRAVEL_MM) position_setpoint = SYSTEM_MAX_TRAVEL_MM;

        // 6. Emergency Safety Intercept
        if (gpio_safety_is_emergency_active()) {
            state = MACHINE_STATE_EMERGENCY;
        }

        // 7. Closed-Loop Control Decision
        if (state == MACHINE_STATE_EMERGENCY) {
            pid_reset(&g_pid);
            motor_brake(&g_motor);
            motor_set_effort(&g_motor, 0.0f);
        } else if (state == MACHINE_STATE_MOVING) {
            float duty = pid_compute(&g_pid, position_setpoint, current_pos_mm, 0.01f);
            motor_set_effort(&g_motor, duty);
        } else { // MACHINE_STATE_IDLE
            pid_reset(&g_pid);
            motor_set_effort(&g_motor, 0.0f);
        }

        vTaskDelayUntil(&last_wake_time, period);
    }
}

// Local IHM & Telemetry Display Task Pinned to Core 0 (5 Hz / 200 ms period)
static void ihm_task(void *pvParameters) {
    (void)pvParameters;
    TickType_t last_wake_time = xTaskGetTickCount();
    const TickType_t period = pdMS_TO_TICKS(200); // 5 Hz

    float pos_mm = 0.0f;
    float vel_mm_s = 0.0f;
    machine_state_t state = MACHINE_STATE_IDLE;

    while (1) {
        if (shared_data_lock(pdMS_TO_TICKS(10))) {
            pos_mm = g_system_data.current_position;
            vel_mm_s = g_system_data.current_velocity;
            state = (machine_state_t)g_system_data.machine_state;
            shared_data_unlock();
        }

        uint32_t current_time_ms = pdTICKS_TO_MS(xTaskGetTickCount());
        ihm_update(&g_ihm, pos_mm, vel_mm_s, state, current_time_ms);

        vTaskDelayUntil(&last_wake_time, period);
    }
}
#endif

void app_main(void) {
    // 1. Initialize Shared Data & IPC Mutex
    shared_data_init();

    // 2. Initialize Safety Interruption System (GPIO 12 Emergency ISR)
    gpio_safety_init();

    // 3. Initialize Kinematics Model
    kinematics_init(&g_kinematics, 0, 1, DEFAULT_EMA_ALPHA);

    // 4. Initialize Encoder PCNT Module
    encoder_init(&g_encoder, NULL);

    // 5. Initialize Motor MCPWM Module
    motor_init(&g_motor, NULL);

    // 6. Initialize PID Controller Module
    pid_init(&g_pid, NULL);

    // 7. Initialize IHM Display & Status LED Manager
    ihm_init(&g_ihm, NULL);

    // 8. Initialize Modbus RTU Communication Kernel
    if (modbus_slave_init() == ESP_OK) {
        modbus_slave_start_task();
    }

#ifndef HOST_TEST
    // 9. Create Control Loop Task Pinned to Core 1 (100 Hz, Priority 10)
    xTaskCreatePinnedToCore(
        control_loop_task,
        "ControlLoopTask",
        4096,
        NULL,
        10,
        &s_control_task_handle,
        1
    );

    gpio_safety_set_control_task_handle(s_control_task_handle);

    // 10. Create IHM Task Pinned to Core 0 (5 Hz, Priority 5)
    xTaskCreatePinnedToCore(
        ihm_task,
        "IHMTask",
        3072,
        NULL,
        5,
        NULL,
        0
    );

    ESP_LOGI(TAG, "Linear Actuator Controller System Fully Initialized & Operational.");
#endif
}
