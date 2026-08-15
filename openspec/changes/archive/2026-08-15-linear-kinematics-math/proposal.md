## Why

O controlador de guia linear exige a conversão exata da contagem de pulsos do encoder em posição absoluta (mm) e a derivação de velocidade instantânea (mm/s). Esta mudança implementa o módulo matemático e cinemático desacoplado de hardware e do FreeRTOS, garantindo alta precisão, resiliência contra divisões por zero, suavização por filtro passa-baixas (EMA) contra ruídos de leitura, zeramento de referência (homing) e testes unitários automatizados via `pytest`.

## What Changes

- **Novo Módulo C/C++ (`main/linear_kinematics.h`, `main/linear_kinematics.c`)**:
  - Conversão de contagem de encoder em posição absoluta com constante $0.0424115$ mm/contagem.
  - Suporte a calibração de zeramento (`zero_offset`) e inversão de sentido (`direction = ±1`).
  - Cálculo de velocidade instantânea com derivada discreta $\Delta x / dt$.
  - Proteção numérica (*guardrail*) contra $dt \le 0.0001$ s para evitar retornos `NaN` e `+INF`.
  - Tratamento de inicialização (`is_initialized`) prevenindo picos (*spikes*) de velocidade no 1º ciclo de execução.
  - Filtro Passa-Baixas Exponential Moving Average (EMA) configurável para a velocidade estimada.
  - Funções de serialização em ponto fixo para registradores Modbus da `shared_data.h`.
- **Suíte de Testes Unitários (`tests/test_kinematics.py`)**:
  - Cobertura de testes em Python para posição absoluta, calibração, proteção contra $dt \le 0$, inicialização sem surtos, convergência do filtro EMA e conversão de registradores Modbus.

## Capabilities

### New Capabilities
- `kinematics-math`: Módulo cinemático e matemático desacoplado para conversão sensorial de encoder, filtragem de velocidade e conversão para Modbus no controlador de guia linear.

### Modified Capabilities
<!-- Nenhuma capacidade existente alterada -->

## Impact

- **Código Afetado**: `main/linear_kinematics.h`, `main/linear_kinematics.c`, `main/CMakeLists.txt`, `tests/test_kinematics.py`.
- **APIs & Comunicação**: Mapeamento de registradores para a estrutura `SystemData` em `shared_data.h`.
- **Dependências**: Nenhuma biblioteca externa nova no ESP32. Suíte de testes utiliza `pytest` em Python.
