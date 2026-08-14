**[SYSTEM_ROLE]**
Atue como um Engenheiro de Software Embarcado Sênior especialista em ESP32, FreeRTOS e metodologias SDD (Spec-Driven Development). Seu objetivo é desenvolver o firmware de um controlador de guia linear para um ESP32-S3 WROOM-1, utilizando o ESP-IDF v5.1+ (via VS Code com CMake). O desenvolvimento será feito iterativamente.

**[CORE_CONTEXT_AND_CONSTRAINTS]**

* **Atenção Crítica de API:** Utilize estritamente as APIs modernas do ESP-IDF v5.x (ex: `esp_modbus` / `freertos`).
* **Física da Planta:** Avanço linear de 42.4115 mm/volta. Resolução do sistema de 0.0424115 mm/contagem.
* **Arquitetura FreeRTOS:** Sistema dividido entre o Core 0 (I/O e Modbus) e Core 1 (Controle e Leitura).
* **Padrão de Testes (Python):** Os testes unitários não rodarão no ESP32. Eles serão escritos em Python (utilizando `pytest` e `pymodbus`) para validação externa (HIL - Hardware-in-the-Loop via Serial). A lógica em C++ deve ser estruturada para suportar essa abordagem.

**[CURRENT_TASK: SPEC 1 - Kernel FreeRTOS e Modbus RTU]**
Nesta etapa inicial, estabeleça a fundação do firmware criando o gerenciamento do FreeRTOS e a comunicação Modbus RTU Slave. Não implemente a lógica de controle PID, PCNT ou MCPWM ainda.

**1. Requisitos do C++ (Kernel e Modbus):**

* **Estrutura de Dados Compartilhada (IPC):**
  * Crie uma `struct` (ex: `SystemData`) ou classe *Singleton* protegida por um *Mutex* do FreeRTOS (`SemaphoreHandle_t`) para garantir *thread-safety* entre os cores.
  * Atributos com inicialização padrão:
    * `float position_setpoint = 0.0f` (mm)
    * `float current_position = 0.0f` (mm)
    * `float current_velocity = 0.0f` (mm/s)
    * `uint16_t machine_state = 0` (0: `IDLE`, 1: `MOVING`, 2: `EMERGENCY`)

* **Configuração da Serial e Modbus RTU Slave (Core 0):**
  * **Periférico UART:** `UART_NUM_0` (acessível diretamente pelo único cabo USB-C plugado na porta UART/COM da placa ESP32-S3, utilizando os pinos padrões de console `GPIO 43` TX e `GPIO 44` RX / conversor USB-Serial da placa).
  * **Configuração da Porta Serial:** 115200 bps, 8 bits de dados, sem paridade (8N1), 1 stop bit. Slave ID: `1`.
  * **Gerenciamento de Logs:** Desativar a saída de logs legíveis por texto na UART0 (`esp_log_level_set("*", ESP_LOG_NONE)`) para evitar contaminação do tráfego binário Modbus RTU.
  * **Modbus Stack:** Utilizar a biblioteca `esp_modbus` do ESP-IDF v5.x.
  * **Sincronização com IPC:** A Task Modbus deve sincronizar periodicamente os buffers de registradores com a estrutura IPC global utilizando o *Mutex* para garantir que a gravação/leitura ocorra sem *race conditions*.

* **Mapa de Registradores Modbus RTU:**
  * **Holding Registers (Leitura/Escrita):**
    * `0x0000 - 0x0001`: *Setpoint de Posição* (`float` IEEE 754 de 32 bits, ordenação Big-Endian / ABCD. Reg `0x0000`: MSW, Reg `0x0001`: LSW).
  * **Input Registers (Somente Leitura):**
    * `0x0000 - 0x0001`: *Posição Atual* (`float` IEEE 754 de 32 bits, Big-Endian / ABCD). Inicializa em `0.0`.
    * `0x0002 - 0x0003`: *Velocidade Atual* (`float` IEEE 754 de 32 bits, Big-Endian / ABCD). Inicializa em `0.0`.
    * `0x0004`: *Estado da Máquina* (`uint16_t`, 0 = `IDLE`, 1 = `MOVING`, 2 = `EMERGENCY`). Inicializa em `0`.

* **Task Placeholder (Core 1):**
  * Crie uma Task pinada ao Core 1 rodando em um loop periódico com `vTaskDelay` (ou `vTaskDelayUntil`) a 100Hz (período de 10ms), que servirá de esqueleto para o futuro loop de controle PID.

* **Organização dos Arquivos:**
  * Estruture os arquivos `.h` e `.cpp` apropriadamente na pasta `main/` (ex: `main.cpp`, `shared_data.h`, `modbus_slave.h`, `modbus_slave.cpp`) e configure o `main/CMakeLists.txt` incluindo as dependências (`freertos`, `esp_modbus`, `driver`).

**2. Requisitos do Teste Unitário (Python):**

* Crie o diretório `tests/` na raiz do projeto e o arquivo `test_modbus_kernel.py`.
* **Cenário de Teste:**
  1. Conectar via `pymodbus` à porta serial configurada (parâmetros: 115200 baud, 8N1, Slave ID 1).
  2. Escrever um valor de teste de *Setpoint* de posição (ex: `150.5` mm) no Holding Register `0x0000` utilizando payload float IEEE 754 Big-Endian.
  3. Ler o Holding Register `0x0000` de volta e verificar se o valor lido é idêntico ao valor escrito (tolerância float `1e-3`).
  4. Ler os Input Registers `0x0000` (Posição) e `0x0004` (Status) e validar se retornam os valores iniciais mockados (`0.0` mm e `0` / `IDLE`).

Gere a árvore de arquivos, o código em C++ e o script de teste em Python para esta Spec. Aguarde minhas instruções para a Spec 2.