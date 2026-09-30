## Context

O ensaio de malha aberta foi originalmente concebido com parada ao alcançar a metade do curso ($212.0\text{ mm}$). Contudo, para levantar a resposta ao degrau completa (permitindo observar com nitidez a velocidade assintótica máxima em regime permanente, a curvatura de aceleração completa e o amortecimento), é necessário estender a trajetória do ensaio até 80% do curso útil total ($339.292\text{ mm}$).

## Goals / Non-Goals

**Goals:**
- Estender a distância percorrida no ensaio de malha aberta de 50% ($212.0\text{ mm}$) para 80% ($339.292\text{ mm}$).
- Preservar a margem de segurança de $84.82\text{ mm}$ (20% do curso restante) para frenagem eletrodinâmica ativa (`motor_brake`), garantindo parada completa bem antes do fim mecânico.
- Ajustar o watchdog/timeout de segurança de $2.5\text{ s}$ para $3.5\text{ s}$ ($3500\text{ ms}$).
- Ampliar a capacidade do buffer interno em RAM de 300 para 400 amostras a 100 Hz ($4.8\text{ KB}$ de SRAM), assegurando capacidade para até 4 segundos de gravação ininterrupta.
- Atualizar a interface do supervisório e os testes unitários para refletir a meta de 80% ($339\text{ mm}$) e 400 amostras.

**Non-Goals:**
- Alterar o mapa de registradores Modbus ou protocolo de comunicação (mantém-se o registrador de índice `0x0009` e comando `CMD_OPEN_LOOP_TEST = 5`).
- Alterar a pré-condição de início (continua exigindo $|pos| \le 5.0\text{ mm}$, repouso e integridade do botão de emergência).

## Decisions

### 1. Limiar de Deslocamento a 80% do Curso
- **Decisão**: Alterar o limiar de corte no loop de controle do Core 1 (`main.c`) para:
  ```c
  const float target_travel_mm = SYSTEM_MAX_TRAVEL_MM * 0.80f; // 339.292 mm
  ```
- **Racional**: $424.115 \times 0.8 = 339.292\text{ mm}$. A margem restante de $84.823\text{ mm}$ é mais de quatro vezes superior à distância típica de frenagem ativa (< $20\text{ mm}$ a $400\text{ mm/s}$), eliminando risco de colisão mecânica.

### 2. Extensão do Timeout e Capacidade de Amostragem
- **Decisão**:
  - `BURST_BUFFER_MAX_SAMPLES` aumentado de 300 para 400 em `shared_data.h`.
  - Timeout estendido de $2500\text{ ms}$ para $3500\text{ ms}$ em `main.c`.
- **Racional**: Como o deslocamento aumentou em 60% ($212 \to 339\text{ mm}$), o tempo de percurso aumenta proporcionalmente para ~1.2 s - 1.8 s. Um timeout de 3.5 s e 400 amostras (4.0 s a 100 Hz) oferece folga ideal sem exceder memória (alocação de apenas $4.8\text{ KB}$ em RAM).

### 3. Interface do Supervisório e Testes
- **Decisão**:
  - Atualizar botões e labels em `ui_main.py` para `80% (339 mm)`.
  - Atualizar linha tracejada do plot gráfico para $339.29\text{ mm}$.
  - Atualizar `tests/test_open_loop_test.py` com `OpenLoopSampleStruct * 400`.

## Risks / Trade-offs

- **[Risco] Maior velocidade e energia cinética ao iniciar a frenagem aos 80%**
  → *Mitigação*: A frenagem eletrodinâmica por curto-circuito dos enrolamentos via ponta MCPWM (`motor_brake`) dissipa a energia rapidamente em menos de 20 mm. Com 84.8 mm restantes, o fator de segurança é $> 4\times$.
- **[Risco] Tempo de download do buffer Modbus ligeiramente maior (400 vs 300 pontos)**
  → *Mitigação*: A leitura via Modbus TCP sobre SPI W5500 a 5 MHz leva aproximadamente 1-2 ms por registro. 400 pontos levam menos de 800 ms no total.
