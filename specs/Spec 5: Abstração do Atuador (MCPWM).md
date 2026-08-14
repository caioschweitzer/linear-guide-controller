**[SYSTEM_ROLE]**
Atue como um Engenheiro de Software Embarcado Sênior especialista em ESP32, FreeRTOS e metodologias SDD (Spec-Driven Development). Seu objetivo é desenvolver o firmware de um controlador de guia linear para um ESP32-S3 WROOM-1, utilizando o ESP-IDF v5.1+ (via VS Code com CMake). O desenvolvimento está sendo feito iterativamente.

**[CORE_CONTEXT_AND_CONSTRAINTS]**

* **Atenção Crítica de API:** Utilize estritamente as APIs modernas do ESP-IDF v5.x. É **obrigatório** o uso de `<driver/mcpwm_prelude.h>` com alocação via *handles* (`mcpwm_timer_handle_t`, `mcpwm_oper_handle_t`, `mcpwm_cmpr_handle_t`, `mcpwm_gen_handle_t`). O uso de APIs legadas resultará em falha no build.
* **Hardware (Atuador):** Motor CC 12V acionado por driver L298N. Pino de Enable/PWM: `GPIO 4`. Pinos de Direção: `GPIO 5` (IN1) e `GPIO 6` (IN2).
* **Arquitetura FreeRTOS:** O módulo desenvolvido aqui será instanciado no Core 1 pela Task de Controle.
* **Padrão de Testes (Python):** Testes unitários/HIL em Python (`pytest`).

**[CURRENT_TASK: SPEC 5 - Abstração do Atuador (MCPWM)]**
Nesta etapa, implemente o módulo de abstração de hardware responsável por acionar o driver de motor L298N, gerando PWM de alta resolução e controlando os sinais de direção.

**1. Requisitos do C++ (Abstração de Hardware - Motor L298N):**

* **Classe `MotorDriver`:** Crie os arquivos `.h` e `.cpp` na pasta `main/`.
* **Configuração do MCPWM (GPIO 4):**
* Instancie um timer do MCPWM com uma frequência adequada para o motor (ex: 15 kHz ou 20 kHz para evitar ruído audível).
* Aloque um operador, conecte ao timer, crie um comparador e roteie um gerador para o `GPIO 4`.


* **Configuração de Direção (GPIO 5 e 6):**
* Configure os pinos IN1 e IN2 como saídas digitais padrão usando o driver GPIO nativo do ESP-IDF.


* **Interface Limpa:**
* O método principal deve ser `set_effort(float effort_percent)`.
* O parâmetro de entrada deve variar de $-100.0$ a $100.0$.
* A lógica interna deve traduzir o sinal: valores positivos definem IN1=1/IN2=0, valores negativos definem IN1=0/IN2=1. O valor absoluto da porcentagem deve atualizar o comparador do MCPWM para definir o *duty cycle*.
* Implemente uma zona morta (*deadband*) em $0.0$ para frear o motor (IN1=0, IN2=0, duty=0).



**2. Requisitos do Teste Unitário (Python):**

* No diretório `tests/`, crie o arquivo `test_motor_mcpwm.py`.
* **Cenário de Teste 1 (Sentido Reverso):** Escreva um teste que simule a chamada de `set_effort(-50.0)`. Afirme (*assert*) que os estados lógicos resultantes de direção representam a marcha à ré e que o valor do *duty cycle* subjacente foi atualizado para 50%.
* **Cenário de Teste 2 (Parada Total):** Simule a chamada de `set_effort(0.0)`. Valide se o sinal de PWM cai imediatamente para 0% e se ambos os pinos de direção entram em estado de repouso ou frenagem, garantindo que não há vazamento de tensão para o L298N.

Gere a atualização da árvore de arquivos, os códigos C++ da classe `MotorDriver` e o script de teste em Python. Não altere o `main.cpp` nesta etapa.