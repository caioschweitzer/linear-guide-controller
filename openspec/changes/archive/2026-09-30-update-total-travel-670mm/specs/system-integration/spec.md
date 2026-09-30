# system-integration Specification

## MODIFIED Requirements

### Requirement: Closed-Loop Control Decision & Setpoint Clamping
The control loop SHALL clamp the position setpoint within the physical rail bounds $[0.0\text{ mm}, 670.0\text{ mm}]$ and compute PID effort only when `machine_state == MACHINE_STATE_MOVING`. In `MACHINE_STATE_IDLE` or `MACHINE_STATE_EMERGENCY`, the motor duty SHALL be forced to 0.0% and `pid_reset()` executed.

#### Scenario: Normal closed-loop movement
- **WHEN** machine state is `MACHINE_STATE_MOVING` and position setpoint is set to 150.0 mm
- **THEN** PID compute method SHALL calculate control effort and update motor MCPWM duty cycle

#### Scenario: Setpoint out of physical bounds
- **WHEN** position setpoint exceeds 670.0 mm or is below 0.0 mm
- **THEN** setpoint SHALL be clamped to the safe boundary $[0.0\text{ mm}, 670.0\text{ mm}]$ before PID calculation
