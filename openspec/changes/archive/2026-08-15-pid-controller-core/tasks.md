## 1. PID Controller Implementation

- [x] 1.1 Create `main/pid_controller.h` with `pid_config_t`, `pid_controller_t`, function prototypes (`pid_init`, `pid_compute`, `pid_reset`, `pid_set_gains`), and constants
- [x] 1.2 Implement `pid_init()` and `pid_reset()` in `main/pid_controller.c`
- [x] 1.3 Implement derivative on measurement computation ($D_{\text{raw}} = -K_d \cdot \frac{\Delta x}{\Delta t}$) in `main/pid_controller.c`
- [x] 1.4 Implement 1st-order IIR derivative low-pass filter ($\alpha_d = 0.15f$) in `main/pid_controller.c`
- [x] 1.5 Implement conditional anti-windup integration in `main/pid_controller.c`
- [x] 1.6 Implement in-position deadband logic (`deadband_mm` = 0.05 mm) in `main/pid_controller.c`
- [x] 1.7 Implement numerical guardrails (`dt <= 0.0001s`, `NaN`/`INF` protection) in `main/pid_controller.c`
- [x] 1.8 Update `main/CMakeLists.txt` to register `pid_controller.c` in build sources

## 2. Unit Testing & Validation

- [x] 2.1 Create `tests/test_pid_controller.py` test suite using ctypes
- [x] 2.2 Add unit tests for proportional response ($P = K_p \cdot e$)
- [x] 2.3 Add unit tests for conditional anti-windup freezing and fast recovery on error reversal
- [x] 2.4 Add unit tests for derivative kick elimination during setpoint step changes
- [x] 2.5 Add unit tests for in-position deadband effort zeroing ($|e| \le 0.05\text{ mm}$)
- [x] 2.6 Add unit tests for numerical guardrails (`dt = 0.0`, `NaN`, `INF` inputs)
