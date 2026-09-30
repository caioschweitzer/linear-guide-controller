## 1. Firmware Buffer & Parameters

- [x] 1.1 Atualizar `BURST_BUFFER_MAX_SAMPLES` de 300 para 400 em `main/include/shared_data.h`.

## 2. Core 1 Control Loop Execution

- [x] 2.1 Atualizar limiar de corte do ensaio para 80% do curso (`SYSTEM_MAX_TRAVEL_MM * 0.80f` = $339.292\text{ mm}$) em `main/src/main.c`.
- [x] 2.2 Estender o watchdog/timeout de segurança do ensaio para $3.5\text{ s}$ ($3500\text{ ms}$) em `main/src/main.c`.

## 3. Supervisory UI & Graph Updates

- [x] 3.1 Atualizar textos de botões e labels em `tools/supervisory/ui_main.py` para referenciar 80% do curso ($339\text{ mm}$).
- [x] 3.2 Atualizar a linha de referência do gráfico de setpoint para $339.29\text{ mm}$ ao carregar o ensaio.

## 4. Automated Verification & Testing

- [x] 4.1 Atualizar a definição de estrutura em `tests/test_open_loop_test.py` para 400 amostras e validar o novo limiar.
- [x] 4.2 Executar a suíte de testes com `pytest` e compilar o firmware ESP-IDF (`idf.py build`).
