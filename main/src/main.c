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

#define SYSTEM_MAX_TRAVEL_MM 670.0f

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

        float kp = 2.0f, ki = 0.5f, kd = 0.05f;
        float open_loop_pwm = 100.0f;
        float open_loop_coast_pos_mm = 400.0f;
        uint16_t open_loop_mode = OPEN_LOOP_MODE_BRAKE;

        // 4. Fast Snapshot Mutex Lock (< 1 ms hold)
        if (shared_data_lock(pdMS_TO_TICKS(1))) {
            position_setpoint = g_system_data.position_setpoint;
            state = (machine_state_t)g_system_data.machine_state;
            kp = g_system_data.kp;
            ki = g_system_data.ki;
            kd = g_system_data.kd;
            open_loop_pwm = g_system_data.open_loop_pwm;
            open_loop_coast_pos_mm = g_system_data.open_loop_coast_pos_mm;
            open_loop_mode = g_system_data.open_loop_mode;

            // Publish telemetry to shared structure for Core 0 (IHM & Modbus)
            g_system_data.current_position = current_pos_mm;
            g_system_data.current_velocity = current_vel_mm_s;
            g_system_data.duty_cycle = g_motor.current_effort;
            g_system_data.button_estop = (gpio_get_level(GPIO_EMERGENCY_PIN) != 0);
            g_system_data.button_start = (gpio_get_level(GPIO_START_PIN) != 0);
            g_system_data.safety_enable = (gpio_get_level(GPIO_SAFETY_ENABLE_PIN) != 0);
            g_system_data.led_status = (g_ihm.led_state != 0);
            shared_data_unlock();
        }

        // Dynamically apply updated PID gains if changed via Modbus
        if (kp != g_pid.config.kp || ki != g_pid.config.ki || kd != g_pid.config.kd) {
            pid_set_gains(&g_pid, kp, ki, kd);
        }

        // 5. Mechanical Boundary Clamping
        if (position_setpoint < 0.0f) position_setpoint = 0.0f;
        if (position_setpoint > SYSTEM_MAX_TRAVEL_MM) position_setpoint = SYSTEM_MAX_TRAVEL_MM;

        // 6. Emergency Safety Intercept
        if (gpio_safety_is_emergency_active()) {
            state = MACHINE_STATE_EMERGENCY;
        }

        // 7. Closed-Loop Control Decision
        static bool s_open_loop_running = false;
        static TickType_t s_open_loop_start_tick = 0;
        static bool s_open_loop_coasting = false;
        static uint16_t s_coast_zero_vel_ticks = 0;

        if (state == MACHINE_STATE_EMERGENCY) {
            s_open_loop_running = false;
            s_open_loop_coasting = false;
            s_coast_zero_vel_ticks = 0;
            pid_reset(&g_pid);
            motor_brake(&g_motor);
            motor_set_effort(&g_motor, 0.0f);
        } else if (state == MACHINE_STATE_MOVING) {
            s_open_loop_running = false;
            s_open_loop_coasting = false;
            s_coast_zero_vel_ticks = 0;
            float duty = pid_compute(&g_pid, position_setpoint, current_pos_mm, 0.01f);
            motor_set_effort(&g_motor, duty);
        } else if (state == MACHINE_STATE_HOMING) {
            s_open_loop_running = false;
            s_open_loop_coasting = false;
            s_coast_zero_vel_ticks = 0;
            pid_reset(&g_pid);
            if (gpio_get_level(GPIO_HOME_PIN) != 0) { // Active-HIGH indicates home sensor triggered
                motor_brake(&g_motor);
                motor_set_effort(&g_motor, 0.0f);
                encoder_clear_count(&g_encoder);
                kinematics_reset(&g_kinematics);
                shared_data_request_state_change(MACHINE_STATE_IDLE);
            } else {
                motor_set_effort(&g_motor, -60.0f);
            }
        } else if (state == MACHINE_STATE_OPEN_LOOP_TEST) {
            pid_reset(&g_pid);
            if (!s_open_loop_running) {
                s_open_loop_running = true;
                s_open_loop_coasting = false;
                s_coast_zero_vel_ticks = 0;
                s_open_loop_start_tick = xTaskGetTickCount();
            }

            uint32_t elapsed_ms = pdTICKS_TO_MS(xTaskGetTickCount() - s_open_loop_start_tick);
            const float target_travel_mm = SYSTEM_MAX_TRAVEL_MM * 0.80f; // 536.0 mm (80% of travel)
            const float coast_endstop_guard_mm = SYSTEM_MAX_TRAVEL_MM - 20.0f; // 650.0 mm
            const uint32_t open_loop_timeout_ms = 7500; // 1.5x of 5000 ms

            float applied_duty = open_loop_pwm;
            if (open_loop_mode == OPEN_LOOP_MODE_COAST) {
                if (!s_open_loop_coasting && current_pos_mm >= open_loop_coast_pos_mm) {
                    s_open_loop_coasting = true;
                    s_coast_zero_vel_ticks = 0;
                }
                if (s_open_loop_coasting) {
                    applied_duty = 0.0f;
                }
            }

            // Record sample to in-RAM burst buffer (100 Hz sampling)
            if (g_burst_buffer.sample_count < BURST_BUFFER_MAX_SAMPLES) {
                uint16_t idx = g_burst_buffer.sample_count;
                g_burst_buffer.samples[idx].time_ms = elapsed_ms;
                g_burst_buffer.samples[idx].position = current_pos_mm;
                g_burst_buffer.samples[idx].velocity = current_vel_mm_s;
                g_burst_buffer.samples[idx].duty_pct = applied_duty;
                g_burst_buffer.sample_count++;
            }

            if (open_loop_mode == OPEN_LOOP_MODE_COAST) {
                if (s_open_loop_coasting) {
                    if (fabsf(current_vel_mm_s) <= 2.0f) {
                        s_coast_zero_vel_ticks++;
                    } else {
                        s_coast_zero_vel_ticks = 0;
                    }

                    // Natural stop detected (150 ms sustained near-zero velocity)
                    if (s_coast_zero_vel_ticks >= 15) {
                        motor_set_effort(&g_motor, 0.0f);
                        s_open_loop_running = false;
                        s_open_loop_coasting = false;
                        g_burst_buffer.status = BURST_STATUS_READY;
                        shared_data_request_state_change(MACHINE_STATE_IDLE);
                    }
                    // Safety endstop guard while coasting
                    else if (current_pos_mm >= coast_endstop_guard_mm) {
                        motor_brake(&g_motor);
                        motor_set_effort(&g_motor, 0.0f);
                        s_open_loop_running = false;
                        s_open_loop_coasting = false;
                        g_burst_buffer.status = BURST_STATUS_READY;
                        shared_data_request_state_change(MACHINE_STATE_IDLE);
                    }
                    // Buffer full or safety timeout (7.5 s)
                    else if (g_burst_buffer.sample_count >= BURST_BUFFER_MAX_SAMPLES || elapsed_ms >= open_loop_timeout_ms) {
                        motor_set_effort(&g_motor, 0.0f);
                        s_open_loop_running = false;
                        s_open_loop_coasting = false;
                        g_burst_buffer.status = BURST_STATUS_READY;
                        shared_data_request_state_change(MACHINE_STATE_IDLE);
                    }
                    // Coasting with 0% effort (no active brake)
                    else {
                        motor_set_effort(&g_motor, 0.0f);
                    }
                } else {
                    if (current_pos_mm >= coast_endstop_guard_mm) {
                        motor_brake(&g_motor);
                        motor_set_effort(&g_motor, 0.0f);
                        s_open_loop_running = false;
                        g_burst_buffer.status = BURST_STATUS_READY;
                        shared_data_request_state_change(MACHINE_STATE_IDLE);
                    } else if (elapsed_ms >= open_loop_timeout_ms) {
                        motor_brake(&g_motor);
                        motor_set_effort(&g_motor, 0.0f);
                        s_open_loop_running = false;
                        g_burst_buffer.status = BURST_STATUS_ABORTED;
                        shared_data_request_state_change(MACHINE_STATE_IDLE);
                    } else {
                        motor_set_effort(&g_motor, applied_duty);
                    }
                }
            } else {
                // Stop condition 1: 80% travel threshold reached (536.0 mm)
                if (current_pos_mm >= target_travel_mm) {
                    motor_brake(&g_motor);
                    motor_set_effort(&g_motor, 0.0f);
                    s_open_loop_running = false;
                    g_burst_buffer.status = BURST_STATUS_READY;
                    shared_data_request_state_change(MACHINE_STATE_IDLE);
                }
                // Stop condition 2: Safety timeout (7.5 seconds)
                else if (elapsed_ms >= open_loop_timeout_ms) {
                    motor_brake(&g_motor);
                    motor_set_effort(&g_motor, 0.0f);
                    s_open_loop_running = false;
                    g_burst_buffer.status = BURST_STATUS_ABORTED;
                    shared_data_request_state_change(MACHINE_STATE_IDLE);
                }
                // Ongoing drive: Configured open-loop step PWM effort
                else {
                    motor_set_effort(&g_motor, applied_duty);
                }
            }
        } else { // MACHINE_STATE_IDLE
            s_open_loop_running = false;
            s_open_loop_coasting = false;
            s_coast_zero_vel_ticks = 0;
            pid_reset(&g_pid);
            motor_set_effort(&g_motor, 0.0f);
        }

        vTaskDelayUntil(&last_wake_time, period);
    }
}

// Local IHM & Telemetry Display Task Pinned to Core 0 (10 Hz / 100 ms period)
static void ihm_task(void *pvParameters) {
    (void)pvParameters;
    TickType_t last_wake_time = xTaskGetTickCount();
    const TickType_t period = pdMS_TO_TICKS(100); // 10 Hz task execution

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
#endif
}
