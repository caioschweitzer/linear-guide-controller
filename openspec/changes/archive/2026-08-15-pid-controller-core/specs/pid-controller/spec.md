# PID Controller Specification

## ADDED Requirements

### Requirement: Derivative on Measurement Calculation
The system SHALL compute derivative action strictly based on the rate of change of the measured position ($D = -K_d \cdot \frac{\Delta x}{\Delta t}$) rather than error rate, preventing derivative kick during setpoint step changes.

#### Scenario: Setpoint step response
- **WHEN** setpoint changes abruptly while measured position remains constant
- **THEN** derivative output component SHALL remain zero without impulse spikes

### Requirement: Derivative First-Order Low-Pass Filter
The system SHALL filter raw derivative computations using a first-order IIR filter ($D_{\text{filtered}} = \alpha_d \cdot D_{\text{raw}} + (1 - \alpha_d) \cdot D_{\text{prev}}$, default $\alpha_d = 0.15f$) to suppress encoder quantization noise.

#### Scenario: High-frequency position noise
- **WHEN** measured position exhibits single-count quantization jitter
- **THEN** filtered derivative output SHALL attenuate noise spikes smoothly

### Requirement: Conditional Anti-Windup Integration
The system SHALL freeze the integral accumulator when the unsaturated control output exceeds limits (`output_min` or `output_max`) AND the current error has the same sign as the saturation condition.

#### Scenario: Saturated output with persisting error
- **WHEN** control output reaches +100.0% and positive error persists
- **THEN** integral term SHALL stop accumulating further positive error

#### Scenario: Saturated output with reversing error
- **WHEN** control output is saturated at +100.0% and error reverses sign
- **THEN** integral integration SHALL resume immediately to reduce output effort

### Requirement: In-Position Deadband
The system SHALL return zero control effort ($0.0\%$) when the absolute position error $|e(t)|$ is less than or equal to `deadband_mm` (default 0.05 mm), avoiding motor humming and continuous micro-oscillations at rest.

#### Scenario: Position within deadband
- **WHEN** position error $|e(t)| \le 0.05\text{ mm}$
- **THEN** PID compute method SHALL return 0.0% effort

### Requirement: Numerical Guardrails and Reset API
The system SHALL ignore derivative updates when $dt \le 0.0001\text{ s}$ to prevent division by zero, SHALL output 0.0% effort if inputs are NaN or Infinity, and SHALL provide a `pid_reset()` function to zero integral accumulators and historical state.

#### Scenario: Division by zero prevention
- **WHEN** `dt <= 0.0001f` is passed to `pid_compute()`
- **THEN** system SHALL skip derivative calculation without raising NaN or float overflow exceptions

#### Scenario: Invalid floating-point input
- **WHEN** `setpoint` or `current_position` is NaN or Infinity
- **THEN** system SHALL force 0.0% output effort
