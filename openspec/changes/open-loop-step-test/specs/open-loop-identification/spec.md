# Open-Loop Identification Specification

## ADDED Requirements

### Requirement: Open-Loop Step Test Routine at Full Effort
The firmware SHALL provide a deterministic open-loop test routine executing within the 100 Hz Core 1 control loop. When activated, the routine SHALL drive the motor with +100.0% effort until the linear position reaches or exceeds half of the total travel ($212.0\text{ mm}$, half of $424.115\text{ mm}$) or a safety timeout of $2.5\text{ seconds}$ expires. Upon reaching the threshold or timeout, the system SHALL immediately engage active braking (`motor_brake`), set effort to 0.0%, and transition to `MACHINE_STATE_IDLE`.

#### Scenario: Full Effort Drive to Mid-Stroke
- **WHEN** the open-loop step test routine is triggered from `MACHINE_STATE_IDLE`
- **THEN** the motor driver MUST output +100.0% duty cycle continuously until position reaches $\ge 212.0\text{ mm}$.

#### Scenario: Active Braking on Threshold Reached
- **WHEN** current linear position reaches or exceeds $212.0\text{ mm}$ during the test
- **THEN** the firmware MUST instantly cut motor duty to 0%, apply electromagnetic braking, and set the state to `MACHINE_STATE_IDLE`.

#### Scenario: Safety Timeout Triggered
- **WHEN** the test runs for longer than $2.5\text{ seconds}$ without reaching $212.0\text{ mm}$
- **THEN** the firmware MUST immediately abort the test, apply braking, cut motor duty to 0%, and log a timeout event.

### Requirement: Safety Interlock and Zero Position Pre-Condition
The firmware and supervisory SHALL enforce pre-conditions before allowing execution of the open-loop test routine. The routine SHALL be rejected if the current position absolute value is greater than $5.0\text{ mm}$ ($|pos| > 5.0\text{ mm}$) or if the emergency safety interlock is active.

#### Scenario: Initiation Rejection Away from Zero
- **WHEN** the open-loop test command is received while $|pos| > 5.0\text{ mm}$
- **THEN** the firmware MUST reject the command, keep motor effort at 0.0%, and remain in `MACHINE_STATE_IDLE`.

#### Scenario: Initiation Rejection Under Emergency
- **WHEN** the open-loop test command is received while in `MACHINE_STATE_EMERGENCY` or while E-stop is tripped
- **THEN** the firmware MUST reject the command and maintain safety lockout.

#### Scenario: Successful Initiation Near Zero
- **WHEN** the open-loop test command is received while $|pos| \le 5.0\text{ mm}$ and system is healthy in `MACHINE_STATE_IDLE`
- **THEN** the firmware MUST transition to `MACHINE_STATE_OPEN_LOOP_TEST` and commence data acquisition.

### Requirement: Internal RAM Burst Capture Buffer
The firmware SHALL allocate an internal memory buffer in RAM capable of recording at least 300 data points at 100 Hz ($10\text{ ms}$ interval), capturing relative timestamp (milliseconds), position (mm), and velocity (mm/s). The firmware SHALL expose registers indicating test status (0: Idle, 1: Capturing, 2: Ready/Complete, 3: Aborted) and the total number of captured points.

#### Scenario: Deterministic 100 Hz Data Sampling
- **WHEN** the system enters `MACHINE_STATE_OPEN_LOOP_TEST`
- **THEN** every 10 ms cycle MUST append relative timestamp, current position, and current velocity into the RAM buffer until completion.

#### Scenario: Buffer Completion Flagging
- **WHEN** the test stops (either by reaching 212.0 mm or timing out)
- **THEN** the buffer status MUST be set to Ready/Complete and the total sample count MUST be published for retrieval.

### Requirement: Supervisory Trigger and CSV Data Export
The supervisory software SHALL provide a dedicated control button to trigger the open-loop test, read the captured burst buffer points from the ESP32 via Modbus upon test completion, and prompt the user to save the trajectory data to a `.csv` file.

#### Scenario: Supervisory Test Triggering
- **WHEN** the operator clicks the Open-Loop Step Test button in the supervisory UI
- **THEN** the supervisory MUST verify that position is near zero, send the test command via Modbus, and display an active acquisition indicator.

#### Scenario: CSV Export Generation
- **WHEN** the supervisory detects test completion
- **THEN** it MUST read all buffer samples over Modbus and prompt the user to save a CSV file containing columns `time_s`, `position_mm`, `velocity_mm_s`, and `duty_pct`.
