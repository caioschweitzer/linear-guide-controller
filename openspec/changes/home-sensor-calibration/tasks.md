## 1. GPIO Pin & Data Structure Updates

- [x] 1.1 Add `#define GPIO_HOME_PIN GPIO_NUM_16` to `main/include/shared_data.h`.
- [x] 1.2 Update `machine_state_t` enum in `main/include/shared_data.h` to include `MACHINE_STATE_HOMING = 3`.
- [x] 1.3 Configure `GPIO 16` input with internal pull-up (`GPIO_PULLUP_ENABLE`) in `main/src/gpio_safety.c`.

## 2. Homing Control Loop & State Machine Logic

- [x] 2.1 Implement homing motion handling in Core 1 control loop (`main/src/main.c` / `pid_controller.c`): drive motor reverse effort (`-15.0%`) while in `MACHINE_STATE_HOMING`.
- [x] 2.2 Add Home sensor trigger detection (`gpio_get_level(GPIO_HOME_PIN) == 0`) inside control loop to execute zero position reset (`encoder_clear_count()`) and transition state to `MACHINE_STATE_IDLE`.
- [x] 2.3 Ensure emergency interrupt (`GPIO 12`) immediately aborts homing motion and transitions state to `MACHINE_STATE_EMERGENCY`.

## 3. Modbus Slave & Supervisory UI Updates

- [x] 3.1 Map `CMD_HOME` (`4`) in `main/src/modbus_slave.c` to request `MACHINE_STATE_HOMING`.
- [x] 3.2 Update `IHMDisplayTask` state string and supervisory SCADA UI `StatusBadge` to display `STATE: HOMING` when state code is `3`.

## 4. Documentation & Verification

- [x] 4.1 Update GPIO pinout table and schematics in `docs/02_hardware_and_schematics.md` to reflect `GPIO 16` Home Sensor assignment.
- [x] 4.2 Add automated unit tests in `tests/test_state_machine.py` and `tests/test_system_integration.py` verifying homing movement, zero position clearing, and emergency interrupts during homing.
- [x] 4.3 Run full `pytest` suite to ensure all tests pass.
