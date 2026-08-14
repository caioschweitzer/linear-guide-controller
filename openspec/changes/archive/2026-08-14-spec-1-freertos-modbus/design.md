## Context

O controlador de guia linear para ESP32-S3 exige arquitetura determinística de tempo real, segregando responsabilidades pesadas de comunicação (Modbus RTU Slave, USB Serial, I/O) no Core 0 e a malha de controle em malha fechada (100Hz) no Core 1.
A comunicação de testes e controle externo é realizada via protocolo Modbus RTU Slave através de uma conexão física USB-C direta com o computador.

## Goals / Non-Goals

**Goals:**
- Implementar a estrutura IPC `SystemData` protegida por `SemaphoreHandle_t` (Mutex).
- Inicializar a stack `esp_modbus` em `UART_NUM_0` (115200 8N1, Slave ID 1).
- Mapear registradores Modbus (Holding e Input Registers) convertendo o formato float32 IEEE 754 Big-Endian (ABCD).
- Silenciar os logs de texto na `UART_NUM_0` (`ESP_LOG_NONE`) para garantir integridade na transmissão dos quadros binários Modbus.
- Criar a Task Placeholder no Core 1 rodando a 100Hz (período de 10ms).
- Escrever testes automatizados em Python (`pytest` + `pymodbus`).

**Non-Goals:**
- Não implementar malha PID, leitura do encoder via PCNT ou modulação MCPWM do atuador (previstos para as Specs 4, 5 e 6).
- Não implementar lógica de máquina de estados de segurança completa (prevista para a Spec 2).

## Decisions

1. **Uso de UART_NUM_0 via cabo USB-C:**
   - *Decisão:* Utilizar a porta USB-C com o conversor USB-Serial da própria placa (`UART_NUM_0` / GPIO 43 TX e GPIO 44 RX).
   - *Alternativas consideradas:* Usar a porta USB-CDC nativa ou módulo RS485 externo nos GPIOs 17/18.
   - *Motivo:* Permite teste HIL direto com apenas um cabo USB-C plugado no PC, sem necessidade de hardware adicional.

2. **Supressão de Logs de Debug na Serial:**
   - *Decisão:* Executar `esp_log_level_set("*", ESP_LOG_NONE)` no bootstrap da aplicação.
   - *Alternativas consideradas:* Manter logs na UART0.
   - *Motivo:* Caracteres ASCII do logger interfeririam diretamente nos bytes binários do Modbus RTU causando erros de framing/CRC no `pymodbus`.

3. **IPC Thread-Safe com Mutex:**
   - *Decisão:* Proteger os dados compartilhados com `xSemaphoreCreateMutex()` e copiá-los periodicamente entre a struct `SystemData` e os registradores da `esp_modbus`.
   - *Alternativas consideradas:* Acesso direto sem trava ou uso de filas (`QueueHandle_t`).
   - *Motivo:* O Mutex permite acesso rápido de leitura/escrita mantendo consistente o grupo de variáveis (setpoint, posição, velocidade, estado).

## Risks / Trade-offs

- **[Risco] Interrupções da UART afetando o tempo real do Core 0:** 
  - *Mitigação:* A Task de controle de 100Hz é pinada exclusivamente ao Core 1 com prioridade superior, garantindo isolamento total em relação ao processamento serial do Core 0.
- **[Risco] Desalinhamento de Endianness no Float32 entre Python e ESP32:**
  - *Mitigação:* Padronizado explicitamente IEEE 754 Big-Endian (ABCD) no `pymodbus` e no mapeamento de memória em C++.
