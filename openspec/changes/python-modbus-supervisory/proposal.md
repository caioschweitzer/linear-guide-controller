## Why

The linear guide controller firmware exposes control parameters, motion commands, and real-time state via Modbus RTU, but currently lacks a dedicated graphical supervisory interface (SCADA / HMI) for live monitoring, PID tuning, and manual motion control from a desktop station. Creating a Python-based supervisory UI will provide operators and developers with real-time telemetry plotting (position/velocity curves), state machine monitoring, and direct control over setpoints and emergency procedures.

## What Changes

- Create a desktop Python supervisory application (`tools/supervisory_ui.py` / `supervisory/`) using **PyQt6** and **PyQtGraph**.
- Implement asynchronous / non-blocking Modbus RTU communication worker thread using `pymodbus` to poll telemetry at 20Hz-50Hz without freezing the UI.
- Provide interactive controls for setpoint position (mm), start/stop/homing/reset commands, and remote software Emergency Stop.
- Include live PID gain sliders/spinboxes (`Kp`, `Ki`, `Kd`) with an explicit "Apply Gains" trigger sending 32-bit floats to holding registers `0x0003 - 0x0008`.
- Display real-time dual-channel telemetry graph (Target Position vs Actual Position and Velocity).
- Display machine state badges (`IDLE`, `MOVING`, `HOMING`, `ERROR`) and discrete hardware pin indicators (`E-Stop`, `Safety Enable`).

## Capabilities

### New Capabilities
- `modbus-supervisory-ui`: Graphical Python supervisory control interface (SCADA) for real-time ESP32 Modbus RTU monitoring and control.

### Modified Capabilities
*(None - existing firmware Modbus register mapping remains unchanged)*

## Impact

- **New files**: `tools/supervisory_ui.py`, `tools/requirements_supervisory.txt`, `tests/test_supervisory_ui.py`.
- **Dependencies**: `PyQt6`, `pyqtgraph`, `pymodbus`, `pyserial`.
- **Firmware compatibility**: Operates directly against the existing Modbus RTU slave registers on the ESP32 (Slave ID 1, 115200 baud).
