## Why

O controlador de guia linear necessita de um módulo de abstração de hardware desacoplado e resiliente para contagem de pulsos de quadratura do encoder incremental de 250 PPR (1000 contagens/volta em X4). O hardware PCNT do ESP32-S3 desonera a CPU, mas é limitado a contadores de 16 bits assinados (-32.768 a +32.767), o que causaria estouros (overflow) e saltos incorretos de posição em trajetos longos. Esta mudança implementa um driver em C nativo com suporte a acúmulo de estouros em 32-bit, resistores de pull-up internos nos GPIOs 14/15, filtro antirruído glitch, zeramento atômico e suporte a testes unitários em host (`pytest`).

## What Changes

- **Novo Módulo C (`main/encoder_pcnt.h`, `main/encoder_pcnt.c`)**:
  - Configuração de leitura de quadratura X4 em 2 canais PCNT nos pinos GPIO 14 (Canal A) e GPIO 15 (Canal B).
  - Habilitação de Pull-Up interno (`GPIO_PULLUP_ONLY`) nos pinos GPIO 14 e 15 para estabilidade contra ruídos de comutação da ponte H.
  - Filtro de ruídos glitch (`pcnt_glitch_filter_config_t`) configurado com `max_glitch_ns = 1000` ($1\mu s$).
  - Configuração de Watch Points (`PCNT_UNIT_WATCH_POINT_MAX` em +30.000 e `MIN` em -30.000) e ISR callback para acúmulo de estouros de 16-bit em acumulador `int32_t`.
  - Zeramento atômico (`encoder_clear_count`) resetando simultaneamente o hardware PCNT e o acumulador de 32-bit com proteção thread-safe (`portMUX_TYPE`).
  - Suporte a modo de emulação (`#ifdef HOST_TEST`) para injeção de contagens em testes em host.
- **Registro no CMake (`main/CMakeLists.txt`)**:
  - Adição de `encoder_pcnt.c` na lista de fontes do componente principal.
- **Suíte de Testes Unitários (`tests/test_encoder_pcnt.py`)**:
  - Testes em Python para inicialização, acúmulo de pulsos de quadratura, estouro do contador de 16-bit e zeramento atômico.

## Capabilities

### New Capabilities
- `encoder-pcnt`: Driver de abstração do periférico PCNT do ESP32-S3 em modo de quadratura X4 com acúmulo de 32-bit e tratamento de ruídos.

### Modified Capabilities
<!-- Nenhuma capacidade existente alterada -->

## Impact

- **Código Afetado**: `main/encoder_pcnt.h`, `main/encoder_pcnt.c`, `main/CMakeLists.txt`, `tests/test_encoder_pcnt.py`.
- **Hardware & GPIOs**: Pinos GPIO 14 (Canal A) e GPIO 15 (Canal B) do ESP32-S3.
- **APIs**: `<driver/pulse_cnt.h>` do ESP-IDF v5.1+.
- **Dependências**: Nenhuma biblioteca externa nova. Suíte de testes utiliza `pytest` em Python.
