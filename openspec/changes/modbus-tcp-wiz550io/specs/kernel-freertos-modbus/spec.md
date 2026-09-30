## MODIFIED Requirements

### Requirement: Modbus RTU Slave Communication over USB-C
The system SHALL run an `esp_modbus` TCP Slave stack listening on TCP port 502 bound to `esp_netif` Ethernet interface, supporting Holding Registers for position setpoint (`0x0000-0x0001`), command (`0x0002`), Kp (`0x0003-0x0004`), Ki (`0x0005-0x0006`), and Kd (`0x0007-0x0008`), Input Registers for position (`0x0000-0x0001`), velocity (`0x0002-0x0003`), and state (`0x0004`), Discrete Inputs, and Coils.

#### Scenario: Holding Register Setpoint Write
- **WHEN** a Modbus TCP Master writes a 32-bit float value to Holding Register `0x0000-0x0001` over socket TCP 502
- **THEN** the system MUST update the `position_setpoint` field in the shared `SystemData` structure under Mutex lock.

#### Scenario: Holding Register PID Gains Read Write
- **WHEN** a Modbus TCP Master reads or writes 32-bit float values to Holding Registers `0x0003-0x0004` (Kp), `0x0005-0x0006` (Ki), or `0x0007-0x0008` (Kd)
- **THEN** the system MUST update or return the active Kp, Ki, and Kd parameters in `SystemData` under Mutex lock and apply them to the closed-loop controller.

#### Scenario: Input Registers Read
- **WHEN** a Modbus TCP Master reads Input Registers `0x0000-0x0001` (Position), `0x0002-0x0003` (Velocity), or `0x0004` (State)
- **THEN** the system MUST return the current values stored in the shared `SystemData` structure encoded in IEEE 754 Big-Endian float format or 16-bit unsigned integer.

## REMOVED Requirements

### Requirement: Serial Log Suppression
**Reason**: Replaced Modbus RTU on UART0 with Modbus TCP over Ethernet, allowing standard text logging on USB-C console.
**Migration**: Restore standard `ESP_LOG` logging output (`esp_log_level_set("*", ESP_LOG_INFO)`) on `UART_NUM_0`.

## ADDED Requirements

### Requirement: Console Serial Log Restoration
The system SHALL maintain active standard ASCII log output (`esp_log`) on `UART_NUM_0` at 115200 baud for real-time monitoring and debugging over USB-C console.

#### Scenario: Active Log Output
- **WHEN** system events, network state changes, or motor state transitions occur
- **THEN** the ESP32 MUST print formatted `esp_log` messages to `UART_NUM_0` without corrupting Modbus communication.
