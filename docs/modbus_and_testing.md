# Modbus RTU Register Mapping & Automated Host Testing

This document defines the Modbus RTU register map for host integration and describes how to execute automated unit/integration test suites.

---

## 1. Modbus RTU Communication Configuration

- **Baud Rate**: `115200`
- **Data Bits**: `8`
- **Parity**: `None`
- **Stop Bits**: `1`
- **Slave ID**: `1`
- **Physical Interface**: UART0 (GPIO 43 TX / GPIO 44 RX) via RS485 Transceiver

---

## 2. Modbus Register Map

### Holding Registers (Read / Write) - Function Codes 0x03 / 0x06 / 0x10

| Address | Data Type | Name | Range | Description |
| :---: | :---: | :--- | :---: | :--- |
| `0x0000` | Float32 (IEEE 754) | `position_setpoint` | `0.0` to `424.115` mm | Target position setpoint (Big-Endian word order) |
| `0x0002` | uint16 | `command` | 1, 2, 3, 99 | Command register:<br>`1`: START (Transition to MOVING)<br>`2`: STOP (Transition to IDLE)<br>`3`: RESET (Clear EMERGENCY state)<br>`99`: E-STOP (Simulate Emergency) |

### Input Registers (Read Only) - Function Code 0x04

| Address | Data Type | Name | Description |
| :---: | :---: | :--- | :--- |
| `0x0000` | Float32 (IEEE 754) | `current_position` | Measured linear position in mm |
| `0x0002` | Float32 (IEEE 754) | `current_velocity` | Calculated linear velocity in mm/s |
| `0x0004` | uint16 | `machine_state` | Current Machine State:<br>`0`: IDLE<br>`1`: MOVING<br>`2`: EMERGENCY |

---

## 3. Automated Host Unit & Integration Testing (`pytest`)

The controller includes a C host abstraction compilation mode (`-DHOST_TEST`) that allows full firmware validation on Linux using Python `ctypes` and dynamic shared libraries.

### Running Test Suite:

To run all 29 automated test cases across the 8 project modules:

```bash
# Activate python virtual environment and run pytest
tests/.venv/bin/pytest tests/
```

### Test Suite Directory Structure:

```
tests/
├── test_encoder_pcnt.py       # Encoder PCNT unit & overflow test cases
├── test_ihm_display.py        # HD44780 LCD & LED state test cases
├── test_kinematics.py         # Quadrature to linear position/velocity test cases
├── test_modbus_kernel.py      # Modbus register encoding/decoding test cases
├── test_motor_mcpwm.py        # H-bridge direction & duty effort test cases
├── test_pid_controller.py     # Anti-windup, deadband, & derivative test cases
├── test_state_machine.py      # Atomic FSM transition & interrupt test cases
└── test_system_integration.py# Closed-loop HIL system simulation test cases
```

### Test Results Summary:
```
============================== 29 passed in 1.68s ==============================
```
