# IHM Display & LED Specification

## Purpose
Specifies the local Human-Machine Interface (HMI) for the linear actuator system, managing 16x2 HD44780 LCD line formatting via PCF8574 I2C expander, non-blocking GPIO 7 status LED timing, snapshot mutex IPC pattern, and I2C fault resilience.

## Requirements

### Requirement: Strict 16-Character LCD Line Formatting
The system SHALL format telemetry data for a 16x2 LCD using `snprintf` to produce line buffers of exactly 16 characters (+ null terminator), preventing buffer overflows and display misalignment.
- **Line 1**: Position in mm (`P:%7.2f mm    `)
- **Line 2**: Velocity and State (`V:%5.1f S:%-6s`)

#### Scenario: Extreme value formatting
- **WHEN** position is `12345.678` mm and state is `MOVING`
- **THEN** Line 1 and Line 2 outputs SHALL be bounded to exactly 16 visible characters

### Requirement: Non-blocking Status LED Management (GPIO 7)
The system SHALL control the status LED on GPIO 7 based on the system state without blocking task execution (`vTaskDelay` inside LED logic is forbidden):
- `STATE_INIT` / `STATE_IDLE`: Solid ON or OFF
- `STATE_HOMING` / `STATE_MOVING` / `STATE_AUTO`: 1 Hz blink (500 ms ON / 500 ms OFF)
- `STATE_EMERGENCY_STOP` / `STATE_FAULT`: 5 Hz blink (100 ms ON / 100 ms OFF)

#### Scenario: Emergency state LED indication
- **WHEN** system state enters `STATE_EMERGENCY_STOP`
- **THEN** GPIO 7 LED output SHALL toggle every 100 ms (5 Hz)

#### Scenario: Moving state LED indication
- **WHEN** system state enters `STATE_MOVING`
- **THEN** GPIO 7 LED output SHALL toggle every 500 ms (1 Hz)

### Requirement: I2C Fault Resilience
The system SHALL detect I2C transmission failures (NACK or Timeout), set `is_connected = false`, skip write attempts during failure states, and attempt bus recovery/re-initialization every 5 seconds without blocking FreeRTOS task execution.

#### Scenario: LCD disconnected during operation
- **WHEN** PCF8574 I2C write returns a transmission failure
- **THEN** driver SHALL flag disconnect state and continue task execution without crashing or blocking

### Requirement: Core 0 Non-Blocking Snapshot Mutex Pattern
The IHM task running on Core 0 SHALL read shared telemetry data via a short-timeout Mutex snapshot (`shared_data_read`), releasing the Mutex immediately before performing slow I2C LCD transmission outside the critical section.

#### Scenario: Core 0 IHM update
- **WHEN** IHM task updates display
- **THEN** Mutex hold duration SHALL be under 10 ms
