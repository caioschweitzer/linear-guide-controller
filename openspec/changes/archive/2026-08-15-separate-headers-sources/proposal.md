## Why

As the ESP32-S3 linear actuator controller codebase expands, housing all 19 header (`.h`) and source (`.c`) files directly under `main/` creates visual clutter and violates standard ESP-IDF component structure guidelines. Separating public header contracts into `main/include/` and source implementations into `main/src/` enforces clean API boundaries and improves project maintainability.

## What Changes

- Reorganize component files inside `main/`: move `.h` header files into `main/include/` and `.c` source files into `main/src/`.
- Update `main/CMakeLists.txt` to register source files under `src/` and set header inclusion path to `include`.
- Update host testing scripts (`tests/test_system_integration.py` and compilation flags) to look for headers in `main/include/` and sources in `main/src/`.
- Rebuild host test shared library (`tests/libsystem_integration.so`) and verify pytest test suite.
- Rebuild and re-flash ESP32-S3 firmware with `idf.py build` & `idf.py flash`.

## Capabilities

### New Capabilities
- `separate-headers-sources`: Reorganize component architecture by separating public headers into `main/include/` and source implementations into `main/src/`.

### Modified Capabilities
<!-- None: Hardware and Modbus protocol requirements remain unchanged -->

## Impact

- `main/CMakeLists.txt`: Updated paths for `SRCS` and `INCLUDE_DIRS`.
- `main/include/`: Contains public interface headers (`shared_data.h`, `modbus_slave.h`, `ihm_display.h`, `gpio_safety.h`, `motor_mcpwm.h`, `encoder_pcnt.h`, `linear_kinematics.h`, `pid_controller.h`).
- `main/src/`: Contains source files (`main.c`, `shared_data.c`, `modbus_slave.c`, `ihm_display.c`, `gpio_safety.c`, `motor_mcpwm.c`, `encoder_pcnt.c`, `linear_kinematics.c`, `pid_controller.c`).
- `tests/test_system_integration.py`: Updated GCC path arguments for host testing.
