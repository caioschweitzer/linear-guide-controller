## Why

O sensor de fim de curso de referência (*Home*) instalado fisicamente na guia linear possui saída com lógica **Active-HIGH** (fornece 3.3V / nível lógico ALTO quando acionado pelo carro e 0V / nível BAIXO em repouso).
No entanto, o firmware do ESP32 atualmente configura o pino `GPIO 16` (`GPIO_HOME_PIN`) com resistor de *pull-up* interno ativado e avalia o acionamento em nível BAIXO (Active-LOW). Essa discrepância faz com que o controlador interprete o sensor como acionado quando está em repouso e vice-versa, impedindo a calibração correta do ponto zero (*homing*).

É necessário alinhar a configuração de hardware e o loop de controle do ESP32 para utilizar **pull-down interno** no pino `GPIO 16` e **lógica Active-HIGH** na rotina de calibração de *homing* e telemetria Modbus.

## What Changes

- **Configuração de GPIO**: Em `main/src/gpio_safety.c`, alterar a inicialização de `GPIO_HOME_PIN` (GPIO 16) para desativar o pull-up (`pull_up_en = GPIO_PULLUP_DISABLE`) e ativar o pull-down interno (`pull_down_en = GPIO_PULLDOWN_ENABLE`).
- **Lógica de Homing**: Em `main/src/main.c`, alterar o critério de parada na máquina de estados (`MACHINE_STATE_HOMING`) para detectar o acionamento quando `gpio_get_level(GPIO_HOME_PIN) != 0` (Active-HIGH), efetuando frenagem, reset de contagem do encoder e transição para `MACHINE_STATE_IDLE`.
- **Telemetria Modbus**: Em `main/src/modbus_slave.c`, garantir que o registrador de Discrete Inputs (Bit 3) reflita fielmente o estado ativo do sensor (1 = acionado/HIGH, 0 = desacionado/LOW).
- **Documentação**: Atualizar tabelas de pinagem e circuitos em `docs/02_hardware_and_schematics.md` refletindo o sensor Active-HIGH com pull-down.
- **Testes Automatizados**: Atualizar testes unitários e de integração em `tests/` para validar a lógica Active-HIGH.

## Capabilities

### Modified Capabilities
- `state-machine-safety`: Atualizar a lógica de detecção de fim de curso de Home para Active-HIGH com resistor de pull-down interno.

## Impact

- **Código C do Firmware**:
  - `main/src/gpio_safety.c`: `io_conf_home` com `pull_down_en = GPIO_PULLDOWN_ENABLE` e `pull_up_en = GPIO_PULLUP_DISABLE`.
  - `main/src/main.c`: detecção em `control_loop_task` para `gpio_get_level(GPIO_HOME_PIN) != 0`.
  - `main/src/modbus_slave.c`: mapeamento do Bit 3 de discrete inputs.
- **Documentação de Hardware**:
  - `docs/02_hardware_and_schematics.md`: atualizar descrição do pino GPIO 16 (Pull-down, Active-HIGH).
- **Testes**:
  - `tests/test_system_integration.py` e testes de hardware/estado.
