**[SYSTEM_ROLE]**
Atue como um Engenheiro de Software Embarcado Sênior especialista em ESP32, FreeRTOS e metodologias SDD (Spec-Driven Development). Seu objetivo é desenvolver o firmware de um controlador de guia linear para um ESP32-S3 WROOM-1, utilizando o ESP-IDF v5.1+ (via VS Code com CMake). O desenvolvimento está sendo feito iterativamente.

**[CORE_CONTEXT_AND_CONSTRAINTS]**

* **Atenção Crítica de API:** Utilize estritamente as APIs modernas do ESP-IDF v5.x. Para o barramento I2C, utilize o driver atualizado (ex: `driver/i2c_master.h` se aplicável na versão, ou a API padrão `driver/i2c.h` garantindo compatibilidade com v5).
* **Hardware (IHM):** Display LCD 16x2 via interface I2C (módulo PCF8574). Pinos: `GPIO 1` (SDA) e `GPIO 2` (SCL). LED indicador de status no `GPIO 7`.
* **Arquitetura FreeRTOS:** O módulo desenvolvido aqui rodará no Core 0 (junto com o Modbus). Ele deve ler a estrutura de dados global compartilhada (criada na Spec 1) utilizando *Mutex* de forma não bloqueante ou com timeout mínimo, para não travar o barramento I2C caso o Core 1 esteja acessando os dados.
* **Padrão de Testes (Python):** Testes unitários em Python (`pytest`). A lógica de formatação do display deve ser isolada para permitir testes de software independentes de hardware.

**[CURRENT_TASK: SPEC 7 - Interface Homem-Máquina (Display I2C e LED)]**
Nesta etapa, implemente o gerenciador da IHM local, responsável por exibir os dados de telemetria da guia linear e sinalizar visualmente o estado de operação da máquina.

**1. Requisitos do C++ (IHM e I2C):**

* **Classe `DisplayIHM`:** Crie os arquivos `.h` e `.cpp` na pasta `main/`.
* **Gerenciamento do Display:** Configure o barramento I2C como Master e implemente (ou importe via componente) um driver básico para o LCD HD44780 via expansor PCF8574.
* **Formatação de Tela:**
* A classe deve possuir um método de atualização (ex: `update_screen(float position, float velocity, SystemState state)`).
* **Linha 1:** Deve mostrar a posição (ex: `P: 120.45 mm`).
* **Linha 2:** Deve mostrar a velocidade e/ou o status de forma compactada, garantindo que nunca ultrapasse os 16 caracteres.


* **Gerenciamento do LED (GPIO 7):**
* Integre a lógica do LED vinculada à Máquina de Estados (Spec 2).
* `IDLE`: LED apagado ou acesso fixo.
* `MOVING`: Piscar em baixa frequência (ex: 1 Hz).
* `EMERGENCY`: Piscar rapidamente (ex: 5 Hz ou padrão SOS).



**2. Requisitos do Teste Unitário (Python):**

* No diretório `tests/`, crie o arquivo `test_ihm_display.py`.
* **Cenário de Teste 1 (Formatação de String):** Como não teremos o LCD físico no teste unitário nativo, valide a função puramente em software. Injete valores extremos de posição (ex: `1234.56789`) e confirme se a classe/módulo formata e trunca a *string* corretamente para evitar *overflow* de buffer (> 16 caracteres) na linha do LCD.
* **Cenário de Teste 2 (Lógica de Pisca do LED):** Teste a função ou máquina de estados responsável pelo *timing* do LED. Injete o estado `EMERGENCY` e simule a passagem de tempo, validando se a alternância de estado (ON/OFF) do pino do LED ocorre no intervalo esperado de alta frequência.

Gere a atualização da árvore de arquivos, os códigos C++ da classe da IHM (e driver LCD se necessário) e o script de teste em Python. Não altere o `main.cpp` nesta etapa.