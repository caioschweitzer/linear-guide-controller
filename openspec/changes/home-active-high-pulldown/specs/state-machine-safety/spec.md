## ADDED Requirements

### Requirement: Active-HIGH Home Sensor Electrical Configuration
The system SHALL configure `GPIO 16` (`GPIO_HOME_PIN`) as a digital input with internal pull-down enabled (`GPIO_PULLDOWN_ENABLE`) and internal pull-up disabled (`GPIO_PULLUP_DISABLE`) to interface with an Active-HIGH mechanical/optical limit switch.

#### Scenario: Pin Initialization
- **WHEN** the firmware initializes GPIO safety peripherals via `gpio_safety_init()`
- **THEN** `GPIO 16` MUST have its internal pull-down resistor enabled and pull-up resistor disabled.

### Requirement: Active-HIGH Homing Zero Calibration Routine
While in `MACHINE_STATE_HOMING`, the control loop SHALL continuously drive the motor in reverse at creep speed (`-15.0%` PWM effort) and monitor `GPIO 16`. When `gpio_get_level(GPIO_HOME_PIN) != 0` (Active-HIGH signal detected), the controller SHALL immediately brake the motor, set effort to `0.0%`, reset encoder PCNT counts, reset kinematic estimators, and transition the machine state to `MACHINE_STATE_IDLE`.

#### Scenario: Home Sensor Triggered during Homing
- **WHEN** the machine is in `MACHINE_STATE_HOMING` and `GPIO 16` reads HIGH (`!= 0`)
- **THEN** the motor MUST be actively braked, encoder counts cleared to zero, kinematics filter reset, and machine state set to `MACHINE_STATE_IDLE`.

#### Scenario: Home Sensor Not Yet Triggered
- **WHEN** the machine is in `MACHINE_STATE_HOMING` and `GPIO 16` reads LOW (`== 0`)
- **THEN** the motor MUST continue driving at creep effort (`-15.0%`).

### Requirement: Discrete Input Telemetry Active-HIGH Mapping
The Modbus slave task SHALL read the level of `GPIO 16` and reflect its status in the Discrete Inputs register (Bit 3). Bit 3 SHALL be set to `1` when `GPIO 16` is HIGH (sensor active) and `0` when LOW (sensor idle).

#### Scenario: Sensor Actuation Reflected in Modbus Telemetry
- **WHEN** `GPIO 16` is physically at 3.3V (HIGH)
- **THEN** the discrete inputs register Bit 3 MUST be evaluated as `1`.
