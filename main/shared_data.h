#ifndef SHARED_DATA_H
#define SHARED_DATA_H

#include <stdint.h>
#include <stdbool.h>
#include <stdatomic.h>
#include "freertos/FreeRTOS.h"
#include "freertos/semphr.h"
#include "driver/gpio.h"

#ifdef __cplusplus
extern "C" {
#endif

#define GPIO_EMERGENCY_PIN GPIO_NUM_12
#define GPIO_START_PIN     GPIO_NUM_11

typedef enum {
    MACHINE_STATE_IDLE = 0,
    MACHINE_STATE_MOVING = 1,
    MACHINE_STATE_EMERGENCY = 2
} machine_state_t;

typedef struct {
    float position_setpoint;  // mm
    float current_position;   // mm
    float current_velocity;   // mm/s
    uint16_t machine_state;   // 0: IDLE, 1: MOVING, 2: EMERGENCY
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
