# Kinematics Math Specification

## ADDED Requirements

### Requirement: Linear Position Calculation
The system SHALL compute absolute linear position in millimeters ($mm$) from accumulated raw encoder counts using a resolution constant of $0.0424115$ mm/count, taking into account calibration zero offset and direction multipliers.

#### Scenario: Standard position calculation without offset
- **WHEN** raw encoder count is 1000, zero offset is 0, and direction is +1
- **THEN** calculated linear position SHALL be 42.4115 mm

#### Scenario: Calibrated position with zero offset and inverted direction
- **WHEN** raw encoder count is 1100, zero offset is 100, and direction is -1
- **THEN** calculated linear position SHALL be -42.4115 mm

### Requirement: Velocity Derivative with dt Protection
The system SHALL compute instantaneous linear velocity ($mm/s$) by deriving position over time ($dt$) and MUST enforce a numerical guardrail if $dt \le 0.0001$ seconds to prevent division by zero, `NaN`, or infinite values.

#### Scenario: Normal velocity calculation
- **WHEN** position changes by 21.20575 mm over a time step $dt = 0.1$ seconds
- **THEN** instantaneous velocity SHALL be 212.0575 mm/s

#### Scenario: Division by zero protection
- **WHEN** a velocity calculation request is made with $dt = 0.0$ seconds
- **THEN** system SHALL retain the previously computed valid velocity without generating `NaN` or `+INF`

### Requirement: Startup Spike Prevention
The system SHALL track an initialization state (`is_initialized`) and set the initial velocity to $0.0$ mm/s during the first calculation cycle post-initialization or reset.

#### Scenario: First execution cycle after startup
- **WHEN** system executes velocity calculation for the first time with an arbitrary initial position count
- **THEN** initial velocity SHALL be 0.0 mm/s and internal state SHALL update without reporting speed spikes

### Requirement: Low-Pass Exponential Moving Average Velocity Filtering
The system SHALL apply an Exponential Moving Average (EMA) filter to raw derived velocity using a smoothing coefficient $\alpha$ ($0 < \alpha \le 1.0$) to suppress quantization noise.

#### Scenario: Velocity noise smoothing via EMA filter
- **WHEN** step changes occur in raw derived velocity with filter coefficient $\alpha = 0.2$
- **THEN** output velocity SHALL converge smoothly according to $v_{filtered} = \alpha \cdot v_{inst} + (1 - \alpha) \cdot v_{prev}$

### Requirement: Modbus Integer Fixed-Point Serialization
The system SHALL provide helper functions to convert floating-point position and velocity into fixed-point integer values suitable for 16-bit and 32-bit Modbus registers.

#### Scenario: Position fixed-point scale conversion
- **WHEN** linear position is 42.4115 mm and scale factor is 100
- **THEN** fixed-point Modbus register value SHALL be 4241 (representing 42.41 mm)
