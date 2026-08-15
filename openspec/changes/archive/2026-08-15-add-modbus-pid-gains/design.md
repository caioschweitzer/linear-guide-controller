## Context

The linear guide actuator controller relies on a 100 Hz PID control loop executed on Core 1 (`control_loop_task`). While initial PID gains ($K_p = 2.0$, $K_i = 0.5$, $K_d = 0.05$) are defined as compile-time defaults in `pid_controller.h`, supervisory systems (PLCs, SCADA) require real-time read and write access over Modbus RTU to tune controller performance dynamically under varying payload conditions.

## Goals / Non-Goals

**Goals:**
- Extend the Modbus Holding Register table from 3 to 9 registers to accommodate Float32 representations for $K_p$, $K_i$, and $K_d$.
- Provide thread-safe, atomic IPC synchronization between Core 0 (Modbus slave task) and Core 1 (100 Hz PID control task).
- Automatically initialize Modbus holding registers with default gain values on startup.
- Update `g_pid` gains dynamically during active control without resetting the integrator state unless requested.

**Non-Goals:**
- Non-volatile flash (NVS) storage persistence across power reboot cycles in this release.

## Decisions

### Decision 1: Modbus Holding Register Layout
- **Holding Registers (`FC 0x03` / `FC 0x06` / `FC 0x10`)**:
  - `0x0000` - `0x0001`: `position_setpoint` (Float32, default `0.0` mm)
  - `0x0002`: `command` (uint16: `1`=START, `2`=STOP, `3`=RESET, `99`=EMERGENCY)
  - `0x0003` - `0x0004`: `kp` (Float32, default `2.0`)
  - `0x0005` - `0x0006`: `ki` (Float32, default `0.5`)
  - `0x0007` - `0x0008`: `kd` (Float32, default `0.05`)
- **Total Count**: `HOLDING_REG_COUNT` = 9 registers (18 bytes).

### Decision 2: Shared IPC Snapshotting (`shared_data.h`)
- Extend `SystemData` structure with `kp`, `ki`, `kd` float fields.
- `shared_data_init()` sets default values (`kp=2.0`, `ki=0.5`, `kd=0.05`).
- `modbus_slave_init()` populates `g_modbus_holding_reg` with initial Float32 register words.
- `modbus_slave_task` converts incoming holding register words to floats via `registers_to_float()` and updates `g_system_data`.
- `control_loop_task` detects changes in `g_system_data.kp/ki/kd` and calls `pid_set_gains(...)` on the live controller.

### Decision 3: Fail-Safe Guardrails
- If NaN or infinite float values are written, or if gains are negative ($< 0.0$), the system ignores the invalid input and preserves the current valid gains.

## Risks / Trade-offs

- **[Risk] SCADA writes unstable PID gains causing motor overshoot** → **Mitigation**: Bounds checking ($K_p \ge 0, K_i \ge 0, K_d \ge 0$) and physical software limit clamping ($0.0$ to $424.115$ mm) remain active regardless of gain settings.
- **[Risk] Mutex contention between Core 0 and Core 1** → **Mitigation**: Fast snapshot locking ($< 1$ ms lock duration) guarantees core separation.
