## Why

Para uma caracterização mais completa e precisa da dinâmica do atuador linear em regime permanente e identificação de parâmetros (constante de tempo mecânica, velocidade assintótica máxima e efeitos de atrito dinâmico), é vantajoso percorrer uma extensão maior do curso útil da guia linear. O limiar de 50% ($212.0\text{ mm}$) corta o degrau prematuramente em alguns cenários; expandir o teste para 80% do curso total ($339.29\text{ mm}$) fornece uma janela temporal de observação significativamente maior, mantendo uma margem segura de desaceleração de $84.8\text{ mm}$ (20% do curso restante) com frenagem eletrodinâmica ativa.

## What Changes

- **Limiar de Deslocamento Expandido para 80% do Curso**:
  - Ponto de corte alterado de 50% ($212.05\text{ mm}$) para 80% de $424.115\text{ mm}$ ($339.292\text{ mm}$).
- **Margem de Segurança e Frenagem Eletrodinâmica Ativa**:
  - Garantia de $84.82\text{ mm}$ livres restantes após o corte até o batente final mecânico, permitindo parada completa e segura com `motor_brake`.
- **Ajuste do Timeout de Segurança e Capacidade do Buffer em RAM**:
  - Extensão do watchdog/timeout de corte de $2.5\text{ s}$ para $3.5\text{ s}$.
  - Expansão do buffer estático de amostragem na RAM do ESP32 de 300 para 400 amostras (4.0 segundos a 100 Hz) para comportar com folga o deslocamento mais longo.
- **Atualização da Interface do Supervisório**:
  - Atualização dos textos, botões e labels em `tools/supervisory/ui_main.py` de "100% -> 212 mm" para "100% -> 339 mm (80%)".
  - Atualização da linha de referência no plot gráfico de setpoint para $339.29\text{ mm}$.
- **Atualização dos Testes Automatizados**:
  - Ajuste de asserts e mocks em `tests/test_open_loop_test.py` para a nova capacidade de 400 amostras e o limiar de 80%.

## Capabilities

### New Capabilities
- `open-loop-identification`: Especificação da rotina determinística de ensaio ao degrau em malha aberta a 100% de PWM estendida até 80% do curso ($339.29\text{ mm}$), gravação em RAM a 100 Hz (até 400 pontos), intertravamento de posição inicial próxima de zero ($|pos| \le 5.0\text{ mm}$) e exportação para CSV.

## Impact

- **Firmware ESP32**:
  - `main/src/main.c`: Limiar de corte atualizado para `SYSTEM_MAX_TRAVEL_MM * 0.80f` ($339.292\text{ mm}$) e timeout de $3500\text{ ms}$.
  - `main/include/shared_data.h`: `BURST_BUFFER_MAX_SAMPLES` expandido para 400.
- **Supervisório Python**:
  - `tools/supervisory/ui_main.py`: Labels e botões atualizados para indicar 80% / 339 mm.
- **Testes Unitários**:
  - `tests/test_open_loop_test.py`: Atualizado para refletir 400 amostras e o limiar de 80%.
