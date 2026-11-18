# Design

## Context

O sistema já possui o modo de malha aberta com PWM configurável e coleta em lote de $N$ curvas (`MACHINE_STATE_OPEN_LOOP_TEST`), gravando amostras a 100 Hz em `g_burst_buffer` (até 550 amostras) e usando `motor_set_effort(&g_motor, duty)` / `motor_brake(&g_motor)` em `main/src/main.c`. Veja `proposal.md` para a motivação.

## Goals / Non-Goals

**Goals:**
- Permitir selecionar entre o modo atual (**Freio Ativo**, `0`) e o novo modo **Parada Natural / Coast-to-Stop** (`1`).
- No modo Coast-to-Stop, aplicar o degrau no PWM configurado até atingir a posição de transição (`open_loop_coast_pos_mm`, padrão `400.0 mm`, faixa `[50.0, 536.0] mm`), zerar o esforço (`0.0%`) sem freio ativo e continuar gravando até a parada natural por atrito e inércia.
- Registrar e transferir `duty_pct` por amostra para que gráficos e CSVs reflitam o degrau `PWM% -> 0%`.
- Manter compatibilidade total com coleta de $N$ curvas e exportação normalizada.

- **Non-Goals:**
- Modificar o comportamento funcional do modo `0` além da ampliação do timeout de segurança em 1,5x (`5.0 s` → `7.5 s`) e do buffer (`550` → `825` amostras).
- Implementar detecção automática de parâmetros de atrito/inércia dentro do firmware.

## Decisions

1. **Mapa Modbus estendido (retrocompatível)**
   - **Holding Registers (`HOLDING_REG_COUNT`: `12` → `15`)**:
     - `0x000C`: `open_loop_mode` (`uint16`: `0 = BRAKE`, `1 = COAST`, padrão `0`).
     - `0x000D`–`0x000E`: `open_loop_coast_pos_hi/lo` (`Float32` em mm, clamp `[50.0, 536.0]`, padrão `400.0`).
   - **Input Registers (`INPUT_REG_COUNT`: `15` → `17`)**:
     - `0x000F`–`0x0010`: `sample_duty_hi/lo` (`Float32` %, esforço aplicado na amostra `burst_read_index`).
   - **Alternativa considerada**: Inferir a transição para `0%` no supervisório comparando posição com o limiar. Rejeitada porque gravar `duty_pct` diretamente em `open_loop_sample_t` garante alinhamento exato no tick de 10 ms sem depender de sincronismo externo.

2. **Lógica de duas fases e parada natural no firmware (`main/src/main.c`)**
   - **Fase 1 (Degrau positivo)**: Enquanto `!s_open_loop_coasting`, aplica `open_loop_pwm` e grava amostra com `duty_pct = open_loop_pwm`. Ao atingir `current_pos_mm >= coast_pos_mm`, muda para `s_open_loop_coasting = true`, zera `s_coast_zero_vel_ticks` e chama `motor_set_effort(&g_motor, 0.0f)` (sem `motor_brake`).
   - **Fase 2 (Desaceleração livre / Coast)**: Aplica `0.0f`, grava amostra com `duty_pct = 0.0f` e monitora `fabsf(current_vel_mm_s) <= 2.0f` por `15` ciclos consecutivos (`150 ms`) para confirmar parada natural (evitando falso positivo por ruído pontual de velocidade).
   - **Guardas de segurança e timeout (1.5x)**: Timeout geral de segurança ampliado de `5000 ms` para `7500 ms` (`7.5 s`), e `BURST_BUFFER_MAX_SAMPLES` ampliado de `550` para `825` (`8.25 s` a 100 Hz). Se `current_pos_mm >= 650.0f` (20 mm antes do fim de curso de 670 mm), aciona `motor_brake` imediatamente e encerra a captura como `BURST_STATUS_READY`. Se `g_burst_buffer.sample_count >= BURST_BUFFER_MAX_SAMPLES` (`825` amostras) ou `elapsed_ms >= 7500`, encerra com `0.0f` e `BURST_STATUS_READY`.

3. **Normalização de curvas com degrau `PWM -> 0%`**
   - `compute_normalized_curve` continua alinhando as $N$ curvas pelo menor comprimento comum; na exportação do CSV normalizado, o campo `duty_pct` pode preservar o perfil médio ou o degrau nominal configurado, enquanto cada curva individual já possui `duty_pct` por amostra.

## Risks / Trade-offs

- **Desaceleração mais longa que 5,5 s (550 amostras)** → Se a posição de corte for alta e o PWM alto, o carro pode não parar antes de 5,5 s ou percorrer mais distância. Mitigação: padrão conservador de `400.0 mm` para o corte (deixando `250 mm` de margem até o guarda de `650 mm`) e encerramento limpo com `BURST_STATUS_READY` ao atingir 550 amostras.
- **Comportamento da ponte H com `effort = 0.0%`** → `motor_set_effort(&g_motor, 0.0f)` zera `PWM` e coloca `IN1=0, IN2=0` (mesmo estado de saída do `motor_brake` no driver atual), o que em drivers com pino PWM de habilitação coloca a ponte em alta impedância (roda livre / *coast*).
