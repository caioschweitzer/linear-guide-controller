## Why

The WIZ550io (W5500) SPI2 MISO signal was incorrectly assigned to `GPIO 19`, which is hardwired to the ESP32-S3's native USB D- line (USB OTG / USB-Serial-JTAG PHY). This creates a direct hardware conflict with the USB-C console logging port that the firmware relies on for `esp_log` output, and was incorrectly passed through the hardware compliance audit in `docs/02_hardware_and_schematics.md`.

## What Changes

- **BREAKING — GPIO 19 (MISO) reassigned to GPIO 8**: Move `ETH_SPI_MISO_GPIO` from `GPIO 19` (USB D-) to `GPIO 8` (free general-purpose I/O on ESP32-S3 WROOM-1).
- **Firmware**: Update `ETH_SPI_MISO_GPIO` define in `main/src/modbus_slave.c`.
- **Hardware Documentation**: Update the pinout table in `docs/02_hardware_and_schematics.md` to reflect `GPIO 8` for MISO, and correct the compliance audit section (section 5.3) which erroneously claimed zero USB/SPI collisions.
- **WIZ550io `wiz550io-ethernet-driver` spec**: Update the SPI pin list to reflect the corrected MISO assignment.

## Capabilities

### New Capabilities
- (none)

### Modified Capabilities
- `wiz550io-ethernet-driver`: SPI MISO pin changes from `GPIO 19` to `GPIO 8` — the hardware pin requirement in the spec must be updated to reflect the corrected assignment.

## Impact

- **Firmware**: `main/src/modbus_slave.c` — single `#define` change.
- **Hardware wiring**: Physical wire for SPI MISO must be moved from ESP32-S3 pin `GPIO 19` to `GPIO 8` on the breadboard/PCB.
- **Documentation**: `docs/02_hardware_and_schematics.md` — pinout table row and compliance audit section 5.3.
- **USB-C console**: Conflict resolved; `GPIO 19/20` remain exclusively owned by the native USB PHY.
