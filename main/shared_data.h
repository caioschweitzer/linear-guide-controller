#ifndef SHARED_DATA_H
#define SHARED_DATA_H

#include <stdint.h>
#include <stdbool.h>
#include "freertos/FreeRTOS.h"
#include "freertos/semphr.h"

#ifdef __cplusplus
extern "C" {
#endif

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

// Function prototypes for thread-safe operations
void shared_data_init(void);
bool shared_data_lock(TickType_t timeout_ticks);
void shared_data_unlock(void);

#ifdef __cplusplus
}
#endif

#endif // SHARED_DATA_H
