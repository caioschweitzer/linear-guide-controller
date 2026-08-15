## 1. Data Model & Modbus Slave Implementation

- [x] 1.1 Update `main/shared_data.h` and `main/shared_data.c` to add atomic discrete boolean fields (`button_estop`, `button_start`, `safety_enable`, `led_status`)
- [x] 1.2 Update `main/modbus_slave.h` and `main/modbus_slave.c` to define Discrete Inputs (0x02) and Coils (0x01/0x05) register mappings and descriptors
- [x] 1.3 Update `main/main.c` snapshot updates to sync GPIO inputs and status LED coil writebacks

## 2. Automated Host Testing & Documentation Update

- [x] 2.1 Update `tests/test_modbus_kernel.py` to validate reading Discrete Inputs (FC 0x02) and reading/writing Coils (FC 0x01/0x05)
- [x] 2.2 Update `docs/modbus_and_testing.md` register map tables to document Coils and Discrete Inputs
