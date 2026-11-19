# Chapter 3: Dual-Core FreeRTOS Architecture & Kernel IPC

## 1. Multi-Core Task Architecture

The ESP32-S3 contains two Xtensa LX7 32-bit cores. To prevent serial communication overhead or display updates from delaying the control loop, tasks are explicitly pinned across both cores:

```
                      ESP32-S3 DUAL-CORE PROCESSOR
 ┌───────────────────────────────────┐   ┌───────────────────────────────────┐
 │              CORE 0               │   │              CORE 1               │
 │    (I/O, Comm & User Interface)   │   │    (Deterministic Control Loop)   │
 ├───────────────────────────────────┤   ├───────────────────────────────────┤
 │ • Modbus Slave Task (P4, 4096B)   │   │ • Control Loop Task (P10, 4096B)  │
 │ • IHM LCD Display Task (P5, 3072B)│   │   - 100 Hz (10 ms) Period         │
 │ • Start Debounce Task (P4, 2048B) │   │   - PCNT Encoder Hardware Read    │
 └───────────────────────────────────┘   │   - PID Calculation & MCPWM Drive │
                   │                     └───────────────────────────────────┘
                   │                                       ▲
                   ▼                                       │ Direct Notification
        ┌─────────────────────┐                   ┌──────────────────────────┐
        │  g_system_mutex     │                   │ GPIO 12 Emergency ISR    │
        │ (Mutex-Protected)   │                   │ (IRAM-Resident, < 1 µs)  │
        └─────────────────────┘                   └──────────────────────────┘
```

---

## 2. Kernel Synchronization & Inter-Process Communication (IPC)

### 2.1 Mutex Protection (`g_system_mutex`)
All telemetry variables and setpoints shared between Core 0 and Core 1 reside in the global `SystemData` structure (`main/include/shared_data.h`). 

To prevent race conditions:
- Tasks must acquire `g_system_mutex` prior to reading or writing `g_system_data`.
- Mutex lock duration is strictly bounded to $< 1\text{ ms}$ (snapshot pattern).
- Mutex acquisition uses a timeout guard (`pdMS_TO_TICKS(10)`).

### 2.2 Atomic Machine State (`_Atomic s_atomic_machine_state`)
Because FreeRTOS mutexes **cannot** be acquired inside an Interrupt Service Routine (ISR), the system state machine uses a lock-free C11 `_Atomic` variable:

```c
static _Atomic machine_state_t s_atomic_machine_state = ATOMIC_VAR_INIT(MACHINE_STATE_IDLE);
```

This guarantees that `gpio12_emergency_isr` can transition the machine state to `MACHINE_STATE_EMERGENCY` atomically in constant time ($O(1)$) without taking a mutex lock.

---

## 3. Finite State Machine (FSM)

The system operates across five distinct operational states:

```
             ┌──────────────┐   HOME / |pos|<=5mm    ┌──────────────────┐
             │ MACHINE_STATE│◄──────────────────────►│  MACHINE_STATE   │
             │    HOMING    │                        │ OPEN_LOOP_TEST   │
             └──────▲───────┘                        └──────────────────┘
                    │ Modbus HOME (4)                         ▲
                    │                                         │ Modbus OPEN_LOOP_TEST (5)
             ┌──────┴───────┐   Start Button Toggle /         │
             │ MACHINE_STATE│◄──────────────────────►┌────────┴───────┐
             │     IDLE     │   Modbus START / STOP  │ MACHINE_STATE  │
             └──────▲───────┘                        │     MOVING     │
                    │                                └────────┬───────┘
                    │ Level-Checked RESET (E-Stop Released)   │
                    │                                         │ E-Stop (GPIO 12 HIGH) /
             ┌──────┴───────┐                                 │ Modbus EMERGENCY (99)
             │ MACHINE_STATE│◄────────────────────────────────┘
             │  EMERGENCY   │ (Lockout State: Motor Disabled,
             └──────────────┘  Requires E-Stop LOW + Explicit Reset)
```

### 3.1 State Transition Rules & Safety Guards
1. **IDLE $\leftrightarrow$ MOVING**: Allowed only if no active Emergency condition exists (`gpio_safety_is_emergency_active() == false`). The physical Start button (`GPIO 11`, 50 ms debounce) toggles between `IDLE` and `MOVING`.
2. **ANY $\rightarrow$ EMERGENCY**: Instantaneous transition. Disables PWM output (`motor_set_effort(0.0)`) and de-asserts motor enable pin (`GPIO 13`).
3. **EMERGENCY Lockout**: When in `EMERGENCY`, all movement commands (`START` / `HOME` / `OPEN_LOOP_TEST`) are rejected.
4. **Level-Checked Safe Reset**: Transitioning out of `EMERGENCY` back to `IDLE` via `shared_data_request_state_change(MACHINE_STATE_IDLE)` requires that the physical E-stop button (`GPIO 12`) has been physically released (`LOW` level in Active-HIGH logic).
5. **IDLE $\rightarrow$ HOMING**: Drives motor at `-60.0%` effort until `GPIO_HOME_PIN` (`GPIO 37`) goes `HIGH` (`!= 0`), then brakes, zeroes encoder/kinematics, and returns to `IDLE`.
6. **IDLE $\rightarrow$ OPEN_LOOP_TEST**: Requires `|pos| <= 5.0 mm`. Supports two modes with an 825-sample (8.25 s @ 100 Hz) RAM burst buffer and `7500 ms` safety timeout:
   - **Active Brake (`mode = 0`)**: Drives at configured `open_loop_pwm` (`1.0%–100.0%`) until `536.0 mm` (80% travel), then applies `motor_brake`.
   - **Coast-to-Stop (`mode = 1`)**: Drives at `open_loop_pwm` until `open_loop_coast_pos_mm` (`50.0–536.0 mm`, default `400.0 mm`), steps effort to `0.0%` without active braking, and records until natural stop (`|vel| <= 2.0 mm/s` for 150 ms) or endstop guard (`650.0 mm`).

---

## 4. Priority Allocation

| Task Name | Core | Priority | Stack Size | Responsibilities |
| :--- | :--- | :--- | :--- | :--- |
| `ControlLoopTask` | Core 1 | 10 (Highest) | 4096 Bytes | 100 Hz PID / Open-Loop / Homing regulation & motor MCPWM drive |
| `IHMDisplayTask` | Core 0 | 5 | 3072 Bytes | 10 Hz LCD display refresh & status LED blinking |
| `ModbusSlaveTask` | Core 0 | 4 | 4096 Bytes | Modbus TCP (W5500 Ethernet) event processing & register sync |
| `StartDebounceTask`| Core 0 | 4 | 2048 Bytes | 50 ms debounced monitoring of physical Start button (`IDLE <-> MOVING` toggle) |
