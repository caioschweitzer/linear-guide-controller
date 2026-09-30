## Context

The ESP32 firmware uses ESP-IDF `esp_netif` with WIZ550io (W5500 SPI Ethernet module). By default, `esp_netif_defaults` enables the lwIP DHCP client. In point-to-point setups (direct connection between ESP32 and PC/SCADA host) or closed industrial networks lacking a DHCP server, the ESP32 fails to acquire an IP address or experiences high startup latency while waiting for DHCP discovery to time out.

By configuring a fixed static IP address during `esp_netif` setup, the network link becomes operational immediately upon physical PHY link-up.

## Goals / Non-Goals

**Goals:**
- Stop the DHCP client on the Ethernet `esp_netif` instance during startup (`esp_netif_dhcpc_stop`).
- Configure fixed static IPv4 settings: IP `192.168.1.100`, Netmask `255.255.255.0`, Gateway `192.168.1.1`.
- Log the static IP configuration to console upon `IP_EVENT_ETH_GOT_IP` / link state handlers.
- Synchronize default IP configuration in Supervisory UI (`tools/supervisory/main.py`) and automated test scripts (`tests/test_modbus_kernel.py`).

**Non-Goals:**
- Dynamic IP address configuration via runtime Modbus registers or EEPROM/NVS.
- Multi-interface routing or IPv6 support.

## Decisions

### Decision 1: Disable DHCP client and apply `esp_netif_set_ip_info`
- **Choice**: Call `esp_netif_dhcpc_stop(eth_netif)` followed by `esp_netif_set_ip_info(eth_netif, &ip_info)` immediately after creating the network interface.
- **Rationale**: This guarantees lwIP does not broadcast DHCP DISCOVER packets and immediately binds `192.168.1.100` to the MAC interface.
- **Alternatives Considered**: Waiting for DHCP timeout before fallback to static IP (rejected because DHCP timeout causes unwanted delay of 10-30 seconds on boot).

### Decision 2: Network Subnet Selection (`192.168.1.100/24`)
- **Choice**: Use default IP `192.168.1.100`, Netmask `255.255.255.0`, Gateway `192.168.1.1`.
- **Rationale**: standard subnet for lab and industrial Ethernet test benches.
- **Alternatives Considered**: `169.254.x.x` APIPA link-local (rejected as IP changes between boots and causes host socket connection issues).

## Risks / Trade-offs

- **[Subnet Mismatch]** → Host PC Ethernet adapter must be configured on `192.168.1.x` subnet (e.g. `192.168.1.50`).
  - *Mitigation*: Update project documentation and supervisory tool connection presets.
