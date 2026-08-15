## Context

O firmware da guia linear no ESP32-S3 exige a integração completa de todos os subsistemas em C nativo com separação rígida de tarefas por núcleo no FreeRTOS. A malha de controle PID deve rodar no Core 1 com período estrito de 10 ms (100 Hz), enquanto tarefas de comunicação (Modbus RTU), interface visual (LCD I2C 16x2 + LED status) e acionamento por botão rodam no Core 0. A sincronização de dados ocorre por snapshot protegido pelo mutex global `g_system_mutex`.

## Goals / Non-Goals

**Goals:**
- Implementar o ponto de entrada `main/main.c` em C nativo com a função `app_main()`.
- Criar a `Task_ControlLoop` pinada no Core 1 rodando a 100 Hz com `vTaskDelayUntil`.
- Criar a `Task_IHM` (5 Hz) e `Task_Modbus` pinadas no Core 0.
- Implementar clamping mecânico de setpoint $[0.0\text{ mm}, 424.115\text{ mm}]$.
- Garantir corte imediato de dever MCPWM para 0.0% e reset de memória do PID ao disparar emergência.
- Fornecer suíte de testes de integração em Python (`tests/test_system_integration.py`).

**Non-Goals:**
- Não usar suporte a C++ classes em `main.c`.

## Decisions

### Decisão 1: Arquitetura FreeRTOS Dual-Core Pinned Tasks
- **Escolha**: Pinar `Task_ControlLoop` no Core 1 (prioridade alta 10) e `Task_IHM` / `Task_Modbus` no Core 0 (prioridade 5).
- **Razão**: Evita que processamentos pesados de I2C ou pacotes Modbus no Core 0 causem jitter na amostragem e controle do motor no Core 1.

### Decisão 2: Snapshot Mutex com Timeout Mínimo
- **Escolha**: Usar `shared_data_lock(pdMS_TO_TICKS(1))` para capturar foto local dos registradores de setpoint e estado e atualizar posição e velocidade.
- **Razão**: O lock dura menos de 1 ms. Se o mutex não for obtido dentro de 1 ms, o loop utiliza os valores da iteração anterior sem bloquear o determinismo de 100 Hz.

### Decisão 3: Interceptação e Parada Dupla de Emergência
- **Escolha**: Tanto a ISR no GPIO 12 quanto o loop de controle a 100 Hz zeram o dever MCPWM para 0.0%, garantindo redundância de corte físico e de software.
- **Razão**: Elimina qualquer possibilidade de inércia ou esforço residual em caso de emergência.

## Risks / Trade-offs

- **[Jitter no FreeRTOS]** → `vTaskDelayUntil` garante periodicidade absoluta a 100 Hz.
- **[Concorrência do Mutex]** → Com tempo de retenção em microssegundos (< 100 us), a probabilidade de disputa entre Core 0 e Core 1 é negligenciável.
