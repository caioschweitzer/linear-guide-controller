## Why

Standard industrial PLCs and HMIs use standard Modbus RTU Discrete Inputs (Read-Only 1-bit) and Coils (Read/Write 1-bit) for physical I/O control and telemetry. Currently, all system state and binary flags are mapped to 16-bit Holding and Input registers. Adding Discrete Inputs and Coils expands the Modbus slave capabilities to conform with standard industrial 4-table Modbus architecture.

## What Changes

- Add Modbus Discrete Inputs (Function Code 0x02):
  - `0x0000`: E-Stop Button Pin State (`GPIO 12` — 0: Pressed/Active, 1: Released/OK)
  - `0x0001`: Start Push Button Pin State (`GPIO 11` — 1: Pressed, 0: Released)
  - `0x0002`: Hardware Safety Enable Line (`GPIO 13` — 1: Enabled, 0: Disabled)
- Add Modbus Coils (Function Code 0x01 / 0x05):
  - `0x0000`: Status LED Control / Readback (`GPIO 7` — 1: ON, 0: OFF)
  - `0x0001`: Remote Software Emergency Trigger (1: Active)
  - `0x0002`: Remote Software Start Command (1: Active)
- Update `main/modbus_slave.h` and `main/modbus_slave.c` to configure `PARAM_DISCRETE_INPUTS` and `PARAM_COILS` register areas in ESP-IDF `esp_modbus`.
- Extend `main/shared_data.h` and `main/shared_data.c` to maintain atomic binary flag fields for button and LED states.
- Update documentation and Python pytest suite (`tests/test_modbus_kernel.py`).

## Capabilities

### New Capabilities
- `modbus-coils-discrete-inputs`: Modbus RTU Discrete Inputs (FC 0x02) and Coils (FC 0x01/0x05) mapping for physical buttons, LED indicator, and software binary triggers.

### Modified Capabilities
<!-- None -->

## Impact

- `main/modbus_slave.h` / `main/modbus_slave.c`: Register area descriptors expansion in ESP-IDF.
- `main/shared_data.h` / `main/shared_data.c`: Additional atomic bit fields in shared data structure.
- `tests/test_modbus_kernel.py`: New unit test cases for reading discrete inputs and reading/writing coils.
- `docs/modbus_and_testing.md`: Update register map documentation.
