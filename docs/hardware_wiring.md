# Hardware Pinout & Electrical Wiring Specification

This document defines the physical interface connections, pin assignments, and electrical power specifications for the ESP32-S3 Linear Actuator Controller system.

---

## 1. ESP32-S3 Microcontroller Pinout Table

| Pin Function | GPIO | Peripheral Module | Signal Direction | Hardware Characteristics |
| :--- | :---: | :--- | :---: | :--- |
| **Motor PWM Signal** | `GPIO 4` | MCPWM Operator A | Output | 20 kHz PWM, Push-Pull, 3.3V Logic |
| **Motor Direction IN1** | `GPIO 5` | GPIO Output | Output | H-Bridge Direction Control A |
| **Motor Direction IN2** | `GPIO 6` | GPIO Output | Output | H-Bridge Direction Control B |
| **Status LED** | `GPIO 7` | GPIO Output | Output | Low-side NPN driver / Direct LED |
| **Display I2C SDA** | `GPIO 8` | I2C Master (0) | Open-Drain | 100 kHz, 4.7 kΩ External Pull-up to 3.3V |
| **Display I2C SCL** | `GPIO 9` | I2C Master (0) | Open-Drain | 100 kHz, 4.7 kΩ External Pull-up to 3.3V |
| **Start Push Button** | `GPIO 11` | GPIO Input | Input | Active-LOW, Internal/External Pull-up (50ms debounce) |
| **Emergency Stop (E-Stop)**| `GPIO 12` | GPIO Interrupt | Input | Active-LOW, Falling Edge ISR, Priority 1 interrupt |
| **Motor Driver Safety Enable** | `GPIO 13` | GPIO Output | Output | Hardware Safety Cutoff Pin (Forced LOW by ISR) |
| **Encoder Phase A** | `GPIO 14` | PCNT Unit 0, Chan A| Input | Quadrature Phase A, Internal Pull-up (1000 ns glitch filter) |
| **Encoder Phase B** | `GPIO 15` | PCNT Unit 0, Chan B| Input | Quadrature Phase B, Internal Pull-up (1000 ns glitch filter) |
| **Modbus RTU TX** | `GPIO 43` | UART0 | Output | 115200 baud, 8N1, RS485 Transceiver TXD |
| **Modbus RTU RX** | `GPIO 44` | UART0 | Input | 115200 baud, 8N1, RS485 Transceiver RXD |

---

## 2. Power Supply & Electrical Interfaces

- **Logic Supply Voltage**: 5.0 VDC (via USB-C or external VIN pin) stepping down to 3.3 VDC via onboard LDO regulator.
- **Motor Power Supply (VMOT)**: 12.0 VDC to 24.0 VDC external supply rated for peak actuator current (e.g. 5A–10A).
- **Ground Commoning**: All GND pins (ESP32-S3, H-bridge motor driver, rotary encoder, RS485 transceiver, and LCD display) MUST share a common star ground point to prevent ground loop noise.

---

## 3. Emergency Stop (E-Stop) Hardware Cutoff Circuit

```
                      +3.3V
                        |
                       [R] 10k Pull-up
                        |
 [NC Emergency Button]--+------> GPIO 12 (ESP32-S3 E-Stop ISR Pin)
   (Connected to GND)

                  GPIO 13 ------> H-Bridge Enable Pin (Active-HIGH)
                                  (Forced to 0V immediately upon ISR trigger)
```

### Safety Intercept Behavior:
1. **Normal Operation**: GPIO 12 is pulled HIGH by internal/external resistor. GPIO 13 outputs 3.3V (Logic 1) to enable the H-bridge motor driver.
2. **E-Stop Activation**: Pressing the Emergency button breaks contact, pulling GPIO 12 to 0V (Falling Edge).
3. **Hardware Level Cutoff**: The hardware ISR fires directly out of IRAM, immediately forcing GPIO 13 LOW (0V) to physically disconnect power to the motor driver gates within microseconds.
4. **State Machine Transition**: The ISR atomically sets `MACHINE_STATE_EMERGENCY` in software and interrupts the Core 1 PID task to zero the PWM duty cycle output.
