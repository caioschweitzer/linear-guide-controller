## Why

Currently, the linear guide controller lacks a dedicated hardware pin and automated software routine for mechanical homing (finding the physical zero datum). The Home sensor spatial position ($37.68\text{ mm}$) was documented, but in firmware, all safety inputs were tied to `GPIO 12` (Emergency Stop). To accurately calibrate the absolute linear position upon startup or error recovery, the system requires a dedicated Home sensor input pin (`GPIO 16`) and an automated homing procedure (`MACHINE_STATE_HOMING` / command `3`) that drives the carriage slowly until the Home sensor is activated, zeroing the encoder position accumulator.

## What Changes

- **Dedicated GPIO Allocation**: Assign `GPIO 16` as an Active-LOW digital input with internal pull-up (`GPIO_PULLUP_ENABLE`) dedicated to the physical Home Sensor (`GPIO_HOME_PIN`).
- **Homing State Machine (`MACHINE_STATE_HOMING`)**: Introduce/formalize a homing motion state. When `CMD_HOME` (`3`) is requested, the controller enters `MACHINE_STATE_HOMING`, driving the motor in the reverse/homing direction at a safe creep effort (e.g. `-15.0%`).
- **Zero Calibration Trigger**: When `GPIO 16` detects the Home sensor activation (falling edge / LOW level), the control loop halts motor effort, calls `encoder_clear_count()` to reset the hardware PCNT counter and software accumulator to $0.00\text{ mm}$ (or calibrated datum offset), and transitions state to `MACHINE_STATE_IDLE`.
- **Safety Safeguards**: If an Emergency Stop occurs during homing, motion halts instantly, and homing is aborted.
- **Supervisory SCADA UI Update**: Update the Python SCADA supervisory client `HOME` button to initiate the `CMD_HOME` procedure and reflect `HOMING` state in the UI status badge.

## Capabilities

### New Capabilities
- `home-sensor-calibration`: Dedicated Home sensor input handling on `GPIO 16` with automated homing state machine for encoder zero-point calibration.

### Modified Capabilities
- `kernel-freertos-modbus`: Enhanced command register `0x0002` processing to handle `CMD_HOME` (`3`) state transitions.

## Impact

- **Firmware files**: `main/include/gpio_safety.h`, `main/src/gpio_safety.c`, `main/include/shared_data.h`, `main/src/main.c`, `main/src/modbus_slave.c`.
- **Documentation**: Update pinout tables in `docs/02_hardware_and_schematics.md` and state machine diagrams in `docs/03_software_architecture_freertos.md`.
- **Test suite**: Add automated unit and HIL simulation tests in `tests/test_state_machine.py` and `tests/test_system_integration.py`.
