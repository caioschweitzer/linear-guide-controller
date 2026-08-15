## Why

Currently, PID control gains ($K_p$, $K_i$, $K_d$) are hardcoded at compile time in `pid_controller.h`. Industrial supervisory systems (SCADA, PLCs, and host software) require real-time visibility and dynamic gain tuning over Modbus RTU to optimize closed-loop linear actuator response under varying loads without recompiling firmware.

## What Changes

- **Modbus Holding Register Expansion**: Expand the Holding Register map to expose Float32 registers for $K_p$ (`0x0003`-`0x0004`), $K_i$ (`0x0005`-`0x0006`), and $K_d$ (`0x0007`-`0x0008`).
- **Thread-Safe Telemetry Integration**: Extend `SystemData` in `shared_data.h` to store current PID parameters and synchronize them atomically between Core 0 (Modbus task) and Core 1 (100 Hz PID control task).
- **Dynamic Gain Tuning**: Update `main.c` control loop to dynamically apply updated $K_p$, $K_i$, and $K_d$ values to `g_pid` when modified via Modbus RTU transactions.
- **Documentation & Test Coverage**: Update Chapter 4 Modbus documentation (`docs/04_modbus_rtu_and_communication.md`) and extend the pytest verification suite (`tests/test_modbus_kernel.py`).

## Capabilities

### New Capabilities
None.

### Modified Capabilities
- `pid-controller`: Require support for dynamic runtime gain updating during active closed-loop control.
- `kernel-freertos-modbus`: Expand holding register memory map from 3 to 9 registers (`0x0000` through `0x0008`) to support PID gain read/write operations.

## Impact

- `main/include/modbus_slave.h` & `main/src/modbus_slave.c`: Update `holding_reg_params_t` struct and `HOLDING_REG_COUNT` from 3 to 9 registers.
- `main/include/shared_data.h`: Add `kp`, `ki`, `kd` parameters to `SystemData`.
- `main/src/main.c`: Call `pid_set_gains(...)` in `control_loop_task` when gains change.
- `docs/04_modbus_rtu_and_communication.md`: Add holding registers `0x0003` to `0x0008` to table and documentation.
- `tests/test_modbus_kernel.py`: Add unit test cases for PID gain read/write Modbus registers.
