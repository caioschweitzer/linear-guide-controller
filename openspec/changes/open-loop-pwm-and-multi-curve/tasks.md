# Tasks

## 1. Firmware: Registrador Modbus e Controle de PWM em Malha Aberta

- [x] 1.1 Estender `holding_reg_params_t` e `HOLDING_REG_COUNT` (`10` -> `12`) em `main/include/modbus_slave.h` com `open_loop_pwm_hi` (`0x000A`) e `open_loop_pwm_lo` (`0x000B`), inicializando em `100.0f` em `modbus_slave_init()` (`main/src/modbus_slave.c`); verificar que o build do firmware/host-test compila sem warnings.
- [x] 1.2 Adicionar campo `open_loop_pwm` (padrão `100.0f`) em `main/include/shared_data.h` / `main/src/shared_data.c`, sincronizá-lo com clamp `[1.0f, 100.0f]` (e fallback `100.0f` para NaN/Inf) em `modbus_slave_sync_buffers()`, e utilizá-lo em `main/src/main.c` dentro de `MACHINE_STATE_OPEN_LOOP_TEST` em `motor_set_effort(&g_motor, open_loop_pwm)`; verificar com testes unitários em host que valores válidos, fora da faixa e NaN são tratados corretamente.

## 2. Supervisório: Envio do Nível de PWM e Coleta de N Curvas

- [x] 2.1 Atualizar `tools/supervisory/modbus_worker.py` para aceitar `pwm_pct: float = 100.0` em `queue_open_loop_test()`, escrever o Float32 no Holding Register `0x000A` antes de enviar `CMD_OPEN_LOOP_TEST` (`5`), e preencher `duty_pct` das amostras baixadas com o PWM configurado; verificar via teste unitário com cliente Modbus mockado (`pytest`).
- [x] 2.2 Criar módulo utilitário `tools/supervisory/curve_utils.py` com a função pura `compute_normalized_curve(curves, duty_pct)` (alinhamento pelo menor comprimento, média ponto a ponto de posição/velocidade e normalização min-max em `[0.0, 1.0]`) e escrever testes `pytest` cobrindo $N = 1$, $N > 1$, curvas com comprimentos diferentes e caso degenerado constante.
- [x] 2.3 Atualizar `tools/supervisory/ui_main.py` para adicionar os controles de **PWM do Degrau (%)** (`1.0%`–`100.0%`, padrão `100.0%`) e **Número de Curvas (N)** (`1`–`50`, padrão `1`), exibir progresso (`Curva k de N`), implementar a máquina de estados de coleta sequencial com retorno automático ao home (`CMD_HOME` -> `IDLE` com `|pos| <= 5.0 mm` -> pausa de 500 ms -> próximo ensaio), interromper com segurança em falhas/parada e exportar a curva normalizada em CSV ao final; verificar executando `pytest` e abrindo/inspecionando a UI.

## 3. Validação Final

- [x] 3.1 Executar a suíte completa de testes (`pytest` e build/testes do ESP-IDF disponíveis no repositório) e confirmar que todos passam após as alterações finais.
