# Motor MCPWM Driver Specification

## ADDED Requirements

### Requirement: 20 kHz High-Resolution MCPWM Generation
The system SHALL initialize an ESP32-S3 MCPWM timer operating at 20 kHz with a 10 MHz clock resolution (500 ticks period) connected to GPIO 4 (L298N Enable pin).

#### Scenario: Normal PWM generation
- **WHEN** motor driver `motor_init()` is called
- **THEN** MCPWM generator on GPIO 4 SHALL be configured for 20 kHz inaudible PWM output

### Requirement: L298N Direction Control Logic
The system SHALL drive digital outputs on GPIO 5 (IN1) and GPIO 6 (IN2) according to the sign of `effort_percent`:
- For `effort_percent > 0.0f`: IN1=1, IN2=0, Duty = effort_percent%
- For `effort_percent < 0.0f`: IN1=0, IN2=1, Duty = |effort_percent|%
- For `effort_percent == 0.0f`: IN1=0, IN2=0, Duty = 0% (Passive Brake)

#### Scenario: Forward direction drive
- **WHEN** `motor_set_effort(driver, 50.0f)` is called
- **THEN** GPIO 5 SHALL be set HIGH, GPIO 6 SHALL be set LOW, and PWM duty cycle SHALL be set to 50%

#### Scenario: Reverse direction drive
- **WHEN** `motor_set_effort(driver, -50.0f)` is called
- **THEN** GPIO 5 SHALL be set LOW, GPIO 6 SHALL be set HIGH, and PWM duty cycle SHALL be set to 50%

#### Scenario: Total stop / Passive brake
- **WHEN** `motor_set_effort(driver, 0.0f)` is called
- **THEN** GPIO 5 SHALL be set LOW, GPIO 6 SHALL be set LOW, and PWM duty cycle SHALL be set to 0%

### Requirement: Direction Reversal Shoot-Through Protection
The system SHALL perform an automatic short brake phase (IN1=0, IN2=0, Duty=0%) when a direction change is requested (effort changing sign from positive to negative or vice versa) before energizing the new direction.

#### Scenario: Reversing direction from forward to reverse
- **WHEN** motor is running at +80.0% effort and `motor_set_effort(driver, -80.0f)` is called
- **THEN** driver SHALL execute a brake transition (IN1=0, IN2=0, Duty=0%) before engaging IN1=0, IN2=1 at 80% duty

### Requirement: Effort Clamping and Fail-Safe Numerical Protection
The system SHALL clamp effort inputs strictly within $[-100.0\%, +100.0\%]$ and SHALL immediately trigger passive brake ($0.0\%$ effort) if the input effort is NaN or Infinity (`isnan(effort) || isinf(effort)`).

#### Scenario: Over-range effort input
- **WHEN** `motor_set_effort(driver, 150.0f)` is called
- **THEN** effective effort applied SHALL be clamped to +100.0%

#### Scenario: Invalid floating-point effort (NaN/INF)
- **WHEN** `motor_set_effort(driver, NAN)` or `motor_set_effort(driver, INFINITY)` is called
- **THEN** driver SHALL force immediate passive brake (IN1=0, IN2=0, Duty=0%)
