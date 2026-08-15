## MODIFIED Requirements

### Requirement: Modbus RTU Slave Communication over USB-C
The system SHALL run an `esp_modbus` RTU Slave stack on `UART_NUM_0` at 115200 baud, 8 data bits, no parity, 1 stop bit, with Slave ID 1 via the onboard USB-C serial port, supporting Holding Registers for position setpoint (`0x0000-0x0001`), command (`0x0002`), Kp (`0x0003-0x0004`), Ki (`0x0005-0x0006`), and Kd (`0x0007-0x0008`).

#### Scenario: Holding Register Setpoint Write
- **WHEN** a Modbus Master writes a 32-bit float value to Holding Register `0x0000-0x0001`
- **THEN** the system MUST update the `position_setpoint` field in the shared `SystemData` structure under Mutex lock.

#### Scenario: Holding Register PID Gains Read Write
- **WHEN** a Modbus Master reads or writes 32-bit float values to Holding Registers `0x0003-0x0004` (Kp), `0x0005-0x0006` (Ki), or `0x0007-0x0008` (Kd)
- **THEN** the system MUST update or return the active Kp, Ki, and Kd parameters in `SystemData` under Mutex lock and apply them to the closed-loop controller.

#### Scenario: Input Registers Read
- **WHEN** a Modbus Master reads Input Registers `0x0000-0x0001` (Position), `0x0002-0x0003` (Velocity), or `0x0004` (State)
- **THEN** the system MUST return the current values stored in the shared `SystemData` structure encoded in IEEE 754 Big-Endian float format or 16-bit unsigned integer.
