## Why

The linear actuator controller requires a robust state machine (`IDLE`, `MOVING`, `EMERGENCY`) and a hardware-interrupt driven safety subsystem to guarantee immediate motor cutoff upon Emergency button activation. Additionally, a thread-safe atomic state architecture, software debounce for the Start button, level-checked reset validation, and Modbus command control registers must be established for system operation and automated HIL integration testing.

## What Changes

- Implement system state machine enum (`MACHINE_STATE_IDLE`, `MACHINE_STATE_MOVING`, `MACHINE_STATE_EMERGENCY`) with atomic thread-safe state access.
- Configure `GPIO 11` (Start Button) with software debounce in the Core 0 I/O task.
- Configure `GPIO 12` (Emergency Button) as a high-priority `IRAM_ATTR` ISR triggered on falling edge.
- Implement immediate physical hardware PWM/driver cutoff within the Emergency ISR before task notification.
- Enforce strict state transition rules: `IDLE -> MOVING` requires Start command AND `GPIO 12 == HIGH`; `EMERGENCY -> IDLE` (Reset) requires Reset command AND static level check `GPIO 12 == HIGH`.
- Add Modbus Command Holding Register (`0x0001`) with flags for `START` (1), `STOP` (2), `RESET` (3), and `SIMULATE_EMERGENCY` (99).
- Add automated Python integration tests (`tests/test_state_machine.py`) using `pytest` to validate normal state transitions, emergency lockout rejection, and safe reset rules.

## Capabilities

### New Capabilities
- `state-machine-safety`: State machine management, IRAM emergency ISR with immediate PWM cutoff, level-checked reset rules, Modbus control register, and automated pytest state machine validation.

### Modified Capabilities
(None)

## Impact

- `main/shared_data.h` / `main/shared_data.c`: Updated state variable types and atomic/thread-safe access helpers.
- `main/modbus_slave.c`: Added Command Holding Register (`0x0001`) handling for remote Start, Stop, Reset, and Emergency simulation.
- `main/gpio_safety.h` / `main/gpio_safety.c`: Added GPIO 11 debounce task logic, GPIO 12 IRAM ISR with hardware cutoff, and state transition validator.
- `main/main.c`: Integrated GPIO safety and state machine initialization.
- `tests/test_state_machine.py`: Added automated pytest suite for state machine transitions.
