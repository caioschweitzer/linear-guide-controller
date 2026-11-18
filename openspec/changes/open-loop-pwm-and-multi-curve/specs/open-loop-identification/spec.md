# Spec Delta

## MODIFIED Requirements

### Requirement: Open-Loop Step Test Routine at Full Effort up to 80% Travel
The firmware SHALL provide a deterministic open-loop test routine executing within the 100 Hz Core 1 control loop. When activated, the routine SHALL drive the motor with the configured positive step PWM effort (clamped to `[1.0%, 100.0%]`, defaulting to `+100.0%`) received via Modbus Holding Register until the linear position reaches or exceeds 80% of the total 670 mm travel ($536.0\text{ mm}$, 80% of $670.0\text{ mm}$) or a safety timeout of $5.0\text{ seconds}$ expires. Upon reaching the 80% threshold or timeout, the system SHALL immediately engage active braking (`motor_brake`), set effort to 0.0%, and transition to `MACHINE_STATE_IDLE`.

#### Scenario: Full Effort Drive to 80% of Stroke
- **WHEN** the open-loop step test routine is triggered from `MACHINE_STATE_IDLE` without overriding the default PWM level
- **THEN** the motor driver MUST output +100.0% duty cycle continuously until position reaches $\ge 536.0\text{ mm}$.

#### Scenario: Configurable PWM Step Drive to 80% of Stroke
- **WHEN** the operator configures a target PWM level (e.g., 60.0%) via Modbus Holding Register and triggers the open-loop step test from `MACHINE_STATE_IDLE`
- **THEN** the motor driver MUST output the configured duty cycle (+60.0%) continuously until position reaches $\ge 536.0\text{ mm}$ or the 5.0 s safety timeout expires.

#### Scenario: Out-of-Range PWM Clamping
- **WHEN** a PWM value outside `[1.0%, 100.0%]` is written to the open-loop PWM Holding Register
- **THEN** the firmware MUST clamp the applied step effort to `[1.0%, 100.0%]` (or fall back to `100.0%` if non-finite) before driving the motor.

#### Scenario: Active Braking on 80% Travel Threshold
- **WHEN** current linear position reaches or exceeds $536.0\text{ mm}$ during the test
- **THEN** the firmware MUST instantly cut motor duty to 0%, apply electromagnetic braking, and transition to `MACHINE_STATE_IDLE`, leaving $134.0\text{ mm}$ of clearance before the mechanical endstop.

#### Scenario: Safety Timeout Triggered
- **WHEN** the test runs for longer than $5.0\text{ seconds}$ without reaching $536.0\text{ mm}$
- **THEN** the firmware MUST immediately abort the test, apply active braking, cut motor duty to 0%, and mark buffer status as aborted.

### Requirement: Supervisory UI Indicator and CSV Data Export
The supervisory software SHALL allow the operator to configure the open-loop step PWM percentage (`1.0%` to `100.0%`, default `100.0%`), reflect the selected PWM and 80% travel target ($536\text{ mm}$) in UI controls, transmit the PWM level before starting the test, automatically retrieve the burst buffer upon test completion, and prompt the user to save the trajectory data to a `.csv` file with the applied `duty_pct`.

#### Scenario: Supervisory UI Action
- **WHEN** the operator sets the step PWM spinbox to a value (e.g., `75.0%`) and inspects or starts the open-loop test
- **THEN** the supervisory MUST display the configured PWM percentage alongside the 536 mm / 80% target and write that PWM value to the firmware before issuing `CMD_OPEN_LOOP_TEST`.

#### Scenario: Complete Trajectory Export
- **WHEN** the supervisory downloads the completed 80% burst buffer for a single run (`N = 1`)
- **THEN** it MUST plot the trajectory and prompt the user to save the complete dataset to a CSV file containing `time_s`, `position_mm`, `velocity_mm_s`, and `duty_pct` equal to the configured step PWM.

## ADDED Requirements

### Requirement: Automated Multi-Curve Collection Sequence
The supervisory software SHALL provide a spinbox to select the number of consecutive open-loop curves $N$ ($N \ge 1$, default `1`). When $N > 1$, the supervisory SHALL automatically orchestrate $N$ consecutive step tests, commanding `CMD_HOME` between runs and waiting until the machine returns to `MACHINE_STATE_IDLE` with `|pos| <= 5.0 mm` before starting the next run.

#### Scenario: Sequential Multi-Curve Execution
- **WHEN** the operator sets $N = 3$ and starts the open-loop test from `MACHINE_STATE_IDLE` with `|pos| <= 5.0 mm`
- **THEN** the supervisory MUST execute run 1, download its burst buffer, issue `CMD_HOME`, wait for `IDLE` near `0 mm`, and repeat automatically for runs 2 and 3 while displaying progress (`1/3`, `2/3`, `3/3`).

#### Scenario: Multi-Curve Sequence Aborted on Fault or Stop
- **WHEN** an emergency state, burst abort/timeout, or manual stop occurs during a multi-curve sequence
- **THEN** the supervisory MUST immediately halt the batch sequence, report the interruption in the log/status, and NOT start subsequent runs.

### Requirement: Normalized Curve Computation and Export
Upon completing all $N$ runs of a multi-curve collection, the supervisory software SHALL compute a consolidated normalized curve across the $N$ collected curves and export it to a `.csv` file.

#### Scenario: Normalized Curve CSV Export After N Runs
- **WHEN** all $N$ curves are collected and downloaded successfully
- **THEN** the supervisory MUST align the curves by sample index/timestamp, compute the mean position, mean velocity, and normalized position and velocity in `[0.0, 1.0]`, plot the consolidated curve, and prompt the user to save the normalized dataset to CSV.
