## Why

The ESP32-S3 linear actuator controller system has completed code implementation across all hardware, control, communication, and display modules. Comprehensive documentation detailing the hardware interfaces, GPIO pinouts, FreeRTOS dual-core architecture, Modbus RTU register mapping, PID tuning, and Python integration testing procedures is required to enable operation, maintenance, and future hardware scaling.

## What Changes

- Create a master system documentation manual (`docs/README.md` and module guides) detailing both hardware setup and software architecture.
- Document ESP32-S3 hardware specifications, pin assignments (Encoder PCNT, MCPWM Motor Driver, GPIO Safety E-Stop/Start, IHM LCD I2C & Status LED, Modbus RTU UART0).
- Document software architecture: FreeRTOS dual-core task distribution, IPC snapshot mutex synchronization, atomic state machine, PID control loop, and Modbus RTU slave registers.
- Document automated host testing (`pytest` + `ctypes`) and hardware verification workflows.

## Capabilities

### New Capabilities
- `system-documentation`: Comprehensive software architecture and hardware wiring/usage documentation manual for the ESP32-S3 linear actuator controller.

### Modified Capabilities
<!-- None -->

## Impact

- Adds documentation in `docs/` directory.
- No breaking firmware modifications or runtime performance impact.
