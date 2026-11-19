# Chapter 4: Industrial Modbus TCP Protocol Specification

## 1. Protocol Overview

The controller implements a full Modbus TCP slave stack powered by the `espressif/esp-modbus` v2.1.3 library, using the onboard WIZ550io (W5500) SPI Ethernet module for Ethernet connectivity. This replaces the previous RS485 serial (RTU) interface, resolving the hardware UART0/USB-C conflict and enabling remote supervisory connectivity.

| Parameter | Configuration |
| :--- | :--- |
| **Interface** | Modbus TCP over 100Base-T Ethernet (WIZ550io / W5500) |
| **Transport** | IPv4 TCP Socket |
| **TCP Port** | `502` (IANA Standard Modbus Port) |
| **IP Assignment** | Static IP (`192.168.1.100` / `255.255.255.0`, Gateway `192.168.1.1`) |
| **Default Slave ID** | `1` (0x01) |
| **Supported Function Codes** | FC 0x01 (Read Coils), FC 0x02 (Read Discrete Inputs), FC 0x03 (Read Holding Regs), FC 0x04 (Read Input Regs), FC 0x05 (Write Single Coil), FC 0x06 (Write Single Reg), FC 0x10 (Write Multiple Regs) |
| **Console Logging** | Re-enabled on `UART_NUM_0` / USB-C (`ESP_LOG_INFO`) — no longer consumed by Modbus |

---

## 2. WIZ550io (W5500) SPI Ethernet Hardware Interface

The WIZ550io module connects to the ESP32-S3 via the SPI2 (VSPI) bus:

| Signal | ESP32-S3 GPIO | Direction | Description |
| :--- | :--- | :--- | :--- |
| **SPI MOSI** | `GPIO 8` | Output | SPI Master Out / Slave In |
| **SPI MISO** | `GPIO 10` | Input | SPI Master In / Slave Out |
| **SPI SCLK** | `GPIO 18` | Output | SPI Clock (5 MHz) |
| **SPI CS** | `GPIO 21` | Output | Chip Select (Active-Low) |
| **W5500 RST** | `GPIO 9` | Output | Hardware Reset (Active-Low) |
| **W5500 INT** | `GPIO 17` | Input | Interrupt (Active-Low, ethernet events) |

### Firmware Initialization Flow

```
  modbus_slave_init()
       │
       ├─ Hardware Reset GPIO 9 LOW (50ms) -> HIGH -> Delay 500ms (WIZ550io RDY)
       │
       ├─ spi_bus_initialize(SPI2_HOST)          // 5 MHz, MOSI 8, MISO 10, SCLK 18
       │
       ├─ eth_w5500_config_t + eth_mac_new_w5500()
       │   eth_phy_new_w5500()
       │   esp_eth_driver_install()
       │
       ├─ esp_netif_new() + esp_eth_new_netif_glue()
       │   esp_netif_dhcpc_stop()
       │   esp_netif_set_ip_info(192.168.1.100)
       │
       └─ mbc_slave_create_tcp(port=502)
           mbc_slave_set_descriptor(...)         // Bind register tables
           mbc_slave_start()                     // TCP listener active
```

---

## 3. Complete Modbus 4-Table Register Map

### 3.1 Coils (Binary Read/Write — FC 0x01 / FC 0x05)

| Address | Name | Description | Access |
| :--- | :--- | :--- | :--- |
| `0x0000` | `Status LED` | Physical Status LED output (`GPIO 7`). Write `1` to turn ON, `0` for OFF. | R/W |
| `0x0001` | `Remote E-Stop` | Write `1` to trigger Remote Emergency Stop transition. | Write-Only |
| `0x0002` | `Remote Start` | Write `1` to trigger Remote Start transition (if safe). | Write-Only |

### 3.2 Discrete Inputs (Binary Read-Only — FC 0x02)

