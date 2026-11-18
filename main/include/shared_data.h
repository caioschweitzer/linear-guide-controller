#ifndef SHARED_DATA_H
#define SHARED_DATA_H

#include <stdint.h>
#include <stdbool.h>
#include <stdatomic.h>
#ifndef HOST_TEST
#include "freertos/FreeRTOS.h"
#include "freertos/semphr.h"
#include "driver/gpio.h"
#else
#include <stddef.h>
typedef uint32_t TickType_t;
typedef void* SemaphoreHandle_t;
#define pdTRUE true
#define pdFALSE false
#define pdMS_TO_TICKS(ms) ((TickType_t)(ms))
#define GPIO_NUM_37 37
#define GPIO_NUM_16 16
#define GPIO_NUM_12 12
#define GPIO_NUM_11 11
static inline SemaphoreHandle_t xSemaphoreCreateMutex(void) { static int dummy = 1; return (void*)&dummy; }
static inline bool xSemaphoreTake(SemaphoreHandle_t mutex, TickType_t ticks) { (void)mutex; (void)ticks; return true; }
static inline void xSemaphoreGive(SemaphoreHandle_t mutex) { (void)mutex; }
int gpio_get_level(int pin);
#endif

#ifdef __cplusplus
extern "C" {
#endif

#define GPIO_EMERGENCY_PIN     GPIO_NUM_12
#define GPIO_START_PIN         GPIO_NUM_11
#define GPIO_HOME_PIN          GPIO_NUM_37
#define GPIO_SAFETY_ENABLE_PIN GPIO_NUM_13

typedef enum {
    MACHINE_STATE_IDLE = 0,
    MACHINE_STATE_MOVING = 1,
    MACHINE_STATE_EMERGENCY = 2,
    MACHINE_STATE_HOMING = 3,
    MACHINE_STATE_OPEN_LOOP_TEST = 4
} machine_state_t;

#define BURST_BUFFER_MAX_SAMPLES 825

#define OPEN_LOOP_MODE_BRAKE 0
#define OPEN_LOOP_MODE_COAST 1

typedef enum {
    BURST_STATUS_IDLE = 0,
    BURST_STATUS_CAPTURING = 1,
    BURST_STATUS_READY = 2,
    BURST_STATUS_ABORTED = 3
} burst_status_t;

typedef struct {
    uint32_t time_ms;
    float position;
    float velocity;
    float duty_pct;
} open_loop_sample_t;

typedef struct {
    open_loop_sample_t samples[BURST_BUFFER_MAX_SAMPLES];
    uint16_t sample_count;
    uint16_t status;      // burst_status_t
    uint16_t read_index;  // For Modbus indexed reading
} burst_buffer_t;

typedef struct {
    float position_setpoint;  // mm
    float current_position;   // mm
    float current_velocity;   // mm/s
    float duty_cycle;         // % motor effort (-100.0 to 100.0)
    float kp;                 // Proportional gain
    float ki;                 // Integral gain
    float kd;                 // Derivative gain
    float open_loop_pwm;      // Open-loop step test PWM % (1.0 to 100.0)
    float open_loop_coast_pos_mm; // Step-down position for coast mode (50.0 to 536.0 mm)
    uint16_t open_loop_mode;  // 0: Brake at 80%, 1: Coast to natural stop
    uint16_t machine_state;   // 0: IDLE, 1: MOVING, 2: EMERGENCY
    bool button_estop;        // Discrete Input 0x0000 (1: Active/Pressed, 0: Normal/Released)
    bool button_start;        // Discrete Input 0x0001 (1: Pressed, 0: Released)
    bool safety_enable;       // Discrete Input 0x0002 (1: Enabled, 0: Disabled)
    bool led_status;          // Coil 0x0000 (1: ON, 0: OFF)
} SystemData;

// Global instance & mutex handle
extern SystemData g_system_data;
extern SemaphoreHandle_t g_system_mutex;
extern burst_buffer_t g_burst_buffer;

// Function prototypes for thread-safe IPC
void shared_data_init(void);
bool shared_data_lock(TickType_t timeout_ticks);
void shared_data_unlock(void);

// Atomic / ISR-safe state machine helpers
machine_state_t shared_data_get_state(void);
void shared_data_set_state_atomic(machine_state_t state);

// Level-checked state transition guard function
bool shared_data_request_state_change(machine_state_t new_state);

#ifdef __cplusplus
}
#endif

#endif // SHARED_DATA_H
