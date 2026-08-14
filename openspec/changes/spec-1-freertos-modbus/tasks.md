## 1. Estrutura IPC e Mutex FreeRTOS

- [x] 1.1 Criar cabeçalho `main/shared_data.h` com a struct `SystemData` e utilitários de trava/destrava de Mutex (`SemaphoreHandle_t`).
- [x] 1.2 Implementar a inicialização da struct `SystemData` com valores padrão (`0.0f` para setpoint, posição e velocidade, e `0` para estado da máquina).

## 2. Comunicação Modbus RTU Slave (Core 0)

- [x] 2.1 Criar `main/modbus_slave.h` e `main/modbus_slave.c` para abstração e inicialização do stack `esp_modbus` em `UART_NUM_0` (115200 8N1, Slave ID 1).
- [x] 2.2 Configurar o mapa de memória Modbus (`Holding Registers` float32 no offset `0x0000` e `Input Registers` no offset `0x0000`).
- [x] 2.3 Implementar a Task do Modbus no Core 0 sincronizando a struct IPC sob proteção do Mutex.
- [x] 2.4 Configurar o silenciamento de logs no `UART_NUM_0` (`esp_log_level_set("*", ESP_LOG_NONE)`).

## 3. Kernel FreeRTOS & Loop Placeholder (Core 1)

- [x] 3.1 Implementar a `Task_ControlLoop` pinada ao Core 1 rodando periodicamente em loop a 100Hz (período de 10ms) com `vTaskDelay`.
- [x] 3.2 Atualizar `main/main.c` e `main/CMakeLists.txt` integrando os módulos do Kernel FreeRTOS, Modbus Slave e dependências do ESP-IDF (`freertos`, `esp_modbus`, `driver`).

## 4. Testes HIL em Python

- [x] 4.1 Criar o diretório `tests/` e o arquivo `tests/test_modbus_kernel.py` utilizando `pytest` e `pymodbus`.
- [x] 4.2 Escrever cenário de teste serial para conexão Modbus RTU Slave ID 1, escrita de Setpoint float32 no Holding Register `0x0000`, e leitura de validação dos Input Registers de posição e estado.
