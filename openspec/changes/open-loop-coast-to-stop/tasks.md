# Tasks

## 1. Firmware: Registradores Modbus e Amostra com Duty Cycle

- [x] 1.1 Estender `holding_reg_params_t` (`HOLDING_REG_COUNT`: `12` -> `15`) com `open_loop_mode` (`0x000C`, padrão `0`) e `open_loop_coast_pos_hi/lo` (`0x000D`–`0x000E`, padrão `400.0f`), e estender `input_reg_params_t` (`INPUT_REG_COUNT`: `15` -> `17`) com `sample_duty_hi/lo` (`0x000F`–`0x0010`) e `open_loop_sample_t.duty_pct` em `main/include/modbus_slave.h`, `main/include/shared_data.h`, `main/src/shared_data.c` e `main/src/modbus_slave.c`; verificar com testes unitários em host (`pytest`) que o clamp `[50.0f, 536.0f]`, validação de modo (`0` ou `1`) e leitura indexada de `sample_duty` funcionam.
- [x] 1.2 Aumentar o timeout de segurança do teste em malha aberta em 1.5x (`5000 ms` -> `7500 ms`) em `main/src/main.c` e ampliar `BURST_BUFFER_MAX_SAMPLES` (`550` -> `825` amostras = `8.25 s`) em `main/include/shared_data.h`, atualizando `tests/test_open_loop_test.py` (`BurstBufferStruct` e `test_open_loop_80_percent_travel_geometry`); verificar que os testes em host passam.
- [x] 1.3 Implementar a lógica de duas fases no estado `MACHINE_STATE_OPEN_LOOP_TEST` em `main/src/main.c`: no modo Coast (`open_loop_mode == 1`), aplicar `open_loop_pwm` até `current_pos_mm >= open_loop_coast_pos_mm`, zerar esforço (`motor_set_effort(&g_motor, 0.0f)` sem `motor_brake`), continuar gravando amostras a 100 Hz com `duty_pct = 0.0f` até parada natural (`fabsf(current_vel_mm_s) <= 2.0f` por 15 ciclos consecutivos), guarda de fim de curso (`>= 650.0f`), timeout (`7500 ms`) ou limite do buffer (`825` amostras); verificar em testes/compilação que o modo `0` (Freio Ativo) permanece inalterado além do novo timeout.

## 2. Supervisório: Seleção de Modo, Posição de Corte e Leitura de Duty por Amostra

- [x] 2.1 Atualizar `tools/supervisory/modbus_worker.py` para aceitar `mode: int = 0` e `coast_pos_mm: float = 400.0` em `queue_open_loop_test()`, escrever `open_loop_mode` (`0x000C`) e `open_loop_coast_pos` (`0x000D`–`0x000E`) antes de `CMD_OPEN_LOOP_TEST`, e ler 8 registradores (`0x0009`–`0x0010`) em `_do_download_burst_buffer()` para preencher `duty_pct` por amostra; verificar via testes `pytest` com cliente Modbus mockado.
- [x] 2.2 Atualizar `tools/supervisory/ui_main.py` para adicionar seletor de modo (**Freio Ativo** vs **Parada Natural (Degrau -> 0%)**) e campo de posição de corte do degrau (`50.0`–`536.0 mm`, padrão `400.0 mm`), integrando-os ao envio do teste e à coleta em lote de $N$ curvas; verificar com testes `pytest` headless da UI.

## 3. Validação Final

- [x] 3.1 Executar a suíte completa de testes (`tests/.venv/bin/pytest -v`) e confirmar que todos os testes passam após as alterações finais.
