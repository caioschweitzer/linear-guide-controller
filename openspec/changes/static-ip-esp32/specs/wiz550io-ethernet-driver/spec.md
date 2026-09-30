## MODIFIED Requirements

### Requirement: SPI Master W5500 Driver Initialization
The system SHALL initialize the ESP32 SPI Master driver on SPI2 (VSPI) and attach the WIZ550io (W5500) PHY and MAC driver to `esp_netif` using MOSI (GPIO 23), MISO (GPIO 19), SCLK (GPIO 18), CS (GPIO 21), RST (GPIO 22), and INT (GPIO 17). The system SHALL stop the DHCP client and configure a fixed static IP address (`192.168.1.100`), netmask (`255.255.255.0`), and gateway (`192.168.1.1`).

#### Scenario: Ethernet Driver Startup
- **WHEN** the ESP32 boots and network initialization is executed
- **THEN** the system MUST initialize the SPI bus at 10MHz, instantiate `esp_eth_mac_new_w5500` and `esp_eth_phy_new_w5500`, install the ethernet driver, attach it to `esp_netif`, stop DHCP client (`esp_netif_dhcpc_stop`), and assign static IP `192.168.1.100`.

#### Scenario: IP Address Assignment
- **WHEN** the ethernet link goes UP
- **THEN** the `esp_netif` network interface MUST immediately apply the static IP configuration (`192.168.1.100`), raise `IP_EVENT_ETH_GOT_IP`, and log the static IP address to the console.
