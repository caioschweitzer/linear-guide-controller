## Context

O controlador de guia linear exige o acionamento de um motor CC 12V via ponte H L298N. O ESP32-S3 oferece o periférico de hardware Motor Control PWM (MCPWM), acessível via a API moderna do ESP-IDF v5.1+ (`<driver/mcpwm_prelude.h>`). O controle do atuador exige regulação de duty cycle no pino GPIO 4 (Enable) e saídas digitais rápidas nos pinos GPIO 5 (IN1) e GPIO 6 (IN2). A abstração em C nativo deve gerenciar os handles do periférico MCPWM, garantir um chaveamento silencioso a 20 kHz e proteger a ponte H contra impulsos eletromotrizes causados por reversões abruptas de sentido.

## Goals / Non-Goals

**Goals:**
- Implementar a abstração do motor em C nativo (`motor_mcpwm.h` / `motor_mcpwm.c`).
- Utilizar a API moderna do ESP-IDF v5.1+ (`mcpwm_timer_handle_t`, `mcpwm_oper_handle_t`, `mcpwm_cmpr_handle_t`, `mcpwm_gen_handle_t`).
- Configurar frequência PWM inaudível de 20 kHz no GPIO 4 (Enable).
- Configurar saídas digitais em GPIO 5 (IN1) e GPIO 6 (IN2) para controle de sentido.
- Implementar clamping de esforço em $[-100.0\%, +100.0\%]$ e fail-safe de emergência para `NaN` / `INF`.
- Adicionar transição com freio passivo ($IN1=0, IN2=0, \text{duty}=0\%$) em reversões de sentido para evitar picos de Back-EMF no L298N.
- Suportar modo de emulação (`#ifdef HOST_TEST`) para testes unitários em Python via `pytest`.

**Non-Goals:**
- Não integrar a malha fechada do controlador PID nesta etapa (escopo da Spec 6).
- Não alterar a rotina principal em `main.c` nesta fase.

## Decisions

### Decisão 1: Abstração em C Nativo com Contexto `motor_driver_t`
- **Escolha**: Criar a API em C nativo com a struct `motor_driver_t`.
- **Razão**: Manter consistência com a arquitetura em C nativo do firmware (`main.c`, `shared_data.c`, `linear_kinematics.c`, `encoder_pcnt.c`).

### Decisão 2: Timer MCPWM a 20 kHz com Clock Resolution de 10 MHz
- **Escolha**: Frequência de 20 kHz com clock base de 10 MHz (500 ticks por período).
- **Razão**: Garante chaveamento acima da faixa audível humana ($> 18\text{ kHz}$) com resolução de 0,2% por tick.

### Decisão 3: Frenagem Intermediária na Inversão de Sentido
- **Escolha**: Antes de aplicar uma mudança de sentido (de $+effort$ para $-effort$ ou vice-versa), zerar temporariamente as saídas ($IN1=0, IN2=0, \text{duty}=0\%$).
- **Razão**: Previne sobrecorrente de comutação e surtos de contra-força eletromotriz (Back-EMF) que poderiam queimar o L298N ou provocar resets por descontinuidade de alimentação no ESP32.

### Decisão 4: Fail-Safe Numérico contra `NaN` e `INF`
- **Escolha**: Avaliar `isnan(effort)` e `isinf(effort)`. Em caso positivo, forçar freio instantâneo a 0%.
- **Razão**: Evita comportamentos indefinidos no hardware caso a malha de controle PID produza valores numéricos inválidos.

## Risks / Trade-offs

- **[Perdas de Comutação no L298N a 20 kHz]** → Ponte H BJT L298N possui pequenas perdas de comutação em 20 kHz. Testes térmicos preliminares indicam que com o dissipador padrão do L298N a temperatura permanece estável sob carga nominal de 12V.
- **[Tempo de Transição de Inversão]** → A inserção da etapa de frenagem ao mudar de sentido introduz uma transição de microssegundos que não impacta a dinâmica da guia linear (constante de tempo mecânica > 50 ms).
