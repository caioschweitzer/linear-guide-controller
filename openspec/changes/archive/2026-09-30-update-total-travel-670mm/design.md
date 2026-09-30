## Context

O atuador linear com fuso de esferas e carro deslizante possui agora um curso físico útil de $670.0\text{ mm}$, delimitado pelo sensor óptico de home ($0.0\text{ mm}$) e pelo primeiro microswitch de fim de curso mecânico ($670.0\text{ mm}$). O firmware anteriormente operava com um limite de $424.115\text{ mm}$ herdado da especificação inicial do protótipo.
Com a expansão física do curso, o ensaio de identificação de parâmetros em malha aberta (resposta ao degrau a 100% PWM) deve cobrir 80% do novo curso útil ($536.0\text{ mm}$), preservando uma margem de segurança de $134.0\text{ mm}$ (20%) para desaceleração e parada por frenagem eletrodinâmica antes do fim de curso.

## Goals / Non-Goals

**Goals:**
- Atualizar a constante `SYSTEM_MAX_TRAVEL_MM` para `670.0f` em `main/src/main.c`.
- Atualizar o clamping de setpoint de posição no Core 1 para $[0.0\text{ mm}, 670.0\text{ mm}]$.
- Atualizar o limiar do ensaio em malha aberta para `SYSTEM_MAX_TRAVEL_MM * 0.80f` ($536.0\text{ mm}$).
- Estender o timeout do ensaio em malha aberta para $5.0\text{ s}$ ($5000\text{ ms}$) e a capacidade do buffer em RAM para 550 amostras ($5.5\text{ s}$ a 100 Hz).
- Ajustar os limites de curso e os rótulos de identificação no supervisório PyQt6 (`tools/supervisory/ui_main.py`).
- Atualizar a documentação do projeto (`docs/01_system_overview_and_physics.md` e `docs/04_modbus_rtu_and_communication.md`).
- Atualizar os testes automatizados (`tests/test_system_integration.py` e `tests/test_open_loop_test.py`).

**Non-Goals:**
- Alterar a resolução cinemática (`MM_PER_COUNT = 0.0424115 mm/count`), que depende exclusivamente do passo do fuso mecânico e dos pulsos do encoder.
- Alterar a lógica de homing ou a polaridade dos sensores de fim de curso.
- Redesenhar o protocolo Modbus TCP ou alterar o endereçamento dos registradores.

## Decisions

### 1. Limiar do Teste em Malha Aberta a 80% ($536.0\text{ mm}$) e Margem de $134.0\text{ mm}$
- **Decisão**: O ensaio em malha aberta cortará em $536.0\text{ mm}$ ($670.0 \times 0.80$).
- **Racional**: Com a velocidade máxima de translação da guia (~$200\text{ a }400\text{ mm/s}$), a distância típica de frenagem com `motor_brake` (curto-circuito dos enrolamentos via ponta H) é inferior a $25\text{ mm}$. A margem de $134.0\text{ mm}$ fornece um fator de segurança superior a $5\times$, prevenindo qualquer impacto no fim de curso mesmo sob carga máxima ou inércia elevada.
- **Alternativa Considerada**: Testar a 90% ($603\text{ mm}$). Rejeitado para manter margem preventiva ampla de desaceleração sem risco de bater no fim de curso.

### 2. Extensão do Timeout para 5.0 s e Buffer para 550 Amostras
- **Decisão**: Aumentar `BURST_BUFFER_MAX_SAMPLES` de 400 para 550 em `main/include/shared_data.h` e o timeout de ensaio de 3500 ms para 5000 ms.
- **Racional**: A $150\text{ mm/s}$, o deslocamento de $536\text{ mm}$ requer aproximadamente $3.6\text{ s}$. Um timeout de $5.0\text{ s}$ previne cortes espúrios. A 100 Hz, 550 amostras armazenam $5.5\text{ s}$ contínuos de telemetria em RAM (ocupando apenas $550 \times 12\text{ bytes} \approx 6.6\text{ kB}$, insignificante frente aos 512 kB de SRAM do ESP32-S3).

### 3. Ajuste do Supervisório para 670 mm
- **Decisão**: Atualizar os ranges dos componentes interativos (`sp_spinbox` para 0.0–670.0 mm e `sp_slider` para 0–6700, fator 10x) e a legenda/referência do ensaio de degrau.
- **Racional**: Permite que o operador envie qualquer setpoint dentro da nova área física útil e visualize corretamente o limiar de 536 mm no gráfico de identificação.

## Risks / Trade-offs

- **[Risk] Teste em malha aberta ultrapassa o curso em caso de falha de leitura do encoder** → **Mitigation**: Além do corte por posição ($536.0\text{ mm}$), o watchdog de $5.0\text{ s}$ e a interrupção física de fim de curso (`gpio_safety` / interrupção de emergência) acionam corte imediato de energia e freio.
- **[Risk] Saturação de memória por expansão do buffer** → **Mitigation**: O incremento de 150 amostras adiciona apenas ~1.8 kB em BSS/SRAM no ESP32-S3, sem impacto em heap ou estabilidade do FreeRTOS.
