#ifndef MODBUS_SLAVE_H
#define MODBUS_SLAVE_H

#include <stdint.h>
#include <stdbool.h>
#include "esp_err.h"

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

// Function prototypes
esp_err_t modbus_slave_init(void);
void modbus_slave_start_task(void);

#ifdef __cplusplus
}
#endif

#endif // MODBUS_SLAVE_H
