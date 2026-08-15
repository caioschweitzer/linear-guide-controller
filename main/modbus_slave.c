#include "modbus_slave.h"
#include "shared_data.h"
#include "gpio_safety.h"
#include <string.h>

#ifndef HOST_TEST
#include "esp_log.h"
#include "driver/uart.h"
#include "mbcontroller.h"

#define MB_SLAVE_ADDR 1
#define MB_PORT_NUM UART_NUM_0
#define MB_DEV_SPEED 115200
#endif

// Internal buffers mapped to Modbus stack
static holding_reg_params_t s_holding_reg = {0, 0, 0};
static input_reg_params_t s_input_reg = {0, 0, 0, 0, 0};

static void* s_mbc_handle = NULL;

// Helper to convert float to 2 x uint16 (Big-Endian IEEE 754)
static void float_to_registers(float src, uint16_t* hi, uint16_t* lo) {
    uint32_t val;
    memcpy(&val, &src, sizeof(float));
    *hi = (uint16_t)((val >> 16) & 0xFFFF);
    *lo = (uint16_t)(val & 0xFFFF);
}

// Helper to convert 2 x uint16 (Big-Endian IEEE 754) to float
static float registers_to_float(uint16_t hi, uint16_t lo) {
    uint32_t val = ((uint32_t)hi << 16) | lo;
    float result;
    memcpy(&result, &val, sizeof(float));
    return result;
}

esp_err_t modbus_slave_init(void) {
#ifndef HOST_TEST
    // 1. Suppress plain ASCII logging on UART0 to avoid polluting Modbus RTU frames
    esp_log_level_set("*", ESP_LOG_NONE);

    // 2. Initialize Modbus controller for Serial Slave (esp-modbus 2.x API)
    mb_communication_info_t comm_info = {
        .ser_opts = {
            .mode = MB_RTU,
            .port = MB_PORT_NUM,
            .uid = MB_SLAVE_ADDR,
            .baudrate = MB_DEV_SPEED,
            .data_bits = UART_DATA_8_BITS,
            .stop_bits = UART_STOP_BITS_1,
            .parity = MB_PARITY_NONE
        }
    };

    esp_err_t err = mbc_slave_create_serial(&comm_info, &s_mbc_handle);
    if (err != ESP_OK) return err;

    // 3. Register holding area
    mb_register_area_descriptor_t reg_area_holding = {
        .type = MB_PARAM_HOLDING,
        .start_offset = HOLDING_REG_START_ADDR,
        .address = (void*)&s_holding_reg,
        .size = sizeof(s_holding_reg)
    };
    err = mbc_slave_set_descriptor(s_mbc_handle, reg_area_holding);
    if (err != ESP_OK) return err;

    // 4. Register input area
    mb_register_area_descriptor_t reg_area_input = {
        .type = MB_PARAM_INPUT,
        .start_offset = INPUT_REG_START_ADDR,
        .address = (void*)&s_input_reg,
        .size = sizeof(s_input_reg)
    };
    err = mbc_slave_set_descriptor(s_mbc_handle, reg_area_input);
    if (err != ESP_OK) return err;

    // 5. Start Modbus slave
    err = mbc_slave_start(s_mbc_handle);
    return err;
#else
    return ESP_OK;
#endif
}

#ifndef HOST_TEST
static void modbus_slave_task(void *pvParameters) {
    (void)pvParameters;

    while (1) {
        if (s_mbc_handle) {
            mb_event_group_t event = mbc_slave_check_event(s_mbc_handle, MB_EVENT_HOLDING_REG_WR | MB_EVENT_INPUT_REG_RD);
            (void)event;
        }

        // Process Command Register if set
        uint16_t cmd = s_holding_reg.command;
        if (cmd != CMD_NONE) {
            s_holding_reg.command = CMD_NONE; // Reset command register after reading
            if (cmd == CMD_START) {
                shared_data_request_state_change(MACHINE_STATE_MOVING);
            } else if (cmd == CMD_STOP) {
                shared_data_request_state_change(MACHINE_STATE_IDLE);
            } else if (cmd == CMD_RESET) {
                shared_data_request_state_change(MACHINE_STATE_IDLE);
            } else if (cmd == CMD_SIMULATE_EMERGENCY) {
                gpio_safety_trigger_emergency_software();
            }
        }

        if (shared_data_lock(pdMS_TO_TICKS(10))) {
            // Read setpoint from Modbus holding registers
            g_system_data.position_setpoint = registers_to_float(s_holding_reg.setpoint_hi, s_holding_reg.setpoint_lo);

            // Write current position, velocity, state to Modbus input registers
            float_to_registers(g_system_data.current_position, &s_input_reg.pos_hi, &s_input_reg.pos_lo);
            float_to_registers(g_system_data.current_velocity, &s_input_reg.vel_hi, &s_input_reg.vel_lo);
            s_input_reg.state = (uint16_t)shared_data_get_state();

            shared_data_unlock();
        }

        vTaskDelay(pdMS_TO_TICKS(20));
    }
}
#endif

void modbus_slave_start_task(void) {
#ifndef HOST_TEST
    xTaskCreatePinnedToCore(
        modbus_slave_task,
        "ModbusSlaveTask",
        4096,
        NULL,
        4,
        NULL,
        0 // Core 0
    );
#endif
}
