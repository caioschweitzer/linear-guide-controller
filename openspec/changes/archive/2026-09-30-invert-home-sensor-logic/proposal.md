## Why

O sensor magnético de referência (*Home*) instalado fisicamente na bancada está conectado eletricamente entre o barramento de **+3.3V** e o pino **GPIO 16** do ESP32-S3, que opera com resistor interno de **pull-down** ativado. Devido à característica do contato do sensor (Normalmente Fechado em repouso), quando o carro está livre sem o ímã o contato conduz 3.3V para o pino (`gpio == 1`), e quando o ímã é aproximado (carro na origem) o contato se abre, fazendo o pull-down levar o pino a 0V (`gpio == 0`).
Atualmente, o firmware interpreta `gpio != 0` como sensor acionado e `gpio == 0` como livre. Essa discrepância lógica faz com que o supervisório mostre permanentemente `DETECTED 🎯` com o carro no meio da guia, e faz com que o comando "FIND HOME" aborte imediatamente sem movimentar o motor. É necessário inverter a interpretação lógica do sensor no firmware, mantendo o circuito elétrico e o pull-down físico.

## What Changes

- **Inversão da Condição de Parada do Homing (`MACHINE_STATE_HOMING`)**:
  - Em `main/src/main.c`, alterar a detecção de chegada ao zero mecânico de `gpio_get_level(GPIO_HOME_PIN) != 0` para `gpio_get_level(GPIO_HOME_PIN) == 0` (nível BAIXO / 0V indica ímã presente).
  - Ao detectar nível 0V, aplicar freio eletrodinâmico (`motor_brake`), zerar o contador do encoder e transicionar para `MACHINE_STATE_IDLE`.
- **Inversão da Telemetria de Entrada Discreta Modbus (Bit 3)**:
  - Em `main/src/modbus_slave.c`, mapear o Bit 3 de Discrete Inputs para ligar (`1`) quando `gpio_get_level(GPIO_HOME_PIN) == 0` (0V = Ímã Detectado) e desligar (`0`) quando `gpio_get_level(GPIO_HOME_PIN) != 0` (3.3V = Livre / Repouso).
- **Preservação da Configuração de Hardware do Pino**:
  - Manter `pull_down_en = GPIO_PULLDOWN_ENABLE` e `pull_up_en = GPIO_PULLUP_DISABLE` em `main/src/gpio_safety.c`, pois o sensor conduz 3.3V em repouso e necessita do pull-down para drenar o pino a 0V quando aberto pelo ímã.
- **Documentação do Circuito e Lógica**:
  - Atualizar `docs/02_hardware_and_schematics.md` documentando o circuito (+3.3V -> Sensor NF -> GPIO 16 com Pull-down interno) e a lógica de detecção por nível 0V.
- **Testes Automatizados**:
  - Ajustar/adicionar validações em `tests/test_system_integration.py` e testes de hardware para a lógica de Home em nível 0V.

## Capabilities

### New Capabilities
<!-- No new capabilities -->

### Modified Capabilities
- `state-machine-safety`: Atualizar a lógica de detecção de homing para nível BAIXO (0V) com o circuito pull-down mantido.
- `kernel-freertos-modbus`: Atualizar a entrada discreta Modbus Bit 3 para reportar ativo (1) quando o nível do pino for 0V.

## Impact

- **Firmware ESP32**:
  - `main/src/main.c`: Lógica de homing em `control_loop_task`.
  - `main/src/modbus_slave.c`: Mapeamento de `discrete_data` (Bit 3).
- **Documentação**:
  - `docs/02_hardware_and_schematics.md`.
- **Supervisório SCADA**:
  - Passará a refletir `CLEAR` quando livre e `DETECTED 🎯` quando o ímã estiver em frente ao sensor.
