# Chapter 2: Hardware Electronics & Electrical Wiring

## 1. System Pinout Specification

The ESP32-S3 microcontroller communicates with sensors, actuators, user interface displays, and the Ethernet WIZ550io module through dedicated GPIO pins:

| Peripheral / Signal | ESP32-S3 GPIO | Signal Type | Electrical Characteristics |
| :--- | :--- | :--- | :--- |
| **I2C Display SDA** | `GPIO 1` | Open-Drain | I2C Data Line (External 4.7kΩ Pull-Up) |
| **I2C Display SCL** | `GPIO 2` | Open-Drain | I2C Clock Line (External 4.7kΩ Pull-Up) |
| **Motor PWM Enable** | `GPIO 4` | MCPWM Output | 20 kHz PWM (0 to 100% duty) |
| **Motor Direction IN1** | `GPIO 5` | Digital Output | Direction Control Signal 1 |
| **Motor Direction IN2** | `GPIO 6` | Digital Output | Direction Control Signal 2 |
| **Status LED Indicator** | `GPIO 7` | Digital Output | Active-HIGH Output (System State LED) |
| **Start Button** | `GPIO 11` | Digital Input | Active-LOW (Internal Pull-Up, Debounced) |
| **Emergency Stop Button** | `GPIO 12` | Interrupt Input | Active-LOW (Internal Pull-Up, Negedge ISR) |
| **Driver Safety Cutoff** | `GPIO 13` | Digital Output | Active-HIGH (Hardware MOSFET Gate Enable) |
| **Encoder Phase A** | `GPIO 14` | Digital Input | Quadrature A (Internal Pull-Up) |
| **Encoder Phase B** | `GPIO 15` | Digital Input | Quadrature B (Internal Pull-Up) |
| **Home Sensor** | `GPIO 16` | Digital Input | Active-LOW / 0V (NC Magnetic Sensor, +3.3V supply, Internal Pull-Down) |
| **W5500 INT** | `GPIO 17` | Input | WIZ550io Interrupt (Active-Low, Ethernet Events) |
| **W5500 SPI SCLK** | `GPIO 18` | SPI2 Clock | SPI2 Clock to WIZ550io (10 MHz) |
| **W5500 SPI MISO** | `GPIO 10` | SPI2 Input | SPI2 Master In / Slave Out |
| **W5500 SPI CS** | `GPIO 21` | SPI2 Output | SPI2 Chip Select (Active-Low) |
| **W5500 RST** | `GPIO 9` | Digital Output | WIZ550io Hardware Reset (Active-Low) |
| **W5500 SPI MOSI** | `GPIO 8` | SPI2 Output | SPI2 Master Out / Slave In |
| **Console TX (USB-C)** | `GPIO 43` | UART Output | UART0 TX — ESP-IDF console logging (re-enabled) |
| **Console RX (USB-C)** | `GPIO 44` | UART Input | UART0 RX — UART0 receive (USB-C programmer port) |

---

## 2. Emergency Cutoff Hardware Circuitry

To achieve true physical safety independent of FreeRTOS task scheduling or software lockups, `GPIO 13` acts as a direct hardware gate to the H-Bridge motor driver enable pin:

```
                  +3.3V / +5V Power Rail
                           │
                    ┌──────┴──────┐
                    │ Push-Button │  (Normally Closed / Active-Low)
                    │  (E-Stop)   │
                    └──────┬──────┘
                           │
   ESP32-S3 GPIO 12 ◄──────┴───────┐
   (Negedge ISR)                   │
                             ┌─────┴─────┐
                             │ 10kΩ Pull │
                             └─────┬─────┘
                                  GND

   ESP32-S3 GPIO 13 ───────────────┐
   (Hardware Enable Output)        │
                                   ▼
                             ┌───────────┐
                             │  N-MOSFET │ ───► Power to H-Bridge Driver
                             └───────────┘
```

### Safety Interlock Behavior:
1. Under normal operation (`IDLE` / `MOVING`), `GPIO 13` is set to `HIGH` (+3.3V), keeping the H-bridge driver enabled.
2. When the Emergency Stop button is pressed (`GPIO 12` pulled `LOW`), the IRAM-resident interrupt (`gpio12_emergency_isr`) immediately executes in $< 1\ \mu\text{s}$, driving `GPIO 13` `LOW` (0V).
3. The N-MOSFET turns off instantly, cutting power to the H-Bridge motor driver regardless of PWM signals.

### 2.1 Magnetic Home Sensor Circuitry

The mechanical datum (Home) is detected by a magnetic sensor with a contact that is Normally Closed (NC) in the absence of a magnetic field, connected between +3.3V and `GPIO 16`:

```text
       +3.3V Power Rail
             │
             ▼
        ┌─────────┐
        │ SENSOR  │ (NC Magnetic Sensor / Closed in free air)
        └────┬────┘
             │
             ├──────────────────────────► ESP32-S3 GPIO 16 (Digital Input)
             │
        ┌────┴────┐
        │  45kΩ   │ (Internal Pull-Down Resistor in ESP32-S3)
        │ PULL-   │
        │  DOWN   │
        └────┬────┘
             ▼
            GND
```

