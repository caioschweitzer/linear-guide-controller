## Context

The ESP32-S3 linear actuator controller system consists of 8 firmware modules (`shared_data`, `gpio_safety`, `linear_kinematics`, `encoder_pcnt`, `motor_mcpwm`, `pid_controller`, `ihm_display`, `modbus_slave`, `main`) and 8 Python host unit/integration test suites.

To provide clear operational guidance, a structured documentation folder (`docs/`) will be created containing a main system manual (`README.md`), hardware pinout schematic guide, software architecture overview, and API/Modbus register reference.

## Goals / Non-Goals

**Goals:**
- Create a complete hardware and software documentation manual under `docs/`.
- Document all ESP32-S3 physical GPIO assignments, power connections, and peripheral interfaces.
- Document FreeRTOS task configuration, core pinning, IPC mutex patterns, and state machine rules.
- Document Modbus RTU register mapping and testing instructions.

**Non-Goals:**
- Modifying underlying firmware functionality or C source code logic.

## Decisions

### Decision 1: Structure Documentation under `docs/` Directory
- **Choice**: Store Markdown documentation in `docs/` with dedicated sections:
  - `docs/README.md`: Master Documentation & Quick Start
  - `docs/hardware_wiring.md`: Schematic & GPIO Pinout Table
  - `docs/software_architecture.md`: FreeRTOS Tasks, Core Allocation & State Machine
  - `docs/modbus_and_testing.md`: Modbus Register Map & Pytest HIL/Host Verification
- **Rationale**: Keeps technical manual clean, modular, and easy to maintain alongside code.

## Risks / Trade-offs

- **[Risk]**: Documentation drift as future features are added.
- **Mitigation**: Link specification requirements in `openspec/specs/` to corresponding `docs/` sections.
