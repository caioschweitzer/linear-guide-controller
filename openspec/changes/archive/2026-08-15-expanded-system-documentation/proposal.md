## Why

While the ESP32-S3 linear actuator controller code and host integration test suite are complete and passing, the existing project documentation consists of high-level overview files. A comprehensive, multi-chapter technical manual suite is needed to thoroughly document the underlying physics, mechanical parameters, dual-core FreeRTOS kernel objects, Modbus RTU communication diagrams, and 32 automated host test cases.

## What Changes

- Create a structured 5-chapter documentation suite under `docs/`:
  - `docs/01_system_overview_and_physics.md`: Problem statement, mechanical properties, kinematics equations, EMA filtering, and control system requirements.
  - `docs/02_hardware_and_schematics.md`: Complete pinout specification, electrical wiring, E-stop hardware cutoff MOSFET gate, and I2C LCD/LED connections.
  - `docs/03_software_architecture_freertos.md`: Dual-core task pinning, IPC mutex snapshot locking, atomic ISR state machine transitions, and task notification flow.
  - `docs/04_modbus_rtu_and_communication.md`: Modbus RTU protocol parameters, full 4-table register map (Coils, Discrete Inputs, Holding, Input Registers), and ASCII sequence diagrams.
  - `docs/05_testing_and_hil_simulation.md`: Host GCC compilation architecture (`-DHOST_TEST`), `libsystem_integration.so` build pipeline, and exhaustive breakdown of all 32 pytest test cases across 8 modules.
- Update master `docs/README.md` to index and link the new 5-chapter manual suite.

## Capabilities

### New Capabilities
- `expanded-system-documentation`: Comprehensive 5-chapter technical documentation covering system physics, hardware wiring, FreeRTOS IPC kernel objects, Modbus sequence diagrams, and HIL unit/integration testing suite.

### Modified Capabilities
<!-- None: Code execution and hardware specs remain unchanged -->

## Impact

- `docs/`: Expanded into a 5-chapter comprehensive technical manual suite.
- `docs/README.md`: Updated master index table linking all chapters.