#### Sensor Operational Logic:
1. **Carriage Away from Home (Free Air / Repouso)**: The magnetic contact is closed, applying +3.3V directly to `GPIO 16` (`gpio == 1`). The firmware interprets this as `CLEAR` / un-triggered.
2. **Carriage at Home Datum (Magnet Present)**: The magnetic field opens the NC contact, disconnecting the 3.3V rail. The internal pull-down resistor pulls `GPIO 16` to 0V (`gpio == 0`). The firmware interprets this as `HOME DETECTED`, engages active braking (`motor_brake`), clears the encoder count to zero, and returns to `IDLE`.
3. **Fail-Safe Disconnection**: If the sensor wire is broken or disconnected, `GPIO 16` pulls to 0V via pull-down, immediately preventing the carriage from crashing in search of a missing datum.

---

## 3. Motor Driver & PWM Interface

The actuator motor is driven by a standard dual-channel H-Bridge driver (e.g. L298N) controlled by the ESP32-S3 **MCPWM (Motor Control Pulse Width Modulator)** peripheral:
- **Frequency**: 20 kHz (above audible frequency range) on `GPIO 4` (Enable).
- **Forward Motion**: PWM applied on `GPIO 4`, `GPIO 5` (`IN1`) set `HIGH`, `GPIO 6` (`IN2`) set `LOW`.
- **Reverse Motion**: PWM applied on `GPIO 4`, `GPIO 5` (`IN1`) set `LOW`, `GPIO 6` (`IN2`) set `HIGH`.
- **Passive Braking / Zero Stop**: Both `GPIO 5` (`IN1`) and `GPIO 6` (`IN2`) set `LOW`, PWM duty 0%.

---

## 4. User Interface (IHM) & Network Interfaces

### 4.1 HD44780 I2C LCD Display (16x2)
- Connected to `GPIO 1` (SDA) and `GPIO 2` (SCL) operating at 50 kHz I2C bus clock.
- Updated periodically with string change caching by the Core 0 IHM Task.

### 4.2 WIZ550io (W5500) 100Base-T Ethernet — Modbus TCP
- The WIZ550io module connects via SPI2 (5 MHz, Mode 0) using GPIOs 8 (MOSI), 9 (RST), 10 (MISO), 17 (INT), 18 (SCLK), 21 (CS).
- Initialised by `mbc_slave_create_tcp()` on TCP port **502**.
- A **static IP address** (`192.168.1.100`, Netmask `255.255.255.0`, Gateway `192.168.1.1`) is configured at boot via `esp_netif_dhcpc_stop()` + `esp_netif_set_ip_info()`. DHCP is disabled.
- The ESP-IDF console is re-enabled on `UART0` (`GPIO 43/44` / USB-C) since it no longer conflicts with Modbus bus traffic.

### 4.3 Console Logging (USB-C)
- `UART_NUM_0` (`GPIO 43` TX, `GPIO 44` RX) is used exclusively for **ESP-IDF console logging** at `ESP_LOG_INFO`.
- No RS485 transceiver is required; the USB-C port connects directly to the host via the onboard USB-to-UART bridge.

---

## 5. ESP32-S3 Datasheet Pin Routing & Compliance Audit

A comprehensive hardware pin routing audit was performed against the Espressif ESP32-S3 Datasheet (`docs/esp32-s3_datasheet_en.pdf`). The system's pin routing complies with all hardware silicon constraints:

1. **Strapping Pin Isolation**:
   - ESP32-S3 hardware strapping pins (`GPIO 0`, `GPIO 3`, `GPIO 45`, `GPIO 46`) control chip boot modes and `VDD_SPI` power rail voltage.
   - **Verification**: None of the active system signals use these strapping pins, preventing boot mode corruption during startup.

2. **SPI Flash & PSRAM Protection**:
   - Octal SPI / Quad SPI Flash and PSRAM utilize `GPIO 26` through `GPIO 37`.
   - **Verification**: All active system pins (`GPIO 1, 2, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 17, 18, 21, 43, 44`) are fully isolated from the internal SPI memory bus.

3. **Native USB & JTAG Pin Preservation**:
   - Native USB OTG (`GPIO 19` D-, `GPIO 20` D+) and JTAG debugging pins (`GPIO 39–42`) are reserved exclusively by hardware and must not be used for any other peripheral.
   - **Verification**: `GPIO 19` (USB D-) and `GPIO 20` (USB D+) are unassigned in firmware. SPI2 MOSI is routed to `GPIO 8` and MISO to `GPIO 10`. Zero signal collisions with native USB and JTAG debug hardware.

4. **Hardware UART0 COM Port Mapping**:
   - `GPIO 43` (TXD0) and `GPIO 44` (RXD0) are mapped to `UART_NUM_0`, connected to the onboard USB-to-Serial converter (CP210x / CH340).
   - **Previously**: UART0 was used for Modbus RTU, requiring log suppression (`ESP_LOG_NONE`).
   - **Current**: UART0 is used solely for ESP-IDF console logging (`ESP_LOG_INFO`). Modbus communication is now handled exclusively over Ethernet (TCP port 502).
