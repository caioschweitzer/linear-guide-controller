## Why

O controlador de guia linear requer um módulo de abstração de hardware para acionamento do motor CC de 12V via driver ponte H L298N. O periférico MCPWM (`<driver/mcpwm_prelude.h>`) do ESP32-S3 permite gerar sinais PWM de alta resolução no pino GPIO 4 (Enable), enquanto os pinos GPIO 5 (IN1) e GPIO 6 (IN2) controlam a direção de rotação. Para proteger a ponte H contra surtos de Back-EMF e evitar instabilidades numéricas no controle PID, a abstração deve implementar transições com freio rápido em inversões de sentido, clamping rigoroso do esforço em $[-100.0\%, +100.0\%]$, fail-safe contra `NaN`/`INF` e suporte a testes unitários em host (`pytest`).

## What Changes

- **Novo Módulo C (`main/motor_mcpwm.h`, `main/motor_mcpwm.c`)**:
  - Configuração do timer MCPWM a 20 kHz (inaudível) no GPIO 4 (Enable) via API moderna do ESP-IDF v5.x (`mcpwm_prelude.h`).
  - Configuração dos pinos de direção GPIO 5 (IN1) e GPIO 6 (IN2) como saídas digitais.
  - Implementação de `motor_set_effort(driver, effort_percent)` com clamping em $[-100.0\%, +100.0\%]$ e fail-safe de emergência para `NaN`/`INF`.
  - Mecanismo de transição com frenagem curta passiva ($IN1=0, IN2=0, \text{duty}=0\%$) ao detectar inversão de sentido de rotação.
  - Suporte a modo de emulação de host (`#ifdef HOST_TEST`) para execução de testes em Python.
- **Registro no CMake (`main/CMakeLists.txt`)**:
  - Adição de `motor_mcpwm.c` na lista de fontes do componente principal.
- **Suíte de Testes Unitários (`tests/test_motor_mcpwm.py`)**:
  - Testes em Python para marcha avante, marcha ré, freio/parada total, clamping de esforço, fail-safe de `NaN`/`INF` e transição de inversão de sentido.

## Capabilities

### New Capabilities
- `motor-mcpwm`: Driver de abstração do periférico MCPWM do ESP32-S3 e controle de ponte H L298N com proteções elétricas e guardrails numéricos.

### Modified Capabilities
<!-- Nenhuma capacidade existente alterada -->

## Impact

- **Código Afetado**: `main/motor_mcpwm.h`, `main/motor_mcpwm.c`, `main/CMakeLists.txt`, `tests/test_motor_mcpwm.py`.
- **Hardware & GPIOs**: Pinos GPIO 4 (Enable/PWM), GPIO 5 (IN1) e GPIO 6 (IN2) do ESP32-S3.
- **APIs**: `<driver/mcpwm_prelude.h>` e `<driver/gpio.h>` do ESP-IDF v5.1+.
- **Dependências**: Nenhuma biblioteca externa nova. Suíte de testes utiliza `pytest` em Python.
