## Context

Spec 1 established the dual-core FreeRTOS kernel with Mutex-protected IPC (`SystemData`) and Modbus RTU slave communication. Spec 2 builds upon this foundation by adding a hardware-driven Emergency ISR on `GPIO 12`, software debounce on `GPIO 11`, an atomic state transition guardrail, and Modbus command register handling.

## Goals / Non-Goals

**Goals:**
- Implement atomic, thread-safe, and ISR-safe state machine management (`IDLE`, `MOVING`, `EMERGENCY`).
- Configure `GPIO 12` (Emergency Button) with `IRAM_ATTR` ISR for immediate hardware PWM cutoff and task notification.
- Configure `GPIO 11` (Start Button) with software debounce in Core 0.
- Implement strict level-checked state transition rules (`gpio_get_level(GPIO_12) == HIGH` for Reset).
- Map Modbus Holding Register `0x0001` for remote Start (1), Stop (2), Reset (3), and Emergency (99).
- Create automated HIL integration tests in `tests/test_state_machine.py`.

**Non-Goals:**
- PID motion control implementation (deferred to Spec 6).
- Encoder PCNT hardware reading (deferred to Spec 4).
- MCPWM driver frequency modulation (deferred to Spec 5).

## Decisions

### 1. Atomic State Storage vs Mutex in ISR
- **Decision:** Use C11 atomic operations (`_Atomic machine_state_t`) or atomic volatile getters/setters for `machine_state`.
- **Rationale:** Calling `xSemaphoreTake` or FreeRTOS Mutex functions inside an ISR triggers kernel panic. Atomic operations allow instant state mutation directly within the ISR context without locking.

### 2. Immediate Physical Hardware Cutoff in ISR
- **Decision:** Disable motor output GPIO / PWM drive pins directly within the `GPIO 12` ISR before calling `vTaskNotifyGiveFromISR`.
- **Rationale:** FreeRTOS task scheduling incurs non-zero latency. Physical motor drive signals must be cut immediately upon falling edge detection.

### 3. Level-Checked Transition Guards
- **Decision:** Evaluate `gpio_get_level(GPIO_12)` during `EMERGENCY -> IDLE` (Reset) and `IDLE -> MOVING` (Start) transitions.
- **Rationale:** Prevents system reset or movement while the physical Emergency button is still held down.

### 4. Modbus Command Holding Register `0x0001`
- **Decision:** Map Holding Register `0x0001` as a Command Register. Writing `1` triggers Start, `2` triggers Stop, `3` triggers Reset, and `99` triggers Simulated Emergency.
- **Rationale:** Enables remote control via Modbus Master and allows automated integration testing with `pytest` without manual physical button presses.

## Risks / Trade-offs

- **[Risk]** Noise or contact bounce on `GPIO 12` triggering false Emergency interrupts.
  - *Mitigation*: Internal pull-up enabled, hardware RC filter on PCB if needed, and level verification in task context.
- **[Risk]** Uninitialized `ControlLoopTask` handle when ISR fires during early boot.
  - *Mitigation*: Null-check `g_control_task_handle` in ISR before invoking `vTaskNotifyGiveFromISR`.
