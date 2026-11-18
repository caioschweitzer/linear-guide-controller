# Design

## Context

O sistema já possui a rotina de identificação em malha aberta (`MACHINE_STATE_OPEN_LOOP_TEST`) operando no loop de controle a 100 Hz no Core 1 (`main/src/main.c`), com buffer em RAM (`g_burst_buffer`) para até 550 amostras e transferência via Modbus RTU para o supervisório Python (`tools/supervisory/`). Veja `proposal.md` para a motivação.

Atualmente:
- `HOLDING_REG_COUNT` é `10` (`0x0000`–`0x0009`), usando IEEE-754 Float32 em dois registradores consecutivos (MSW/LSW) para `setpoint`, `kp`, `ki` e `kd`.
- `main/src/main.c` aplica `motor_set_effort(&g_motor, 100.0f)` fixo durante `MACHINE_STATE_OPEN_LOOP_TEST`.
- `tools/supervisory/modbus_worker.py` fixa `duty_pct: 100.0` ao montar as amostras recebidas.
- `tools/supervisory/ui_main.py` dispara um único ensaio por clique e abre o diálogo de salvamento CSV imediatamente após `burst_data_ready`.

## Goals / Non-Goals

**Goals:**
- Permitir configurar o nível de PWM do degrau (`1.0%` a `100.0%`) no supervisório e transmiti-lo ao firmware via Modbus Holding Register antes de iniciar o teste.
- Manter compatibilidade retroativa: se nenhum valor for escrito no novo registrador, o firmware inicia com `100.0%`.
- Orquestrar no supervisório a coleta automática de $N$ curvas consecutivas ($N \ge 1$) com retorno automático ao home (`CMD_HOME`) entre execuções.
- Calcular e exportar em CSV a curva consolidada e normalizada ao final das $N$ coletas, usando função pura testável em `pytest`.

**Non-Goals:**
- Alterar o limite de curso de 80% ($536.0\text{ mm}$) ou o timeout de segurança de $5.0\text{ s}$ no firmware.
- Armazenar múltiplas curvas simultaneamente na RAM do ESP32 (cada curva continua sendo baixada para o PC antes da próxima).
- Implementar ajuste automático de modelo (FOPDT/PID autotuning) dentro desta mudança.

## Decisions

1. **Representação Modbus do nível de PWM (`0x000A`–`0x000B`, Float32)**
   - **Escolha**: Adicionar `open_loop_pwm_hi` (`0x000A`) e `open_loop_pwm_lo` (`0x000B`) ao final de `holding_reg_params_t`, aumentando `HOLDING_REG_COUNT` de `10` para `12`, inicializado em `100.0f`.
   - **Alternativa considerada**: Usar `uint16` em décimos de percentual (`0`–`1000`) em um único registrador. Rejeitada porque todos os demais parâmetros contínuos (`setpoint`, `kp`, `ki`, `kd`) usam Float32 (2 registradores) com os helpers existentes `float_to_registers` / `registers_to_float`.
   - **Segurança/Validação**: Em `modbus_slave_sync_buffers()`, validar com `isfinite()` e fazer clamp para `[1.0f, 100.0f]` (fallback para `100.0f` se não finito).

2. **Orquestração de $N$ curvas no supervisório (`ui_main.py`)**
   - **Escolha**: Implementar máquina de estados leve na `MainWindow` (`_batch_active`, `_batch_total`, `_batch_index`, `_batch_curves`, `_batch_phase` ∈ `{"IDLE", "RUNNING_TEST", "WAITING_HOME", "SETTLING"}`) reagindo aos sinais já existentes (`burst_data_ready`, `burst_status_changed`, `telemetry_updated`).
   - **Alternativa considerada**: Criar uma thread separada bloqueante para coordenar os $N$ ensaios. Rejeitada para evitar concorrência com o loop de polling do `ModbusWorker` e manter toda a lógica de UI na thread principal do Qt.
   - **Fluxo entre curvas**: Ao concluir a curva $k < N$, o supervisório envia `CMD_HOME`, aguarda `machine_state == 0 (IDLE)` e `abs(current_position) <= 5.0`, aguarda `500 ms` via `QTimer.singleShot` para estabilização mecânica e então envia o próximo `OPEN_LOOP_TEST` com o PWM configurado.

3. **Cálculo da curva normalizada**
   - **Escolha**: Extrair função pura `compute_normalized_curve(curves, duty_pct)` (em `tools/supervisory/curve_utils.py` ou módulo dedicado importado por `ui_main.py`) para facilitar testes unitários sem Qt/hardware.
   - **Alinhamento e normalização**:
     - Alinhar pelo menor comprimento comum `M = min(len(c) for c in curves)` no grid de 10 ms.
     - Calcular média ponto a ponto: `position_mean_mm[i]` e `velocity_mean_mm_s[i]`.
     - Normalizar posição no intervalo $[0, 1]$: `(pos_mean[i] - pos_min) / (pos_max - pos_min)` (ou `0.0` se `pos_max == pos_min`).
     - Normalizar velocidade no intervalo $[0, 1]$: `(vel_mean[i] - vel_min) / (vel_max - vel_min)` (ou `0.0` se `vel_max == vel_min`).
     - Exportar CSV com cabeçalho `time_s,position_mean_mm,velocity_mean_mm_s,position_norm,velocity_norm,duty_pct,curve_count`.
   - **Comportamento para $N = 1$**: Mantém o fluxo padrão de exportação da curva individual (`time_s,position_mm,velocity_mm_s,duty_pct`) e disponibiliza também o botão/opção de exportar curva normalizada quando desejado.

## Risks / Trade-offs

- **Timeout de 5,0 s com PWM baixo** → Em níveis de PWM muito baixos (ex.: `< 30%`), o atuador pode não vencer o atrito estático ou não atingir $536.0\text{ mm}$ em $5.0\text{ s}$, disparando `BURST_STATUS_ABORTED`. Mitigação: documentar na UI/log que PWM baixo pode atingir o timeout de segurança de 5 s e interromper o lote com segurança caso ocorra abort.
- **Diferença de duração entre as $N$ curvas** → Pequenas variações de atrito fazem com que uma curva atinja $536.0\text{ mm}$ em $K$ amostras e outra em $K+2$ amostras. Mitigação: truncar no menor comprimento comum `min(len)` preserva o alinhamento temporal exato de 10 ms até o ponto em que todas as execuções ainda estavam ativas.
- **Homologação do registrador Modbus estendido** → Clientes Modbus que leiam apenas `0x0000`–`0x0008` continuam funcionando sem impacto, pois os novos registradores ficam em `0x000A`–`0x000B`.
