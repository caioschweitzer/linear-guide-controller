# State Machine & Safety Specification

## ADDED Requirements

### Requirement: Homing Sequence with Active-LOW Zero-Volt Detection
The system SHALL execute the mechanical homing routine (`MACHINE_STATE_HOMING`) by driving the motor in the reverse direction until `GPIO 16` (`GPIO_HOME_PIN`) detects a logic LOW level (0V), indicating the magnetic contact has opened upon reaching the home datum. Upon detection, the controller SHALL apply `motor_brake`, clear the encoder position to zero, and return to `MACHINE_STATE_IDLE`.

#### Scenario: Homing motion towards origin
- **WHEN** the system enters `MACHINE_STATE_HOMING` and `GPIO 16` is HIGH (3.3V, sensor contact closed in free air)
- **THEN** the motor driver MUST drive the motor in reverse at -60.0% effort.

#### Scenario: Home datum detected
- **WHEN** the carriage brings the magnet over the home sensor, opening the contact and causing `GPIO 16` to drop to 0V (pull-down)
- **THEN** the motor driver MUST immediately apply `motor_brake`, zero the encoder accumulator, and transition to `MACHINE_STATE_IDLE`.
