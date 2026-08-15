#ifndef PID_CONTROLLER_H
#define PID_CONTROLLER_H

#include <stdbool.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

#define PID_DEFAULT_KP            2.0f
#define PID_DEFAULT_KI            0.5f
#define PID_DEFAULT_KD            0.05f
#define PID_DEFAULT_MIN_OUTPUT    -100.0f
#define PID_DEFAULT_MAX_OUTPUT    100.0f
#define PID_DEFAULT_DEADBAND_MM   0.05f
#define PID_DEFAULT_ALPHA_D       0.15f

typedef struct {
    float kp;
    float ki;
    float kd;
    float output_min;
    float output_max;
    float deadband_mm;
    float alpha_d;
} pid_config_t;

typedef struct {
    pid_config_t config;
    float integral_accumulator;
    float prev_position;
    float prev_derivative_filtered;
    float last_output;
    bool is_first_run;
    bool is_initialized;
} pid_controller_t;

/**
 * @brief Initialize PID controller with custom or default configuration.
 * 
 * @param pid Pointer to PID controller struct
 * @param config Pointer to configuration struct (NULL for defaults)
 */
void pid_init(pid_controller_t *pid, const pid_config_t *config);

/**
 * @brief Reset PID internal state (integrator accumulator and historical position).
 * 
 * @param pid Pointer to PID controller struct
 */
void pid_reset(pid_controller_t *pid);

/**
 * @brief Dynamically update PID gains.
 * 
 * @param pid Pointer to PID controller struct
 * @param kp Proportional gain
 * @param ki Integral gain
 * @param kd Derivative gain
 */
void pid_set_gains(pid_controller_t *pid, float kp, float ki, float kd);

/**
 * @brief Compute PID control output.
 * 
 * Implements:
 * - Derivative on measurement (no derivative kick on setpoint step)
 * - 1st-order IIR low-pass filter on derivative component
 * - Conditional anti-windup (freezes integral accumulation during saturation)
 * - In-position deadband (zeros output when error <= deadband_mm)
 * - Numerical guardrails for dt <= 0.0001s and NaN/INF protection
 * 
 * @param pid Pointer to PID controller struct
 * @param setpoint Target position in mm
 * @param current_position Current measured position in mm
 * @param dt Time delta in seconds
 * @return float Control output (clamped effort percent from output_min to output_max)
 */
float pid_compute(pid_controller_t *pid, float setpoint, float current_position, float dt);

#ifdef __cplusplus
}
#endif

#endif // PID_CONTROLLER_H
