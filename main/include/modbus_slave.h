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

// Modbus RTU Serial Configuration (UART0 via onboard USB-C serial bridge)
#define MB_SLAVE_ADDR           1
#define MB_UART_PORT_NUM        0          // UART_NUM_0
#define MB_UART_BAUDRATE        115200     // 8N1

// Modbus Command Register Flags
#define CMD_NONE                0
#define CMD_START               1
#define CMD_STOP                2
#define CMD_RESET               3
#define CMD_HOME                4
#define CMD_OPEN_LOOP_TEST      5
#define CMD_SIMULATE_EMERGENCY  99

// Modbus Register Map Offsets & Sizes
#define HOLDING_REG_START_ADDR  0x0000
#define HOLDING_REG_COUNT       15     // Setpoint (2), Command (1), Kp (2), Ki (2), Kd (2), Burst Read Index (1), OL PWM (2), OL Mode (1), OL Coast Pos (2)

#define INPUT_REG_START_ADDR    0x0000
#define INPUT_REG_COUNT         17     // Pos (2), Vel (2), Duty (2), State (1), Burst Status (1), Count (1), Time (2), Pos (2), Vel (2), Duty (2)

#define DISCRETE_REG_START_ADDR 0x0000
#define DISCRETE_REG_COUNT      3      // E-Stop (Bit 0), Start (Bit 1), Safety Enable (Bit 2)

#define COIL_REG_START_ADDR     0x0000
#define COIL_REG_COUNT          3      // LED Status (Bit 0), Remote Emergency (Bit 1), Remote Start (Bit 2)

// Holding register structure
typedef struct {
    uint16_t setpoint_hi;      // 0x0000 Float32 MSW
    uint16_t setpoint_lo;      // 0x0001 Float32 LSW
    uint16_t command;          // 0x0002 uint16 (1: START, 2: STOP, 3: RESET, 4: HOME, 5: OPEN_LOOP_TEST, 99: SIMULATE_EMERGENCY)
    uint16_t kp_hi;            // 0x0003 Float32 MSW
    uint16_t kp_lo;            // 0x0004 Float32 LSW
    uint16_t ki_hi;            // 0x0005 Float32 MSW
    uint16_t ki_lo;            // 0x0006 Float32 LSW
    uint16_t kd_hi;            // 0x0007 Float32 MSW
    uint16_t kd_lo;            // 0x0008 Float32 LSW
    uint16_t burst_read_index; // 0x0009 uint16 Sample index to read (0 to 399)
    uint16_t open_loop_pwm_hi; // 0x000A Float32 MSW (1.0 to 100.0 %)
    uint16_t open_loop_pwm_lo; // 0x000B Float32 LSW (1.0 to 100.0 %)
    uint16_t open_loop_mode;   // 0x000C uint16 (0: BRAKE, 1: COAST)
    uint16_t open_loop_coast_pos_hi; // 0x000D Float32 MSW (50.0 to 536.0 mm)
    uint16_t open_loop_coast_pos_lo; // 0x000E Float32 LSW (50.0 to 536.0 mm)
} holding_reg_params_t;

// Input register structure
typedef struct {
    uint16_t pos_hi;             // Float32 MSW (0x0000)
    uint16_t pos_lo;             // Float32 LSW (0x0001)
    uint16_t vel_hi;             // Float32 MSW (0x0002)
    uint16_t vel_lo;             // Float32 LSW (0x0003)
    uint16_t duty_hi;            // Float32 MSW (0x0004)
    uint16_t duty_lo;            // Float32 LSW (0x0005)
    uint16_t state;              // uint16_t (0: IDLE, 1: MOVING, 2: EMERGENCY, 3: HOMING, 4: OPEN_LOOP_TEST) (0x0006)
    uint16_t burst_status;       // uint16_t (0: IDLE, 1: CAPTURING, 2: READY, 3: ABORTED) (0x0007)
    uint16_t burst_sample_count; // uint16_t total recorded samples (0x0008)
    uint16_t sample_time_hi;     // uint32_t ms MSW (0x0009)
    uint16_t sample_time_lo;     // uint32_t ms LSW (0x000A)
    uint16_t sample_pos_hi;      // Float32 MSW (0x000B)
    uint16_t sample_pos_lo;      // Float32 LSW (0x000C)
    uint16_t sample_vel_hi;      // Float32 MSW (0x000D)
    uint16_t sample_vel_lo;      // Float32 LSW (0x000E)
    uint16_t sample_duty_hi;     // Float32 MSW (0x000F)
    uint16_t sample_duty_lo;     // Float32 LSW (0x0010)
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
void modbus_slave_sync_buffers(void);

#ifdef __cplusplus
}
#endif

#endif // MODBUS_SLAVE_H
