## 1. Hardware (Do This Before Flashing)

- [x] 1.1 Reassign SPI wires for ESP32-S3 WROOM-1 compatibility: MOSI -> GPIO 8, MISO -> GPIO 10, RST -> GPIO 9.

## 2. Firmware Update

- [x] 2.1 Update SPI pin definitions (`MOSI=8`, `MISO=10`, `RST=9`) and add 500ms WIZ550io startup delay in `main/src/modbus_slave.c`.
- [x] 2.2 Validate ESP-IDF build with `idf.py build`.

## 3. Documentation Update

- [x] 3.1 Update the pinout table in `docs/02_hardware_and_schematics.md`: MOSI -> GPIO 8, MISO -> GPIO 10, RST -> GPIO 9.
- [x] 3.2 Correct section 4.2 in `docs/02_hardware_and_schematics.md`: update GPIO range for WIZ550io.
- [x] 3.3 Correct the compliance audit (section 5, item 3) in `docs/02_hardware_and_schematics.md`: document native USB D- (GPIO 19) / D+ (GPIO 20) reservation and new SPI pinout.

## 4. Verification

- [x] 4.1 Flash firmware to ESP32-S3 and verify USB-C console (`esp_log`) output is active.
- [x] 4.2 Verify WIZ550io Ethernet link comes up and ESP32 announces static IP `192.168.1.100` on console.
- [x] 4.3 Connect supervisory client to `192.168.1.100:502` and confirm Modbus TCP registers respond correctly.
