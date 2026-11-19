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
| **Chapter 4** | [Industrial Modbus TCP Protocol Specification](04_modbus_rtu_and_communication.md) | WIZ550io (W5500) SPI Ethernet interface, TCP port 502, complete 4-table Modbus register map (Coils, Discrete Inputs, Holding, Input Registers), supervisory SCADA client (multi-curve open-loop, sine trajectory, themes), and auto-reconnect logic. |
| **Chapter 5** | [Host-Native Unit & Integration Testing Suite](05_testing_and_hil_simulation.md) | GCC `-DHOST_TEST` simulation architecture, Python `ctypes` binding, and exhaustive breakdown of all 62 pytest test cases. |

---

## 🛠️ Quick Start & Build Instructions

### 1. Host Test Execution (`pytest`)
To run all 54 host-native unit and integration tests (with 8 TCP HIL tests skipped when no hardware is attached) on your Linux workstation:
```bash
cd /path/to/controlador_guia_linear
PYTHONPATH=. tests/.venv/bin/pytest tests/ -v
```

### 2. HIL Tests Against Live ESP32 (via Ethernet)
```bash
MODBUS_HOST=<ESP32_IP> MODBUS_PORT=502 \
PYTHONPATH=. tests/.venv/bin/pytest tests/ -v
```

### 2. ESP32-S3 Firmware Compilation & Flashing
To compile and flash the firmware onto the physical ESP32-S3 microcontroller:
```bash
source /home/{USER}/.espressif/v6.0/esp-idf/export.sh
idf.py build
idf.py -p /dev/{PORT} flash
```
