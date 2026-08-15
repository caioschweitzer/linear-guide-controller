## Context

O sistema necessita de uma Interface Homem-Máquina local composta por um display LCD 16x2 acionado por I2C (expansor PCF8574, endereço 0x27) e um LED indicador de status conectado ao GPIO 7. O módulo roda no Core 0 em conjunto com o protocolo Modbus e atualiza a interface visual a 5 Hz (200 ms). É essencial desacoplar o tempo de transmissão lenta do I2C da malha de controle PID do Core 1 através da técnica de leitura por snapshot do Mutex.

## Goals / Non-Goals

**Goals:**
- Implementar o módulo `ihm_display` em C nativo (`ihm_display.h` / `ihm_display.c`).
- Abstrair o barramento I2C Master (`driver/i2c_master.h` no ESP-IDF v5.x e simulação em `#ifdef HOST_TEST`).
- Implementar driver PCF8574 + HD44780 em modo 4-bits.
- Formatar estritamente duas linhas de 16 caracteres (`snprintf` com buffer de 17 bytes).
- Implementar controle de LED não-bloqueante no GPIO 7 ($1\text{ Hz}$ para MOVING/AUTO, $5\text{ Hz}$ para EMERGENCY/FAULT).
- Fornecer resiliência a falhas I2C (LCD desplugado).
- Fornecer suíte de testes unitários em Python via `ctypes`.

**Non-Goals:**
- Não criar tasks FreeRTOS em `main.c` nesta etapa.

## Decisions

### Decisão 1: Formatação Estrita de 16 Caracteres
- **Escolha**: Utilizar `snprintf(line1, 17, "P:%7.2f mm   ", position)` e `snprintf(line2, 17, "V:%5.1f S:%-6s", velocity, state_str)`.
- **Razão**: Garante que o buffer de linha nunca estoure e que o texto impresso no LCD HD44780 ocupe exatamente 16 colunas, sem desalinhamento de memória.

### Decisão 2: Controle de Timing do LED por Ticks/Milissegundos
- **Escolha**: Comparar `(current_time_ms - last_toggle_ms) >= interval_ms`.
- **Razão**: Elimina o uso de `vTaskDelay` interno no driver de LED, permitindo que a função seja chamada dentro de loops de eventos sem bloquear a thread.

### Decisão 3: Padrão Snapshot Mutex
- **Escolha**: Ler a struct `shared_data_t` com Mutex não-bloqueante no início do ciclo e liberar imediatamente o Mutex antes de efetuar a transmissão I2C de 32 bytes para o LCD.
- **Razão**: Transmissões I2C demoram alguns milissegundos. Se o Mutex permanecesse retido durante o envio I2C, o Core 1 (PID) sofreria *starvation*.

## Risks / Trade-offs

- **[Display I2C Lento]** → Escrever 32 caracteres via PCF8574 em I2C a 100 kHz exige aproximadamente 800 I2C write bytes (nibles + strobe EN). A 5 Hz (cada 200 ms), essa carga ocupa menos de 2% de banda do Core 0.
- **[Atraso de Re-conexão I2C]** → Se o LCD for desconectado e reconectado, a tentativa de re-inicialização ocorre a cada 5s para não onerar o barramento.
