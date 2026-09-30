# Design Document: Home Sensor & Automated Homing Calibration

## 1. Hardware Pin Assignment & Electrical Logic

`GPIO 16` is designated as the dedicated **Home Sensor** input pin:

| Signal Name | ESP32-S3 GPIO | Mode | Electrical Config | Function |
| :--- | :--- | :--- | :--- | :--- |
| `GPIO_HOME_PIN` | `GPIO 16` | Input | Active-LOW (Internal Pull-Up) | Mechanical zero-position optical/limit sensor contact. |

- **Untriggered (Carriage Away from Home)**: Pin pulled `HIGH` (+3.3V) by internal pull-up.
- **Triggered (Carriage at Home Datum $37.68\text{ mm}$ / $0.00\text{ mm}$)**: Sensor pulls pin `LOW` (GND).

---

## 2. State Machine Extensions & Homing Flow

```
                                  ┌────────────────┐
                                  │ MACHINE_STATE_ │
                                  │      IDLE      │
                                  └───────┬────────┘
                                          │
                                          │ Command 3 (CMD_HOME)
                                          ▼
                                  ┌────────────────┐
                                  │ MACHINE_STATE_ │
                                  │     HOMING     │
                                  └───────┬────────┘
                                          │
                  ┌───────────────────────┴───────────────────────┐
                  │                                               │
                  ▼ Home Sensor Active (GPIO 16 == LOW)           ▼ Emergency Triggered (GPIO 12 == LOW)
        ┌───────────────────┐                           ┌───────────────────┐
        │ Zero Position &   │                           │ Instant Cutoff &  │
        │ Halt Motor Effort │                           │ Emergency Lockout │
        └─────────┬─────────┘                           └─────────┬─────────┘
                  │                                               │
                  ▼                                               ▼
        ┌───────────────────┐                           ┌───────────────────┐
        │ MACHINE_STATE_    │                           │ MACHINE_STATE_    │
        │       IDLE        │                           │     EMERGENCY     │
        └───────────────────┘                           └───────────────────┘
```

### Homing Sequence Algorithm (Core 1 Control Loop):
1. **Initiation**: User or Modbus host sends `command = 3` (`CMD_HOME`). State transitions to `MACHINE_STATE_HOMING`.
2. **Creep Motion**: In `MACHINE_STATE_HOMING`, the control task drives the motor effort in reverse (`-15.0%` duty cycle).
3. **Sensor Detection**: The control loop samples `gpio_get_level(GPIO_HOME_PIN)`.
4. **Zeroing Calibration**: When `GPIO 16 == 0` (Active LOW):
   - Motor effort is immediately set to `0.0%` (passive brake).
   - Encoder tick counter and software accumulator are zeroed via `encoder_clear_count()`.
   - `g_system_data.current_position` is set to `0.00 mm` (or datum offset `37.68 mm`).
   - Machine state transitions back to `MACHINE_STATE_IDLE`.

---

## 3. Kernel & IPC Synchronization

- **State Representation**: Add `MACHINE_STATE_HOMING = 3` to `machine_state_t` enum in `main/include/shared_data.h`.
- **Modbus Synchronization**: Input Register `0x0004` (`machine_state`) reports state code `3` (`HOMING`).
- **LCD Display**: LCD display formatting reflects state `"HOMING"` in line 2 telemetry.

---

## 4. Host Integration Testing & Mocking

- Extend host wrapper `tests/libsystem_integration.so` to support simulated home sensor state toggle.
- Add host unit tests in `tests/test_state_machine.py` validating homing trigger, creep effort, position zeroing, and emergency cancellation.