| Address | Name | Description | Access |
| :--- | :--- | :--- | :--- |
| `0x0000` | `E-Stop Button Pin` | Physical Emergency Button (`GPIO 12`, Active-HIGH). `1` = Pressed/Active, `0` = Normal. | Read-Only |
| `0x0001` | `Start Button Pin` | Physical Start Button (`GPIO 11`, Active-HIGH). `1` = Pressed, `0` = Normal. | Read-Only |
| `0x0002` | `Safety Enable Pin` | Motor Hardware Enable Line (`GPIO 13`). `1` = Enabled, `0` = Disabled. | Read-Only |
| `0x0003` | `Home Sensor Pin` | Home Sensor (`GPIO 37`, NC to GND + Pull-Up). `1` = Home Detected, `0` = Clear. | Read-Only |

### 3.3 Holding Registers (Word Read/Write — FC 0x03 / FC 0x06 / FC 0x10)

| Address | Parameter | Format | Unit / Values | Description |
| :--- | :--- | :--- | :--- | :--- |
| `0x0000` – `0x0001` | `position_setpoint` | Float32 (Big-Endian) | mm | Target linear position setpoint (`0.0` to `670.0` mm). |
| `0x0002` | `command` | uint16 | Enumerated | `1` = START, `2` = STOP, `3` = RESET, `4` = HOME, `5` = OPEN_LOOP_TEST, `99` = EMERGENCY |
| `0x0003` – `0x0004` | `kp` | Float32 (Big-Endian) | Dimensionless | Proportional Gain $K_p$ (Default: `2.0`). |
| `0x0005` – `0x0006` | `ki` | Float32 (Big-Endian) | 1/s | Integral Gain $K_i$ (Default: `0.5`). |
| `0x0007` – `0x0008` | `kd` | Float32 (Big-Endian) | s | Derivative Gain $K_d$ (Default: `0.05`). |
| `0x0009` | `burst_read_index` | uint16 | `0` – `824` | Sample index to expose in burst Input Registers (`0x0009`–`0x0010`). |
| `0x000A` – `0x000B` | `open_loop_pwm` | Float32 (Big-Endian) | % | Open-loop step PWM level (`1.0` to `100.0 %`, Default: `100.0`). |
| `0x000C` | `open_loop_mode` | uint16 | Enumerated | `0` = Active Brake (`536 mm`), `1` = Coast-to-Stop (Default: `0`). |
| `0x000D` – `0x000E` | `open_loop_coast_pos_mm` | Float32 (Big-Endian) | mm | Step-down to `0%` threshold in Coast mode (`50.0` to `536.0` mm, Default: `400.0`). |

### 3.4 Input Registers (Word Read-Only — FC 0x04)

| Address | Parameter | Format | Unit / Values | Description |
| :--- | :--- | :--- | :--- | :--- |
| `0x0000` – `0x0001` | `current_position` | Float32 (Big-Endian) | mm | Real-time position from encoder feedback. |
| `0x0002` – `0x0003` | `current_velocity` | Float32 (Big-Endian) | mm/s | EMA-filtered linear velocity. |
| `0x0004` – `0x0005` | `duty_cycle` | Float32 (Big-Endian) | % | Applied motor PWM duty cycle (`-100.0` to `+100.0`). |
| `0x0006` | `machine_state` | uint16 | Enumerated | `0` = IDLE, `1` = MOVING, `2` = EMERGENCY, `3` = HOMING, `4` = OPEN_LOOP_TEST |
| `0x0007` | `burst_status` | uint16 | Enumerated | `0` = IDLE, `1` = CAPTURING, `2` = READY, `3` = ABORTED |
| `0x0008` | `burst_sample_count` | uint16 | Count | Total recorded samples in RAM buffer (`0` to `825`). |
| `0x0009` – `0x000A` | `sample_time_ms` | uint32 | ms | Relative timestamp of sample at `burst_read_index`. |
| `0x000B` – `0x000C` | `sample_pos_mm` | Float32 (Big-Endian) | mm | Position of sample at `burst_read_index`. |
| `0x000D` – `0x000E` | `sample_vel_mm_s` | Float32 (Big-Endian) | mm/s | Velocity of sample at `burst_read_index`. |
| `0x000F` – `0x0010` | `sample_duty_pct` | Float32 (Big-Endian) | % | Applied PWM duty of sample at `burst_read_index`. |

---

## 4. Communication Data Flow Diagrams

