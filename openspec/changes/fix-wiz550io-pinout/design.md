## Context

The ESP32-S3 WROOM-1 module has `GPIO 19` hardwired to the native USB PHY D- line. The current WIZ550io SPI2 configuration assigns `GPIO 19` as the MISO line, creating a hardware-level conflict with the USB-C console logging port. The ESP32-S3 GPIO Matrix cannot remap the USB PHY — it is physically fixed on GPIO 19/20. This means both peripherals cannot coexist: driving GPIO 19 as SPI MISO disables the USB-Serial-JTAG console.

The fix is a single GPIO reassignment: move MISO from `GPIO 19` to a conflict-free pin. The SPI2 peripheral supports full GPIO Matrix routing on the ESP32-S3, so any free GPIO works without performance penalty at 10 MHz.

## Goals / Non-Goals

**Goals:**
- Reassign `ETH_SPI_MISO_GPIO` from `GPIO 19` to `GPIO 8` in firmware.
- Correct the pinout table and compliance audit in `docs/02_hardware_and_schematics.md`.
- Update the `wiz550io-ethernet-driver` capability spec (delta) with the corrected pin list.

**Non-Goals:**
- Changing any other SPI2 pins (SCLK 18, MOSI 23, CS 21, RST 22, INT 17 are all conflict-free).
- Changing the SPI clock speed, mode, or any other Ethernet driver configuration.
- PCB re-spin — this is a breadboard/prototype wire move only.

## Decisions

### Decision: GPIO 8 for MISO
- **Choice**: Move MISO to `GPIO 8`.
- **Rationale**: GPIO 8 is general-purpose on all WROOM-1 variants (N4, N8), has no strapping function, no USB/JTAG role, and is not used by any other firmware peripheral. It is also physically adjacent to the lower GPIO bank on most WROOM breakout boards, minimizing rewiring effort.
- **Alternatives Considered**:
  - `GPIO 9` — equally valid, no conflict. GPIO 8 chosen arbitrarily.
  - `GPIO 10` — valid, but used as IOMUX for SPI flash on some non-WROOM modules; safe on WROOM-1 but GPIO 8 is cleaner.
  - Keeping GPIO 19 and disabling USB-Serial-JTAG — rejected; USB-C console logging is a core requirement restored by the `modbus-tcp-wiz550io` change.

## Risks / Trade-offs

- **[Physical Rewire Required]** → The breadboard wire for MISO must be moved from pin `GPIO 19` to pin `GPIO 8`. This is a mandatory hardware step before flashing the updated firmware; mismatched wiring will silently produce all-zero SPI reads.
  - *Mitigation*: Document clearly in tasks and in `docs/02_hardware_and_schematics.md`.
