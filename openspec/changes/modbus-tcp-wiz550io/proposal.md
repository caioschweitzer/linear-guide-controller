## Why

Modbus RTU over serial UART0 blocked standard console logging (`esp_log`), restricted telemetry bandwidth, and introduced physical noise vulnerability over serial lines. Migrating to Modbus TCP using the WIZ550io Ver1.1 (W5500 Ethernet SPI module) unlocks USB-C console logging, provides high-speed 10/100 Mbps Ethernet communication with galvanic isolation, and allows multi-client supervisory connections.

## What Changes

- **Firmware**: Replace `mbc_slave_create_serial()` with `mbc_slave_create_tcp()` in ESP-IDF `esp-modbus` stack.
- **Ethernet Integration**: Add SPI Master driver initialization and `esp_eth` W5500 PHY/MAC driver to connect to `esp_netif` (lwIP stack).
- **Pinout Allocation**: Assign SPI pins (MOSI: GPIO 23, MISO: GPIO 19, SCLK: GPIO 18, CS: GPIO 21) and W5500 control pins (RST: GPIO 22, INT: GPIO 17).
- **Console Logging**: Re-enable `esp_log` console debugging on `UART0` / USB-C port (`esp_log_level_set("*", ESP_LOG_INFO)`).
- **Supervisory Application**: **BREAKING**: Replace `ModbusSerialClient` with `ModbusTcpClient` in `tools/supervisory/main.py` and update `ui_main.py` to prompt for IP address and Port (default 502) instead of COM port.
- **Automated Tests**: Update Pytest automated HIL test scripts to execute Modbus TCP client tests against the ESP32 IP address.

## Capabilities

### New Capabilities
- `wiz550io-ethernet-driver`: SPI Master driver integration and ESP-IDF `esp_eth` W5500 stack configuration for network connectivity.

### Modified Capabilities
- `kernel-freertos-modbus`: Replace Modbus RTU serial slave on UART0 with Modbus TCP slave on port 502 over Ethernet, and restore console logging on UART0.
- `modbus-supervisory-ui`: Replace Modbus RTU serial connection logic with Modbus TCP connection logic, including IP address/Port UI controls.

## Impact

- **ESP32 Firmware**: `main/src/modbus_slave.c`, `main/include/modbus_slave.h`, `main/src/main.c`, `main/CMakeLists.txt`.
- **Python Supervisory**: `tools/supervisory/main.py`, `tools/supervisory/ui_main.py`.
- **Hardware Pinout**: Reclaims UART0 for serial logging; allocates 6 GPIOs (17, 18, 19, 21, 22, 23) for WIZ550io Ethernet SPI.
- **Tests**: `tests/test_modbus_kernel.py` and supervisory integration tests updated for TCP socket connections.
