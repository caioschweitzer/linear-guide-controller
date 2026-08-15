## 1. Motor MCPWM Driver Implementation

- [x] 1.1 Create `main/motor_mcpwm.h` header with `motor_config_t`, `motor_driver_t` context, function prototypes, and constants
- [x] 1.2 Implement MCPWM timer (20 kHz), operator, comparator, and generator setup on GPIO 4 in `main/motor_mcpwm.c`
- [x] 1.3 Implement GPIO direction control for IN1 (GPIO 5) and IN2 (GPIO 6) in `main/motor_mcpwm.c`
- [x] 1.4 Implement effort clamping ($[-100.0\%, +100.0\%]$) and `NaN`/`INF` fail-safe in `main/motor_mcpwm.c`
- [x] 1.5 Implement direction reversal shoot-through protection (brake phase before direction flip) in `main/motor_mcpwm.c`
- [x] 1.6 Add host emulation support (`#ifdef HOST_TEST`) for offline testing in `main/motor_mcpwm.c`
- [x] 1.7 Update `main/CMakeLists.txt` to register `motor_mcpwm.c` in build sources

## 2. Unit Testing & Validation

- [x] 2.1 Create `tests/test_motor_mcpwm.py` test suite for motor driver
- [x] 2.2 Add unit tests for forward effort (+50.0% -> IN1=1, IN2=0, Duty=50%)
- [x] 2.3 Add unit tests for reverse effort (-50.0% -> IN1=0, IN2=1, Duty=50%)
- [x] 2.4 Add unit tests for passive brake / total stop (0.0% effort -> IN1=0, IN2=0, Duty=0%)
- [x] 2.5 Add unit tests for effort clamping (+150% -> 100%) and `NaN`/`INF` fail-safe (forces brake)
- [x] 2.6 Add unit tests for direction reversal brake transition (+80% to -80%)
