## ADDED Requirements

### Requirement: Modbus Discrete Inputs Interface (Function Code 0x02)
The Modbus slave SHALL expose discrete binary hardware input states under Function Code 0x02:
- Address `0x0000`: Emergency Stop Button State (`GPIO 12` — 0: Active/Pressed, 1: OK/Released)
- Address `0x0001`: Start Button State (`GPIO 11` — 1: Pressed, 0: Released)
- Address `0x0002`: Motor Driver Safety Enable Line (`GPIO 13` — 1: Enabled, 0: Disabled)

#### Scenario: Read Discrete Inputs
- **WHEN** a Modbus master sends Function Code 0x02 to read discrete inputs `0x0000` through `0x0002`
- **THEN** the system SHALL return a 1-byte bitmask containing the live physical GPIO logic states of the E-Stop button, Start button, and Safety Enable pin.

### Requirement: Modbus Coils Interface (Function Code 0x01 / 0x05)
The Modbus slave SHALL expose discrete binary output & control coils under Function Codes 0x01 (Read Coils) and 0x05 (Write Single Coil):
- Address `0x0000`: Status LED Control / State (`GPIO 7` — 1: ON, 0: OFF)
- Address `0x0001`: Remote Software Emergency Trigger (1: Force E-Stop)
- Address `0x0002`: Remote Software Start Command (1: Trigger Start)

#### Scenario: Write Coil Command
- **WHEN** a Modbus master writes `0xFF00` (ON) to Coil `0x0001` (Remote Emergency)
- **THEN** the system SHALL immediately switch the machine state to `EMERGENCY` and turn off motor PWM duty output.
