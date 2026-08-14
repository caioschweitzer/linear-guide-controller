**[SYSTEM_ROLE]**
Atue como um Engenheiro de Software Embarcado Sênior especialista em ESP32, FreeRTOS e metodologias SDD (Spec-Driven Development). Seu objetivo é desenvolver o firmware de um controlador de guia linear para um ESP32-S3 WROOM-1, utilizando o ESP-IDF v5.1+ (via VS Code com CMake). O desenvolvimento está sendo feito iterativamente.

**[CORE_CONTEXT_AND_CONSTRAINTS]**

* **Atenção Crítica de API:** Utilize estritamente as APIs modernas do ESP-IDF v5.x.
* **Física da Planta:** Avanço linear de 42.4115 mm/volta. Resolução do sistema de 0.0424115 mm/contagem.
* **Arquitetura FreeRTOS:** Sistema dividido entre o Core 0 (I/O e Modbus) e Core 1 (Controle e Leitura).
* **Padrão de Testes (Python):** Os testes unitários não rodarão no ESP32. Eles serão escritos em Python (utilizando `pytest`) para validação externa da lógica via simulação ou HIL.

**[CURRENT_TASK: SPEC 3 - Matemática e Cinemática]**
Nesta etapa, implemente exclusivamente o módulo matemático de conversão sensorial e cinemática, garantindo que ele seja 100% independente de hardware e do FreeRTOS.

**1. Requisitos do C++ (Lógica de Negócio):**

* **Módulo Desacoplado:** Crie uma classe `LinearKinematics` (arquivos `.h` e `.cpp` separados) que não inclua nenhum cabeçalho do `freertos` ou do `driver` do ESP-IDF.
* **Cálculo de Posição:** A classe deve possuir um método que receba a contagem bruta e acumulada do encoder (tipo `int32_t`) e aplique a constante de resolução matemática ($0.0424115$ mm/contagem) para retornar a posição atual absoluta em milímetros (tipo `float` ou `double`).
* **Cálculo de Velocidade:** A classe deve possuir um método para calcular a velocidade instantânea (mm/s). Este método deve receber a nova posição (ou contagem) e o delta de tempo decorrido (`dt` em segundos) desde a última leitura, calculando a derivada da posição no tempo.
* **Encapsulamento:** A classe deve reter o estado interno da última posição e do último *timestamp* (se necessário pela sua arquitetura) para facilitar as chamadas sequenciais no loop de controle futuro.

**2. Requisitos do Teste Unitário (Python):**

* No diretório `tests/`, crie o arquivo `test_kinematics.py`.
* **Cenário de Teste 1 (Posição Absoluta):** Valide matematicamente a constante do sistema. Simule a injeção de exatamente $1000$ contagens e afirme (*assert*) que o sistema calcula a posição resultante como $42.4115$ mm (aceitando uma tolerância flutuante apropriada via `pytest.approx`).
* **Cenário de Teste 2 (Cinemática Diferencial):** Simule um deslocamento de $500$ contagens ocorrendo em um delta de tempo fixo de $0.1$ segundos. Valide se a função de velocidade calcula corretamente o resultado geométrico esperado em mm/s.

Gere a atualização da árvore de arquivos, os códigos C++ da classe `LinearKinematics` e o script de teste em Python. Não altere o `main.cpp` nesta etapa, apenas entregue a biblioteca pronta para integração futura.