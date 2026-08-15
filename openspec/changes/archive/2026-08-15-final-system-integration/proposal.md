## Why

Para concluir o desenvolvimento do firmware do controlador da guia linear no ESP32-S3, é necessário realizar a integração final de todos os módulos C desenvolvidos nas Specs 1 a 7 (`shared_data`, `gpio_safety`, `linear_kinematics`, `encoder_pcnt`, `motor_mcpwm`, `pid_controller`, `ihm_display` e `modbus_slave`). O sistema deve ser estruturado com separação rígida de tarefas em arquitetura FreeRTOS Dual-Core (Core 0 para I/O/IHM/Modbus e Core 1 para o loop de controle crítico determinístico a 100 Hz), fechar a malha PID com guardrails de setpoint $[0.0\text{ mm}, 424.115\text{ mm}]$, integrar o corte imediato via ISR de emergência e fornecer validação por testes de integração automatizados em Python.

## What Changes

- **Integração do Ponto de Entrada (`main/main.c`)**:
  - Inicialização sequencial dos subsistemas (`shared_data_init`, `gpio_safety_init`, `kinematics_init`, `encoder_pcnt_init`, `motor_mcpwm_init`, `pid_init`, `ihm_init`).
  - Criação da `Task_ControlLoop` pinada ao Core 1 rodando a 100 Hz ($10\text{ ms}$) via `vTaskDelayUntil`.
  - Criação da `Task_IHM` (5 Hz) e `Task_Modbus` no Core 0.
  - Loop de controle a 100 Hz executando leitura do encoder, conversão cinemática, snapshot de Mutex, clamping de setpoint, cálculo de esforço PID e atualização MCPWM.
  - Interceptação imediata de emergência zerando o dever do motor (0.0%) e executando `pid_reset()`.
- **Registro no CMake (`main/CMakeLists.txt`)**:
  - Verificação e garantia de registro de todos os módulos C no componente `main`.
- **Suíte de Testes de Integração (`tests/test_system_integration.py`)**:
  - Testes automatizados em Python via `ctypes` compilando a biblioteca compartilhada de integração `tests/libsystem_integration.so`.
  - Validação da sequência de boot em `IDLE`, malha fechada PID em `MOVING` e zeramento imediato em `EMERGENCY`.

## Capabilities

### New Capabilities
- `system-integration`: Integração completa do firmware em C nativo com malha fechada PID determinística no Core 1 (100 Hz) e tarefas de I/O, IHM e Modbus no Core 0.

### Modified Capabilities
<!-- Nenhuma capacidade existente alterada -->

## Impact

- **Código Afetado**: `main/main.c`, `main/CMakeLists.txt`, `tests/test_system_integration.py`.
- **Hardware**: ESP32-S3 Dual Core (Core 0: IHM I2C, Modbus, GPIO 7 LED, GPIO 11 Start; Core 1: PCNT Encoder GPIO 4/5, MCPWM GPIO 15/16, Emergency ISR GPIO 12).
- **APIs**: ESP-IDF v5.x FreeRTOS, GPIO, PCNT, MCPWM, I2C Master, Modbus RTU.
- **Dependências**: Nenhuma biblioteca externa nova. Testes de integração via `pytest` e `ctypes`.
