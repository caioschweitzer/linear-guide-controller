#ifndef MODBUS_SLAVE_H
#define MODBUS_SLAVE_H

#include <stdint.h>
#include <stdbool.h>
#ifndef HOST_TEST
#include "esp_err.h"
#else
typedef int esp_err_t;
#define ESP_OK 0
#define ESP_FAIL -1
#endif

#ifdef __cplusplus
extern "C" {
#endif

// Modbus Command Register Flags
#define CMD_NONE                0
#define CMD_START               1
#define CMD_STOP                2
#define CMD_RESET               3
#define CMD_SIMULATE_EMERGENCY  99

// Modbus Register Map Offsets & Sizes
#define HOLDING_REG_START_ADDR  0x0000
#define HOLDING_REG_COUNT       3      // Setpoint (2 x 16-bit), Command (1 x 16-bit)

#define INPUT_REG_START_ADDR    0x0000
#define INPUT_REG_COUNT         5      // Pos (2 regs float32), Vel (2 regs float32), State (1 reg uint16)

#define DISCRETE_REG_START_ADDR 0x0000
#define DISCRETE_REG_COUNT      3      // E-Stop (Bit 0), Start (Bit 1), Safety Enable (Bit 2)

#define COIL_REG_START_ADDR     0x0000
#define COIL_REG_COUNT          3      // LED Status (Bit 0), Remote Emergency (Bit 1), Remote Start (Bit 2)

// Holding register structure
typedef struct {
    uint16_t setpoint_hi; // MSW
    uint16_t setpoint_lo; // LSW
    uint16_t command;     // 1: START, 2: STOP, 3: RESET, 99: SIMULATE_EMERGENCY
} holding_reg_params_t;

// Input register structure
typedef struct {
    uint16_t pos_hi;   // Float32 MSW
    uint16_t pos_lo;   // Float32 LSW
    uint16_t vel_hi;   // Float32 MSW
    uint16_t vel_lo;   // Float32 LSW
    uint16_t state;    // uint16_t (0: IDLE, 1: MOVING, 2: EMERGENCY)
} input_reg_params_t;

// Discrete inputs structure (FC 0x02)
typedef struct {
    uint8_t discrete_inputs; // Bit 0: E-Stop (0:Active, 1:OK), Bit 1: Start (1:Pressed), Bit 2: Safety Enable (1:Enabled)
} discrete_reg_params_t;

// Coils structure (FC 0x01 / 0x05)
typedef struct {
    uint8_t coils;           // Bit 0: LED Status (1:ON), Bit 1: Remote Emergency (1:Trigger), Bit 2: Remote Start (1:Trigger)
} coil_reg_params_t;

// Exported buffers for host testing & inspection
extern holding_reg_params_t g_modbus_holding_reg;
extern input_reg_params_t g_modbus_input_reg;
extern discrete_reg_params_t g_modbus_discrete_reg;
extern coil_reg_params_t g_modbus_coil_reg;

// Function prototypes
esp_err_t modbus_slave_init(void);
void modbus_slave_start_task(void);

#ifdef __cplusplus
}
#endif

#endif // MODBUS_SLAVE_H
