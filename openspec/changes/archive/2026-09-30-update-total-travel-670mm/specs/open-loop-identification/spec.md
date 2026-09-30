# open-loop-identification Specification

## ADDED Requirements

### Requirement: Open-Loop Step Test Routine at Full Effort up to 80% Travel
The firmware SHALL provide a deterministic open-loop test routine executing within the 100 Hz Core 1 control loop. When activated, the routine SHALL drive the motor with +100.0% effort until the linear position reaches or exceeds 80% of the total 670 mm travel ($536.0\text{ mm}$, 80% of $670.0\text{ mm}$) or a safety timeout of $5.0\text{ seconds}$ expires. Upon reaching the 80% threshold or timeout, the system SHALL immediately engage active braking (`motor_brake`), set effort to 0.0%, and transition to `MACHINE_STATE_IDLE`.

#### Scenario: Full Effort Drive to 80% of Stroke
- **WHEN** the open-loop step test routine is triggered from `MACHINE_STATE_IDLE`
- **THEN** the motor driver MUST output +100.0% duty cycle continuously until position reaches $\ge 536.0\text{ mm}$.

#### Scenario: Active Braking on 80% Travel Threshold
- **WHEN** current linear position reaches or exceeds $536.0\text{ mm}$ during the test
- **THEN** the firmware MUST instantly cut motor duty to 0%, apply electromagnetic braking, and transition to `MACHINE_STATE_IDLE`, leaving $134.0\text{ mm}$ of clearance before the mechanical endstop.

#### Scenario: Safety Timeout Triggered
- **WHEN** the test runs for longer than $5.0\text{ seconds}$ without reaching $536.0\text{ mm}$
- **THEN** the firmware MUST immediately abort the test, apply active braking, cut motor duty to 0%, and mark buffer status as aborted.

### Requirement: Extended Internal RAM Burst Capture Buffer
The firmware SHALL allocate an internal memory buffer in RAM capable of recording at least 550 data points at 100 Hz ($10\text{ ms}$ interval, representing up to $5.5\text{ seconds}$ of travel), capturing relative timestamp (milliseconds), position (mm), and velocity (mm/s).

#### Scenario: High-Resolution 100 Hz Logging
- **WHEN** the system is in `MACHINE_STATE_OPEN_LOOP_TEST`
- **THEN** each 10 ms cycle MUST append timestamp, position, and velocity into the RAM buffer until reaching $536.0\text{ mm}$ or timeout.

#### Scenario: Buffer Ready Signaled
- **WHEN** the test completes upon reaching 80% of travel ($536.0\text{ mm}$)
- **THEN** the buffer status MUST be set to Ready and the recorded sample count published via Modbus.

### Requirement: Supervisory UI Indicator and CSV Data Export
The supervisory software SHALL reflect the 80% travel target ($536\text{ mm}$) in UI controls, automatically retrieve the burst buffer upon test completion, and prompt the user to save the trajectory data to a `.csv` file.

#### Scenario: Supervisory UI Action
- **WHEN** the operator inspects the supervisory motion controls
- **THEN** the open-loop test button MUST display the updated 80% / 536 mm target.

#### Scenario: Complete Trajectory Export
- **WHEN** the supervisory downloads the completed 80% burst buffer
- **THEN** it MUST plot the trajectory and prompt the user to save the complete dataset to a CSV file containing `time_s`, `position_mm`, `velocity_mm_s`, and `duty_pct`.
