## 1. Firmware State Machine & Data Model

- [x] 1.1 Adicionar `MACHINE_STATE_OPEN_LOOP_TEST = 4` em `main/include/shared_data.h` e atualizar funções de transição de estado.
- [x] 1.2 Definir a estrutura de amostra `open_loop_sample_t` e o buffer estático de 300 amostras em `shared_data.h` e `shared_data.c`.

## 2. Core 1 Control Loop Execution

- [x] 2.1 Implementar a rotina do ensaio em malha aberta dentro de `control_loop_task` em `main/src/main.c` com acionamento de +100% de esforço.
- [x] 2.2 Implementar interrupção por limiar de posição ($pos \ge 212.0\text{ mm}$) e frenagem ativa eletrodinâmica imediata (`motor_brake`).
- [x] 2.3 Implementar interrupção por watchdog/timeout de segurança ($2.5\text{ s}$) e corte de emergência.
- [x] 2.4 Gravar amostras a cada ciclo de 10 ms (100 Hz) no buffer de RAM e sinalizar status de conclusão (`READY`).

## 3. Modbus Slave Burst Interface

- [x] 3.1 Adicionar comando `CMD_OPEN_LOOP_TEST = 5` e registradores de buffer em `main/include/modbus_slave.h`.
- [x] 3.2 Implementar despacho do comando e leitura indexada do buffer de amostras em `main/src/modbus_slave.c`.

## 4. Supervisory UI & Modbus Worker Integration

- [x] 4.1 Implementar métodos de comando e download sequencial do buffer no `tools/supervisory/modbus_worker.py`.
- [x] 4.2 Adicionar botão "🚀 Ensaio Malha Aberta (100%)" e checagem de pré-condição ($|pos| \le 5.0\text{ mm}$) em `tools/supervisory/ui_main.py`.
- [x] 4.3 Implementar geração e exportação de arquivo CSV (`time_s`, `position_mm`, `velocity_mm_s`, `duty_pct`) com diálogo de salvamento.

## 5. Automated Verification & Testing

- [x] 5.1 Criar teste automatizado em pytest (`tests/test_open_loop_test.py`) para validar comando, intertravamentos e integridade da estrutura de dados.
- [x] 5.2 Executar suíte de testes do projeto e validar compilação/sintaxe do firmware e supervisório.
