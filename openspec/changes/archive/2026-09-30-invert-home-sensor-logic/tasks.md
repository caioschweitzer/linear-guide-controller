## 1. Atualização do Firmware ESP32

- [x] 1.1 Inverter a detecção de Home na rotina de controle (`MACHINE_STATE_HOMING`) em `main/src/main.c` para acionar quando `gpio_get_level(GPIO_HOME_PIN) == 0`.
- [x] 1.2 Inverter a telemetria do Bit 3 de entradas discretas Modbus em `main/src/modbus_slave.c` para reportar ativo (`1`) quando `gpio_get_level(GPIO_HOME_PIN) == 0`.
- [x] 1.3 Verificar e manter a configuração de pull-down interno no pino `GPIO 16` em `main/src/gpio_safety.c`.

## 2. Atualização da Documentação Técnica

- [x] 2.1 Atualizar a descrição do pino GPIO 16 e do circuito do sensor magnético (+3.3V com pull-down interno, active a 0V) em `docs/02_hardware_and_schematics.md`.

## 3. Validação e Testes Automatizados

- [x] 3.1 Adicionar/atualizar teste unitário de transição de Homing validando a chegada ao batente em nível 0V em `tests/test_system_integration.py`.
- [x] 3.2 Executar a suíte de testes com `pytest` e verificar aprovação de 100%.
