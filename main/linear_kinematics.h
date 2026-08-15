#ifndef LINEAR_KINEMATICS_H
#define LINEAR_KINEMATICS_H

#include <stdint.h>
#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

// Physical system constants
#define MM_PER_COUNT        0.0424115f  // mm per encoder count (42.4115 mm / 1000 counts)
#define DEFAULT_EMA_ALPHA   0.2f        // Default EMA low-pass filter factor
#define MIN_DT_SECONDS      0.0001f     // Minimum delta time guardrail (100 microseconds)

typedef struct {
    int32_t zero_offset;       // Counter zero offset (counts)
    int8_t direction;          // Direction multiplier (+1 or -1)
    float alpha;               // EMA smoothing factor (0.0 < alpha <= 1.0)
    bool is_initialized;       // State flag to track initial execution
    float last_position;       // Last computed position (mm)
    float last_velocity;       // Last computed raw velocity (mm/s)
    float filtered_velocity;   // EMA filtered velocity (mm/s)
} kinematics_t;

/**
 * @brief Initialize kinematics context with calibration parameters.
 * 
 * @param kin Pointer to kinematics context
 * @param zero_offset Zero homing offset in raw encoder counts
 * @param direction Direction multiplier (+1 for normal, -1 for inverted)
 * @param alpha EMA filter smoothing factor (0.0 < alpha <= 1.0, 0 for default 0.2)
 */
void kinematics_init(kinematics_t *kin, int32_t zero_offset, int8_t direction, float alpha);

/**
 * @brief Reset internal filter state and initialization flag.
 * 
 * @param kin Pointer to kinematics context
 */
void kinematics_reset(kinematics_t *kin);

/**
 * @brief Update calibration zero offset.
 * 
 * @param kin Pointer to kinematics context
 * @param zero_offset New zero offset in counts
 */
void kinematics_set_zero_offset(kinematics_t *kin, int32_t zero_offset);

/**
 * @brief Update direction multiplier.
 * 
 * @param kin Pointer to kinematics context
 * @param direction Direction multiplier (+1 or -1)
 */
void kinematics_set_direction(kinematics_t *kin, int8_t direction);

/**
 * @brief Calculate absolute position in mm from raw encoder count.
 * 
 * Formula: pos = (raw_count - zero_offset) * direction * MM_PER_COUNT
 * 
 * @param kin Pointer to kinematics context
 * @param raw_count Accumulated raw encoder count
 * @return float Calculated position in mm
 */
float kinematics_calculate_position(const kinematics_t *kin, int32_t raw_count);

/**
 * @brief Calculate velocity (mm/s) given new position and delta time.
 * 
 * Enforces dt guardrail (dt > MIN_DT_SECONDS) and handles first-cycle initialization.
 * Applies EMA filter: v_filt = alpha * v_inst + (1 - alpha) * v_prev.
 * 
 * @param kin Pointer to kinematics context
 * @param current_position Current position in mm
 * @param dt Delta time in seconds
 * @return float Filtered velocity in mm/s
 */
float kinematics_calculate_velocity(kinematics_t *kin, float current_position, float dt);

/**
 * @brief Full kinematics update step: computes position and filtered velocity.
 * 
 * @param kin Pointer to kinematics context
 * @param raw_count Accumulated raw encoder count
 * @param dt Delta time in seconds
 * @param out_velocity Optional pointer to receive filtered velocity (can be NULL)
 * @return float Computed position in mm
 */
float kinematics_update(kinematics_t *kin, int32_t raw_count, float dt, float *out_velocity);

/**
 * @brief Convert float position/velocity to Modbus 16-bit fixed-point integer.
 * 
 * @param value Floating-point position or velocity
 * @param scale Scale factor (e.g. 100.0f for 0.01 mm resolution)
 * @return int16_t Fixed-point integer value
 */
int16_t kinematics_to_modbus_i16(float value, float scale);

/**
 * @brief Convert float position/velocity to Modbus 32-bit fixed-point integer.
 * 
 * @param value Floating-point position or velocity
 * @param scale Scale factor (e.g. 100.0f or 1000.0f)
 * @return int32_t Fixed-point integer value
 */
int32_t kinematics_to_modbus_i32(float value, float scale);

/**
 * @brief Convert Modbus 16-bit fixed-point integer back to float.
 * 
 * @param reg_val Fixed-point 16-bit register value
 * @param scale Scale factor
 * @return float Converted float value
 */
float kinematics_modbus_i16_to_float(int16_t reg_val, float scale);

#ifdef __cplusplus
}
#endif

#endif // LINEAR_KINEMATICS_H
