## 1. Environment & Project Setup

- [x] 1.1 Create supervisory dependencies file `tools/requirements_supervisory.txt` containing `PyQt6`, `pyqtgraph`, `pymodbus`, and `pyserial`.
- [x] 1.2 Setup modular directory structure `tools/supervisory/` with `modbus_worker.py`, `ui_main.py`, and `main.py`.

## 2. Modbus Telemetry Worker Implementation

- [x] 2.1 Implement `QThread` `ModbusWorker` in `tools/supervisory/modbus_worker.py` handling auto-detection of ports and periodic 20Hz polling over `pymodbus`.
- [x] 2.2 Add thread-safe command queueing in `ModbusWorker` for sending Setpoints (0x0000), Commands (0x0002), and PID Gains (0x0003 - 0x0008).
- [x] 2.3 Implement disconnect detection, exception guardrails, and Qt signal emissions for real-time telemetry frames.

## 3. Graphical User Interface (PyQt6 & PyQtGraph)

- [x] 3.1 Build main window layout in `tools/supervisory/ui_main.py` featuring Dark Theme styling, Serial connection bar, and State status badge.
- [x] 3.2 Implement live `PyQtGraph` widget plotting Setpoint Position, Measured Position, and Velocity telemetry in real time.
- [x] 3.3 Add Motion Control Panel with target setpoint slider/spinbox, `Start`, `Stop`, `Home`, `Reset` buttons, and prominent red `E-STOP` button.
- [x] 3.4 Add PID Parameter Tuning Panel with float inputs for `Kp`, `Ki`, `Kd` and "Apply PID Gains" trigger.

## 4. Verification & Testing

- [x] 4.1 Implement automated host-level Python unit/mock tests in `tests/test_supervisory_ui.py` to verify ModbusWorker data decoding and signal dispatching.
- [x] 4.2 Validate end-to-end integration with ESP32-S3 firmware or mock Modbus RTU serial interface.
