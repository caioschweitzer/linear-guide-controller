## Context

The linear actuator controller requires detailed technical documentation that serves as an end-to-end engineering manual. The documentation must clearly describe mechanical physics, dual-core FreeRTOS IPC, Modbus slave communications, and automated host unit/integration testing.

## Goals / Non-Goals

**Goals:**
- Author 5 structured Markdown manuals under `docs/`:
  1. `01_system_overview_and_physics.md`
  2. `02_hardware_and_schematics.md`
  3. `03_software_architecture_freertos.md`
  4. `04_modbus_rtu_and_communication.md`
  5. `05_testing_and_hil_simulation.md`
- Provide clear ASCII sequence diagrams for multi-core IPC, emergency ISR handling, and Modbus master-slave telemetry transactions.
- Document all 32 pytest test cases in `tests/` with exact assertions and test conditions.

**Non-Goals:**
- Modifying application C source files or test scripts.

## Decisions

- **Modular Chaptered Layout**: Split documentation into numbered chapter files (`01_` through `05_`) for easy readability, maintenance, and clear sectioning.
- **ASCII Sequence & Data Flow Diagrams**: Use clear ASCII art diagrams to illustrate task pinning, state machine transitions, and Modbus request/response handling.

## Risks / Trade-offs

- [Risk]: Documentation becoming out of sync with future code refactoring.
  - *Mitigation*: Reference exact header files (`main/include/`) and test modules (`tests/`) directly in the manual text.
