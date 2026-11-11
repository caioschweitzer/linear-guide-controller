# Design

## Context

The current linear guide controller runs an `esp-modbus` TCP slave on port 502 bound to an external WIZ550io (W5500) Ethernet SPI module. While functional, the physical Ethernet cable restricts linear guide bench setups, requires 6 GPIOs (SPI MOSI/MISO/SCLK/CS, RST, INT), and mandates an Ethernet switch/router near the machine.
The ESP32-S3 contains an internal 2.4 GHz 802.11 b/g/n Wi-Fi subsystem. Migrating to Wi-Fi Station (STA) mode maintains the same standard Modbus TCP protocol over TCP/IP, allowing the existing Python supervisory UI (`pymodbus`) to communicate wirelessly without changes to the Modbus register map.

## Goals / Non-Goals

**Goals:**
- Replace WIZ550io SPI driver and `esp_eth` with native ESP-IDF `esp_wifi` station mode and `nvs_flash`.
- Configure default credentials: SSID `"cerberus"`, password `"asenhaehsecreta"`.
- Support robust auto-reconnection if Wi-Fi signal drops.
- Print clear IP and connection status messages to the console log upon obtaining an IP.
- Ensure supervisory UI seamlessly connects over Wi-Fi by entering the ESP32's Wi-Fi IP address.

**Non-Goals:**
- SoftAP (Access Point) mode or captive portal web configuration (not needed; fixed STA mode fits lab/bench workflow).
- Changing Modbus registers, coils, telemetry sampling, or control loop timings.
- Dual Ethernet + Wi-Fi simultaneous bridging.

## Decisions

### 1. ESP-IDF Wi-Fi Station Mode (`esp_wifi` + `esp_netif`)
- **Decision**: Initialize Wi-Fi in Station mode using `esp_netif_create_default_wifi_sta()` with an event handler for `WIFI_EVENT` and `IP_EVENT`.
- **Rationale**: Standard ESP-IDF pattern for wireless connectivity. Uses `nvs_flash_init()` for Wi-Fi RF calibration and persistence.
- **Alternatives considered**:
  - *Keep W5500 and add Wi-Fi concurrently*: Adds unnecessary complexity, power consumption, and GPIO usage.
  - *ESP-NOW*: Does not use TCP/IP; would break Modbus TCP compliance and require rewriting the Python supervisory communication stack.

### 2. Network IP Allocation (DHCP with Console Logging vs. Static Fallback)
- **Decision**: Enable DHCP client by default so the "cerberus" router assigns an IP, and log the assigned IP address boldly to USB-C UART console (`ESP_LOGI(TAG, "Wi-Fi Connected! IP: %s", ip_str)`). Provide compile-time optional static IP if desired.
- **Rationale**: On Wi-Fi access points, DHCP avoids IP conflicts with other network devices. Logging the IP allows instant discovery for the supervisory.

### 3. Supervisory UI Alignment
- **Decision**: Retain `tools/supervisory/modbus_worker.py` and `ui_main.py` TCP client architecture, adding a placeholder/hint for Wi-Fi IP entry and updating connection logs.
- **Rationale**: `ModbusTcpClient` in `pymodbus` works transparently over Wi-Fi as long as the PC and ESP32 are on the same subnet (or reachable via routing).

## Risks / Trade-offs

- **[Risk] Wireless latency jitter vs. hardwired Ethernet**
  → *Mitigation*: The supervisory telemetry runs at 100 ms polling interval (10 Hz), well within normal 2.4 GHz Wi-Fi latency (< 5-10 ms). The emergency stop is handled in firmware via GPIO interrupt, so motor safety never relies on network latency.
- **[Risk] Temporary Wi-Fi disconnect during movement**
  → *Mitigation*: The event handler initiates immediate `esp_wifi_connect()` upon `WIFI_EVENT_STA_DISCONNECTED`. Modbus TCP reconnect logic in `tools/supervisory/modbus_worker.py` already handles socket disconnects with retry loops.
- **[Risk] Mock tests in x86/Linux build environment**
  → *Mitigation*: Keep network driver headers isolated under `#ifndef HOST_TEST` / `#ifdef ESP_PLATFORM` guards so `pytest tests/` unit tests continue to compile and run cleanly.
