# Master Technical Manual: ESP32-S3 Linear Actuator Controller

Welcome to the comprehensive technical documentation suite for the ESP32-S3 Linear Actuator Controller.

---

## 📚 Technical Manual Chapters

This documentation suite is organized into 5 dedicated technical chapters:

| Chapter | Document Title | Description & Content Overview |
| :--- | :--- | :--- |
| **Chapter 1** | [System Overview & Physical Kinematics](01_system_overview_and_physics.md) | Problem statement, lead screw geometry, scale factors ($K_{\text{scale}} = 0.010602875$), EMA velocity filter, and control requirements. |
| **Chapter 2** | [Hardware Electronics & Electrical Wiring](02_hardware_and_schematics.md) | Complete GPIO pinout table, hardware MOSFET E-stop cutoff gate, MCPWM motor driver interface, and LCD display wiring. |
| **Chapter 3** | [Dual-Core FreeRTOS Architecture & Kernel IPC](03_software_architecture_freertos.md) | Core 0/1 task pinning, `g_system_mutex` snapshot IPC, C11 `_Atomic` state machine transitions, and task notification flow. |
| **Chapter 4** | [Industrial Modbus RTU Protocol Specification](04_modbus_rtu_and_communication.md) | RS485 parameters, complete 4-table Modbus register map (Coils, Discrete Inputs, Holding, Input Registers), and ASCII sequence diagrams. |
| **Chapter 5** | [Host-Native Unit & Integration Testing Suite](05_testing_and_hil_simulation.md) | GCC `-DHOST_TEST` simulation architecture, Python `ctypes` binding, and exhaustive breakdown of all 32 pytest test cases. |

---

## 🛠️ Quick Start & Build Instructions

### 1. Host Test Execution (`pytest`)
To run all 32 host integration tests on your Linux workstation:
```bash
cd tests
source .venv/bin/activate
pytest . -v -s
```

### 2. ESP32-S3 Firmware Compilation & Flashing
To compile and flash the firmware onto the physical ESP32-S3 microcontroller:
```bash
source /home/{USER}/.espressif/v6.0/esp-idf/export.sh
idf.py build
idf.py -p /dev/{PORT} flash
```
