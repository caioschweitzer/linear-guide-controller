# Spec Delta

## Purpose

Provides wireless local area network connectivity for the linear guide controller via built-in Wi-Fi station mode, enabling Modbus TCP communication and telemetry without external Ethernet wiring.

## ADDED Requirements

### Requirement: Wi-Fi Station Mode Initialization and Auto-Reconnect
The system SHALL initialize the ESP-IDF Wi-Fi driver in station (STA) mode with non-volatile storage (NVS) and automatically handle Wi-Fi connection and reconnection events.

#### Scenario: Successful Wi-Fi association
- **WHEN** the ESP32 boots and finds the configured access point
- **THEN** it MUST connect to the AP and acquire an IP address via DHCP or static assignment.

#### Scenario: Reconnection on Wi-Fi disconnection
- **WHEN** the Wi-Fi connection is lost during operation
- **THEN** the system MUST trigger auto-reconnect attempts periodically until the connection is restored.

### Requirement: Default Wi-Fi Credentials
The system SHALL configure the default Wi-Fi SSID to `"cerberus"` and default WPA2 password to `"asenhaehsecreta"`.

#### Scenario: Boot with default credentials
- **WHEN** the ESP32 initializes Wi-Fi without stored custom overrides
- **THEN** it SHALL use SSID `"cerberus"` and password `"asenhaehsecreta"` to associate with the network.

### Requirement: Modbus TCP Service over Wi-Fi
The system SHALL bind the Modbus TCP slave service to port 502 on the active Wi-Fi station network interface (`esp_netif_sta`).

#### Scenario: Modbus TCP Client Connection
- **WHEN** a supervisory Modbus TCP client connects to the ESP32's assigned Wi-Fi IP address on port 502
- **THEN** the Modbus slave MUST accept the TCP connection and process Modbus requests normally.
