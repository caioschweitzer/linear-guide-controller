## Context

The linear guide actuator controller utilizes an ESP32-S3 microcontroller operating at 240 MHz with FreeRTOS dual-core execution. To ensure hardware safety, signal integrity, and long-term reliability, a thorough pin routing verification was conducted against the official Espressif ESP32-S3 Datasheet (`docs/esp32-s3_datasheet_en.pdf`).

## Goals / Non-Goals

**Goals:**
- Perform a complete electrical and peripheral routing verification of all 13 active system GPIO pins (`GPIO 1, 2, 4, 5, 6, 7, 11, 12, 13, 14, 15, 43, 44`).
- Verify zero interference with ESP32-S3 hardware strapping pins (`GPIO 0, 3, 45, 46`), Octal Flash/PSRAM bus lines (`GPIO 26-37`), native USB OTG (`GPIO 19, 20`), and JTAG (`GPIO 39-42`).
- Ensure all peripheral multiplexing (MCPWM, PCNT, I2C, UART0, IRAM ISR) matches official silicon specifications.

**Non-Goals:**
- Physical PCB fabrication or board revision layout changes.

## Decisions

### Decision 1: Hardware UART0 Default Mapping for Modbus RS485 / USB-COM
- **Choice**: Utilize ESP32-S3 hardware default `UART_NUM_0` pins (`GPIO 43` TX, `GPIO 44` RX).
- **Rationale**: On standard ESP32-S3 boards (DevKitC-1), UART0 is wired directly to the onboard USB-to-Serial converter bridge (CP210x / CH340), exposing the Modbus RTU interface directly over USB-C as a virtual COM port (`/dev/ttyUSB0` or `COMx`).

### Decision 2: MCPWM and I2C Pin Separation
- **Choice**: Route I2C LCD Display (HD44780 via PCF8574) to `GPIO 1` (SDA) and `GPIO 2` (SCL), and MCPWM Motor Driver to `GPIO 4` (PWM Enable), `GPIO 5` (IN1), `GPIO 6` (IN2).
- **Rationale**: Prevents peripheral signal overlap and avoids using GPIO 4 and 5 for I2C, which would clash with the high-frequency 20 kHz MCPWM motor output signals.

### Decision 3: PCNT Encoder Pin Assignment with Internal Pull-Ups
- **Choice**: Route Quadrature X4 Encoder signals to `GPIO 14` (Phase A) and `GPIO 15` (Phase B) with internal pull-up enabled (`gpio_pullup_en`).
- **Rationale**: Eliminates floating input states during high-speed quadrature counting while avoiding collision with SPI Flash lines.

### Decision 4: IRAM-Resident Emergency Cutoff Hardware Interlock
- **Choice**: Configure `GPIO 12` (E-Stop Button) as a falling-edge IRAM interrupt controlling `GPIO 13` (Hardware MOSFET Enable Cutoff).
- **Rationale**: Guarantees sub-microsecond physical power cutoff to the motor driver independent of FreeRTOS task scheduling or software lockups.

## Risks / Trade-offs

- **[Risk] Pin assignment overlap with Octal Flash/PSRAM** → **Mitigation**: Verified against Datasheet Section 2 (Pin Description Table) that all active GPIOs (1, 2, 4, 5, 6, 7, 11, 12, 13, 14, 15, 43, 44) are completely isolated from the SPI Flash/PSRAM bus (`GPIO 26-37`).
- **[Risk] Strapping pin corruption during power-up** → **Mitigation**: Confirmed no system peripherals are connected to strapping pins (`GPIO 0, 3, 45, 46`), preventing boot mode failures or VDD_SPI voltage selection errors.
