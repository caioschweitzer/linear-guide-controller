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
#define GPIO_SAFETY_ENABLE_PIN GPIO_NUM_13

typedef enum {
    MACHINE_STATE_IDLE = 0,
    MACHINE_STATE_MOVING = 1,
    MACHINE_STATE_EMERGENCY = 2
} machine_state_t;

typedef struct {
    float position_setpoint;  // mm
    float current_position;   // mm
    float current_velocity;   // mm/s
    float kp;                 // Proportional gain
    float ki;                 // Integral gain
    float kd;                 // Derivative gain
    uint16_t machine_state;   // 0: IDLE, 1: MOVING, 2: EMERGENCY
    bool button_estop;        // Discrete Input 0x0000 (0: Active, 1: Released)
    bool button_start;        // Discrete Input 0x0001 (1: Pressed, 0: Released)
    bool safety_enable;       // Discrete Input 0x0002 (1: Enabled, 0: Disabled)
    bool led_status;          // Coil 0x0000 (1: ON, 0: OFF)
} SystemData;

// Global instance & mutex handle
extern SystemData g_system_data;
extern SemaphoreHandle_t g_system_mutex;

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
