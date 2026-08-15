#include "pid_controller.h"
#include <math.h>
#include <stddef.h>

void pid_init(pid_controller_t *pid, const pid_config_t *config) {
    if (!pid) return;

    if (config) {
        pid->config = *config;
    } else {
        pid->config.kp = PID_DEFAULT_KP;
        pid->config.ki = PID_DEFAULT_KI;
        pid->config.kd = PID_DEFAULT_KD;
        pid->config.output_min = PID_DEFAULT_MIN_OUTPUT;
        pid->config.output_max = PID_DEFAULT_MAX_OUTPUT;
        pid->config.deadband_mm = PID_DEFAULT_DEADBAND_MM;
        pid->config.alpha_d = PID_DEFAULT_ALPHA_D;
    }

    pid_reset(pid);
    pid->is_initialized = true;
}

void pid_reset(pid_controller_t *pid) {
    if (!pid) return;
    pid->integral_accumulator = 0.0f;
    pid->prev_position = 0.0f;
    pid->prev_derivative_filtered = 0.0f;
    pid->last_output = 0.0f;
    pid->is_first_run = true;
}

void pid_set_gains(pid_controller_t *pid, float kp, float ki, float kd) {
    if (!pid) return;
    pid->config.kp = kp;
    pid->config.ki = ki;
    pid->config.kd = kd;
}

float pid_compute(pid_controller_t *pid, float setpoint, float current_position, float dt) {
    if (!pid || !pid->is_initialized) return 0.0f;

    // Fail-safe numerical protection for NaN and INF inputs
    if (isnan(setpoint) || isinf(setpoint) ||
        isnan(current_position) || isinf(current_position) ||
        isnan(dt) || isinf(dt)) {
        return 0.0f;
    }

    float error = setpoint - current_position;

    // In-position deadband check (zeros effort when within deadband)
    if (fabsf(error) <= pid->config.deadband_mm) {
        return 0.0f;
    }

    // Proportional term
    float p_term = pid->config.kp * error;

    // Derivative on Measurement (prevents derivative kick on setpoint steps)
    float d_term = 0.0f;
    if (pid->is_first_run || dt <= 0.0001f) {
        pid->prev_position = current_position;
        pid->prev_derivative_filtered = 0.0f;
        pid->is_first_run = false;
        d_term = 0.0f;
    } else {
        float delta_x = current_position - pid->prev_position;
        float d_raw = -pid->config.kd * (delta_x / dt);
        
        // 1st-order IIR derivative low-pass filter
        d_term = (pid->config.alpha_d * d_raw) + ((1.0f - pid->config.alpha_d) * pid->prev_derivative_filtered);
        pid->prev_derivative_filtered = d_term;
        pid->prev_position = current_position;
    }

    // Unsaturated control output estimate prior to new integration
    float u_unsat_current = p_term + pid->integral_accumulator + d_term;

    // Conditional Anti-Windup: freeze integration if saturated in direction of error
    bool saturate_high = (u_unsat_current >= pid->config.output_max && error > 0.0f);
    bool saturate_low = (u_unsat_current <= pid->config.output_min && error < 0.0f);

    if (!saturate_high && !saturate_low && dt > 0.0001f) {
        pid->integral_accumulator += pid->config.ki * error * dt;
    }

    float i_term = pid->integral_accumulator;
    float u_total = p_term + i_term + d_term;

    // Output Clamping
    if (u_total > pid->config.output_max) u_total = pid->config.output_max;
    if (u_total < pid->config.output_min) u_total = pid->config.output_min;

    pid->last_output = u_total;
    return u_total;
}
