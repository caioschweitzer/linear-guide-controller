# Tasks

## 1. Firmware Wi-Fi Station Integration

- [x] 1.1 Update `main/CMakeLists.txt` to include `esp_wifi` and `nvs_flash` in component requirements and verify CMake configuration.
- [x] 1.2 Implement Wi-Fi Station mode initialization (`esp_wifi`), NVS storage setup (`nvs_flash`), and event handlers with default SSID `"cerberus"` and password `"asenhaehsecreta"` in `main/src/modbus_slave.c` and `main/include/modbus_slave.h`.
- [x] 1.3 Bind the Modbus TCP slave service (`mbc_slave_create_tcp`) to the Wi-Fi station netif and remove obsolete WIZ550io SPI Ethernet driver code and pin bindings.

## 2. Supervisory UI and Verification

- [x] 2.1 Update `tools/supervisory/modbus_worker.py` and `tools/supervisory/ui_main.py` with Wi-Fi connection defaults, log messages, and UI guidance for entering the Wi-Fi assigned IP.
- [x] 2.2 Update test mock declarations if needed and verify complete test suite execution with `tests/.venv/bin/pytest tests/`.
