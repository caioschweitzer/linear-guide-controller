# Chapter 5: Host-Native Unit & Integration Testing Suite

## 1. Host Test Architecture (`-DHOST_TEST`)

To enable rapid automated testing on Linux continuous integration (CI) servers without requiring physical ESP32 hardware, the firmware implements a host compilation abstraction layer (`-DHOST_TEST`):

```
                       HOST AUTOMATED TEST PIPELINE
 ┌─────────────────────────────────────────────────────────────────────────┐
 │                            pytest Test Suite                            │
 │                        (tests/test_*.py - 32 tests)                     │
 └─────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
 ┌─────────────────────────────────────────────────────────────────────────┐
 │                             Python ctypes                               │
 │                (In-Memory Symbol Binding & C Structure Sync)            │
 └─────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
 ┌─────────────────────────────────────────────────────────────────────────┐
 │                   libsystem_integration.so (GCC Shared Lib)             │
 │  • shared_data.c      • gpio_safety.c        • linear_kinematics.c     │
 │  • encoder_pcnt.c     • motor_mcpwm.c        • pid_controller.c        │
 │  • ihm_display.c      • modbus_slave.c                                 │
 └─────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Shared Library Compilation Pipeline

The host integration wrapper compiles the actual firmware source files in `main/src/` into a shared library (`tests/libsystem_integration.so`):

```bash
gcc -shared -fPIC -O2 -DHOST_TEST \
  main/src/shared_data.c \
  main/src/gpio_safety.c \
  main/src/linear_kinematics.c \
  main/src/encoder_pcnt.c \
  main/src/motor_mcpwm.c \
  main/src/pid_controller.c \
  main/src/ihm_display.c \
  main/src/modbus_slave.c \
  -o tests/libsystem_integration.so \
  -Imain/include
```

---

## 3. Comprehensive Breakdown of the 32 Pytest Test Cases

The test suite consists of 32 unit and integration tests distributed across 8 test modules:

### 3.1 `test_encoder_pcnt.py` (4 tests)
- `test_encoder_initialization_and_zero_reading`: Validates initial tick count is zero after driver setup.
- `test_quadrature_forward_and_reverse_counting`: Verifies bi-directional count increment/decrement.
- `test_16bit_hardware_overflow_accumulation`: Verifies 16-bit PCNT hardware accumulator roll-over handling without integer wrap.
- `test_atomic_zero_reset`: Validates atomic encoder position zeroing routine.

### 3.2 `test_ihm_display.py` (3 tests)
- `test_lcd_formatting_normal_and_extreme`: Tests line formatting for normal and extreme floating point numbers.
- `test_led_timing_and_state_transitions`: Verifies LED blink rate calculations (1 Hz in IDLE, 5 Hz in MOVING, solid ON in EMERGENCY).
- `test_ihm_update_routine`: Tests main IHM refresh loop without NULL pointer panics.

### 3.3 `test_kinematics.py` (4 tests)
- `test_absolute_position_calculation_and_calibration`: Verifies conversion from encoder ticks to physical millimeters using $K_{\text{scale}} = 0.010602875$.
- `test_dt_guardrail_and_startup_spike_prevention`: Ensures $\Delta t$ guardrails prevent infinite velocity spikes when $\Delta t \to 0$.
- `test_differential_kinematics_and_ema_filter`: Tests velocity calculation and Exponential Moving Average smoothing ($\alpha = 0.20$).
- `test_modbus_fixed_point_serialization`: Validates Big-Endian 32-bit float serialization for Modbus Holding/Input registers.

### 3.4 `test_modbus_kernel.py` (5 tests)
- `test_holding_register_setpoint_write_read`: Validates Holding Register setpoint read/write operations.
- `test_input_registers_read_initial_state`: Tests Input Register telemetry readback.
- `test_discrete_inputs_and_coils_c_struct`: Verifies C-struct memory layout alignment for binary registers.
- `test_discrete_inputs_read`: Tests Discrete Input bit-mask read (FC 0x02).
- `test_coils_read_write`: Tests Coil read and write operations (FC 0x01 / 0x05).

### 3.5 `test_motor_mcpwm.py` (5 tests)
- `test_forward_effort`: Verifies positive duty cycle mapping to Forward PWM channel.
- `test_reverse_effort`: Verifies negative duty cycle mapping to Reverse PWM channel.
- `test_passive_brake_and_zero_stop`: Validates passive regenerative braking (0% effort on both channels).
- `test_effort_clamping_and_failsafe`: Ensures effort input is clamped to $[-100.0\%, +100.0\%]$.
- `test_direction_reversal_brake_transition`: Tests insertion of passive brake state during rapid direction reversal.

### 3.6 `test_pid_controller.py` (5 tests)
- `test_proportional_response`: Tests proportional output scaling for position error.
- `test_conditional_anti_windup`: Verifies integrator clamping when control effort saturates.
- `test_derivative_kick_avoidance`: Ensures derivative term acts on position feedback derivative to prevent derivative kick.
- `test_in_position_deadband`: Verifies zero effort output when $|e| \le 0.1\text{ mm}$.
- `test_numerical_guardrails`: Tests immunity to NaN/Inf inputs.

### 3.7 `test_state_machine.py` (3 tests)
- `test_state_machine_normal_flow`: Tests standard `IDLE` $\rightarrow$ `MOVING` $\rightarrow$ `IDLE` state transitions.
- `test_state_machine_emergency_lockout_rejection`: Ensures all start/move requests are rejected while in `EMERGENCY`.
- `test_state_machine_safe_reset`: Validates level-checked reset out of `EMERGENCY` state.

### 3.8 `test_system_integration.py` (3 tests)
- `test_system_boot_sequence`: Simulates complete system boot and initial telemetry hydration.
- `test_closed_loop_moving_state`: Simulates closed-loop position regulation to target setpoint.
- `test_emergency_estop_interruption`: Simulates physical E-stop button press during active movement, verifying instant motor cutoff and lockout.
