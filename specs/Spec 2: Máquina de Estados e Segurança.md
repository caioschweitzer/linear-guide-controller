**[SYSTEM_ROLE]**
Atue como um Engenheiro de Software Embarcado Sênior especialista em ESP32, FreeRTOS e metodologias SDD (Spec-Driven Development). Seu objetivo é desenvolver o firmware de um controlador de guia linear para um ESP32-S3 WROOM-1, utilizando o ESP-IDF v5.1+ (via VS Code com CMake). O desenvolvimento está sendo feito iterativamente.

**[CORE_CONTEXT_AND_CONSTRAINTS]**

* **Atenção Crítica de API:** Utilize estritamente as APIs modernas do ESP-IDF v5.x.
* **Física da Planta:** Avanço linear de 42.4115 mm/volta. Resolução do sistema de 0.0424115 mm/contagem.
* **Arquitetura FreeRTOS:** Sistema dividido entre o Core 0 (I/O e Modbus) e Core 1 (Controle e Leitura).
* **Padrão de Testes (Python):** Os testes unitários não rodarão no ESP32. Eles serão escritos em Python (utilizando `pytest`) para validação externa. A lógica em C++ deve ser estruturada para suportar essa abordagem.

**[CURRENT_TASK: SPEC 2 - Máquina de Estados e Segurança (I/O)]**
Nesta etapa, implemente o gerenciamento de estados do sistema e a lógica de segurança, garantindo que o botão de emergência tenha atuação imediata sobre o firmware.

**1. Requisitos do C++ (Máquina de Estados e ISR):**

* **Definição de Estados:** Crie um `enum` ou classe de Máquina de Estados contendo obrigatoriamente os estados: `IDLE` (Parado/Pronto), `MOVING` (Em operação) e `EMERGENCY` (Falha/Parada de Emergência). Atualize a estrutura global de IPC (criada na Spec 1) para armazenar este estado.
* **Configuração de Entradas:**
* Configure o `GPIO 11` (Botão Start) com *pull-up* interno e lógica de *debounce* por software na Task do Core 0.
* Configure o `GPIO 12` (Botão Emergência) como uma interrupção de hardware (ISR) acionada por borda de descida (assumindo lógica invertida segura com *pull-up*).


* **Tratamento de Emergência (ISR):** A ISR deve possuir a flag `ESP_INTR_FLAG_IRAM` para rodar diretamente da RAM, garantindo latência mínima. Quando acionada, a ISR deve:
1. Alterar o estado global da máquina para `EMERGENCY`.
2. Utilizar `vTaskNotifyGiveFromISR` (ou mecanismo similar seguro para interrupções) para alertar imediatamente a Task de Controle no Core 1.


* **Regra de Transição:** O sistema só pode transicionar de `IDLE` para `MOVING` se receber o comando de Start. Se estiver em `EMERGENCY`, é estritamente proibido transicionar para `MOVING` sem antes passar por um procedimento de *Reset* para `IDLE`.

**2. Requisitos do Teste Unitário (Python):**

* No diretório `tests/`, crie o arquivo `test_state_machine.py`.
* **Cenário de Teste 1 (Fluxo Normal):** Valide via `pytest` se o sistema inicia em `IDLE` e transiciona corretamente para `MOVING` ao receber um comando de Start simulado.
* **Cenário de Teste 2 (Interrupção de Segurança):** Simule o acionamento da emergência (mudança de estado) e tente forçar a máquina de volta para `MOVING`. O teste deve passar se a máquina *recusar* a transição e permanecer bloqueada em `EMERGENCY` até que o comando explícito de *Reset* seja enviado.

Gere a atualização da árvore de arquivos, os novos códigos em C++ (cabeçalhos e implementações) e o script de teste em Python para esta Spec. Integre as chamadas no `main.cpp` preservando a estrutura da Spec 1.