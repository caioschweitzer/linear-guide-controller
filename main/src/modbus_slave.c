#include "modbus_slave.h"
#include "shared_data.h"
#include "gpio_safety.h"
#include <string.h>
#include <math.h>

#ifndef HOST_TEST
#include "esp_log.h"
#include "driver/uart.h"
#include "mbcontroller.h"

#define MB_SLAVE_ADDR 1
#define MB_PORT_NUM UART_NUM_0
#define MB_DEV_SPEED 115200
#endif

// Internal buffers mapped to Modbus stack
holding_reg_params_t g_modbus_holding_reg = {0};
input_reg_params_t g_modbus_input_reg = {0};
discrete_reg_params_t g_modbus_discrete_reg = {0};
coil_reg_params_t g_modbus_coil_reg = {0};

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
    // Populate default holding register values
    float_to_registers(0.0f, &g_modbus_holding_reg.setpoint_hi, &g_modbus_holding_reg.setpoint_lo);
    g_modbus_holding_reg.command = CMD_NONE;
    float_to_registers(2.0f, &g_modbus_holding_reg.kp_hi, &g_modbus_holding_reg.kp_lo);
    float_to_registers(0.5f, &g_modbus_holding_reg.ki_hi, &g_modbus_holding_reg.ki_lo);
    float_to_registers(0.05f, &g_modbus_holding_reg.kd_hi, &g_modbus_holding_reg.kd_lo);
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
        .address = (void*)&g_modbus_holding_reg,
        .size = sizeof(g_modbus_holding_reg)
    };
    err = mbc_slave_set_descriptor(s_mbc_handle, reg_area_holding);
    if (err != ESP_OK) return err;

    // 4. Register input area
    mb_register_area_descriptor_t reg_area_input = {
        .type = MB_PARAM_INPUT,
        .start_offset = INPUT_REG_START_ADDR,
        .address = (void*)&g_modbus_input_reg,
        .size = sizeof(g_modbus_input_reg)
    };
    err = mbc_slave_set_descriptor(s_mbc_handle, reg_area_input);
    if (err != ESP_OK) return err;

    // 5. Register discrete input area
    mb_register_area_descriptor_t reg_area_discrete = {
        .type = MB_PARAM_DISCRETE,
        .start_offset = DISCRETE_REG_START_ADDR,
        .address = (void*)&g_modbus_discrete_reg,
        .size = sizeof(g_modbus_discrete_reg)
    };
    err = mbc_slave_set_descriptor(s_mbc_handle, reg_area_discrete);
    if (err != ESP_OK) return err;

    // 6. Register coil area
    mb_register_area_descriptor_t reg_area_coil = {
        .type = MB_PARAM_COIL,
        .start_offset = COIL_REG_START_ADDR,
        .address = (void*)&g_modbus_coil_reg,
        .size = sizeof(g_modbus_coil_reg)
    };
    err = mbc_slave_set_descriptor(s_mbc_handle, reg_area_coil);
    if (err != ESP_OK) return err;

    // 7. Start Modbus slave
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
            mb_event_group_t event = mbc_slave_check_event(s_mbc_handle, MB_EVENT_HOLDING_REG_WR | MB_EVENT_INPUT_REG_RD | MB_EVENT_COILS_WR);
            (void)event;
        }

        // Process Command Register if set
        uint16_t cmd = g_modbus_holding_reg.command;
        if (cmd != CMD_NONE) {
            g_modbus_holding_reg.command = CMD_NONE; // Reset command register after reading
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

        // Process Coil Triggers (Bit 1: Remote Emergency, Bit 2: Remote Start)
        if (g_modbus_coil_reg.coils & (1 << 1)) {
            g_modbus_coil_reg.coils &= ~(1 << 1); // Clear remote emergency trigger coil
            gpio_safety_trigger_emergency_software();
        }
        if (g_modbus_coil_reg.coils & (1 << 2)) {
            g_modbus_coil_reg.coils &= ~(1 << 2); // Clear remote start trigger coil
            shared_data_request_state_change(MACHINE_STATE_MOVING);
        }

        if (shared_data_lock(pdMS_TO_TICKS(10))) {
            // Read setpoint from Modbus holding registers
            g_system_data.position_setpoint = registers_to_float(g_modbus_holding_reg.setpoint_hi, g_modbus_holding_reg.setpoint_lo);

            // Synchronize PID gains with Modbus holding registers
            float mb_kp = registers_to_float(g_modbus_holding_reg.kp_hi, g_modbus_holding_reg.kp_lo);
            float mb_ki = registers_to_float(g_modbus_holding_reg.ki_hi, g_modbus_holding_reg.ki_lo);
            float mb_kd = registers_to_float(g_modbus_holding_reg.kd_hi, g_modbus_holding_reg.kd_lo);

            if (!isnan(mb_kp) && !isinf(mb_kp) && mb_kp >= 0.0f) g_system_data.kp = mb_kp;
            if (!isnan(mb_ki) && !isinf(mb_ki) && mb_ki >= 0.0f) g_system_data.ki = mb_ki;
            if (!isnan(mb_kd) && !isinf(mb_kd) && mb_kd >= 0.0f) g_system_data.kd = mb_kd;

            float_to_registers(g_system_data.kp, &g_modbus_holding_reg.kp_hi, &g_modbus_holding_reg.kp_lo);
            float_to_registers(g_system_data.ki, &g_modbus_holding_reg.ki_hi, &g_modbus_holding_reg.ki_lo);
            float_to_registers(g_system_data.kd, &g_modbus_holding_reg.kd_hi, &g_modbus_holding_reg.kd_lo);

            // Write current position, velocity, state to Modbus input registers
            float_to_registers(g_system_data.current_position, &g_modbus_input_reg.pos_hi, &g_modbus_input_reg.pos_lo);
            float_to_registers(g_system_data.current_velocity, &g_modbus_input_reg.vel_hi, &g_modbus_input_reg.vel_lo);
            g_modbus_input_reg.state = (uint16_t)shared_data_get_state();

            // Update Discrete Inputs register (Bit 0: E-Stop, Bit 1: Start, Bit 2: Safety Enable)
            uint8_t discrete_bits = 0;
            if (g_system_data.button_estop)    discrete_bits |= (1 << 0);
            if (g_system_data.button_start)    discrete_bits |= (1 << 1);
            if (g_system_data.safety_enable)   discrete_bits |= (1 << 2);
            g_modbus_discrete_reg.discrete_inputs = discrete_bits;

            // Reflect LED status coil (Bit 0)
            if (g_system_data.led_status) {
                g_modbus_coil_reg.coils |= (1 << 0);
            } else {
                g_modbus_coil_reg.coils &= ~(1 << 0);
            }

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
