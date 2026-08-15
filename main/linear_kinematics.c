#include "linear_kinematics.h"
#include <math.h>
#include <stddef.h>

void kinematics_init(kinematics_t *kin, int32_t zero_offset, int8_t direction, float alpha) {
    if (!kin) return;
    
    kin->zero_offset = zero_offset;
    kin->direction = (direction < 0) ? -1 : 1;
    kin->alpha = (alpha > 0.0f && alpha <= 1.0f) ? alpha : DEFAULT_EMA_ALPHA;
    kin->is_initialized = false;
    kin->last_position = 0.0f;
    kin->last_velocity = 0.0f;
    kin->filtered_velocity = 0.0f;
}

void kinematics_reset(kinematics_t *kin) {
    if (!kin) return;
    
    kin->is_initialized = false;
    kin->last_position = 0.0f;
    kin->last_velocity = 0.0f;
    kin->filtered_velocity = 0.0f;
}

void kinematics_set_zero_offset(kinematics_t *kin, int32_t zero_offset) {
    if (!kin) return;
    kin->zero_offset = zero_offset;
}

void kinematics_set_direction(kinematics_t *kin, int8_t direction) {
    if (!kin) return;
    kin->direction = (direction < 0) ? -1 : 1;
}

float kinematics_calculate_position(const kinematics_t *kin, int32_t raw_count) {
    if (!kin) return 0.0f;
    
    int32_t net_count = raw_count - kin->zero_offset;
    return ((float)net_count) * ((float)kin->direction) * MM_PER_COUNT;
}

float kinematics_calculate_velocity(kinematics_t *kin, float current_position, float dt) {
    if (!kin) return 0.0f;
    
    // First cycle post-initialization: prevent speed spikes
    if (!kin->is_initialized) {
        kin->is_initialized = true;
        kin->last_position = current_position;
        kin->last_velocity = 0.0f;
        kin->filtered_velocity = 0.0f;
        return 0.0f;
    }
    
    // Guardrail against dt <= MIN_DT_SECONDS to prevent division by zero or NaN
    if (dt <= MIN_DT_SECONDS) {
        return kin->filtered_velocity;
    }
    
    float instantaneous_velocity = (current_position - kin->last_position) / dt;
    float filtered = (kin->alpha * instantaneous_velocity) + ((1.0f - kin->alpha) * kin->filtered_velocity);
    
    kin->last_position = current_position;
    kin->last_velocity = instantaneous_velocity;
    kin->filtered_velocity = filtered;
    
    return filtered;
}

float kinematics_update(kinematics_t *kin, int32_t raw_count, float dt, float *out_velocity) {
    if (!kin) return 0.0f;
    
    float pos = kinematics_calculate_position(kin, raw_count);
    float vel = kinematics_calculate_velocity(kin, pos, dt);
    
    if (out_velocity != NULL) {
        *out_velocity = vel;
    }
    
    return pos;
}

int16_t kinematics_to_modbus_i16(float value, float scale) {
    if (scale <= 0.0f) scale = 1.0f;
    float scaled = value * scale;
    
    if (scaled >= 32767.0f) return 32767;
    if (scaled <= -32768.0f) return -32768;
    return (int16_t)roundf(scaled);
}

int32_t kinematics_to_modbus_i32(float value, float scale) {
    if (scale <= 0.0f) scale = 1.0f;
    float scaled = value * scale;
    
    if (scaled >= 2147483647.0f) return 2147483647;
    if (scaled <= -2147483648.0f) return -2147483648;
    return (int32_t)roundf(scaled);
}

float kinematics_modbus_i16_to_float(int16_t reg_val, float scale) {
    if (scale <= 0.0f) scale = 1.0f;
    return ((float)reg_val) / scale;
}
