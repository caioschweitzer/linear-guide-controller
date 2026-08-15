**[SYSTEM_ROLE]**
Atue como um Engenheiro de Software Embarcado Sênior especialista em ESP32, FreeRTOS e metodologias SDD (Spec-Driven Development). Seu objetivo é desenvolver o firmware de um controlador de guia linear para um ESP32-S3 WROOM-1, utilizando o ESP-IDF v5.1+ (via VS Code com CMake). O desenvolvimento está sendo feito iterativamente.

**[CORE_CONTEXT_AND_CONSTRAINTS]**

* **Atenção Crítica de API (ESP-IDF v5.x):** Utilize o novo driver I2C Master (`driver/i2c_master.h` no target e abstração `#ifdef HOST_TEST` em testes) para controlar o expansor PCF8574 conectado ao LCD HD44780 16x2.
* **Pinagem de Hardware (IHM):**
  * Display LCD I2C (PCF8574): `GPIO 1` (SDA), `GPIO 2` (SCL), Endereço I2C `0x27`, Frequência `100 kHz`.
  * LED Indicador de Status: `GPIO 7` (Saída digital).
* **Arquitetura FreeRTOS & C Nativo:** Implemente em **C nativo** (`ihm_display.h` e `ihm_display.c`). A Task da IHM rodará no **Core 0** (compartilhado com Modbus) a uma taxa de 5 Hz (200 ms).
* **Concorrência Segura por Snapshot:** A IHM deve obter uma cópia local (snapshot) dos dados compartilhados via `shared_data_read` usando Mutex com timeout curto (< 10 ms). A transmissão I2C e a atualização do LED DEVEM ocorrer **fora** da seção crítica do Mutex para não atrasar a Task de Controle PID do Core 1.
* **Padrão de Testes (Python):** Testes unitários em Python (`pytest`) via `ctypes` compilando o módulo em C para Host.

**[CURRENT_TASK: SPEC 7 - Interface Homem-Máquina (Display I2C e LED - Revisada e Robustecida)]**
Nesta etapa, implemente o gerenciador da IHM local em C, responsável por formatar e exibir a telemetria da guia linear no LCD 16x2, controlar o LED de status via GPIO 7 e resistir a falhas físicas de I2C.

**1. Requisitos do C Nativo (IHM e Driver LCD):**

* **Módulo `ihm_display` (`ihm_display.h` / `ihm_display.c`):**
  * Define `ihm_config_t`: pinos `sda_gpio` (1), `scl_gpio` (2), `led_gpio` (7), `i2c_address` (0x27), `i2c_clk_speed` (100000Hz).
  * Define `ihm_display_t`: guarda barramento I2C, estado do LED, último tick de pisca e flag `is_connected`.
* **Driver LCD HD44780 via PCF8574 (4-bits):**
  * Implementar rotinas de envio de nibles de dados/comandos (RS, RW, EN, Backlight) via barramento I2C.
  * Inicialização do LCD em modo 4-bits: limpa tela, ativa cursor desabilitado e iluminação traseira (Backlight ON).
* **Formatação Estrita de Tela (16 Caracteres por Linha):**
  * Método de formatação `ihm_format_lines(float position_mm, float velocity_mm_s, system_state_t state, char *line1, char *line2)`:
    - **Linha 1:** Posição em mm no formato `P:%7.2f mm   ` (ex: `P: 120.45 mm   `, exatamente 16 caracteres).
    - **Linha 2:** Velocidade e Estado no formato `V:%5.1f S:%-6s` (ex: `V: 12.5 S:MOVING`, exatamente 16 caracteres).
    - Deve utilizar `snprintf` limitando a 17 bytes (16 caracteres + `\0`), impedindo estouro de buffer e desalinhar o display.
* **Gerenciamento do LED de Status (`GPIO 7`) Não-Bloqueante:**
  * `ihm_update_led(ihm_display_t *ihm, system_state_t state, uint32_t current_time_ms)`:
    - `STATE_INIT` / `STATE_IDLE`: LED Aceso Fixo (ON) ou Apagado (OFF).
    - `STATE_HOMING` / `STATE_MOVING` / `STATE_AUTO`: Pisca Lento a **1 Hz** (500 ms ON / 500 ms OFF).
    - `STATE_EMERGENCY_STOP` / `STATE_FAULT`: Pisca Rápido a **5 Hz** (100 ms ON / 100 ms OFF).
    - O controle de temporização DEVE ser feito por diferença de tempo em milissegundos (sem usar `vTaskDelay` interno).
* **Resiliência a Falhas I2C (Display Desconectado):**
  * Se a transmissão I2C retornar erro (`ESP_ERR_TIMEOUT` ou NACK), marcar `is_connected = false` e ignorar transmissões de dados pelas próximas iterações. Tentar re-inicializar o I2C a cada 5 segundos sem travar a Task.

**2. Requisitos do Teste Unitário (Python):**

* No diretório `tests/`, crie o arquivo `test_ihm_display.py`.
* **Cenário de Teste 1 (Formatação e Truncamento de LCD):** Teste a função `ihm_format_lines` com posições extremas (ex: `12345.678`, `-999.99`) e nomes de estados. Afirme (*assert*) que as duas strings retornadas possuem exatamente 16 caracteres e terminam adequadamente.
* **Cenário de Teste 2 (Máquina de Estados e Frequência do LED):** Teste a função `ihm_update_led` simulando passagem de tempo em milissegundos. Valide se em `STATE_MOVING` a alternância ocorre a cada 500 ms (1 Hz) e em `STATE_EMERGENCY_STOP` ocorre a cada 100 ms (5 Hz).

Gere os códigos C do módulo `ihm_display` e o script de teste em Python. Não altere o `main.c` nesta etapa.