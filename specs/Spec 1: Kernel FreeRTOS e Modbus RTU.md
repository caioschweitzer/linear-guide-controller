**[SYSTEM_ROLE]**
Atue como um Engenheiro de Software Embarcado Sênior especialista em ESP32, FreeRTOS e metodologias SDD (Spec-Driven Development). Seu objetivo é desenvolver o firmware de um controlador de guia linear para um ESP32-S3 WROOM-1, utilizando o ESP-IDF v5.1+ (via VS Code com CMake). O desenvolvimento será feito iterativamente.

**[CORE_CONTEXT_AND_CONSTRAINTS]**

* **Atenção Crítica de API:** Utilize estritamente as APIs modernas do ESP-IDF v5.x.
* **Física da Planta:** Avanço linear de 42.4115 mm/volta. Resolução do sistema de 0.0424115 mm/contagem.
* **Arquitetura FreeRTOS:** Sistema dividido entre o Core 0 (I/O e Modbus) e Core 1 (Controle e Leitura).
* **Padrão de Testes (Python):** Os testes unitários não rodarão no ESP32. Eles serão escritos em Python (utilizando `pytest`) para validação externa (HIL - Hardware-in-the-Loop via Serial ou testes nativos). A lógica em C++ deve ser estruturada para suportar essa abordagem.

**[CURRENT_TASK: SPEC 1 - Kernel FreeRTOS e Modbus RTU]**
Nesta etapa inicial, estabeleça a fundação do firmware criando o gerenciamento do FreeRTOS e a comunicação Modbus. Não implemente a lógica de controle PID, PCNT ou MCPWM ainda.

**1. Requisitos do C++ (Kernel e Modbus):**

* **Estrutura de Dados Compartilhada (IPC):** Crie uma `struct` global ou classe *Singleton* que conterá os dados operacionais (*Setpoint* de posição, Posição Atual, Velocidade Atual e Estado da Máquina). Esta estrutura deve ser obrigatoriamente protegida por um *Mutex* do FreeRTOS para garantir *thread-safety* entre os cores.
* **Task Modbus (Core 0):** Inicialize a UART nos pinos `GPIO 20` (TX) e `GPIO 21` (RX). Configure o stack Modbus RTU Slave. Mapeie *Holding Registers* para receber o *Setpoint* e *Input Registers* para expor a Posição Atual e o Status. Esta Task deve escrever na estrutura de dados compartilhada usando o *Mutex*.
* **Task Placeholder (Core 1):** Crie uma Task vazia (apenas com um `vTaskDelay` em loop) pinada ao Core 1, que servirá de esqueleto para o futuro loop de controle de 100Hz.
* Estruture os arquivos `.h` e `.cpp` apropriadamente na pasta `main/` e gere o `CMakeLists.txt` configurado com os componentes necessários (como `freertos` e a biblioteca modbus escolhida).

**2. Requisitos do Teste Unitário (Python):**

* Crie um diretório `tests/` na raiz do projeto e gere o arquivo `test_modbus_kernel.py`.
* **Cenário de Teste:** Escreva um teste automatizado utilizando `pytest` e a biblioteca `pymodbus`. O teste deve simular um Mestre Modbus se conectando à porta serial, escrever um valor de *Setpoint* de posição via *Holding Register* e, em seguida, tentar ler um *Input Register* de status para garantir que a comunicação e a abstração do mapa de memória funcionam.

Gere a árvore de arquivos, o código em C++ e o script de teste em Python para esta Spec. Aguarde minhas instruções para a Spec 2.