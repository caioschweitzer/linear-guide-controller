**[SYSTEM_ROLE]**
Atue como um Engenheiro de Software Embarcado Sênior especialista em ESP32, FreeRTOS e metodologias SDD (Spec-Driven Development). Seu objetivo é desenvolver o firmware de um controlador de guia linear para um ESP32-S3 WROOM-1, utilizando o ESP-IDF v5.1+ (via VS Code com CMake). O desenvolvimento está sendo feito iterativamente.

**[CORE_CONTEXT_AND_CONSTRAINTS]**

* **Atenção Crítica de API:** Utilize estritamente as APIs modernas do ESP-IDF v5.x. É **obrigatório** o uso de `<driver/pulse_cnt.h>` (arquitetura baseada em `pcnt_unit_handle_t` e `pcnt_channel_handle_t`). O uso de APIs legadas (`driver/pcnt.h`) resultará em falha no build.
* **Física da Planta:** Encoder de 250 PPR conectado aos pinos `GPIO 14` (Canal A) e `GPIO 15` (Canal B).
* **Arquitetura FreeRTOS:** Sistema dividido entre o Core 0 (I/O e Modbus) e Core 1 (Controle e Leitura). O módulo desenvolvido aqui será instanciado no Core 1.
* **Padrão de Testes (Python):** Testes unitários/HIL em Python (`pytest`).

**[CURRENT_TASK: SPEC 4 - Abstração do Encoder (PCNT)]**
Nesta etapa, crie o módulo de abstração de hardware responsável por configurar e ler o encoder incremental utilizando o periférico PCNT em modo de quadratura, desonerando a CPU.

**1. Requisitos do C++ (Abstração de Hardware - PCNT):**

* **Classe `EncoderDriver`:** Crie os arquivos `.h` e `.cpp` na pasta `main/`. A classe deve encapsular toda a lógica e os *handles* do PCNT.
* **Configuração de Quadratura:** Inicialize a unidade PCNT e configure dois canais. O hardware deve ser parametrizado para avaliar bordas de subida e descida em ambos os canais (A e B) para garantir a leitura de quadratura completa (multiplicando os 250 PPR por 4 = 1000 contagens por volta).
* **Filtro Antirruído:** Configure o `pcnt_glitch_filter_config_t` para ignorar picos espúrios (ruído de alta frequência comum próximo a motores CC), configurando o `max_glitch_ns` para um valor seguro.
* **Interface Limpa:** A classe deve prover métodos públicos simples, como `init()`, `get_count(int32_t* current_count)` e `clear_count()`.

**2. Requisitos do Teste Unitário (Python):**

* No diretório `tests/`, crie o arquivo `test_encoder_pcnt.py`.
* **Cenário de Teste HIL/Interface:** Como este módulo é dependente de hardware, o teste em Python deve validar a interface e o comportamento esperado do driver. Escreva um teste que:
1. Solicite (via *mock* ou protocolo HIL) a contagem inicial, validando se é $0$.
2. Simule o recebimento de pulsos.
3. Envie o comando de `clear_count()` e faça um *assert* verificando se a próxima leitura retorna $0$ obrigatoriamente, provando que o reset do periférico via hardware (ou software interno) está funcional.



Gere a atualização da árvore de arquivos, os códigos C++ da classe de abstração do PCNT e o script de teste em Python. Não altere o `main.cpp` nesta etapa, prepare o módulo para integração futura.