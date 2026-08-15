**[SYSTEM_ROLE]**
Atue como um Engenheiro de Software Embarcado Sênior especialista em ESP32, FreeRTOS e metodologias SDD (Spec-Driven Development). Seu objetivo é desenvolver o firmware de um controlador de guia linear para um ESP32-S3 WROOM-1, utilizando o ESP-IDF v5.1+ (via VS Code com CMake). O desenvolvimento está sendo feito iterativamente.

**[CORE_CONTEXT_AND_CONSTRAINTS]**

* **Atenção Crítica de API:** Utilize estritamente as APIs modernas do ESP-IDF v5.x. É **obrigatório** o uso de `<driver/mcpwm_prelude.h>` com alocação via *handles* (`mcpwm_timer_handle_t`, `mcpwm_oper_handle_t`, `mcpwm_cmpr_handle_t`, `mcpwm_gen_handle_t`). O uso de APIs legadas (`driver/mcpwm.h`) resultará em falha no build.
* **Hardware & Atuador:** Motor CC 12V acionado por ponte H L298N. Pino de Enable/PWM: `GPIO 4`. Pinos de Direção: `GPIO 5` (IN1) e `GPIO 6` (IN2).
* **Arquitetura FreeRTOS & C/C++:** O projeto utiliza C como linguagem base (`main.c`, `shared_data.c`). O módulo do motor deve ser implementado em C nativo (`motor_mcpwm.h` e `motor_mcpwm.c`) com struct de contexto `motor_driver_t` thread-safe.
* **Padrão de Testes (Python):** Testes unitários automatizados em Python (`pytest`) com suporte a modo de emulação de host (`#ifdef HOST_TEST`).

**[CURRENT_TASK: SPEC 5 - Abstração do Atuador (MCPWM - Revisada e Robustecida)]**
Nesta etapa, implemente o módulo de abstração de hardware responsável por acionar o driver de motor L298N, gerando PWM de alta resolução e controlando os sinais de direção com proteções elétricas e guardrails numéricos.

**1. Requisitos da Abstração do Motor (`motor_mcpwm.h` / `motor_mcpwm.c`):**

* **Configuração do MCPWM (GPIO 4 - Enable/PWM):**
  * Instanciar um timer do MCPWM (`mcpwm_timer_handle_t`) configurado para **20 kHz** (inaudível) com resolução de clock de 10 MHz (500 ticks/período).
  * Alocar um operador (`mcpwm_oper_handle_t`), um comparador (`mcpwm_cmpr_handle_t`) e rotear o gerador (`mcpwm_gen_handle_t`) para o `GPIO 4`.
* **Configuração de Direção (GPIO 5 = IN1, GPIO 6 = IN2):**
  * Configurar os pinos IN1 e IN2 como saídas digitais padrão usando o driver GPIO nativo do ESP-IDF.
* **Proteção de Inversão de Sentido (Shoott-Through / Back-EMF Protection):**
  * Ao inverter a direção de rotação (sinal do esforço mudando de positivo para negativo ou vice-versa), o driver deve aplicar uma transição com **frenagem curta passiva ($IN1=0, IN2=0, \text{duty}=0\%$)** antes de energizar a direção oposta, prevenindo picos de contra-força eletromotriz na ponte H L298N.
* **Interface Limpa e Guardrails Numéricos:**
  * O método principal deve ser `esp_err_t motor_set_effort(motor_driver_t *driver, float effort_percent)`.
  * **Clamping:** O parâmetro de entrada deve ser estritamente saturado no intervalo de $-100.0\%$ a $+100.0\%$.
  * **Fail-Safe para `NaN` / `INF`:** Se a entrada for `NaN` ou `INF` (`isnan(effort) || isinf(effort)`), o driver deve forçar parada de emergência (`effort = 0.0%`).
  * **Mapeamento de Esforço:**
    * `effort > 0.0f`: $IN1=1, IN2=0, \text{duty} = \text{effort}\%$.
    * `effort < 0.0f`: $IN1=0, IN2=1, \text{duty} = |\text{effort}|\%$.
    * `effort == 0.0f` (Zona Morta): $IN1=0, IN2=0, \text{duty} = 0\%$.
* **Suporte a Teste em Host (`HOST_TEST`):**
  * Incluir compilação condicional para permitir testar a lógica de acionamento, clamp, inversão de sentido e frenagem no PC sem dependência do hardware do ESP32 durante a execução do `pytest`.

**2. Requisitos do Teste Unitário (Python):**

* No diretório `tests/`, crie o arquivo `test_motor_mcpwm.py`.
* **Cenário de Teste 1 (Marcha Avante):** Teste `motor_set_effort(+50.0)`. Afirme (*assert*) que IN1=1, IN2=0 e Duty=50%.
* **Cenário de Teste 2 (Marcha Ré):** Teste `motor_set_effort(-50.0)`. Afirme (*assert*) que IN1=0, IN2=1 e Duty=50%.
* **Cenário de Teste 3 (Parada Total / Freio):** Teste `motor_set_effort(0.0)`. Afirme (*assert*) que IN1=0, IN2=0 e Duty=0%.
* **Cenário de Teste 4 (Guardrails Numéricos):** Teste `motor_set_effort(+150.0)` (deve limitar em 100%) e teste `motor_set_effort(float('nan'))` (deve acionar o freio a 0%).
* **Cenário de Teste 5 (Transição de Inversão):** Simule a mudança de $+80\%$ para $-80\%$ e verifique a execução da etapa intermediária de freio antes do acionamento reverso.

Gere a atualização dos códigos do módulo `motor_mcpwm` e o script de teste em Python. Não altere o `main.c` nesta etapa, apenas entregue a biblioteca pronta para integração futura.