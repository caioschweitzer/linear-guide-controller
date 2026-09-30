## MODIFIED Requirements

### Requirement: System State Machine and Atomic Access
The system SHALL maintain a global state machine (`machine_state_t`) with states `IDLE` (0), `MOVING` (1), `EMERGENCY` (2), `HOMING` (3), and `OPEN_LOOP_TEST` (4). The state variable SHALL support atomic, ISR-safe read and write operations without requiring a FreeRTOS Mutex.

#### Scenario: State Initialization
- **WHEN** the firmware powers up and initializes shared data
- **THEN** the system state MUST be initialized to `IDLE` (0).

#### Scenario: ISR Safe State Change
- **WHEN** an Interrupt Service Routine (ISR) changes the machine state to `EMERGENCY`
- **THEN** it MUST perform an atomic store operation without acquiring `g_system_mutex`.

#### Scenario: Open Loop Test State Activation
- **WHEN** an authorized open-loop test command is accepted from `IDLE`
- **THEN** the machine state MUST transition to `OPEN_LOOP_TEST` (4).

### Requirement: Modbus Command Holding Register
The system SHALL expose Holding Register `0x0002` (or offset `0x0001` per legacy mapping) as a Command Register accepting flags `1` (START), `2` (STOP), `3` (RESET), `4` (HOME), `5` (OPEN_LOOP_TEST), and `99` (SIMULATE_EMERGENCY).

#### Scenario: Remote Start via Modbus
- **WHEN** a Modbus Master writes `1` to the Command Register while in `IDLE` with `GPIO 12` HIGH
- **THEN** the system MUST transition to `MOVING`.

#### Scenario: Remote Open Loop Test via Modbus
- **WHEN** a Modbus Master writes `5` to the Command Register while in `IDLE` with $|pos| \le 5.0\text{ mm}$ and `GPIO 12` HIGH
- **THEN** the system MUST transition to `OPEN_LOOP_TEST`.

#### Scenario: Remote Emergency Simulation via Modbus
- **WHEN** a Modbus Master writes `99` to the Command Register
- **THEN** the system MUST immediately disable motor output and transition to `EMERGENCY`.