### 4.1 Holding Register Write Transaction (Setpoint Update via TCP)

```
 [ SCADA / Host ]                [ Core 0: Modbus TCP Slave ]     [ Core 1: Control Loop ]
       │                                      │                               │
       │─── TCP Connect ──────────────────────▶│ (Port 502)                   │
       │─── Write Float32 Setpoint ───────────▶│                              │
       │    (FC 0x10, Reg 0x0000)             │                               │
       │                                      │─── Lock g_system_mutex ──────▶│
       │                                      │    Update position_setpoint   │
       │                                      │    Unlock g_system_mutex      │
       │                                      │                               │
       │                                      │                               │─── Lock g_system_mutex
       │                                      │                               │    Read position_setpoint
       │                                      │                               │    Compute PID Effort
       │◄── ACK Response (0x10) ─────────────│                               │    Drive Motor PWM
```

### 4.2 Discrete Input Read Transaction (Safety Polling via TCP)

```
 [ SCADA / Host ]                [ Core 0: Modbus TCP Slave ]     [ GPIO Pins ]
       │                                      │                          │
       │─── TCP Connect ──────────────────────▶│ (Port 502)               │
       │─── Read Discrete Inputs ─────────────▶│                          │
       │    (FC 0x02, Reg 0x0000, 3 bits)     │                          │
       │                                      │─── Sample Pin States ───▶│ (GPIO 12, 11, 13)
       │                                      │◄── Return Pin Levels ────│
       │                                      │                          │
       │◄── Return Bit Mask Response ─────────│                          │
```

---

## 5. Supervisory SCADA Python Client

The Python supervisory application (`tools/supervisory/`) was migrated from `pymodbus.ModbusSerialClient` to `pymodbus.ModbusTcpClient`.

### 5.1 Connection Configuration (UI)

| UI Control | Default | Description |
| :--- | :--- | :--- |
| **IP Addr** | `192.168.1.100` | Static IP address configured on ESP32-S3 W5500 |
| **Port** | `502` | Standard Modbus TCP port |
| **Slave ID** | `1` | Modbus slave unit ID |

### 5.2 Key Supervisory Capabilities
- **Telemetry & Visualization**: Digital display cards (Position, Velocity, Duty, Setpoint), Dark/Light mode toggle, configurable plot buffer (`max_points`), and Clear Graphs button.
- **Open-Loop Identification**: Configurable step PWM (`1.0%–100.0%`), mode selector (**Freio Ativo** vs **Parada Natural / Coast-to-Stop** with configurable cut position `50.0–536.0 mm`), automated $N$-curve sequential collection (with `CMD_HOME` between runs), and CSV export (raw or normalized).
- **Closed-Loop Sine Wave Trajectory**: Generates and streams sinusoidal setpoints at 20 Hz (`center`, `amplitude`, `frequency`, `cycles`) clamped to `[0.0, 670.0] mm`.

### 5.2 Auto-Reconnect Behaviour

The `ModbusWorker` thread implements non-blocking auto-reconnect:
- When a connection is lost, the `_handle_disconnect()` method records the failure and does **not** exit the polling loop.
- If `_user_wants_connected` is `True` and the socket is down, the thread retries `client.connect()` every **2 seconds** (`reconnect_interval_sec`).
- The UI CONNECT button remains responsive; clicking it again while retrying will clear the flag and halt reconnect attempts.

### 5.3 HIL Test Connection Parameters

The TCP-based HIL test scripts (`tests/test_modbus_kernel.py`, `tests/test_state_machine.py`) accept environment variable overrides:

```bash
# Run hardware-in-the-loop tests against a live ESP32 target
MODBUS_HOST=192.168.1.100 MODBUS_PORT=502 python3 -m pytest tests/ -v
```

| Variable | Default | Description |
| :--- | :--- | :--- |
| `MODBUS_HOST` | `192.168.1.100` | Target ESP32 IP address |
| `MODBUS_PORT` | `502` | Target Modbus TCP port |
| `MODBUS_TIMEOUT` | `0.5` | Socket response timeout (seconds) |
| `MODBUS_RETRIES` | `1` | Number of connection retries |
