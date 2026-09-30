## Why

A guia linear física foi reconfigurada mecanicamente para um curso total útil de $670.0\text{ mm}$, medido entre o sensor home (origem / zero de referência) e o primeiro sensor de fim de curso (limite de fim de curso positivo). O valor anterior de $424.115\text{ mm}$ limitava o envelope operacional do atuador, restringia os limites do supervisório e do loop de controle PID, e forçava o ensaio em malha aberta a cortar em $339.292\text{ mm}$ em vez de explorar o curso estendido. Atualizar essa cota fundamental alinha os parâmetros físicos do firmware, o ensaio de identificação dinâmica em malha aberta, a interface SCADA e toda a documentação ao hardware real montado.

## What Changes

- **Curso Máximo do Sistema Atualizado para $670.0\text{ mm}$**:
  - `SYSTEM_MAX_TRAVEL_MM` no firmware do ESP32 alterado de $424.115\text{ mm}$ para $670.0\text{ mm}$.
  - Limite de saturação/clamping do setpoint de posição no loop determinístico de controle atualizado para $[0.0\text{ mm}, 670.0\text{ mm}]$.
- **Ensaio ao Degrau em Malha Aberta a 80% do Novo Curso**:
  - Limiar de corte do ensaio estendido para $536.0\text{ mm}$ ($80\%$ de $670.0\text{ mm}$).
  - Margem livre de segurança restante garantida em $134.0\text{ mm}$ ($20\%$ do curso restante até o primeiro fim de curso mecânico) para frenagem eletrodinâmica ativa segura.
  - Watchdog/timeout de segurança do ensaio estendido para $5.0\text{ s}$ ($5000\text{ ms}$).
  - Expansão do buffer de captura burst em RAM de 400 para 550 amostras ($5.5\text{ s}$ a 100 Hz).
- **Interface Gráfica do Supervisório (SCADA)**:
  - Sliders e spinboxes de setpoint ajustados para escala até $670.0\text{ mm}$.
  - Botão e avisos do ensaio em malha aberta atualizados para "100% PWM -> 536 mm / 80%".
  - Linha de referência no gráfico de setpoint de identificação atualizada para $536.0\text{ mm}$.
- **Documentação do Sistema**:
  - `docs/01_system_overview_and_physics.md`: $L_{\text{max}}$ atualizado para $670.0\text{ mm}$ na tabela mecânica e no diagrama.
  - `docs/04_modbus_rtu_and_communication.md`: tabela de mapa de registradores Modbus atualizada indicando setpoint até $670.0\text{ mm}$.
- **Validação e Testes Automatizados**:
  - `tests/test_system_integration.py`: assert e clamping de setpoint atualizados para $670.0\text{ mm}$.
  - `tests/test_open_loop_test.py`: cálculo de geometria, limiar de 80% ($536.0\text{ mm}$), margem de desaceleração ($134.0\text{ mm}$) e capacidade de buffer atualizados.

## Capabilities

### New Capabilities
- `open-loop-identification`: Rotina determinística de ensaio ao degrau em malha aberta a 100% de PWM até 80% do curso de 670 mm ($536.0\text{ mm}$), gravação em RAM a 100 Hz (até 550 amostras) e margem de segurança de $134.0\text{ mm}$.

### Modified Capabilities
- `system-integration`: Atualização do limite superior físico de deslocamento ($L_{\text{max}}$) e saturação de setpoint para $670.0\text{ mm}$.

## Impact

- **Firmware ESP32 (`main/`)**:
  - `main/src/main.c`: `SYSTEM_MAX_TRAVEL_MM` atualizado para `670.0f`, timeout de teste para `5000 ms`.
  - `main/include/shared_data.h`: `BURST_BUFFER_MAX_SAMPLES` expandido para 550.
- **Supervisório Python (`tools/supervisory/`)**:
  - `tools/supervisory/ui_main.py`: limites de setpoint ajustados para 670 mm, labels e referências de ensaio para 536 mm.
- **Documentação (`docs/`)**:
  - `docs/01_system_overview_and_physics.md` e `docs/04_modbus_rtu_and_communication.md`.
- **Testes Unitários e de Integração (`tests/`)**:
  - `tests/test_system_integration.py` e `tests/test_open_loop_test.py`.
