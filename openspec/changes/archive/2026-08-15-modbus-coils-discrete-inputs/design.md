## Context

The firmware currently defines Holding Registers (0x03) and Input Registers (0x04) in `modbus_slave.h`. Adding Coils (0x01/0x05) and Discrete Inputs (0x02) allows external SCADA/PLC software to directly monitor physical buttons (`GPIO 11`, `GPIO 12`), safety pins (`GPIO 13`), and actuate binary outputs (`GPIO 7` Status LED).

## Goals / Non-Goals

**Goals:**
- Add Modbus Discrete Inputs descriptor (`PARAM_DISCRETE_INPUTS`) to ESP-IDF `esp_modbus` controller initialization.
- Add Modbus Coils descriptor (`PARAM_COILS`) to ESP-IDF `esp_modbus` controller initialization.
- Update `SystemData` structure in `shared_data.h` to hold discrete bit flags.
- Update Python host test framework (`test_modbus_kernel.py`) to validate discrete inputs and coil reads/writes.

**Non-Goals:**
- Removing existing Holding or Input registers (they remain fully supported).

## Decisions

### Decision 1: Register Area Descriptors in ESP-IDF `esp_modbus`
- **Choice**: Register `mb_register_area_descriptor_t` for Discrete Inputs and Coils alongside existing Holding and Input register descriptors.
- **Rationale**: Follows standard ESP-IDF Modbus stack conventions.

### Decision 2: Shared IPC Structure Bit Flags
- **Choice**: Add `bool button_estop`, `bool button_start`, `bool safety_enable`, `bool led_status` fields to `shared_data`.
- **Rationale**: Allows Core 0 Modbus task to read binary input states safely under snapshot mutex protection.

## Risks / Trade-offs

- **[Risk]**: Increased memory overhead for Modbus register descriptors.
- **Mitigation**: Discrete inputs and coils use tiny byte arrays (< 8 bits per table).
