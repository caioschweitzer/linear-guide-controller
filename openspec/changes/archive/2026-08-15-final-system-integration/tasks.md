## 1. System Integration & Main Entry Implementation

- [x] 1.1 Implement subsystem initialization sequence (`app_main()`) in `main/main.c`
- [x] 1.2 Implement deterministic 100 Hz `Task_ControlLoop` pinned to Core 1 using `vTaskDelayUntil` in `main/main.c`
- [x] 1.3 Implement 5 Hz `Task_IHM` pinned to Core 0 in `main/main.c`
- [x] 1.4 Implement setpoint clamping $[0.0\text{ mm}, 424.115\text{ mm}]$ and closed-loop PID effort calculation in `main/main.c`
- [x] 1.5 Implement emergency E-Stop interceptor with 0.0% duty override and `pid_reset()` in `main/main.c`
- [x] 1.6 Update `main/CMakeLists.txt` to register all C source files and include directories

## 2. Integration Testing & System Validation

- [x] 2.1 Create `tests/test_system_integration.py` test suite using ctypes and host shared library
- [x] 2.2 Add integration tests for system boot sequence (IDLE state, 0.0% duty, 0.0 mm position)
- [x] 2.3 Add integration tests for MOVING state closed-loop PID response and setpoint step changes
- [x] 2.4 Add integration tests for Emergency E-Stop interruption and immediate duty zeroing
