#include "shared_data.h"
#include "esp_log.h"

static atomic_uint_fast16_t s_atomic_machine_state = ATOMIC_VAR_INIT(MACHINE_STATE_IDLE);

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
    atomic_store(&s_atomic_machine_state, (uint_fast16_t)MACHINE_STATE_IDLE);

    if (shared_data_lock(pdMS_TO_TICKS(10))) {
        g_system_data.position_setpoint = 0.0f;
        g_system_data.current_position = 0.0f;
        g_system_data.current_velocity = 0.0f;
        g_system_data.machine_state = MACHINE_STATE_IDLE;
        shared_data_unlock();
    }
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

machine_state_t shared_data_get_state(void) {
    return (machine_state_t)atomic_load(&s_atomic_machine_state);
}

void shared_data_set_state_atomic(machine_state_t state) {
    atomic_store(&s_atomic_machine_state, (uint_fast16_t)state);
    if (g_system_mutex != NULL && xSemaphoreTake(g_system_mutex, 0) == pdTRUE) {
        g_system_data.machine_state = (uint16_t)state;
        xSemaphoreGive(g_system_mutex);
    }
}

bool shared_data_request_state_change(machine_state_t new_state) {
    machine_state_t current = shared_data_get_state();

    // Check emergency hardware pin level (GPIO 12: active low, 1 == SAFE/unpressed, 0 == PRESSED)
    int emergency_pin_level = gpio_get_level(GPIO_EMERGENCY_PIN);

    // Rule 1: Transitioning to EMERGENCY is always granted immediately
    if (new_state == MACHINE_STATE_EMERGENCY) {
        shared_data_set_state_atomic(MACHINE_STATE_EMERGENCY);
        return true;
    }

    // Rule 2: If emergency pin is physically pressed (LOW == 0), no transition to IDLE or MOVING is permitted
    if (emergency_pin_level == 0) {
        shared_data_set_state_atomic(MACHINE_STATE_EMERGENCY);
        return false;
    }

    // Rule 3: Moving requires current state == IDLE
    if (new_state == MACHINE_STATE_MOVING) {
        if (current == MACHINE_STATE_IDLE && emergency_pin_level == 1) {
            shared_data_set_state_atomic(MACHINE_STATE_MOVING);
            return true;
        }
        return false;
    }

    // Rule 4: Reset (EMERGENCY -> IDLE) requires emergency_pin_level == 1 (HIGH)
    if (new_state == MACHINE_STATE_IDLE) {
        if (emergency_pin_level == 1) {
            shared_data_set_state_atomic(MACHINE_STATE_IDLE);
            return true;
        }
        return false;
    }

    return false;
}
