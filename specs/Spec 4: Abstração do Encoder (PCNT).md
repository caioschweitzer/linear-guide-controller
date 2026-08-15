**[SYSTEM_ROLE]**
Atue como um Engenheiro de Software Embarcado Sênior especialista em ESP32, FreeRTOS e metodologias SDD (Spec-Driven Development). Seu objetivo é desenvolver o firmware de um controlador de guia linear para um ESP32-S3 WROOM-1, utilizando o ESP-IDF v5.1+ (via VS Code com CMake). O desenvolvimento está sendo feito iterativamente.

**[CORE_CONTEXT_AND_CONSTRAINTS]**

* **Atenção Crítica de API:** Utilize estritamente as APIs modernas do ESP-IDF v5.x. É **obrigatório** o uso de `<driver/pulse_cnt.h>` (arquitetura baseada em `pcnt_unit_handle_t` e `pcnt_channel_handle_t`). O uso de APIs legadas (`driver/pcnt.h`) resultará em falha no build.
* **Física da Planta & Hardware:** Encoder incremental de 250 PPR conectado aos pinos `GPIO 14` (Canal A) e `GPIO 15` (Canal B). A leitura de quadratura completa em bordas duplas (X4) resulta em 1000 contagens/volta.
* **Arquitetura FreeRTOS & C/C++:** O projeto utiliza C como linguagem base (`main.c`, `shared_data.c`). O módulo de encoder deve fornecer uma interface C nativa (`encoder_pcnt.h` e `encoder_pcnt.c`) thread-safe para integração perfeita no Core 1.
* **Padrão de Testes (Python):** Testes unitários automatizados em Python (`pytest`) com suporte a modo de emulação de host (`#ifdef HOST_TEST` ou mocks).

**[CURRENT_TASK: SPEC 4 - Abstração do Encoder (PCNT - Revisada e Robustecida)]**
Nesta etapa, crie o módulo de abstração de hardware responsável por configurar e ler o encoder incremental utilizando o periférico PCNT em modo de quadratura, desonerando a CPU e tratando estouros de hardware.

**1. Requisitos da Abstração de Hardware do PCNT (`encoder_pcnt.h` / `encoder_pcnt.c`):**

* **Configuração de Quadratura X4:**
  * Inicializar a unidade PCNT (`pcnt_unit_handle_t`) e configurar dois canais (`pcnt_channel_handle_t`).
  * Parametrizar bordas de subida e descida em ambos os canais para multiplicar os 250 PPR por 4 = 1000 contagens por volta.
* **Resistores Internos de Pull-Up:**
  * Habilitar resistores de Pull-Up internos (`GPIO_PULLUP_ONLY`) nos pinos `GPIO 14` e `GPIO 15` para evitar entradas flutuantes e ruídos eletromagnéticos da ponte H.
* **Filtro Antirruído (Glitch Filter):**
  * Habilitar e configurar o `pcnt_glitch_filter_config_t` com `max_glitch_ns = 1000` ($1\mu s$) para rejeitar picos de alta frequência da chaveamento do motor CC.
* **Tratamento de Overflow de Hardware (16-bit para 32-bit Accumulator):**
  * O hardware PCNT é limitado a 16 bits assinados ($-32.768$ a $+32.767$).
  * Configurar *watch points* de evento (`PCNT_UNIT_WATCH_POINT_MAX` em $+30.000$ e `PCNT_UNIT_WATCH_POINT_MIN` em $-30.000$).
  * Registrar ISR callback (`pcnt_unit_register_event_callbacks`) para acumular estouros em um contador de software de 32 bits (`accumulated_overflows`).
  * A contagem total acumulada deve ser calculada por:
    $$\text{contagem\_total} = (\text{accumulated\_overflows} \times 30000) + \text{pcnt\_get\_count()}$$
* **Zeramento Atômico (`encoder_clear_count`):**
  * O método de zeramento deve resetar **simultaneamente e de forma atômica** (`portMUX_TYPE` spinlock) o registrador de hardware (`pcnt_unit_clear_count`) e o acumulador de software (`accumulated_overflows = 0`).
* **Suporte a Teste em Host (`HOST_TEST`):**
  * Incluir compilação condicional que permita emular injeção de contagens e estouros no PC sem dependência dos registradores físicos do ESP32 durante a execução do `pytest`.

**2. Requisitos do Teste Unitário (Python):**

* No diretório `tests/`, crie o arquivo `test_encoder_pcnt.py`.
* **Cenário de Teste 1 (Inicialização e Leitura Bruta):** Valide que a inicialização reporta contagem inicial $0$.
* **Cenário de Teste 2 (Simulação de Pulsos e Quadratura):** Simule a injeção de pulsos de quadratura e verifique o acúmulo correto de contagens.
* **Cenário de Teste 3 (Estouro do Contador 16-bit):** Simule injeção de contagens acima de $30.000$ e valide se o acumulador de software de 32 bits mantém a posição contínua sem descontinuidades ou saltos negativos.
* **Cenário de Teste 4 (Zeramento Atômico):** Injete contagens acumuladas altas e chame `encoder_clear_count()`. Afirme (*assert*) que a leitura subsequente retorna obrigatoriamente $0$.

Gere a atualização dos códigos do módulo `encoder_pcnt` e o script de teste em Python. Não altere o `main.c` nesta etapa, apenas entregue a biblioteca pronta para integração futura.