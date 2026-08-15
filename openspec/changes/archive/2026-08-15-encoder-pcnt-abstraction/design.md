## Context

O controlador de guia linear executa a leitura contínua da posição física por meio de um encoder incremental de 250 PPR em quadratura. O ESP32-S3 possui o periférico de hardware Pulse Counter (PCNT) acessível via a nova API do ESP-IDF v5.1+ (`<driver/pulse_cnt.h>`). Para evitar sobrecarregar a CPU com interrupções a cada borda de pulso, o PCNT realiza a contagem diretamente em hardware. No entanto, como o registrador do PCNT é de 16 bits (-32.768 a +32.767), o software deve implementar uma camada de abstração que estenda essa capacidade para 32 bits mantendo thread-safety e resiliência a ruídos.

## Goals / Non-Goals

**Goals:**
- Implementar a abstração do encoder em C nativo (`encoder_pcnt.h` / `encoder_pcnt.c`) desacoplada do loop principal.
- Usar a API moderna do ESP-IDF v5.1+ (`pcnt_unit_handle_t`, `pcnt_channel_handle_t`).
- Configurar quadratura X4 em GPIO 14 (Canal A) e GPIO 15 (Canal B) com Pull-Up interno.
- Configurar filtro glitch antirruído com limite de 1000 ns ($1\mu s$).
- Acumular estouros de hardware de 16 bits em um acumulador de software de 32 bits usando Watch Points e ISR callbacks.
- Prover função atômica `encoder_clear_count()` e `encoder_get_count()`.
- Suportar modo de emulação (`#ifdef HOST_TEST`) para testes unitários em Python via `pytest`.

**Non-Goals:**
- Não alterar a tarefa principal do FreeRTOS em `main.c` nesta fase.
- Não conectar o driver diretamente à máquina de estados ou registradores Modbus nesta etapa (escopo de integração futura).

## Decisions

### Decisão 1: Abstração em C Nativo com Struct de Contexto (`encoder_driver_t`)
- **Escolha**: Criar a API em C nativo com a struct `encoder_driver_t`.
- **Razão**: Alinhamento com a arquitetura geral em C do firmware (`main.c`, `shared_data.c`, `linear_kinematics.c`).

### Decisão 2: Extensão de 16-bit para 32-bit via PCNT Watch Points
- **Escolha**: Definir `PCNT_UNIT_WATCH_POINT_MAX` em +30.000 e `MIN` em -30.000. Ao atingir esses valores, o ISR callback incrementa/decrementa `accumulated_overflows` e zera a contagem relativa.
- **Razão**: Previne o estouro bruto dos 16 bits e permite leitura contínua sem saltos em cursos longos (> 1,39 m).

### Decisão 3: Habilitação de Internal Pull-Up nos GPIOs
- **Escolha**: Configurar `gpio_pullup_en(GPIO_NUM_14)` e `gpio_pullup_en(GPIO_NUM_15)` antes de inicializar o PCNT.
- **Razão**: Encoders industriais open-collector NPN flutuam em estado lógico alto sem resistores de pull-up, gerando contagens falsas causadas pelo chaveamento da ponte H.

### Decisão 4: Abstração com Suporte a Host Testing (`HOST_TEST`)
- **Escolha**: Prover abstração condicional `#ifdef HOST_TEST` para compilação estática em ambiente Linux/GCC, permitindo testes rápidos em `pytest` via `ctypes`.

## Risks / Trade-offs

- **[Latência de ISR no Core 1]** → O callback do Watch Point executa em contexto de IRAM ISR. Como o evento só ocorre a cada 30.000 contagens (30 voltas completas do encoder), a carga na CPU é desprezível (< 0.001%).
- **[Glitch Filter vs Velocidade Máxima]** → Um filtro de 1000 ns limita a frequência máxima de contagem a 1 MHz, valor ordens de grandeza acima da frequência máxima física do encoder (50 kHz a 3000 RPM).
