## Why

Estabelecer a fundação do firmware do controlador de guia linear para ESP32-S3 (ESP-IDF v5.x), criando a infraestrutura de tarefas do FreeRTOS distribuídas entre o Core 0 (I/O e Modbus) e Core 1 (Controle), com comunicação Modbus RTU Slave pela porta USB-C da placa e estrutura IPC thread-safe protegida por Mutex.

## What Changes

- **Arquitetura FreeRTOS & IPC:** Criação de estrutura de dados compartilhada (`SystemData`) com Setpoint de Posição, Posição Atual, Velocidade Atual e Estado da Máquina, protegida por Mutex FreeRTOS (`SemaphoreHandle_t`).
- **Task Modbus RTU Slave (Core 0):** Configuração do stack `esp_modbus` na `UART_NUM_0` (115200 baud, 8N1, Slave ID 1) conectada à porta USB-C. Mapeamento de Holding Registers (`0x0000` float32) e Input Registers (`0x0000` float32 Posição, `0x0002` float32 Velocidade, `0x0004` uint16 Estado).
- **Gerenciamento de Logs:** Desativação dos logs legíveis do ESP-IDF na UART0 para evitar corrupção dos quadros binários Modbus RTU.
- **Task Placeholder (Core 1):** Esqueleto do loop de controle de 100Hz rodando periodicamente a cada 10ms via `vTaskDelay`.
- **Testes HIL (Python):** Testes de integração serial automatizados com `pytest` e `pymodbus` em `tests/test_modbus_kernel.py`.

## Capabilities

### New Capabilities
- `kernel-freertos-modbus`: Implementação da base do firmware em C++ no ESP32-S3 com tarefas FreeRTOS nos dois cores, comunicação Modbus RTU via USB-C e sincronização IPC por Mutex.

### Modified Capabilities

## Impact

- **Código Firmware:** Arquivos a serem criados/atualizados em `main/`: `main.cpp`, `shared_data.h`, `modbus_slave.h`, `modbus_slave.cpp`, `CMakeLists.txt`.
- **Testes:** Criação do script de teste em `tests/test_modbus_kernel.py`.
- **Componentes ESP-IDF:** `freertos`, `esp_modbus`, `driver`, `nvs_flash`.
- **Ambiente de Teste:** Exige cabo USB-C conectado ao PC e ambiente Python com `pytest` e `pymodbus`.
