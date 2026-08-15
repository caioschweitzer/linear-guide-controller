## ADDED Requirements

### Requirement: Dynamic Runtime Gain Update
The system SHALL support live updating of controller gains (Kp, Ki, Kd) during active closed-loop execution via `pid_set_gains()`, maintaining existing integral accumulator state unless gains are negative or invalid.

#### Scenario: Live gain update during motion
- **WHEN** new positive gain parameters (Kp, Ki, Kd) are passed to `pid_set_gains()` while controller is running
- **THEN** controller MUST immediately adopt the new gain values for subsequent control calculations without resetting the integral term.

#### Scenario: Negative or invalid gain rejection
- **WHEN** negative or NaN/Infinity gain parameters are supplied
- **THEN** system MUST preserve previous valid gain settings and reject the change.
