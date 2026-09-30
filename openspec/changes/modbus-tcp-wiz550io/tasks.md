## 1. WIZ550io W5500 SPI Driver & Ethernet Integration

- [x] 1.1 Add SPI Master driver and ESP-IDF `esp_eth` W5500 MAC/PHY initialization in `main/src/modbus_slave.c`.
- [x] 1.2 Configure GPIO pin assignments (MOSI: 23, MISO: 19, SCLK: 18, CS: 21, RST: 22, INT: 17) for WIZ550io.
- [x] 1.3 Attach W5500 ethernet driver to `esp_netif` stack and handle IP event callbacks (DHCP/Static IP).

## 2. Modbus TCP Slave Core Implementation

- [x] 2.1 Reconfigure `modbus_slave_init()` to use `mbc_slave_create_tcp()` with TCP port 502.
- [x] 2.2 Re-enable standard console log output (`esp_log_level_set("*", ESP_LOG_INFO)`) on `UART_NUM_0`.
- [x] 2.3 Verify Modbus descriptor structures (Holding, Input, Discrete, Coil) bind correctly to Modbus TCP events.

## 3. Python Supervisory SCADA Migration

- [x] 3.1 Replace `ModbusSerialClient` with `ModbusTcpClient` in `tools/supervisory/main.py`.
- [x] 3.2 Update `tools/supervisory/ui_main.py` connection controls to prompt for IP address and Port 502 instead of COM port.
- [x] 3.3 Add auto-reconnect retry logic in the supervisory telemetry worker thread.

## 4. Testing & Verification

- [x] 4.1 Update host/HIL test script (`tests/test_modbus_kernel.py`) for Modbus TCP client sockets.
- [x] 4.2 Verify ESP32 compilation with `idf.py build` and run host automated unit tests.
