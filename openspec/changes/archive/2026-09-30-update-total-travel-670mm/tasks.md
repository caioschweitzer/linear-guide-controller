## 1. Atualização do Firmware ESP32

- [x] 1.1 Atualizar `SYSTEM_MAX_TRAVEL_MM` para `670.0f` em `main/src/main.c`.
- [x] 1.2 Atualizar o limiar de corte do ensaio em malha aberta para 80% do curso ($536.0\text{ mm}$) e timeout de segurança para $5000\text{ ms}$ em `main/src/main.c`.
- [x] 1.3 Expandir a capacidade do buffer de burst `BURST_BUFFER_MAX_SAMPLES` para 550 amostras em `main/include/shared_data.h`.

## 2. Atualização do Supervisório SCADA

- [x] 2.1 Atualizar o limite superior do slider (0 a 6700) e do spinbox de setpoint (0.0 a 670.0 mm) em `tools/supervisory/ui_main.py`.
- [x] 2.2 Atualizar labels de botões, mensagens de diálogo e logs para indicar 536 mm (80%) em `tools/supervisory/ui_main.py`.
- [x] 2.3 Atualizar o valor de referência do setpoint no histórico e no gráfico de resposta ao degrau para $536.0\text{ mm}$ em `tools/supervisory/ui_main.py`.

## 3. Atualização da Documentação Técnica

- [x] 3.1 Atualizar $L_{\text{max}} = 670.0\text{ mm}$ e referências de fim de curso mecânico em `docs/01_system_overview_and_physics.md`.
- [x] 3.2 Atualizar a tabela de registradores Modbus TCP (faixa válida do setpoint de 0.0 a 670.0 mm) em `docs/04_modbus_rtu_and_communication.md`.

## 4. Validação e Testes Automatizados

- [x] 4.1 Atualizar o valor de `SYSTEM_MAX_TRAVEL_MM` para `670.0` e os asserts de clamping em `tests/test_system_integration.py`.
- [x] 4.2 Atualizar o teste geométrico `test_open_loop_80_percent_travel_geometry` em `tests/test_open_loop_test.py` para $536.0\text{ mm}$, margem de $134.0\text{ mm}$ e 550 amostras.
- [x] 4.3 Executar a suíte de testes com `pytest` e verificar aprovação completa.
