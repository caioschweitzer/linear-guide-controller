## Context

The linear guide controller previously communicated telemetry and control commands using Modbus RTU on `UART_NUM_0`. This locked the serial interface, prevented `esp_log` console output, and limited SCADA integration to local serial cables.

The WIZ550io Ver1.1 module utilizes a W5500 hardwired TCP/IP chip communicating via SPI. ESP-IDF provides built-in support for W5500 via the `esp_eth` component and `espressif/esp-modbus` stack for Modbus TCP Slave.

## Goals / Non-Goals

**Goals:**
- Initialize W5500 Ethernet via SPI master on ESP32 (GPIOs: MOSI 23, MISO 19, SCLK 18, CS 21, RST 22, INT 17).
- Bind Modbus TCP Slave server to port 502 via `esp_netif` and `esp-modbus`.
- Maintain identical Modbus register mapping (Holding, Input, Discrete, Coil) for seamless logic continuity.
- Re-enable standard console log output (`ESP_LOG_INFO`) on `UART0` / USB-C.
- Update Python Supervisory application (`tools/supervisory`) to connect over TCP socket.

**Non-Goals:**
- Implementing dynamic IP discovery / MDNS (DHCP or static IP fallback is used).
- Modifying the underlying 200Hz PID control task on Core 1 or safety state machine.

## Decisions

### Decision 1: Hardware SPI Bus Assignment
- **Choice**: Use SPI2 (VSPI) bus (MOSI: GPIO 23, MISO: GPIO 19, SCLK: GPIO 18) with CS: GPIO 21, RST: GPIO 22, INT: GPIO 17.
- **Rationale**: Keeps default SPI hardware pins separate from I2C (GPIO 1, 2), MCPWM (GPIO 4, 5, 6), E-Stop (GPIO 12), and PCNT Encoder (GPIO 14, 15).
- **Alternatives Considered**: Software bit-banging SPI (slower and higher CPU overhead on Core 0).

### Decision 2: Modbus TCP Protocol Configuration in `esp-modbus`
- **Choice**: Use `mbc_slave_create_tcp()` with `MB_PORT_TCP_SLAVE`.
- **Rationale**: `espressif/esp-modbus` manages socket listening, client connections, and Modbus TCP framing automatically while using the exact same descriptor structures (`mb_register_area_descriptor_t`).

### Decision 3: Python Supervisory Connection Transition
- **Choice**: Replace `pymodbus.client.ModbusSerialClient` with `pymodbus.client.ModbusTcpClient`.
- **Rationale**: Standardizes supervisory communication over IP networks and simplifies testing using standard network tools or mock TCP sockets.

## Risks / Trade-offs

- **[Risk: Power Supply Voltage Drop]** → Ethernet PHY transmission causes current spikes (~200mA). Mitigation: Ensure 3.3V power supply decoupling capacitors near WIZ550io header.
- **[Risk: SPI Bus Speed Limits]** → W5500 SPI max clock speed is 8-12 MHz. Mitigation: Configure SPI clock to 10 MHz in ESP-IDF `spi_bus_config_t`.
- **[Risk: Network Disconnection in SCADA]** → TCP socket disconnects during network cable unplug. Mitigation: Implement automatic auto-reconnect loop in Python SCADA thread.

## Migration Plan

1. Configure SPI and Ethernet W5500 driver in ESP32 `modbus_slave.c`.
2. Re-enable `ESP_LOG` output level to `ESP_LOG_INFO`.
3. Update `tools/supervisory/main.py` and `ui_main.py` for Modbus TCP.
4. Update `tests/test_modbus_kernel.py` for TCP socket testing.
