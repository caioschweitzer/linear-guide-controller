## Context

The current `main/` directory contains all header (`.h`) and source (`.c`) files flatly in one directory. Standard ESP-IDF component layout guidelines recommend putting public headers in `main/include/` and source code implementations in `main/src/`.

## Goals / Non-Goals

**Goals:**
- Move all `.h` public headers (`shared_data.h`, `modbus_slave.h`, `ihm_display.h`, `gpio_safety.h`, `motor_mcpwm.h`, `encoder_pcnt.h`, `linear_kinematics.h`, `pid_controller.h`) into `main/include/`.
- Move all `.c` source files (`main.c`, `shared_data.c`, `modbus_slave.c`, `ihm_display.c`, `gpio_safety.c`, `motor_mcpwm.c`, `encoder_pcnt.c`, `linear_kinematics.c`, `pid_controller.c`) into `main/src/`.
- Update `main/CMakeLists.txt` `SRCS` list to point to `src/*.c` and `INCLUDE_DIRS` to `"include"`.
- Update host testing build script in `tests/test_system_integration.py` to compile source files from `main/src/` with include path `-Imain/include`.
- Ensure all 32 pytest host integration tests pass and ESP32 binary builds/flashes cleanly.

**Non-Goals:**
- Refactoring firmware logic or API interfaces.
- Modifying hardware pin assignments or FreeRTOS task logic.

## Decisions

- **Standard ESP-IDF Subdirectory Layout**: Chosen over creating separate top-level custom components because all modules represent the core actuator controller application stack.
- **Maintain Relative Header Includes**: Since `INCLUDE_DIRS` in `CMakeLists.txt` specifies `include`, existing `#include "header.h"` directives remain fully functional without needing path prefix changes in source files.

## Risks / Trade-offs

- [Risk]: Host test shared library (`libsystem_integration.so`) compilation fails if paths in `test_system_integration.py` are not updated.
  - *Mitigation*: Update `c_files` paths in `load_system_lib()` inside `test_system_integration.py` and verify via `pytest`.
- [Risk]: ESP-IDF build system fails to locate source files.
  - *Mitigation*: Specify explicit relative paths `src/<file>.c` in `main/CMakeLists.txt`.
