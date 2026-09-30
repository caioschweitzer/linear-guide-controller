## 1. Firmware Network Initialization Update

- [x] 1.1 Add static IP configuration constants (`STATIC_IP`, `STATIC_NETMASK`, `STATIC_GW`) to network configuration header.
- [x] 1.2 Stop DHCP client on Ethernet `esp_netif` instance using `esp_netif_dhcpc_stop()`.
- [x] 1.3 Apply static IP configuration using `esp_netif_set_ip_info()`.
- [x] 1.4 Update Ethernet event handler to verify static IP assignment upon PHY link-up.

## 2. Supervisory & Integration Test Configuration

- [x] 2.1 Update default connection host IP in `tools/supervisory/main.py` UI to `192.168.1.100`.
- [x] 2.2 Update default target IP address in `tests/test_modbus_kernel.py` socket test fixtures.

## 3. Verification

- [x] 3.1 Validate ESP-IDF build with `idf.py build`.
- [ ] 3.2 Execute supervisory client and verify connection to static IP `192.168.1.100:502`.
