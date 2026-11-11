# modbus-supervisory-ui Specification

## ADDED Requirements

### Requirement: Real-Time Digital Telemetry Display Cards
The supervisory user interface SHALL display prominent digital telemetry cards presenting real-time quantitative values for:
1. Target Setpoint ($SP$) in millimeters with 2 decimal places.
2. Current Position ($PV$) in millimeters with 2 decimal places.
3. Position Error ($e = SP - PV$) in millimeters with 2 decimal places and sign.
4. Linear Velocity ($v$) in millimeters per second with 1 decimal place.
5. Motor Effort / PWM Duty Cycle ($u$) in percentage with 1 decimal place and sign.

#### Scenario: Telemetry Update from Controller
- **WHEN** a new telemetry snapshot arrives from the Modbus TCP worker
- **THEN** each digital display card MUST update its numerical text and unit indicators within the same UI cycle.

#### Scenario: Error Calculation and Visual State
- **WHEN** the actuator moves towards the setpoint
- **THEN** the Position Error card MUST display $(SP - PV)$ and highlight green when $|SP - PV| \le 0.1\text{ mm}$ (in-position).

### Requirement: Circular Rolling Plot Buffer and Dynamic Point Limit Control
The supervisory user interface SHALL provide an interactive buffer size control allowing the operator to adjust the maximum number of historical plot points retained and displayed in the real-time graphs. The rolling plot buffer SHALL operate as a circular FIFO queue (`deque` with `maxlen`), automatically dropping the oldest data points when the limit is exceeded.

#### Scenario: Continuous Circular Plot Rolling
- **WHEN** the number of incoming telemetry samples exceeds the configured maximum point limit
- **THEN** the graphs MUST roll continuously, discarding the oldest sample for each new sample received, without growing unbounded in memory.

#### Scenario: Dynamic Buffer Limit Adjustment
- **WHEN** the operator changes the buffer size spinbox (e.g. from 300 to 1000 points)
- **THEN** the history deques MUST resize dynamically preserving existing data points up to the new capacity.

#### Scenario: Automatic Expansion on Burst Capture Reception
- **WHEN** open-loop burst buffer data is received with more samples than the current graph buffer limit
- **THEN** the supervisory MUST expand the graph buffer capacity to render the entire identification trajectory.
