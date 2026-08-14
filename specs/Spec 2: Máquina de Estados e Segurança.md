**[SYSTEM_ROLE]**
Atue como um Engenheiro de Software Embarcado Sênior especialista em ESP32, FreeRTOS e metodologias SDD (Spec-Driven Development). Seu objetivo é desenvolver o firmware de um controlador de guia linear para um ESP32-S3 WROOM-1, utilizando o ESP-IDF v5.1+ (via VS Code com CMake). O desenvolvimento está sendo feito iterativamente.

**[CORE_CONTEXT_AND_CONSTRAINTS]**

* **Atenção Crítica de API:** Utilize estritamente as APIs modernas do ESP-IDF v5.x / v6.x.
* **Física da Planta:** Avanço linear de 42.4115 mm/volta. Resolução do sistema de 0.0424115 mm/contagem.
* **Arquitetura FreeRTOS:** Sistema dividido entre o Core 0 (I/O e Modbus) e Core 1 (Controle e Leitura).
* **Padrão de Testes (Python):** Os testes unitários não rodarão no ESP32. Eles serão escritos em Python (utilizando `pytest`) para validação externa via Modbus RTU. A lógica em C/C++ deve ser estruturada para suportar essa abordagem.

**[CURRENT_TASK: SPEC 2 - Máquina de Estados e Segurança (I/O)]**
Nesta etapa, implemente o gerenciamento de estados do sistema e a lógica de segurança, garantindo que o botão de emergência tenha atuação imediata sobre o hardware e o firmware.

**1. Requisitos do Firmware C/C++ (Máquina de Estados, ISR e Segurança):**

* **Definição de Estados & Acesso Thread-Safe:**
  * Crie o enum `machine_state_t` contendo obrigatoriamente: `IDLE` (0: Parado/Pronto), `MOVING` (1: Em operação) e `EMERGENCY` (2: Falha/Parada de Emergência).
  * O estado global deve suportar atualizações seguras a partir da ISR sem o uso de Mutexes (evitando panic por chamada ilegal de mutex em ISR).

* **Configuração de Entradas (GPIO):**
  * Configure o `GPIO 11` (Botão Start) com *pull-up* interno e lógica de *debounce* por software na Task do Core 0.
  * Configure o `GPIO 12` (Botão Emergência) como interrupção de hardware (ISR) acionada por borda de descida (lógica invertida segura com *pull-up*).

* **Tratamento de Emergência (ISR e Corte Físico):**
  * A ISR do GPIO 12 deve possuir a flag `ESP_INTR_FLAG_IRAM` para rodar da IRAM com latência mínima.
  * **Atuação Física Imediata:** A ISR deve cortar imediatamente a saída física do motor (desabilitar PWM/driver) antes de qualquer agendamento de software.
  * **Atualização de Estado:** Alterar atomicamente o estado global da máquina para `EMERGENCY`.
  * **Notificação de Task:** Utilizar `vTaskNotifyGiveFromISR` (com `portYIELD_FROM_ISR`) para acordar instantaneamente a Task de Controle no Core 1.

* **Regras Estritas de Transição e Reset:**
  * **IDLE -> MOVING:** Requer comando de Start E validação de que o pino de emergência está desacionado (`gpio_get_level(GPIO_12) == HIGH`).
  * **EMERGENCY -> IDLE (Reset):** O sistema só transiciona para `IDLE` se receber um comando explícito de *Reset* **E** o nível físico do pino de emergência estiver seguro (`gpio_get_level(GPIO_12) == HIGH`). Se o botão de emergência ainda estiver pressionado, o pedido de Reset é rejeitado.
  * **Qualquer Estado -> EMERGENCY:** Acionado instantaneamente por borda de descida no GPIO 12 ou por comando Modbus de Emergência.

* **Integração Modbus (Registrador de Comando):**
  * Adicionar Holding Register de Comando (`0x0001`) para permitir controle via Modbus: `1` = START, `2` = STOP, `3` = RESET, `99` = E-STOP SIMULADO.

**2. Requisitos dos Testes de Integração em Python (pytest):**

* No diretório `tests/`, crie o arquivo `test_state_machine.py`.
* **Cenário de Teste 1 (Fluxo Normal):** Valide via `pytest` se o sistema inicia em `IDLE`, aceita o comando de Start via Modbus/simulação, e transiciona corretamente para `MOVING`.
* **Cenário de Teste 2 (Bloqueio de Emergência & Rejeição de Transição):** Simule o acionamento da emergência (mudança de estado para `EMERGENCY`) e tente forçar a máquina para `MOVING`. O teste deve confirmar que a transição é **rejeitada** e a máquina permanece em `EMERGENCY`.
* **Cenário de Teste 3 (Validação de Reset Seguro):** Teste o envio do comando de *Reset*, confirmando retorno a `IDLE` apenas quando a condição de emergência estiver sanada.

Gere a especificação atualizada e pronta para ser proposta como uma nova alteração OpenSpec.