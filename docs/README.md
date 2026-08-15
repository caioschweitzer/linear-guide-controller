# ESP32-S3 Linear Actuator Controller - Full Technical Manual

Welcome to the technical documentation manual for the **ESP32-S3 Deterministic Linear Actuator Controller**. This documentation provides hardware pinout mappings, FreeRTOS multi-core software architecture guidelines, Modbus RTU register specifications, and automated host testing procedures.

---

## 📚 Technical Documentation Structure

1. 🔌 **[Hardware Wiring & Electrical Pinout Guide](hardware_wiring.md)**
   - Complete ESP32-S3 GPIO Mapping Table (MCPWM, PCNT, Safety, I2C, UART0).
   - Electrical Power Specifications & Star Grounding Guidelines.
   - Emergency Stop (E-Stop) Hardware Cutoff Circuit Schematics.

2. ⚙️ **[Software Architecture & Real-Time Control](software_architecture.md)**
   - FreeRTOS Dual-Core Task Distribution (Core 1 Real-time PID Loop / Core 0 I/O & Modbus).
   - Thread-Safe Shared Data & Mutex Snapshot IPC Patterns.
   - Finite State Machine (FSM) State Transition Rules.
   - Linear Kinematics Equations & Exponential Moving Average (EMA) Velocity Filtering.
   - Closed-Loop PID Algorithm Parameters & Safety Feature Guardrails.

3. 📡 **[Modbus RTU Register Map & Testing Suite](modbus_and_testing.md)**
   - Modbus RTU Slave Configuration (115200 baud, 8N1, Slave ID 1).
   - Holding & Input Register Memory Maps (Float32 IEEE 754 Big-Endian).
   - Host Integration Testing (`pytest` + `ctypes` Host Shared Library execution).

---

## 🚀 Quick Start Guide

### Building Firmware (ESP-IDF v5.x)
```bash
# Set up ESP-IDF target
idf.py set-target esp32s3

# Build firmware binary
idf.py build

# Flash & Monitor ESP32-S3
idf.py -p /dev/ttyUSB0 flash monitor
```

### Running Host Test Suite (Linux Native)
```bash
# Execute unit & integration test suites
tests/.venv/bin/pytest tests/
```

---

## 🛡️ System Features Summary

- **Deterministic Control**: 100 Hz PID control loop pinned to FreeRTOS Core 1.
- **Hardware Safety Cutoff**: IRAM-resident ISR handles Emergency E-Stop interrupts with sub-microsecond response and hardware enable signal pull-down.
- **Linear Stroke**: $424.115\text{ mm}$ travel range clamped automatically.
- **Automated Verification**: 29 automated test cases covering state machine, kinematics, PID, motor drivers, encoder counters, LCD display, Modbus RTU, and integrated closed-loop control.
