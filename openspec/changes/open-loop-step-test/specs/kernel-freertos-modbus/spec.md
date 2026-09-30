## ADDED Requirements

### Requirement: Burst Data Buffer Retrieval Interface
The system SHALL expose Modbus registers to coordinate burst test data transfer between the firmware and supervisory. Holding Register `0x0009` SHALL serve as the sample index selector, and Input Registers starting at `0x0007` SHALL expose buffer status (0: Idle, 1: Running, 2: Ready, 3: Aborted), total captured points count, and the selected sample's timestamp (ms), position (float32), and velocity (float32).

#### Scenario: Sample Index Selection and Data Readout
- **WHEN** a Modbus client writes sample index `k` to Holding Register `0x0009` and reads the corresponding Input Registers
- **THEN** the firmware MUST return the recorded timestamp, position, and velocity corresponding to sample `k` without altering ongoing real-time telemetries.

#### Scenario: Buffer Status and Size Inspection
- **WHEN** a Modbus client reads the buffer status register
- **THEN** the firmware MUST report whether the buffer is currently logging, completed, or idle, alongside the total number of captured samples available for retrieval.
