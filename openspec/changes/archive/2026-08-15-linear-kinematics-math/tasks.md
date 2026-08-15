## 1. Kinematics Module Implementation

- [x] 1.1 Create `main/linear_kinematics.h` header with `kinematics_t` struct definition, function prototypes, and constants
- [x] 1.2 Implement position calculation, zero offset calibration, and direction multiplier in `main/linear_kinematics.c`
- [x] 1.3 Implement velocity calculation with $dt \le 0.0001$ s guardrails, initial cycle spike prevention, and EMA low-pass filtering in `main/linear_kinematics.c`
- [x] 1.4 Implement Modbus fixed-point integer serialization helpers in `main/linear_kinematics.c`
- [x] 1.5 Update `main/CMakeLists.txt` to register `linear_kinematics.c` in build sources

## 2. Unit Testing & Validation

- [x] 2.1 Create `tests/test_kinematics.py` test suite for kinematics module
- [x] 2.2 Add unit tests for absolute position calculation, zero offset, and direction reversal
- [x] 2.3 Add unit tests for $dt \le 0$ division-by-zero protection and 1st-cycle velocity spike prevention
- [x] 2.4 Add unit tests for differential velocity calculation and EMA filter convergence
- [x] 2.5 Add unit tests for Modbus fixed-point integer conversion helpers
