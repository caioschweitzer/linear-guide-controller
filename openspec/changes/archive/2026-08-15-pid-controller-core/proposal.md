## Why

O controle de malha fechada da guia linear exige um algoritmo de regulação PID de posição preciso, estável e robusto. Para evitar choques mecânicos e desestabilização da planta por ruídos do encoder ou saturação do integrador, o algoritmo deve calcular a ação derivativa sobre a medição da posição (prevenindo *Derivative Kick*), aplicar filtragem passa-baixas IIR na derivada, congelar condicionalmente o acumulador integral em saturações (Anti-Windup), aplicar banda morta de posição (`deadband_mm`) e fornecer guardrails contra `dt <= 0` e entradas inválidas (`NaN`/`INF`).

## What Changes

- **Novo Módulo C (`main/pid_controller.h`, `main/pid_controller.c`)**:
  - Implementação da struct `pid_config_t` (ganhos `kp`, `ki`, `kd`, `output_min`, `output_max`, `deadband_mm`, `alpha_d`) e `pid_controller_t` (acumulador, histórico de posições, última derivada filtrada).
  - Cálculo da derivada sobre a posição medida: $D_{\text{raw}} = -K_d \cdot \frac{\Delta x}{\Delta t}$.
  - Filtro IIR de 1ª ordem para o termo derivativo: $D_{\text{filtered}} = \alpha_d \cdot D_{\text{raw}} + (1 - \alpha_d) \cdot D_{\text{prev}}$.
  - Anti-windup condicional que desabilita acúmulo integral se a saída estiver saturada e o erro mantiver o mesmo sinal.
  - Banda morta de posição (`deadband_mm` = 0.05 mm) zerando o esforço final se $|e| \le \text{deadband\_mm}$.
  - Proteção contra `dt <= 0.0001s` e fail-safe para `NaN`/`INF`.
  - Função `pid_reset()` para reiniciar o estado do controlador.
- **Registro no CMake (`main/CMakeLists.txt`)**:
  - Adição de `pid_controller.c` na lista de fontes do componente `main`.
- **Suíte de Testes Unitários (`tests/test_pid_controller.py`)**:
  - Testes em Python cobrindo ação Proporcional, Anti-Windup condicional, ausência de Derivative Kick em degraus de setpoint, banda morta de posição e exceções numéricas.

## Capabilities

### New Capabilities
- `pid-controller`: Algoritmo de controle PID discreto em C puro com Anti-Windup, filtro derivativo sobre medição, banda morta de posição e guardrails numéricos.

### Modified Capabilities
<!-- Nenhuma capacidade existente alterada -->

## Impact

- **Código Afetado**: `main/pid_controller.h`, `main/pid_controller.c`, `main/CMakeLists.txt`, `tests/test_pid_controller.py`.
- **APIs**: C puro padrão ANSI (sem dependência de FreeRTOS ou ESP-IDF).
- **Dependências**: Nenhuma biblioteca externa nova. Testes automatizados via `pytest` e `ctypes`.
