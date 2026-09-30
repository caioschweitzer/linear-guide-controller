## ADDED Requirements

### Requirement: Modbus TCP Supervisory Communication
The Python SCADA supervisory system (`tools/supervisory`) SHALL connect to the ESP32 controller using `pymodbus.client.ModbusTcpClient` over IP network (default port 502) instead of serial COM port.

#### Scenario: TCP Socket Telemetry Connection
- **WHEN** the user specifies a valid IP address (e.g. `192.168.1.100`) and port (default `502`) and clicks Connect
- **THEN** the supervisory worker thread MUST establish a TCP socket connection, poll telemetry at 20Hz, and render real-time plots and status indicators.

#### Scenario: Automatic Network Reconnection
- **WHEN** the TCP network socket experiences a timeout or disconnect event
- **THEN** the supervisory worker thread MUST non-blocking retry connection attempts every 2 seconds without freezing the PyQt6 UI dashboard.
