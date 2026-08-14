## 1. IPC & State Machine Core Structure

- [ ] 1.1 Update `main/shared_data.h` and `main/shared_data.c` to define `machine_state_t` with atomic/ISR-safe setters and getters.
- [ ] 1.2 Implement state transition guard function `shared_data_request_state_change(machine_state_t new_state)` with level-checking logic for `GPIO 12`.

## 2. GPIO Safety Subsystem & ISR Setup

- [ ] 2.1 Create `main/gpio_safety.h` and `main/gpio_safety.c` for GPIO pin initialization (`GPIO 11` input pull-up, `GPIO 12` input pull-up with falling-edge interrupt).
- [ ] 2.2 Implement `IRAM_ATTR gpio12_emergency_isr()` with immediate physical motor cutoff, atomic state update to `EMERGENCY`, and `vTaskNotifyGiveFromISR`.
- [ ] 2.3 Implement Core 0 `start_button_debounce_task()` to monitor `GPIO 11` with software debounce.

## 3. Modbus Control Register Integration

- [ ] 3.1 Update `main/modbus_slave.h` and `main/modbus_slave.c` to map Holding Register `0x0001` as Command Register.
- [ ] 3.2 Implement command processor for `START` (1), `STOP` (2), `RESET` (3), and `SIMULATE_EMERGENCY` (99).

## 4. Main Application Integration & Verification

- [ ] 4.1 Update `main/main.c` to initialize GPIO safety subsystem and link `ControlLoopTask` handle to Emergency ISR notifications.
- [ ] 4.2 Compile firmware with `idf.py build` and verify zero errors/warnings.

## 5. Automated Pytest Integration Suite

- [ ] 5.1 Create `tests/test_state_machine.py` to validate normal state transitions, emergency lockout rejection, and safe reset rules via Modbus.
- [ ] 5.2 Execute test suite with `tests/.venv/bin/pytest -v tests/test_state_machine.py` and verify all tests pass.
