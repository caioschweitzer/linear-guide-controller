## Context

The ESP32-S3 firmware implements a Modbus RTU slave operating on UART0 (115200 baud). While automated HIL test scripts exist (`tests/test_modbus_kernel.py`), human operators need a visual SCADA interface to control motion setpoints, tune PID loops in real time, monitor kinematic telemetry, and visually diagnose safety/E-Stop states.

## Goals / Non-Goals

**Goals:**
- Provide a responsive Python GUI built with **PyQt6** and **PyQtGraph**.
- Decouple serial I/O from the GUI event loop using a dedicated `QThread` Modbus worker to ensure UI rendering remains fluid (60 FPS) and non-blocking.
- Display live graphs of Setpoint Position, Measured Position (mm), and Velocity (mm/s).
- Provide control panels for Motion Commands (`Start`, `Stop`, `Home`, `Reset`), IEEE 754 Floating-Point PID Gain Tuning (`Kp`, `Ki`, `Kd`), and Emergency Stop.
- Include auto-detection of ESP32 serial COM/TTY ports.

**Non-Goals:**
- Web-based remote multi-user server (focused on standalone desktop supervisory station).
- Database log persistence (real-time telemetry display with option for CSV export).

## Decisions

### Decision 1: GUI Framework - PyQt6 + PyQtGraph over Web / Matplotlib
* **Rationale**: `PyQtGraph` uses Qt's `QGraphicsView` framework and NumPy vectors for high-performance real-time plotting, effortlessly rendering 50Hz telemetry updates with low CPU utilization. Standard `matplotlib` embeds in Tkinter/Qt cause UI stuttering at high frame rates.
* **Alternatives Considered**: 
  - *Web (FastAPI + React)*: Adds browser dependency and complex WebSocket setup.
  - *Tkinter*: Lacks native high-rate vector graphing components.

### Decision 2: Multi-Threading Architecture (`QThread` Worker)
```
┌──────────────────────────────────────┐       PyQt Signals       ┌──────────────────────────────────────┐
│             UI Main Thread           │ ◀──────────────────────  │          Modbus Worker Thread        │
│          (PyQt6 Event Loop)          │   (Telemetry Data Frame) │              (QThread)               │
├──────────────────────────────────────┤                          ├──────────────────────────────────────┤
│ - PyQtGraph Real-time Plotting       │                          │ - pymodbus ModbusSerialClient        │
│ - Motion Controls & PID Spinboxes    │ ──────────────────────▶  │ - 50ms Polling Loop (20Hz)           │
│ - Machine State & E-Stop Display     │       PyQt Slots         │ - Write Queue (Commands & Setpoints) │
└──────────────────────────────────────┘   (Commands & Writes)    └──────────────────────────────────────┘
```
* **Rationale**: Blocking serial Modbus RTU reads (`read_input_registers`, `read_holding_registers`) take 5ms - 20ms per cycle. Executing these directly on the Qt main thread causes severe UI lagging and dropped frames. Using `QThread` with thread-safe signals and slots guarantees non-blocking UI response.

## Risks / Trade-offs

- **[Risk] Serial Port Disconnect / Unplug during operation**
  → *Mitigation*: The `QThread` Modbus worker captures `SerialException` / Modbus timeout errors, emits a `connection_lost` signal to update the UI badge to `DISCONNECTED`, and gracefully attempts auto-reconnection without crashing the GUI.

- **[Risk] Simultaneous Read/Write Race Condition on Modbus Bus**
  → *Mitigation*: The worker thread maintains a thread-safe thread message queue for write commands (`write_registers`, `write_coil`) which takes priority over routine telemetry poll requests.
