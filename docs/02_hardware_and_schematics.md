# Chapter 2: Hardware Electronics & Electrical Wiring

## 1. System Pinout Specification

The ESP32-S3 microcontroller communicates with sensors, actuators, user interface displays, and Modbus serial lines through dedicated GPIO pins:

| Peripheral / Signal | ESP32-S3 GPIO | Signal Type | Electrical Characteristics |
| :--- | :--- | :--- | :--- |
| **Encoder Phase A** | `GPIO 15` | Digital Input | Quadrature A (Internal Pull-Up) |
| **Encoder Phase B** | `GPIO 16` | Digital Input | Quadrature B (Internal Pull-Up) |
| **Motor PWM Forward (IN1)** | `GPIO 17` | MCPWM Output | 20 kHz PWM (0 to 100% duty) |
| **Motor PWM Reverse (IN2)** | `GPIO 18` | MCPWM Output | 20 kHz PWM (0 to 100% duty) |
| **Emergency Stop Button** | `GPIO 12` | Interrupt Input | Active-LOW (Internal Pull-Up, Negedge ISR) |
| **Start Button** | `GPIO 11` | Digital Input | Active-LOW (Internal Pull-Up, Debounced) |
| **Driver Safety Cutoff** | `GPIO 13` | Digital Output | Active-HIGH (Hardware MOSFET Gate Enable) |
| **Status LED Indicator** | `GPIO 7` | Digital Output | Active-HIGH Output (System State LED) |
| **I2C Display SDA** | `GPIO 4` | Open-Drain | I2C Data Line (External 4.7kΩ Pull-Up) |
| **I2C Display SCL** | `GPIO 5` | Open-Drain | I2C Clock Line (External 4.7kΩ Pull-Up) |
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

The actuator motor is driven by a standard dual-channel H-Bridge driver controlled by the ESP32-S3 **MCPWM (Motor Control Pulse Width Modulator)** peripheral:
- **Frequency**: 20 kHz (above audible frequency range).
- **Forward Motion**: PWM applied on `GPIO 17` (`IN1`), `GPIO 18` (`IN2`) held `LOW`.
- **Reverse Motion**: PWM applied on `GPIO 18` (`IN2`), `GPIO 17` (`IN1`) held `LOW`.
- **Passive Braking / Zero Stop**: Both `GPIO 17` and `GPIO 18` driven `LOW` (shorting motor terminals for passive regenerative braking).

---

## 4. User Interface (IHM) & Serial Interfaces

### 4.1 HD44780 I2C LCD Display (20x4)
- Connected to `GPIO 4` (SDA) and `GPIO 5` (SCL) operating at 100 kHz I2C bus clock.
- Updated every 200 ms (5 Hz) by the Core 0 IHM Task.

### 4.2 RS485 Modbus RTU Bus
- Connected to `GPIO 43` (TX) and `GPIO 44` (RX) via an external MAX485 / SP3485 transceiver.
- Default settings: 115,200 Baud, 8 Data Bits, No Parity, 1 Stop Bit (8N1).
