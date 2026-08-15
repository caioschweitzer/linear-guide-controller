# Chapter 2: Hardware Electronics & Electrical Wiring

## 1. System Pinout Specification

The ESP32-S3 microcontroller communicates with sensors, actuators, user interface displays, and Modbus serial lines through dedicated GPIO pins:

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
| **Modbus RS485 TX** | `GPIO 43` | UART Output | UART0 TX (115200 Baud) |
| **Modbus RS485 RX** | `GPIO 44` | UART Input | UART0 RX (115200 Baud) |

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

---

## 3. Motor Driver & PWM Interface

The actuator motor is driven by a standard dual-channel H-Bridge driver (e.g. L298N) controlled by the ESP32-S3 **MCPWM (Motor Control Pulse Width Modulator)** peripheral:
- **Frequency**: 20 kHz (above audible frequency range) on `GPIO 4` (Enable).
- **Forward Motion**: PWM applied on `GPIO 4`, `GPIO 5` (`IN1`) set `HIGH`, `GPIO 6` (`IN2`) set `LOW`.
- **Reverse Motion**: PWM applied on `GPIO 4`, `GPIO 5` (`IN1`) set `LOW`, `GPIO 6` (`IN2`) set `HIGH`.
- **Passive Braking / Zero Stop**: Both `GPIO 5` (`IN1`) and `GPIO 6` (`IN2`) set `LOW`, PWM duty 0%.

---

## 4. User Interface (IHM) & Serial Interfaces

### 4.1 HD44780 I2C LCD Display (16x2)
- Connected to `GPIO 1` (SDA) and `GPIO 2` (SCL) operating at 100 kHz I2C bus clock.
- Updated every 200 ms (5 Hz) by the Core 0 IHM Task.

### 4.2 RS485 Modbus RTU Bus
- Connected to `GPIO 43` (TX) and `GPIO 44` (RX) via an external MAX485 / SP3485 transceiver (UART0 default pins).
- Default settings: 115,200 Baud, 8 Data Bits, No Parity, 1 Stop Bit (8N1).

---

## 5. ESP32-S3 Datasheet Pin Routing & Compliance Audit

A comprehensive hardware pin routing audit was performed against the Espressif ESP32-S3 Datasheet (`docs/esp32-s3_datasheet_en.pdf`). The system's pin routing complies with all hardware silicon constraints:

1. **Strapping Pin Isolation**:
   - ESP32-S3 hardware strapping pins (`GPIO 0`, `GPIO 3`, `GPIO 45`, `GPIO 46`) control chip boot modes and `VDD_SPI` power rail voltage.
   - **Verification**: None of the active system signals use these strapping pins, preventing boot mode corruption during startup.

2. **SPI Flash & PSRAM Protection**:
   - Octal SPI / Quad SPI Flash and PSRAM utilize `GPIO 26` through `GPIO 37`.
   - **Verification**: All active system pins (`GPIO 1, 2, 4, 5, 6, 7, 11, 12, 13, 14, 15, 43, 44`) are fully isolated from the internal SPI memory bus.

3. **Native USB & JTAG Pin Preservation**:
   - Native USB OTG (`GPIO 19` D-, `GPIO 20` D+) and JTAG debugging pins (`GPIO 39-42`) are reserved for hardware debugging.
   - **Verification**: Zero signal collisions with native USB and JTAG debug hardware.

4. **Hardware UART0 COM Port Mapping**:
   - `GPIO 43` (TXD0) and `GPIO 44` (RXD0) are the native UART0 pins, directly connected to the onboard USB-to-Serial converter (CP210x / CH340), exposing the Modbus RTU interface transparently over USB-C.
