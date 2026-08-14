#include "shared_data.h"

SystemData g_system_data = {
    .position_setpoint = 0.0f,
    .current_position = 0.0f,
    .current_velocity = 0.0f,
    .machine_state = MACHINE_STATE_IDLE
};

SemaphoreHandle_t g_system_mutex = NULL;

void shared_data_init(void) {
    if (g_system_mutex == NULL) {
        g_system_mutex = xSemaphoreCreateMutex();
    }
    g_system_data.position_setpoint = 0.0f;
    g_system_data.current_position = 0.0f;
    g_system_data.current_velocity = 0.0f;
    g_system_data.machine_state = MACHINE_STATE_IDLE;
}

bool shared_data_lock(TickType_t timeout_ticks) {
    if (g_system_mutex == NULL) return false;
    return (xSemaphoreTake(g_system_mutex, timeout_ticks) == pdTRUE);
}

void shared_data_unlock(void) {
    if (g_system_mutex != NULL) {
        xSemaphoreGive(g_system_mutex);
    }
}
