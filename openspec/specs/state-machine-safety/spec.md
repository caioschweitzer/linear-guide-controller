# State Machine & Safety Specification

## Requirements

### Requirement: System State Machine and Atomic Access
The system SHALL maintain a global state machine (`machine_state_t`) with states `IDLE` (0), `MOVING` (1), and `EMERGENCY` (2). The state variable SHALL support atomic, ISR-safe read and write operations without requiring a FreeRTOS Mutex.

#### Scenario: State Initialization
- **WHEN** the firmware powers up and initializes shared data
- **THEN** the system state MUST be initialized to `IDLE` (0).

#### Scenario: ISR Safe State Change
- **WHEN** an Interrupt Service Routine (ISR) changes the machine state to `EMERGENCY`
- **THEN** it MUST perform an atomic store operation without acquiring `g_system_mutex`.

### Requirement: Emergency Button Hardware ISR and Physical Cutoff
The system SHALL configure `GPIO 12` as a falling-edge hardware interrupt (`ESP_INTR_FLAG_IRAM`) with internal pull-up. Upon triggering, the ISR SHALL immediately disable motor drive signals (PWM / Enable) at the hardware level and notify the Core 1 Control Task using `vTaskNotifyGiveFromISR`.

#### Scenario: Emergency Button Activation
- **WHEN** `GPIO 12` transitions from HIGH to LOW (Emergency button pressed)
- **THEN** the hardware interrupt MUST cut motor output instantly, transition state to `EMERGENCY`, and notify the Core 1 Control Task.

### Requirement: Level-Checked State Transitions and Safe Reset
The system SHALL enforce strict state transition guards. Transition `IDLE -> MOVING` SHALL require a Start command AND `gpio_get_level(GPIO_12) == HIGH`. Transition `EMERGENCY -> IDLE` (Reset) SHALL require a Reset command AND `gpio_get_level(GPIO_12) == HIGH`.

#### Scenario: Valid Start Transition
- **WHEN** the system is in `IDLE`, receives a Start command, and `GPIO 12` is HIGH
- **THEN** the system state MUST change to `MOVING`.

#### Scenario: Blocked Reset Attempt While Emergency Active
- **WHEN** the system is in `EMERGENCY`, receives a Reset command, but `GPIO 12` is LOW (Emergency button still pressed)
- **THEN** the Reset request MUST be rejected and the system MUST remain in `EMERGENCY`.

#### Scenario: Successful Reset Transition
- **WHEN** the system is in `EMERGENCY`, receives a Reset command, and `GPIO 12` is HIGH (Emergency released)
- **THEN** the system state MUST change to `IDLE`.

### Requirement: Modbus Command Holding Register
The system SHALL expose Holding Register `0x0001` as a Command Register accepting flags `1` (START), `2` (STOP), `3` (RESET), and `99` (SIMULATE_EMERGENCY).

#### Scenario: Remote Start via Modbus
- **WHEN** a Modbus Master writes `1` to Holding Register `0x0001` while in `IDLE` with `GPIO 12` HIGH
- **THEN** the system MUST transition to `MOVING`.

#### Scenario: Remote Emergency Simulation via Modbus
- **WHEN** a Modbus Master writes `99` to Holding Register `0x0001`
- **THEN** the system MUST immediately disable motor output and transition to `EMERGENCY`.

### Requirement: Automated State Machine Integration Test
The project SHALL include a Python test script (`tests/test_state_machine.py`) using `pytest` and `pymodbus` to validate state transitions, emergency lockout rejection, and safe reset rules over Modbus RTU.

#### Scenario: Pytest State Machine Verification
- **WHEN** `pytest tests/test_state_machine.py` is executed
- **THEN** it MUST verify initial `IDLE` state, transition to `MOVING` via Start, trigger `EMERGENCY`, confirm rejection of transition to `MOVING` while locked, and verify transition to `IDLE` upon valid `RESET`.

### Requirement: Homing Sequence with Active-LOW Zero-Volt Detection
The system SHALL execute the mechanical homing routine (`MACHINE_STATE_HOMING`) by driving the motor in the reverse direction until `GPIO 16` (`GPIO_HOME_PIN`) detects a logic LOW level (0V), indicating the magnetic contact has opened upon reaching the home datum. Upon detection, the controller SHALL apply `motor_brake`, clear the encoder position to zero, and return to `MACHINE_STATE_IDLE`.

#### Scenario: Homing motion towards origin
- **WHEN** the system enters `MACHINE_STATE_HOMING` and `GPIO 16` is HIGH (3.3V, sensor contact closed in free air)
- **THEN** the motor driver MUST drive the motor in reverse at -60.0% effort.

#### Scenario: Home datum detected
- **WHEN** the carriage brings the magnet over the home sensor, opening the contact and causing `GPIO 16` to drop to 0V (pull-down)
- **THEN** the motor driver MUST immediately apply `motor_brake`, zero the encoder accumulator, and transition to `MACHINE_STATE_IDLE`.

