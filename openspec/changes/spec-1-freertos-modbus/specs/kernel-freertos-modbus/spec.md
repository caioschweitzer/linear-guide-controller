## ADDED Requirements

### Requirement: Thread-Safe IPC Shared Data System
The system SHALL provide a global `SystemData` structure protected by a FreeRTOS Mutex (`SemaphoreHandle_t`) to safely exchange operational parameters between Core 0 and Core 1.

#### Scenario: Mutex Protected Read Write
- **WHEN** Core 0 or Core 1 accesses operational parameters (setpoint, current position, current velocity, machine state)
- **THEN** the system MUST acquire the Mutex before reading or writing and release it immediately after.

### Requirement: Modbus RTU Slave Communication over USB-C
The system SHALL run an `esp_modbus` RTU Slave stack on `UART_NUM_0` at 115200 baud, 8 data bits, no parity, 1 stop bit, with Slave ID 1 via the onboard USB-C serial port.

#### Scenario: Holding Register Setpoint Write
- **WHEN** a Modbus Master writes a 32-bit float value to Holding Register `0x0000-0x0001`
- **THEN** the system MUST update the `position_setpoint` field in the shared `SystemData` structure under Mutex lock.

#### Scenario: Input Registers Read
- **WHEN** a Modbus Master reads Input Registers `0x0000-0x0001` (Position), `0x0002-0x0003` (Velocity), or `0x0004` (State)
- **THEN** the system MUST return the current values stored in the shared `SystemData` structure encoded in IEEE 754 Big-Endian float format or 16-bit unsigned integer.

### Requirement: Serial Log Suppression
The system SHALL disable standard text logger output (`ESP_LOG_NONE`) on `UART_NUM_0` to prevent interference with binary Modbus RTU frames.

#### Scenario: Pure Modbus Binary Output
- **WHEN** the ESP32-S3 boots and runs
- **THEN** no plain ASCII log messages SHALL be transmitted over `UART_NUM_0`.

### Requirement: Core 1 Placeholder Control Task
The system SHALL create a FreeRTOS Task pinned to Core 1 running periodically at 100Hz (10ms interval) as a placeholder for the future control loop.

#### Scenario: Periodic Execution on Core 1
- **WHEN** the firmware is running
- **THEN** the placeholder task MUST execute on Core 1 every 10ms using `vTaskDelay` or `vTaskDelayUntil`.

### Requirement: Automated HIL Pytest Integration
The project SHALL include a Python test script (`tests/test_modbus_kernel.py`) using `pytest` and `pymodbus` to validate serial Modbus RTU communication against the ESP32-S3.

#### Scenario: Automated Modbus Loopback Test
- **WHEN** `pytest tests/test_modbus_kernel.py` is executed over the serial port
- **THEN** it MUST successfully connect to Slave ID 1, write a float setpoint to Holding Register `0x0000`, verify the written setpoint, and read initial Input Registers values.
