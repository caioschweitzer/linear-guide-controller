# Proposal

## Why

Currently, Modbus TCP communication relies on an external WIZ550io (W5500) Ethernet module over SPI, which requires 6 dedicated GPIOs, external cabling, and physical Ethernet infrastructure. Migrating the transport layer to the ESP32's built-in Wi-Fi station mode removes the physical tether to the linear guide, eliminates external SPI hardware dependencies, and enables wireless telemetry and control via an existing Wi-Fi access point ("cerberus").

## What Changes

- **ESP32 Firmware**:
  - Replace the WIZ550io Ethernet SPI driver initialization (`esp_eth`) with the ESP-IDF native Wi-Fi Station driver (`esp_wifi`, `esp_event`, `nvs_flash`).
  - Configure default Wi-Fi credentials with SSID `"cerberus"` and password `"asenhaehsecreta"`.
  - Initialize the default Wi-Fi station network interface (`esp_netif_create_default_wifi_sta`) and handle connection / reconnection events (`WIFI_EVENT` and `IP_EVENT`).
  - Bind the Modbus TCP slave (`mbc_slave_create_tcp`) to the Wi-Fi network interface on port 502.
  - Provide configurable static IP or DHCP acquisition, logging the assigned IP over the console.
- **Python Supervisory**:
  - Update the supervisory connection settings to support Wi-Fi IP configuration, keeping port 502.
  - Update defaults and connection instructions in the UI to document connecting over the wireless local network.
- **Automated Tests**:
  - Ensure unit and mock tests validate Modbus TCP stack operations independently of physical Ethernet drivers.

## Capabilities

### New Capabilities
- `wifi-station-transport`: Built-in Wi-Fi station mode integration (`esp_wifi`, `esp_event`, NVS flash) providing network connectivity for Modbus TCP without external SPI Ethernet hardware.

### Modified Capabilities
- `kernel-freertos-modbus`: Modbus TCP slave network binding switched from SPI Ethernet (`esp_netif_eth`) to Wi-Fi station (`esp_netif_sta`).

## Impact

- **ESP32 Firmware**: `main/src/modbus_slave.c`, `main/include/modbus_slave.h`, `main/src/main.c`, `main/CMakeLists.txt`, `sdkconfig`.
- **Hardware Pinout**: Frees up the 6 SPI / control GPIOs previously assigned to the WIZ550io (MOSI: GPIO 23, MISO: GPIO 19, SCLK: GPIO 18, CS: GPIO 21, RST: GPIO 22, INT: GPIO 17).
- **Python Supervisory**: `tools/supervisory/modbus_worker.py`, `tools/supervisory/ui_main.py`.
- **Tests**: Mock network initialization in `tests/` updated if Ethernet-specific symbols are referenced.
