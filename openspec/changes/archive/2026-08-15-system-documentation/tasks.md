## 1. Hardware Pinout & Wiring Documentation

- [x] 1.1 Create `docs/hardware_wiring.md` documenting ESP32-S3 GPIO mapping (MCPWM, PCNT, Safety E-Stop/Start, IHM I2C, Status LED, Modbus UART0) and electrical power specifications
- [x] 1.2 Document hardware safety circuit layout and active-low emergency cutoff pin behavior

## 2. Software Architecture & Control Loop Documentation

- [x] 2.1 Create `docs/software_architecture.md` detailing FreeRTOS dual-core task allocation (Core 1 100 Hz PID Control vs Core 0 IHM/Modbus/IO)
- [x] 2.2 Document atomic state machine transitions, mutex snapshot IPC pattern, kinematics conversions, and PID filtering algorithms

## 3. Communication, Testing & Master Manual Documentation

- [x] 3.1 Create `docs/modbus_and_testing.md` mapping holding/input registers, serial framing (115200 baud, 8N1, Slave ID 1), and automated host test execution (`pytest`)
- [x] 3.2 Create master `docs/README.md` system manual linking all module documentation guides
