## 1. Shared IPC & Data Structures

- [x] 1.1 Update `SystemData` in `main/include/shared_data.h` to include `kp`, `ki`, and `kd` float fields
- [x] 1.2 Initialize default PID gains (`kp=2.0f`, `ki=0.5f`, `kd=0.05f`) in `shared_data.c`

## 2. Modbus Slave Driver Expansion

- [x] 2.1 Expand `holding_reg_params_t` and `HOLDING_REG_COUNT` from 3 to 9 in `main/include/modbus_slave.h`
- [x] 2.2 Update `modbus_slave_init` and `modbus_slave_task` in `main/src/modbus_slave.c` to encode/decode Float32 PID gains for registers `0x0003-0x0008`

## 3. Control Loop Synchronization

- [x] 3.1 Update `control_loop_task` in `main/src/main.c` to check for updated PID gains in `g_system_data` and call `pid_set_gains(&g_pid, ...)`

## 4. Documentation & Test Suite Update

- [x] 4.1 Update Chapter 4 Modbus documentation (`docs/04_modbus_rtu_and_communication.md`) with holding registers `0x0003` to `0x0008`
- [x] 4.2 Update Pytest test suite (`tests/test_modbus_kernel.py`) to test reading and writing PID gains over Modbus
