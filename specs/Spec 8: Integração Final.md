**[SYSTEM_ROLE]**
Atue como um Engenheiro de Software Embarcado Sênior especialista em ESP32, FreeRTOS e metodologias SDD (Spec-Driven Development). Seu objetivo é finalizar o firmware de um controlador de guia linear para um ESP32-S3 WROOM-1, utilizando o ESP-IDF v5.1+ (via VS Code com CMake).

**[CORE_CONTEXT_AND_CONSTRAINTS]**

* **Física da Planta:** Avanço linear de 42.4115 mm/volta. Resolução do sistema de 0.0424115 mm/contagem.
* **Arquitetura FreeRTOS:** Core 0 dedicado à IHM, Modbus e leitura de botões. Core 1 dedicado exclusivamente ao loop de controle crítico.
* **Sincronização:** É estritamente obrigatório o uso de `SemaphoreHandle_t` (Mutex) para ler ou escrever na estrutura de dados global compartilhada entre as Tasks dos diferentes Cores.

**[CURRENT_TASK: SPEC 8 - Integração Final e Loop de Controle]**
Nesta etapa, implemente o `main.cpp` definitivo, unindo todos os módulos desenvolvidos nas Specs 1 a 7. Feche a malha de controle garantindo o determinismo do tempo real no Core 1.

**1. Requisitos do C++ (Integração no `main.cpp`):**

* **Instanciação e Inicialização:** Inicialize os módulos `MotorDriver`, `EncoderDriver`, `LinearKinematics`, `PIDController`, `DisplayIHM` e a Task do `Modbus`. Conecte as interrupções (ISR de Emergência).
* **Task de Controle (Core 1):**
* Implemente a `Task_ControlLoop` pinada ao Core 1.
* Utilize a função `vTaskDelayUntil` (ou `xTaskDelayUntil` dependendo da versão do FreeRTOS no IDF) para garantir que o loop rode em uma frequência absoluta e invariável de 100 Hz (período de 10 ms).
* **Fluxo de Execução no Loop:**
1. Leia a contagem atual do `EncoderDriver`.
2. Calcule a posição e velocidade em milímetros via `LinearKinematics`.
3. Obtenha o *Mutex*, leia o estado atual da máquina (`IDLE`, `MOVING`, `EMERGENCY`) e o *Setpoint* enviado pelo Modbus, e, no mesmo bloco crítico, escreva a nova posição e velocidade para que o Core 0 possa exibi-las. Libere o *Mutex*.
4. Se o estado for `MOVING`, alimente o `PIDController` com a posição atual e o *Setpoint*. Aplique o esforço resultante no `MotorDriver`.
5. Se o estado for `IDLE` ou `EMERGENCY`, force o `MotorDriver` para 0.0 (parada imediata).





**2. Requisitos do Teste Unitário/Integração (Python):**

* No diretório `tests/`, crie o arquivo `test_system_integration.py`.
* **Cenário de Teste de Integração (Mock Loop):** Crie um teste que simule um ciclo de vida completo do sistema. Via chamadas de software (assumindo que a arquitetura permita injeção de dependência ou execução nativa das classes combinadas):
1. Verifique se o sistema inicia parado.
2. Injete o comando de Start (transição para `MOVING`).
3. Altere o *Setpoint* e simule 10 ciclos de execução (100 ms virtuais), verificando se a saída do Motor aumenta de forma coerente.
4. Acione a interrupção de Emergência e valide se, no ciclo imediatamente seguinte, a saída do Motor cai para zero, mesmo que haja erro no PID.



Gere a atualização da árvore de arquivos final, o código C++ do `main.cpp` integrado e o script de teste de integração em Python. Certifique-se de que os arquivos `CMakeLists.txt` incluam todos os diretórios e dependências necessários para o build final.