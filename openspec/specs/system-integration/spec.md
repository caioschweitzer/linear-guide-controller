# system-integration Specification

## Purpose
TBD - created by archiving change final-system-integration. Update Purpose after archive.
## Requirements
### Requirement: Deterministic 100 Hz Control Task Pinned to Core 1
The system SHALL execute the closed-loop control task (`Task_ControlLoop`) pinned strictly to FreeRTOS Core 1 at a period of 10 ms (100 Hz) using `vTaskDelayUntil`, guaranteeing deterministic execution timing without starvation from Core 0 tasks.

#### Scenario: 100 Hz timing invariance
- **WHEN** Core 0 handles Modbus RTU packets or I2C LCD transmissions
- **THEN** Core 1 control loop period SHALL remain invariant at 10 ms ± 0.1 ms

### Requirement: Closed-Loop Control Decision & Setpoint Clamping
The control loop SHALL clamp the position setpoint within the physical rail bounds $[0.0\text{ mm}, 424.115\text{ mm}]$ and compute PID effort only when `machine_state == MACHINE_STATE_MOVING`. In `MACHINE_STATE_IDLE` or `MACHINE_STATE_EMERGENCY`, the motor duty SHALL be forced to 0.0% and `pid_reset()` executed.

#### Scenario: Normal closed-loop movement
- **WHEN** machine state is `MACHINE_STATE_MOVING` and position setpoint is set to 150.0 mm
- **THEN** PID compute method SHALL calculate control effort and update motor MCPWM duty cycle

#### Scenario: Setpoint out of physical bounds
- **WHEN** position setpoint exceeds 424.115 mm or is below 0.0 mm
- **THEN** setpoint SHALL be clamped to the safe boundary before PID calculation

### Requirement: Immediate Emergency Interception
The control loop SHALL check the atomic safety state (`gpio_safety_is_emergency_active()`) every 10 ms cycle. If active, the motor duty SHALL immediately drop to 0.0%, the state transitioned to `MACHINE_STATE_EMERGENCY`, and the PID state reset.

#### Scenario: Emergency E-Stop activation during motion
- **WHEN** GPIO 12 emergency button is triggered while motor is moving
- **THEN** MCPWM duty cycle SHALL drop to 0.0% within the current control loop iteration

### Requirement: Dual-Core Non-Blocking Snapshot Mutex IPC
The system SHALL synchronize global data (`g_system_data`) between Core 0 and Core 1 using `g_system_mutex` with short-timeout snapshot locks (< 1 ms), preventing lock contention between control and communication tasks.

#### Scenario: Core 0 IHM and Core 1 Control concurrent read/write
- **WHEN** Core 0 IHM task reads telemetry snapshot while Core 1 Control task updates position/velocity
- **THEN** mutex lock duration SHALL be under 1 ms for both cores

