## Why

A guia linear necessita de uma Interface Homem-Máquina (IHM) local visual para permitir monitoramento direto de telemetria (posição, velocidade e estado do sistema) em campo e sinalização de status/alarme por LED. O módulo deve ser implementado em C puro com abstração para o driver I2C Master do ESP-IDF v5.x, garantindo formato estrito de 16 caracteres no LCD HD44780 16x2 (PCF8574), sinalização não-bloqueante no LED (GPIO 7), leitura de snapshot por Mutex no Core 0 sem impactar a malha de controle do Core 1, e resiliência contra desconexão física do I2C.

## What Changes

- **Novo Módulo C (`main/ihm_display.h`, `main/ihm_display.c`)**:
  - Struct `ihm_config_t` (sda_gpio=1, scl_gpio=2, led_gpio=7, i2c_address=0x27, i2c_clk_speed=100kHz) e `ihm_display_t` (handles I2C, estado do LED, timestamp de pisca, flag `is_connected`).
  - Driver LCD 16x2 HD44780 via expansor PCF8574 em modo 4-bits.
  - Função de formatação estrita `ihm_format_lines()` produzindo exatamente 16 caracteres por linha via `snprintf`.
  - Controle de LED não-bloqueante por variação de tempo em milissegundos (`1 Hz` para MOVING/HOMING/AUTO, `5 Hz` para EMERGENCY/FAULT, aceso/apagado para IDLE/INIT).
  - Padrão snapshot para concorrência com o Mutex do `shared_data`.
  - Tratamento de erro I2C (desconexão/NACK) sem travar a execução.
  - Suporte a Host Emulation (`#ifdef HOST_TEST`).
- **Registro no CMake (`main/CMakeLists.txt`)**:
  - Adição de `ihm_display.c` na lista de fontes do componente `main`.
- **Suíte de Testes Unitários (`tests/test_ihm_display.py`)**:
  - Testes em Python via `ctypes` validando formatação de strings do LCD (garantia de 16 caracteres) e temporização do LED (1 Hz vs 5 Hz).

## Capabilities

### New Capabilities
- `ihm-display`: Interface Homem-Máquina local com LCD 16x2 I2C (PCF8574) e sinalização LED de status (GPIO 7).

### Modified Capabilities
<!-- Nenhuma capacidade existente alterada -->

## Impact

- **Código Afetado**: `main/ihm_display.h`, `main/ihm_display.c`, `main/CMakeLists.txt`, `tests/test_ihm_display.py`.
- **Hardware**: GPIO 1 (SDA), GPIO 2 (SCL), GPIO 7 (LED).
- **APIs**: ESP-IDF v5.x `driver/i2c_master.h` no target e C ANSI puro para Host.
- **Dependências**: Nenhuma biblioteca externa nova. Testes via `pytest` e `ctypes`.
