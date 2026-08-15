## 1. Encoder PCNT Hardware Driver Implementation

- [x] 1.1 Create `main/encoder_pcnt.h` header with `encoder_config_t` and `encoder_driver_t` context, function prototypes, and constants
- [x] 1.2 Implement PCNT unit initialization, quadrature channel configuration (GPIO 14/15), and internal Pull-Up configuration in `main/encoder_pcnt.c`
- [x] 1.3 Implement glitch filter configuration (`max_glitch_ns = 1000`) in `main/encoder_pcnt.c`
- [x] 1.4 Implement PCNT watch points (+30000/-30000) and ISR callback for 32-bit overflow accumulation in `main/encoder_pcnt.c`
- [x] 1.5 Implement atomic `encoder_get_count()` and `encoder_clear_count()` functions in `main/encoder_pcnt.c`
- [x] 1.6 Add host emulation support (`#ifdef HOST_TEST`) for offline testing in `main/encoder_pcnt.c`
- [x] 1.7 Update `main/CMakeLists.txt` to register `encoder_pcnt.c` in build sources

## 2. Unit Testing & Validation

- [x] 2.1 Create `tests/test_encoder_pcnt.py` test suite for encoder driver
- [x] 2.2 Add unit tests for driver initialization and zero count reading
- [x] 2.3 Add unit tests for forward and reverse quadrature counting
- [x] 2.4 Add unit tests for 16-bit hardware overflow accumulation into 32-bit integer
- [x] 2.5 Add unit tests for atomic zero reset clearing hardware and software counters
