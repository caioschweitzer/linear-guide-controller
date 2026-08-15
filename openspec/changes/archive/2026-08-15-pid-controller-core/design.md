## Context

O firmware do controlador de guia linear precisa calcular o esforço de controle para acionar o motor CC a cada 10 ms (100 Hz). O módulo PID deve ser implementado em C puro para garantir desacoplamento total da plataforma ESP-IDF, permitindo testes unitários automatizados em Linux. O algoritmo inclui proteções para eliminar solavancos mecânicos (*derivative kick*), ruído de encoder, saturação de integrador (*windup*) e oscilação residual quando em repouso na posição final.

## Goals / Non-Goals

**Goals:**
- Implementar o módulo PID em C nativo (`pid_controller.h` / `pid_controller.c`).
- Garantir desacoplamento total (0 dependências de headers ESP-IDF/FreeRTOS).
- Implementar derivada sobre a medição da posição ($D = -K_d \cdot \frac{\Delta x}{\Delta t}$).
- Filtrar o termo derivativo com filtro passa-baixas IIR de 1ª ordem ($\alpha_d = 0.15f$).
- Implementar Anti-Windup condicional inteligente para travar a integração apenas na direção da saturação.
- Implementar banda morta de posição (`deadband_mm` = 0.05 mm) que zera o esforço quando $|e| \le \text{deadband}$.
- Adicionar proteção numérica contra `dt <= 0.0001s` e entradas `NaN`/`INF`.
- Fornecer API `pid_reset(pid)` para zerar estados.

**Non-Goals:**
- Não integrar a Task de Controle em FreeRTOS nesta etapa (escopo da Spec 7/8).
- Não alterar `main.c` nesta fase.

## Decisions

### Decisão 1: C Nativo e Desacoplamento Total
- **Escolha**: Usar `pid_controller_t` e `pid_config_t` em C nativo ANSI.
- **Razão**: Permite que o algoritmo seja compilado diretamente com `gcc` no Host Linux e testado via Python/`pytest` sem simulação de FreeRTOS.

### Decisão 2: Derivada sobre Medição da Posição
- **Escolha**: $D_{\text{raw}} = -K_d \cdot \frac{\text{current\_position} - \text{prev\_position}}{\Delta t}$.
- **Razão**: Ao receber comandos de degrau via Modbus (ex: setpoint de 0 para 100 mm), a posição física não muda instantaneamente. Isso impede picos derivativos de $100\%$ no motor.

### Decisão 3: Filtro IIR de 1ª Ordem no Termo Derivativo
- **Escolha**: $D_{\text{filtered}} = \alpha_d \cdot D_{\text{raw}} + (1 - \alpha_d) \cdot D_{\text{prev}}$ ($\alpha_d = 0.15f$).
- **Razão**: Suprime trepidações e ruidos de alta frequência advindos da resolução discreta do encoder (0.0424 mm/contagem).

### Decisão 4: Anti-Windup Condicional Inteligente
- **Escolha**: Bloquear $I = I + K_i \cdot e \cdot \Delta t$ quando $u_{\text{unsat}} > u_{\text{max}} \land e > 0$ ou $u_{\text{unsat}} < u_{\text{min}} \land e < 0$.
- **Razão**: Se a saída estiver saturada mas o erro inverter de sinal, a integração é liberada imediatamente, reduzindo o tempo de overshoot.

## Risks / Trade-offs

- **[Banda Morta Excessiva]** → Se `deadband_mm` for configurado com valor alto (ex: > 0.5 mm), a precisão de posicionamento final cai. O valor padrão de 0.05 mm representa ~1 contagem do encoder e é ideal para a guia linear.
- **[Fator de Filtro Alpha]** → $\alpha_d = 0.15f$ introduz um pequeno atraso de fase no termo derivativo que melhora drasticamente a estabilidade sonora e mecânica do motor.
