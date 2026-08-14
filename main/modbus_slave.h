#ifndef MODBUS_SLAVE_H
#define MODBUS_SLAVE_H

#include <stdint.h>
#include <stdbool.h>
#include "esp_err.h"

#ifdef __cplusplus
extern "C" {
#endif

// Modbus Register Map Offsets & Sizes
#define HOLDING_REG_START_ADDR  0x0000
#define HOLDING_REG_COUNT       2      // 1 Float32 (2 x 16-bit registers)

#define INPUT_REG_START_ADDR    0x0000
#define INPUT_REG_COUNT         5      // Pos (2 regs float32), Vel (2 regs float32), State (1 reg uint16)

// Holding register structure
typedef struct {
    uint16_t setpoint_hi; // MSW
    uint16_t setpoint_lo; // LSW
} holding_reg_params_t;

// Input register structure
typedef struct {
    uint16_t pos_hi;   // Float32 MSW
    uint16_t pos_lo;   // Float32 LSW
    uint16_t vel_hi;   // Float32 MSW
    uint16_t vel_lo;   // Float32 LSW
    uint16_t state;    // uint16_t
} input_reg_params_t;

// Function prototypes
esp_err_t modbus_slave_init(void);
void modbus_slave_start_task(void);

#ifdef __cplusplus
}
#endif

#endif // MODBUS_SLAVE_H
