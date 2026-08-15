## ADDED Requirements

### Requirement: Full Hardware and Software Technical Documentation Manual
The system SHALL provide complete technical documentation in the project repository covering hardware wiring, GPIO mappings, FreeRTOS task architecture, Modbus RTU register mapping, PID controller tuning, and test suites.

#### Scenario: Hardware Wiring and Pinout Guidance
- **WHEN** a developer inspects the documentation manual
- **THEN** the documentation SHALL clearly map ESP32-S3 GPIO pins to MCPWM motor outputs (GPIO 4, 5, 6), PCNT encoder inputs (GPIO 14, 15), GPIO safety interrupts (GPIO 11, 12, 13), I2C LCD display (GPIO 8, 9), Status LED (GPIO 7), and Modbus RTU UART0 (TX 43, RX 44).

#### Scenario: Software Architecture and Task Pinning Guidance
- **WHEN** a developer reviews the FreeRTOS dual-core task architecture
- **THEN** the documentation SHALL define Core 1 for the 100 Hz deterministic PID control task and Core 0 for I/O, Modbus RTU, and IHM display tasks, including IPC mutex snapshot access patterns.

#### Scenario: Modbus Register and Testing Verification Guidance
- **WHEN** an operator accesses the Modbus RTU interface or runs integration tests
- **THEN** the documentation SHALL specify holding register `0x0000` (Position Setpoint, Float32) and command register `0x0002` (1: START, 2: STOP, 3: RESET, 99: E-STOP), input registers `0x0000` (Position, Float32), `0x0002` (Velocity, Float32), and `0x0004` (State, uint16), along with pytest execution commands (`pytest tests/`).
