**[SYSTEM_ROLE]**
Atue como um Engenheiro de Software Embarcado Sênior especialista em ESP32, FreeRTOS e metodologias SDD (Spec-Driven Development). Seu objetivo é desenvolver o firmware de um controlador de guia linear para um ESP32-S3 WROOM-1, utilizando o ESP-IDF v5.1+ (via VS Code com CMake). O desenvolvimento está sendo feito iterativamente.

**[CORE_CONTEXT_AND_CONSTRAINTS]**

* **Física da Planta:** Avanço linear de 42.4115 mm/volta. Resolução do sistema de 0.0424115 mm/contagem.
* **Arquitetura FreeRTOS:** O módulo desenvolvido aqui será instanciado no Core 1 pela Task de Controle, rodando a uma frequência fixa (ex: 100Hz).
* **Padrão de Testes (Python):** Testes unitários/HIL em Python (`pytest`). A lógica de negócio em C++ deve ser estritamente desacoplada do hardware para suportar essa validação.

**[CURRENT_TASK: SPEC 6 - Controlador PID e Anti-Windup]**
Nesta etapa, implemente o algoritmo de controle PID em uma classe isolada. A classe não deve ter nenhuma dependência das bibliotecas do ESP-IDF (como `freertos` ou `driver`), consistindo apenas em C++ puro.

**1. Requisitos do C++ (Lógica de Negócio - PID):**

* **Classe `PIDController`:** Crie os arquivos `.h` e `.cpp` na pasta `main/`.
* **Parâmetros de Inicialização:** O construtor (ou método `init`) deve receber os ganhos `Kp`, `Ki`, `Kd`, além dos limites de saída (`output_min` e `output_max`, que para este sistema representarão o esforço do motor de -100.0 a 100.0).
* **Cálculo (Método `compute`):**
* Deve receber o `setpoint` (posição desejada em mm), `current_value` (posição atual em mm) e o `dt` (delta de tempo em segundos).
* Deve calcular o Erro, o termo Proporcional, o termo Integral (acumulando o erro no tempo) e o termo Derivativo (taxa de variação do erro).


* **Anti-Windup:** É obrigatório implementar proteção contra saturação do termo integral. Se a saída calculada atingir `output_min` ou `output_max`, o acumulador integral deve parar de crescer na direção da saturação.
* **Retorno:** O método deve retornar o sinal de controle saturado dentro dos limites operacionais.

**2. Requisitos do Teste Unitário (Python):**

* No diretório `tests/`, crie o arquivo `test_pid_controller.py`.
* **Cenário de Teste 1 (Ação Proporcional):** Zere os ganhos Ki e Kd. Injete um erro constante positivo. Valide se a saída do controlador corresponde exatamente a `Kp * erro`.
* **Cenário de Teste 2 (Anti-Windup):** Configure um ganho Ki alto. Injete um erro constante por várias iterações simuladas para forçar o limite máximo de saída (100.0). Em seguida, inverta o sinal do erro (erro negativo). O teste deve provar que a saída do controlador reage imediatamente para diminuir o esforço, confirmando que o termo integral não acumulou desnecessariamente (*windup*).

Gere a atualização da árvore de arquivos, os códigos C++ da classe `PIDController` e o script de teste em Python. Não altere o `main.cpp` nesta etapa.