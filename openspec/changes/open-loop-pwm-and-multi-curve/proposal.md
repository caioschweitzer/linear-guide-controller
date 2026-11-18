# Proposal

## Why

Atualmente, o ensaio de resposta ao degrau em malha aberta (`MACHINE_STATE_OPEN_LOOP_TEST`) aplica um esforço fixo de 100% de PWM e coleta apenas uma curva por acionamento manual. Para identificação de parâmetros do sistema com diferentes amplitudes de excitação (evitando saturação ou avaliando não linearidades) e para reduzir ruído de medição por meio de múltiplas repetições, é necessário permitir configurar o nível de PWM do degrau e automatizar a coleta de $N$ curvas consecutivas com exportação da curva normalizada ao final.

## What Changes

- **Nível de PWM configurável no degrau de malha aberta**:
  - Firmware (`modbus_slave` / `shared_data` / `main.c`): adicionar registrador Modbus Holding para receber o nível de PWM alvo do ensaio em malha aberta (em `%`, faixa válida `1.0%` a `100.0%`, padrão `100.0%`), substituindo o valor fixo `100.0f` em `motor_set_effort`.
  - Supervisório (`modbus_worker.py` / `ui_main.py`): adicionar controle numérico na interface para escolher o nível de PWM (%) do degrau, enviá-lo via Modbus antes de disparar o comando `CMD_OPEN_LOOP_TEST`, e registrar o PWM real aplicado na coluna `duty_pct` das amostras.
- **Coleta automatizada de $N$ curvas e exportação da curva normalizada**:
  - Supervisório (`ui_main.py`): adicionar seletor de quantidade de curvas $N$ ($N \ge 1$) e indicador de progresso (`Curva k de N`).
  - Quando $N > 1$, após o download de cada curva concluída, o supervisório executa automaticamente o retorno à origem (`CMD_HOME`), aguarda a máquina estabilizar em `IDLE` próximo a `0 mm` (`|pos| <= 5.0 mm`), e inicia a próxima coleta até completar $N$ curvas (interrompendo imediatamente em caso de emergência, timeout/abort ou parada solicitada).
  - Ao final das $N$ coletas, calcular a curva consolidada e normalizada (média ponto a ponto no tempo das $N$ curvas e valores normalizados no intervalo $[0, 1]$) e exportar para arquivo CSV.

## Capabilities

### New Capabilities
<!-- Nenhuma nova capability isolada; a funcionalidade estende a capability existente de identificação em malha aberta. -->

### Modified Capabilities
- `open-loop-identification`: Permitir configuração do nível de PWM do degrau via Modbus/UI (em vez de 100% fixo) e adicionar suporte no supervisório à coleta sequencial de $N$ curvas com retorno automático ao home e exportação da curva normalizada em CSV.

## Impact

- **Firmware ESP32**:
  - `main/include/modbus_slave.h` e `main/src/modbus_slave.c`: ampliação do mapa de Holding Registers (`HOLDING_REG_COUNT`) para incluir o registrador de PWM do ensaio em malha aberta.
  - `main/include/shared_data.h` e `main/src/shared_data.c`: armazenamento thread-safe do nível de PWM de malha aberta.
  - `main/src/main.c`: leitura do nível de PWM configurado ao executar `MACHINE_STATE_OPEN_LOOP_TEST`.
- **Supervisório Python**:
  - `tools/supervisory/modbus_worker.py`: método para escrita do nível de PWM em Holding Register e parametrização de `duty_pct` nas amostras baixadas.
  - `tools/supervisory/ui_main.py`: novos controles de PWM (%) e quantidade de curvas ($N$), máquina de estados de coleta em lote no supervisório, cálculo da curva média/normalizada e exportação CSV.
- **Testes**:
  - Testes unitários em C (host) para o novo registrador Modbus e validação de faixa de PWM.
  - Testes Python (`pytest`) para o cálculo de normalização/agregação de $N$ curvas e escrita Modbus.
