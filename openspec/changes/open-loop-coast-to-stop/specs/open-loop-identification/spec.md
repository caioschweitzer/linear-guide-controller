# Spec Delta

## MODIFIED Requirements

### Requirement: Open-Loop Step Test Routine at Full Effort up to 80% Travel
The firmware SHALL provide a deterministic open-loop test routine executing within the 100 Hz Core 1 control loop. When activated, the routine SHALL drive the motor with the configured positive step PWM effort until the linear position reaches or exceeds 80% of the total 670 mm travel ($536.0\text{ mm}$, 80% of $670.0\text{ mm}$) or a safety timeout of $7.5\text{ seconds}$ (1.5x the original $5.0\text{ s}$) expires. Upon reaching the 80% threshold or timeout, the system SHALL immediately engage active braking (`motor_brake`), set effort to 0.0%, and transition to `MACHINE_STATE_IDLE`.

#### Scenario: Full Effort Drive to 80% of Stroke
- **WHEN** the open-loop step test routine is triggered from `MACHINE_STATE_IDLE`
- **THEN** the motor driver MUST output the configured positive duty cycle continuously until position reaches $\ge 536.0\text{ mm}$.

#### Scenario: Active Braking on 80% Travel Threshold
- **WHEN** current linear position reaches or exceeds $536.0\text{ mm}$ during the test
- **THEN** the firmware MUST instantly cut motor duty to 0%, apply electromagnetic braking, and transition to `MACHINE_STATE_IDLE`, leaving $134.0\text{ mm}$ of clearance before the mechanical endstop.

#### Scenario: Safety Timeout Triggered
- **WHEN** the test runs for longer than $7.5\text{ seconds}$ without reaching $536.0\text{ mm}$
- **THEN** the firmware MUST immediately abort the test, apply active braking, cut motor duty to 0%, and mark buffer status as aborted.

### Requirement: Extended Internal RAM Burst Capture Buffer
The firmware SHALL allocate an internal memory buffer in RAM capable of recording at least 825 data points at 100 Hz ($10\text{ ms}$ interval, representing up to $8.25\text{ seconds}$ of travel, 1.5x the original 550 samples), capturing relative timestamp (milliseconds), position (mm), velocity (mm/s), and applied duty cycle (%).

#### Scenario: High-Resolution 100 Hz Logging
- **WHEN** the system is in `MACHINE_STATE_OPEN_LOOP_TEST`
- **THEN** each 10 ms cycle MUST append timestamp, position, velocity, and duty cycle into the RAM buffer until completion or timeout.

#### Scenario: Buffer Ready Signaled
- **WHEN** the test completes successfully
- **THEN** the buffer status MUST be set to Ready and the recorded sample count published via Modbus.

## ADDED Requirements

### Requirement: Open-Loop Coast-to-Stop Mode (Step-Up to Step-Down 0%)
The firmware SHALL support a selectable coast-to-stop mode (`OPEN_LOOP_MODE_COAST = 1`) alongside active-brake mode (`OPEN_LOOP_MODE_BRAKE = 0`). In coast-to-stop mode, it SHALL apply the configured PWM until reaching the step-down position (`[50.0, 536.0] mm`, default `400.0 mm`), then set effort to `0.0%` without active braking and continue 100 Hz capture until natural stop or safety limits.

#### Scenario: Step-Down to 0% Without Active Braking at Target Position
- **WHEN** the open-loop test runs in coast-to-stop mode and position reaches the configured step-down threshold (e.g., `400.0 mm`)
- **THEN** the firmware MUST set motor effort to `0.0%` (without calling `motor_brake`), keep `MACHINE_STATE_OPEN_LOOP_TEST` active, and continue recording samples at 100 Hz.

#### Scenario: Natural Stop Detection
- **WHEN** the carriage is coasting after the step-down to `0.0%` and absolute velocity remains `<= 2.0 mm/s` for at least `150 ms` (15 consecutive 100 Hz samples)
- **THEN** the firmware MUST mark the burst buffer as Ready (`BURST_STATUS_READY`), set effort to `0.0%`, and transition to `MACHINE_STATE_IDLE`.

#### Scenario: Endstop Safety Guard During Coasting
- **WHEN** the carriage reaches `>= 650.0 mm` (20 mm before the 670 mm mechanical endstop) while coasting
- **THEN** the firmware MUST immediately engage `motor_brake`, set effort to `0.0%`, mark the burst buffer as Ready (`BURST_STATUS_READY`), and transition to `MACHINE_STATE_IDLE`.

#### Scenario: Buffer Capacity or Safety Timeout During Coasting
- **WHEN** the coast-to-stop test reaches the 825-sample RAM buffer limit (`8.25 s`) or the `7.5 s` safety timeout before natural stop
- **THEN** the firmware MUST stop recording, set effort to `0.0%`, mark the burst buffer as Ready (`BURST_STATUS_READY`), and transition to `MACHINE_STATE_IDLE`.

### Requirement: Per-Sample Duty Cycle Recording in Burst Buffer
The firmware and supervisory software SHALL record and retrieve the actual motor effort (`duty_pct`) applied at each 100 Hz sample so that step-up and step-down (`0.0%`) transitions are accurately represented in plots and CSV exports.

#### Scenario: Duty Cycle Transition Captured in CSV
- **WHEN** a coast-to-stop curve with `70.0%` initial PWM is downloaded by the supervisory
- **THEN** samples before the step-down position MUST report `duty_pct = 70.0` and samples after the step-down position MUST report `duty_pct = 0.0`.

### Requirement: Supervisory Controls for Coast-to-Stop Mode
The supervisory software SHALL provide controls to select between **Freio Ativo** (`mode = 0`) and **Parada Natural (Degrau -> 0%)** (`mode = 1`) and to configure the step-down threshold position (`50.0` to `536.0 mm`), transmitting both parameters before starting the open-loop test and supporting multi-curve ($N$) collection in both modes.

#### Scenario: Coast-to-Stop Mode Selected in Supervisory UI
- **WHEN** the operator selects **Parada Natural (Degrau -> 0%)**, sets step-down position to `350.0 mm` and PWM to `80.0%`, and starts the test
- **THEN** the supervisory MUST transmit the mode, step-down position, and PWM level via Modbus before issuing `CMD_OPEN_LOOP_TEST`.
