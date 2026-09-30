## Context

O sensor magnético de fim de curso (origem / home) da bancada está eletricamente conectado entre +3.3V e o pino GPIO 16 do ESP32-S3. Em repouso (carro afastado, sem campo magnético direto), o contato elétrico do sensor permanece fechado (tipo Normalmente Fechado - NF), conduzindo +3.3V ao pino. Quando o carro deslizante atinge a origem mecânica e posiciona o ímã sobre o sensor, o campo magnético abre o contato, cortando o sinal de 3.3V; o resistor interno de pull-down (~45 kΩ) do ESP32 drena imediatamente a linha para 0V (GND).

Atualmente, o firmware (`main/src/main.c` e `main/src/modbus_slave.c`) foi escrito assumindo que a presença do ímã colocaria 3.3V no pino (`gpio != 0`). Isso gera uma inversão completa: o SCADA enxerga o sensor como permanentemente acionado no meio do curso e a rotina de homing aborta no primeiro ciclo de 10 ms.

## Goals / Non-Goals

**Goals:**
- Inverter o teste de detecção do sensor de Home na rotina de controle (`MACHINE_STATE_HOMING`) para considerar Home acionado quando `gpio_get_level(GPIO_HOME_PIN) == 0`.
- Inverter a publicação do Bit 3 no registrador de entradas discretas Modbus TCP em `main/src/modbus_slave.c` para `1` quando `gpio_get_level(GPIO_HOME_PIN) == 0` e `0` quando `!= 0`.
- Manter o resistor de pull-down interno ativado em `main/src/gpio_safety.c` (`pull_down_en = GPIO_PULLDOWN_ENABLE`), garantindo nível 0V sólido quando o contato abrir.
- Atualizar a documentação esquemática em `docs/02_hardware_and_schematics.md`.
- Validar via testes automatizados.

**Non-Goals:**
- Alterar a fiação física existente da bancada.
- Alterar a lógica dos botões de emergência (`GPIO 12`) ou de partida (`GPIO 11`).
- Alterar a interface gráfica do supervisório Python (o SCADA já espera 1 = DETECTED e 0 = CLEAR).

## Decisions

### 1. Inversão Lógica no Firmware mantendo o Circuito com Pull-Down
- **Decisão**: Manter o circuito físico (+3.3V ── Sensor NF ── GPIO 16 ── Pull-Down Interno ── GND) e inverter unicamente as instruções condicionais no código C.
- **Racional**:
  - Quando sem ímã: contato fechado -> 3.3V sobrepuja o pull-down -> pino em HIGH (1) -> interpretado como livre (`CLEAR`).
  - Quando com ímã: contato abre -> pull-down garante 0V sem flutuação -> pino em LOW (0) -> interpretado como `HOME DETECTED`.
  - Essa abordagem evita qualquer retrabalho de solda ou fiação na máquina e é eletricamente robusta.

### 2. Velocidade e Direção de Homing
- **Decisão**: Manter o esforço de -60.0% durante o deslocamento em direção ao Home até a detecção de nível 0.
- **Racional**: O sentido de giro negativo move o carro em direção à origem mecânica; ao encontrar o ímã (nível 0V), `motor_brake` e zeramento do encoder ocorrem imediatamente em $< 10\text{ ms}$.

## Risks / Trade-offs

- **[Risk] Cabo do sensor se desconecta ou rompe** → **Comportamento**: Se o fio de 3.3V partir, o pull-down levará o pino a 0V, simulando sensor acionado. Isso é uma condição de falha segura (*fail-safe*): a máquina não colidirá tentando procurar um home inexistente se o cabo for desconectado.
- **[Risk] Ruído elétrico espúrio durante chaveamento PWM** → **Mitigation**: O resistor de pull-down interno de 45 kΩ combinado com a taxa de amostragem no loop determinístico de 10 ms previne falsos disparos.
