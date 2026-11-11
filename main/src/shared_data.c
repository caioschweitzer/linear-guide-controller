#include "shared_data.h"
#include "gpio_safety.h"
#include <stddef.h>
#include <math.h>
#ifndef HOST_TEST
#include "esp_log.h"
#else
static int s_host_simulated_gpio_level = 0; // 0 == SAFE / unpressed in active-high logic
int gpio_get_level(int pin) {
    (void)pin;
    return s_host_simulated_gpio_level;
}
#endif

static _Atomic uint_fast16_t s_atomic_machine_state = MACHINE_STATE_IDLE;

SystemData g_system_data = {
    .position_setpoint = 0.0f,
    .current_position = 0.0f,
    .current_velocity = 0.0f,
    .kp = 2.0f,
    .ki = 0.5f,
    .kd = 0.05f,
    .machine_state = MACHINE_STATE_IDLE,
    .button_estop = false,
    .button_start = false,
    .safety_enable = true,
    .led_status = false
};

SemaphoreHandle_t g_system_mutex = NULL;
burst_buffer_t g_burst_buffer = {0};

void shared_data_init(void) {
    if (g_system_mutex == NULL) {
        g_system_mutex = xSemaphoreCreateMutex();
    }
    atomic_store(&s_atomic_machine_state, (uint_fast16_t)MACHINE_STATE_IDLE);

    g_burst_buffer.sample_count = 0;
    g_burst_buffer.status = BURST_STATUS_IDLE;
    g_burst_buffer.read_index = 0;

    if (shared_data_lock(pdMS_TO_TICKS(10))) {
        g_system_data.position_setpoint = 0.0f;
        g_system_data.current_position = 0.0f;
        g_system_data.current_velocity = 0.0f;
        g_system_data.kp = 2.0f;
        g_system_data.ki = 0.5f;
        g_system_data.kd = 0.05f;
        g_system_data.machine_state = MACHINE_STATE_IDLE;
        g_system_data.button_estop = false;
        g_system_data.button_start = false;
        g_system_data.safety_enable = true;
        g_system_data.led_status = false;
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

#ifdef HOST_TEST
    if (new_state == MACHINE_STATE_IDLE) {
        gpio_safety_reset_simulation();
        s_host_simulated_gpio_level = 0;
    }
#endif

    // Check emergency hardware pin level (GPIO 12: active-high, 0 == SAFE/unpressed, 1 == PRESSED)
    int emergency_pin_level = gpio_get_level(GPIO_EMERGENCY_PIN);

    // Rule 1: Transitioning to EMERGENCY is always granted immediately
    if (new_state == MACHINE_STATE_EMERGENCY) {
#ifndef HOST_TEST
        gpio_set_level(GPIO_SAFETY_ENABLE_PIN, 0);
#else
        s_host_simulated_gpio_level = 1;
#endif
        if (current == MACHINE_STATE_OPEN_LOOP_TEST) {
            g_burst_buffer.status = BURST_STATUS_ABORTED;
        }
        shared_data_set_state_atomic(MACHINE_STATE_EMERGENCY);
        return true;
    }

    // Rule 2: If emergency pin is physically pressed (HIGH != 0), no transition to IDLE or MOVING is permitted
    if (emergency_pin_level != 0) {
#ifndef HOST_TEST
        gpio_set_level(GPIO_SAFETY_ENABLE_PIN, 0);
#endif
        if (current == MACHINE_STATE_OPEN_LOOP_TEST) {
            g_burst_buffer.status = BURST_STATUS_ABORTED;
        }
        shared_data_set_state_atomic(MACHINE_STATE_EMERGENCY);
        return false;
    }

    // Rule 3: Moving requires current state == IDLE
    if (new_state == MACHINE_STATE_MOVING) {
        if (current == MACHINE_STATE_IDLE && emergency_pin_level == 0) {
#ifndef HOST_TEST
            gpio_set_level(GPIO_SAFETY_ENABLE_PIN, 1);
#endif
            shared_data_set_state_atomic(MACHINE_STATE_MOVING);
            return true;
        }
        return false;
    }

    // Rule 4: Reset (EMERGENCY or OPEN_LOOP_TEST -> IDLE) requires emergency_pin_level == 0 (SAFE)
    if (new_state == MACHINE_STATE_IDLE) {
        if (emergency_pin_level == 0) {
            shared_data_set_state_atomic(MACHINE_STATE_IDLE);
            return true;
        }
        return false;
    }

    // Rule 5: Homing requires emergency_pin_level == 0 (SAFE) and current == IDLE
    if (new_state == MACHINE_STATE_HOMING) {
        if (current == MACHINE_STATE_IDLE && emergency_pin_level == 0) {
#ifndef HOST_TEST
            gpio_set_level(GPIO_SAFETY_ENABLE_PIN, 1);
#endif
            shared_data_set_state_atomic(MACHINE_STATE_HOMING);
            return true;
        }
        return false;
    }

    // Rule 6: Open-Loop Test requires current == IDLE, emergency_pin_level == 0, and |pos| <= 5.0 mm
    if (new_state == MACHINE_STATE_OPEN_LOOP_TEST) {
        float current_pos = 0.0f;
        if (shared_data_lock(pdMS_TO_TICKS(5))) {
            current_pos = g_system_data.current_position;
            shared_data_unlock();
        }
        if (current == MACHINE_STATE_IDLE && emergency_pin_level == 0 && fabsf(current_pos) <= 5.0f) {
#ifndef HOST_TEST
            gpio_set_level(GPIO_SAFETY_ENABLE_PIN, 1);
#endif
            g_burst_buffer.sample_count = 0;
            g_burst_buffer.status = BURST_STATUS_CAPTURING;
            g_burst_buffer.read_index = 0;
            shared_data_set_state_atomic(MACHINE_STATE_OPEN_LOOP_TEST);
            return true;
        }
        return false;
    }

    return false;
}
