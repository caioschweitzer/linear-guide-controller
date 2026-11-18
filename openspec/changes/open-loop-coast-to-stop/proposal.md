# Proposal

## Why

O ensaio de malha aberta atual aplica o degrau de PWM até 80% do curso e aciona imediatamente o freio ativo, interrompendo a coleta antes da desaceleração livre. Para identificar com precisão os parâmetros de atrito, amortecimento e inércia da guia linear, é necessário um modo de coleta em que o degrau inicie no PWM configurado, caia para `0%` ao atingir a posição alvo (sem freio ativo) e continue gravando os dados até a parada natural da guia.

## What Changes

- **Novo modo de ensaio em malha aberta (Degrau + Parada Natural / Coast-to-Stop)**:
  - **Firmware (`modbus_slave`, `shared_data`, `main.c`)**:
    - Adicionar parâmetro de modo de malha aberta via Modbus (`0`: Freio Ativo imediato; `1`: Degrau para `0%` na posição alvo + gravação até parada natural) e parâmetro de posição de transição do degrau para `0%` (faixa segura `[50.0, 536.0] mm`, padrão `400.0 mm`).
    - No modo Parada Natural, ao atingir a posição de transição, o firmware zera o esforço (`motor_set_effort(&g_motor, 0.0f)` sem acionar `motor_brake`) e **continua gravando** posição, velocidade e duty aplicado a 100 Hz até detectar parada natural (`|vel| <= 2.0 mm/s` sustentado após o corte) ou atingir o limite de segurança de curso (`650.0 mm`) / capacidade do buffer.
    - Registrar o esforço aplicado (`duty_pct`) por amostra no buffer de burst para refletir corretamente a transição `PWM% -> 0%` na telemetria e no CSV.
  - **Ampliação do timeout e buffer de malha aberta (1.5x)**:
    - Aumentar o timeout de segurança do teste de malha aberta de `5.0 s` (`5000 ms`) para `7.5 s` (`7500 ms`), e ampliar `BURST_BUFFER_MAX_SAMPLES` de `550` (`5.5 s`) para `825` amostras (`8.25 s` a 100 Hz) para acomodar ensaios com PWM reduzido ou desaceleração livre.
  - **Supervisório (`modbus_worker.py`, `ui_main.py`)**:
    - Adicionar seletor de modo (**Freio Ativo** vs **Parada Natural (Coast)**) e controle da posição de degrau para `0%` (mm) no painel de Malha Aberta.
    - Enviar modo e posição de transição via Modbus antes de `CMD_OPEN_LOOP_TEST`, ler o `duty_pct` real de cada amostra baixada e manter compatibilidade total com a coleta de $N$ curvas e exportação da curva normalizada.

## Capabilities

### New Capabilities
<!-- Estende a capability existente de identificação em malha aberta. -->

### Modified Capabilities
- `open-loop-identification`: Adicionar modo de coleta em malha aberta com degrau descendente para `0%` na posição configurada e gravação contínua até a parada natural por atrito e inércia (sem freio ativo), preservando o modo existente com freio ativo.

## Impact

- **Firmware ESP32**:
  - `main/include/modbus_slave.h` e `main/src/modbus_slave.c`: novos Holding Registers para modo de malha aberta e posição de corte do degrau, além de Input Register (ou campo no buffer) para `duty_pct` da amostra.
  - `main/include/shared_data.h` e `main/src/shared_data.c`: campos de configuração do modo/posição de corte e `duty_pct` em `open_loop_sample_t`.
  - `main/src/main.c`: máquina de fases dentro de `MACHINE_STATE_OPEN_LOOP_TEST` (aceleração -> degrau para 0% -> detecção de parada natural / guarda de fim de curso).
- **Supervisório Python**:
  - `tools/supervisory/modbus_worker.py`: envio dos novos registradores e leitura de `duty_pct` por amostra.
  - `tools/supervisory/ui_main.py`: controles de modo e posição de degrau para `0%` na interface.
- **Testes**:
  - Novos testes unitários em host C e Python (`pytest`) para transição `PWM -> 0%`, detecção de parada natural, guarda de fim de curso e exportação CSV com perfil de degrau completo.
