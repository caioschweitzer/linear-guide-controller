## Why

Para sintonia fina e modelagem matemática da planta (identificação de ganho estático $K$, constante de tempo $\tau$ e tempo morto $\theta$), é necessário registrar a resposta ao degrau em malha aberta com acionamento pleno (100% de esforço PWM). A captura via polling de rede apresenta jitter e taxa insuficiente para registrar dinâmicas rápidas; portanto, um buffer interno em RAM no ESP32 gravando a 100 Hz ($10\text{ ms}$) com intertravamentos rigorosos de segurança e descarregamento no supervisório fornece dados determinísticos com máxima integridade para identificação do sistema.

## What Changes

- **Novo Estado e Comando na FSM**: Adição do estado `MACHINE_STATE_OPEN_LOOP_TEST` (código 4) e comando Modbus `CMD_OPEN_LOOP_TEST` (código 5).
- **Rotina de Teste em Malha Aberta no ESP32**:
  - Acionamento direto do motor a +100% de esforço até atingir metade do curso ($\approx 212.0\text{ mm}$, metade de $424.115\text{ mm}$).
  - Aplicação imediata de freio ativo (`motor_brake`) e corte de esforço ao atingir o limiar ou por timeout de segurança (ex: 2.5 segundos).
  - Intertravamento de pré-condição: recusa do ensaio caso a posição inicial não esteja próxima de zero ($|pos| \le 5.0\text{ mm}$) ou caso haja condição de emergência.
- **Buffer Interno de Aquisição em RAM (Burst Capture)**:
  - Alocação de buffer circular/linear em RAM no ESP32 (ex: até 300 amostras a 100 Hz = 3 segundos de teste) gravando timestamp relativo (ms), posição (mm) e velocidade (mm/s).
  - Mecanismo de sinalização de buffer pronto e transferência paginada ou sequencial via registradores Modbus.
- **Interface e Exportação no Supervisório**:
  - Botão de acionamento "🚀 Malha Aberta (100%)" na UI com validação visual de pré-condições.
  - Leitura dos dados do buffer do ESP32 ao término do ensaio.
  - Exportação dos dados para arquivo CSV (tempo, posição, velocidade, duty cycle) e visualização gráfica imediata.

## Capabilities

### New Capabilities
- `open-loop-identification`: Rotina determinística de ensaio ao degrau em malha aberta a 100% de PWM até metade do curso com gravação em buffer interno em RAM no ESP32 (100 Hz), descarregamento Modbus e exportação para CSV no supervisório.

### Modified Capabilities
- `state-machine-safety`: Inclusão do estado `OPEN_LOOP_TEST` na máquina de estados, regras de transição segura (exigência de $|pos| \le 5.0\text{ mm}$ e ausência de emergência) e transição para `IDLE` com frenagem ativa ao concluir ou abortar.
- `kernel-freertos-modbus`: Suporte ao comando `CMD_OPEN_LOOP_TEST` no registrador de comando e exposição de registradores/área Modbus para status do buffer e leitura paginada dos pontos adquiridos.

## Impact

- **Firmware ESP32 (`main/src/main.c`, `shared_data.h`, `modbus_slave.c`, `modbus_slave.h`)**:
  - Extensão da FSM e loop de controle para gerenciar a rotina de degrau e preencher o buffer de aquisição.
  - Mapeamento Modbus para leitura dos dados do buffer sem afetar a telemetria em tempo real.
- **Supervisório Python (`tools/supervisory/ui_main.py`, `modbus_worker.py`)**:
  - Novo botão e indicador de prontidão de ensaio de malha aberta.
  - Rotina de extração dos pontos do buffer via Modbus e gravação em CSV formatado com diálogo de salvamento (`QFileDialog`).
