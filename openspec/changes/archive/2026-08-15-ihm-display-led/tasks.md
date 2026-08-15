## 1. IHM Display & LED Driver Implementation

- [x] 1.1 Create `main/ihm_display.h` with `ihm_config_t`, `ihm_display_t`, function prototypes, and constants
- [x] 1.2 Implement PCF8574 + HD44780 4-bit nibble command/data write functions in `main/ihm_display.c`
- [x] 1.3 Implement strict 16-character line formatting (`ihm_format_lines`) in `main/ihm_display.c`
- [x] 1.4 Implement non-blocking GPIO 7 status LED controller (`ihm_update_led`) in `main/ihm_display.c`
- [x] 1.5 Implement I2C error handling, disconnection flag, and auto-recovery logic in `main/ihm_display.c`
- [x] 1.6 Add host emulation support (`#ifdef HOST_TEST`) for offline testing in `main/ihm_display.c`
- [x] 1.7 Update `main/CMakeLists.txt` to register `ihm_display.c` in build sources

## 2. Unit Testing & Validation

- [x] 2.1 Create `tests/test_ihm_display.py` test suite using ctypes
- [x] 2.2 Add unit tests for LCD Line 1 and Line 2 16-character formatting and extreme value truncation
- [x] 2.3 Add unit tests for non-blocking LED state transitions and timing (1 Hz MOVING vs 5 Hz EMERGENCY)
- [x] 2.4 Add unit tests for I2C disconnection flag and resilience handling
