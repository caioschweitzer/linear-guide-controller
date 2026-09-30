## ADDED Requirements

### Requirement: SPI Master W5500 Driver Initialization
The system SHALL initialize the ESP32 SPI Master driver on SPI2 (VSPI) and attach the WIZ550io (W5500) PHY and MAC driver to `esp_netif` using MOSI (GPIO 23), MISO (GPIO 19), SCLK (GPIO 18), CS (GPIO 21), RST (GPIO 22), and INT (GPIO 17).

#### Scenario: Ethernet Driver Startup
- **WHEN** the ESP32 boots and `modbus_slave_init()` is invoked
- **THEN** the system MUST initialize the SPI bus at 10MHz, instantiate `esp_eth_mac_new_w5500` and `esp_eth_phy_new_w5500`, install the ethernet driver, and attach it to the `esp_netif` TCP/IP stack.

#### Scenario: IP Address Acquisition
- **WHEN** the ethernet link goes UP
- **THEN** the `esp_netif` network interface MUST start the DHCP client or assign a configured static IP address and log the active IP address to console.
