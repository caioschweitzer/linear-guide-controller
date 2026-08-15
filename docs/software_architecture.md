# Software Architecture & Control Loop Specification

This document details the multi-core task allocation, FreeRTOS synchronization primitives, state machine transitions, kinematics calculations, and PID control algorithms implemented in the ESP32-S3 firmware.

---

## 1. FreeRTOS Dual-Core Task Distribution

To guarantee determinism in position control while serving variable-latency I/O operations, tasks are strictly partitioned across the ESP32-S3's dual cores:

```
+-----------------------------------------------------------------------+
|                             ESP32-S3 CORES                            |
+-----------------------------------++----------------------------------+
|              CORE 0               ||              CORE 1              |
|        (I/O & Communication)      ||       (Real-Time Control)        |
+-----------------------------------++----------------------------------+
| - Task_IHM (5 Hz, Pri 5)          || - Task_ControlLoop (100 Hz, Pri 10)|
|   * LCD HD44780 Refresh           ||   * PCNT Hardware Count Read     |
|   * Status LED Blinking (GPIO 7)  ||   * Kinematics Position/Velocity |
| - ModbusSlaveTask (Pri 4)         ||   * PID Effort Calculation       |
|   * Serial RTU Protocol Stack     ||   * MCPWM Duty & Direction Update|
| - StartButtonDebounceTask (Pri 4) ||                                  |
|   * Software Debounce (50 ms)     ||                                  |
+-----------------------------------++----------------------------------+
                                     ^
                                     | IRAM-Resident Emergency ISR
                                     +--- Triggered by GPIO 12 Falling Edge
```

---

## 2. Shared IPC & Mutex Snapshot Pattern

Thread-safe data exchange between Core 0 and Core 1 is governed by `g_system_mutex` and snapshot copying to avoid priority inversion and task blocking:

```c
typedef struct {
    float position_setpoint;  // Target position in mm (0.0 to 424.115 mm)
    float current_position;   // Calculated linear position in mm
    float current_velocity;   // EMA filtered linear velocity in mm/s
    uint16_t machine_state;   // 0: IDLE, 1: MOVING, 2: EMERGENCY
} SystemData;
```

### Mutex Lock Guidelines:
- **Core 1 Control Loop**: Acquires `g_system_mutex` with a short timeout ($1\text{ ms}$). Reads `position_setpoint` and writes calculated `current_position` and `current_velocity`.
- **Core 0 IHM & Modbus Tasks**: Take a local snapshot of `g_system_data` under mutex protection ($10\text{ ms}$ timeout) and release immediately before rendering or formatting frames.

---

## 3. Finite State Machine (FSM) Transition Rules

```
     +--------+   Start Button / Modbus CMD_START    +--------+
     |        | -----------------------------------> |        |
     |  IDLE  |                                      | MOVING |
     |  (0)   | <----------------------------------- |  (1)   |
     +--------+    Target Reached / Modbus CMD_STOP   +--------+
         ^                                               |
         |                                               |
         | Modbus CMD_RESET                              | GPIO 12 E-Stop /
         | (Only if GPIO 12 HIGH)                        | Hardware Interrupt
         |                                               v
         +--------------------------------------- +-----------+
                                                  | EMERGENCY |
                                                  |    (2)    |
                                                  +-----------+
```

| Transition | Required Condition | Actions Performed |
| :--- | :--- | :--- |
| `IDLE` $\rightarrow$ `MOVING` | Start button pressed OR Modbus `CMD_START` **AND** GPIO 12 == HIGH | Enable MCPWM output, activate PID loop |
| `MOVING` $\rightarrow$ `IDLE` | Target reached OR Modbus `CMD_STOP` | `pid_reset()`, zero motor duty |
| ANY $\rightarrow$ `EMERGENCY` | GPIO 12 Falling Edge (E-Stop ISR) OR Modbus `CMD_SIMULATE_EMERGENCY` | Disable GPIO 13 hardware enable, `pid_reset()`, force $0.0\%$ motor duty |
| `EMERGENCY` $\rightarrow$ `IDLE` | Modbus `CMD_RESET` **AND** GPIO 12 == HIGH (Physical switch released) | Clear emergency state, ready for new operation |

---

## 4. Kinematics & Mathematical Models

### Position Conversion:
$$\text{Position (mm)} = (\text{Raw Count} - \text{Zero Offset}) \times \text{Direction} \times K_{\text{mm}}$$

where $K_{\text{mm}} = \frac{42.4115\text{ mm}}{1000\text{ counts}} = 0.0424115\text{ mm/count}$.

### EMA Velocity Filtering:
Instantaneous velocity $v_{\text{inst}} = \frac{x_k - x_{k-1}}{\Delta t}$.  
Filtered velocity:
$$v_k = \alpha \cdot v_{\text{inst}} + (1 - \alpha) \cdot v_{k-1} \quad (\text{default } \alpha = 0.2)$$

---

## 5. PID Control Algorithm & Safety Features

- **Proportional Gain ($K_p$)**: $2.0$
- **Integral Gain ($K_i$)**: $0.5$ (with conditional anti-windup freezing integration during saturation)
- **Derivative Gain ($K_d$)**: $0.05$ (derivative computed on measurement to eliminate setpoint step kick)
- **Output Limits**: $-100.0\%$ to $+100.0\%$ PWM effort
- **Deadband**: $\pm 0.05\text{ mm}$ (zeros output effort when error is within deadband)
- **Setpoint Boundary Clamping**: $[0.0\text{ mm}, 424.115\text{ mm}]$
