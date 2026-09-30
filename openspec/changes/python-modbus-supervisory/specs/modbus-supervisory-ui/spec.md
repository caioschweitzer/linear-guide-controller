## ADDED Requirements

### Requirement: Serial Port Connection Management
The supervisory UI SHALL auto-detect connected serial ports (ESP32 USB/UART bridge VIDs: 0x303a, 0x10c4, 0x1a86, 0x0403) and provide a manual serial port drop-down menu with Connect/Disconnect options at 115200 baud.

#### Scenario: Auto-detect ESP32 serial port
- **WHEN** the user launches the supervisory application
- **THEN** the application detects available COM / `/dev/ttyUSB` ports and populates the port selection widget.

#### Scenario: Establish Modbus RTU connection
- **WHEN** the user selects a valid serial port and clicks "Connect"
- **THEN** the application initializes the Modbus RTU serial client and starts polling telemetry.

### Requirement: Real-Time Telemetry Graphing
The supervisory UI SHALL plot live target setpoint position, actual measured position (mm), and velocity (mm/s) using PyQtGraph at a minimum refresh rate of 20Hz without freezing the graphical user interface.

#### Scenario: Display live position tracking curve
- **WHEN** the actuator moves along the linear guide
- **THEN** the plot updates real-time position curves for setpoint and actual position.

### Requirement: Motion Setpoint and Command Control
The supervisory UI SHALL allow users to specify target position setpoints (float 32-bit), transmit start/stop/homing/reset commands to Modbus Holding Register 0x0002, and execute an instant software Emergency Stop via coil trigger.

#### Scenario: Transmit motion command
- **WHEN** the user inputs a position setpoint and clicks "Start Motion"
- **THEN** the application writes the 32-bit float setpoint to Holding Register 0x0000 and command `1` to Holding Register 0x0002.

#### Scenario: Trigger software Emergency Stop
- **WHEN** the user clicks the Emergency Stop button
- **THEN** the application immediately writes command `4` to Holding Register 0x0002 and sets the remote emergency coil bit.

### Requirement: Live PID Parameter Tuning
The supervisory UI SHALL allow viewing and editing closed-loop PID control gains (`Kp`, `Ki`, `Kd`) as 32-bit IEEE 754 floating point values and writing them to Holding Registers 0x0003 through 0x0008 upon user confirmation.

#### Scenario: Update PID gains on controller
- **WHEN** the user modifies `Kp`, `Ki`, or `Kd` numerical values and clicks "Apply PID Gains"
- **THEN** the application writes the 32-bit float values to Holding Registers 0x0003, 0x0005, and 0x0007.

### Requirement: Machine State and Safety Status Visualization
The supervisory UI SHALL poll Input Register 0x0004 and Discrete Inputs 0x0000 to display the state machine state (`IDLE`, `MOVING`, `HOMING`, `ERROR`) and discrete hardware safety flags (Hardware E-Stop Pin, Safety Enable).

#### Scenario: Reflect error state visually
- **WHEN** the ESP32 state machine transitions to `ERROR` or `E-STOP` state
- **THEN** the UI updates the state badge to red and logs an alert event in the telemetry console.
