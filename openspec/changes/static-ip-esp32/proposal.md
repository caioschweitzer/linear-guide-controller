## Why

When the ESP32 powers on or resets, waiting for a DHCP server to assign an IP address introduces non-deterministic delays (often several seconds) and introduces a point of failure if no DHCP server is active on the local network. In industrial control and supervisory environments, Modbus TCP servers (slaves) require fixed, predictable IP addresses so SCADA applications and automated test suites can establish socket connections immediately upon boot.

## What Changes

- **Static IP Configuration**: Disable DHCP client on the `esp_netif` Ethernet interface (`esp_netif_dhcpc_stop`) during network initialization.
- **Fixed Network Parameters**: Assign static IP address (`192.168.1.100`), Netmask (`255.255.255.0`), and Gateway (`192.168.1.1`) to the ESP32 Ethernet interface.
- **Kconfig / Header Options**: Expose IP address, Netmask, and Gateway as macros/configuration options in firmware network headers (`ethernet_config.h` or `sdkconfig`).
- **Supervisory Application**: Update supervisory default connection IP to match the static IP address (`192.168.1.100`).

## Capabilities

### Modified Capabilities

- `wiz550io-ethernet-driver`: Update W5500 `esp_netif` initialization to disable DHCP client and set static IP configuration parameters upon link startup.

## Impact

- **ESP32 Firmware**: Ethernet network initialization module (`main/src/ethernet.c` / `main/src/main.c` / `main/include/ethernet_config.h`).
- **Network Link**: Instant network stack readiness without DHCP handshake delays.
- **Supervisory / Testing**: `tools/supervisory/main.py` and test suites default to `192.168.1.100`.
