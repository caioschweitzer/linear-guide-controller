# Kernel FreeRTOS & Modbus Specification

## ADDED Requirements

### Requirement: Home Sensor Discrete Input Reporting
The system SHALL expose the physical state of the Home sensor on Discrete Input Bit 3 via Modbus Function Code 0x02, reporting `1` (Active/Detected) when `GPIO 16` is LOW (0V) and `0` (Clear/Inactive) when `GPIO 16` is HIGH (3.3V).

#### Scenario: Telemetry when magnet is absent
- **WHEN** `GPIO 16` is HIGH (3.3V)
- **THEN** Discrete Input Bit 3 SHALL be `0` (CLEAR).

#### Scenario: Telemetry when magnet is present
- **WHEN** `GPIO 16` is LOW (0V)
- **THEN** Discrete Input Bit 3 SHALL be `1` (DETECTED).
