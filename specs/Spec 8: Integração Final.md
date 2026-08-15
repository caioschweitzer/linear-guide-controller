**[SYSTEM_ROLE]**
Atue como um Engenheiro de Software Embarcado Sênior especialista em ESP32, FreeRTOS e metodologias SDD (Spec-Driven Development). Seu objetivo é finalizar o firmware de um controlador de guia linear para um ESP32-S3 WROOM-1, utilizando o ESP-IDF v5.1+ (via VS Code com CMake).

**[CORE_CONTEXT_AND_CONSTRAINTS]**

* **Física da Planta:** Avanço linear de $42.4115\text{ mm/volta}$. Resolução do encoder de $0.0424115\text{ mm/contagem}$ (1000 CPR). Curso útil de $[0.0\text{ mm}, 424.115\text{ mm}]$.
* **Arquitetura FreeRTOS & C Nativo:** Implemente a integração final no arquivo `main/main.c` em C nativo com a função `app_main()`.
* **Distribuição de Tasks por Cores:**
  * **Core 0:** Task Modbus RTU, `Task_IHM` (5 Hz) e leitura de botões de acionamento (`GPIO 11`).
  * **Core 1:** `Task_ControlLoop` pinada ao Core 1 rodando deterministicamente a **100 Hz** (período de $10\text{ ms}$) via `vTaskDelayUntil`.
* **Sincronização Segura:** Uso de `g_system_mutex` para leitura/escrita por snapshot da estrutura global `g_system_data` com tempo de retenção mínimo (< 1 ms).
* **Padrão de Testes (Python):** Teste de integração do sistema completo em Python (`pytest`) via `ctypes` compilando todos os módulos C em `libsystem_integration.so`.

**[CURRENT_TASK: SPEC 8 - Integração Final e Loop de Controle (Revisada e Robustecida)]**
Nesta etapa, implemente o `main/main.c` definitivo, unindo todos os módulos C desenvolvidos nas Specs 1 a 7 (`shared_data`, `gpio_safety`, `linear_kinematics`, `encoder_pcnt`, `motor_mcpwm`, `pid_controller`, `ihm_display`, `modbus_slave`). Feche a malha de controle garantindo determinismo de tempo real no Core 1.

**1. Requisitos do C Nativo (Integração em `main.c`):**

* **Inicialização dos Módulos em `app_main()`:**
  1. `shared_data_init()`: Cria mutex global `g_system_mutex` e estado inicial.
  2. `gpio_safety_init()`: Configura pino de emergência (`GPIO 12`) com ISR em IRAM para corte imediato.
  3. `kinematics_init()`: Inicializa constante de resolução ($0.0424115\text{ mm/pulse}$).
  4. `encoder_pcnt_init()`: Configura decodificador de quadratura no `GPIO 4` e `GPIO 5`.
  5. `motor_mcpwm_init()`: Configura PWM no `GPIO 15` e direção no `GPIO 16`.
  6. `pid_init()`: Inicializa ganhos do controlador PID ($K_p=2.0, K_i=0.5, K_d=0.05$).
  7. `ihm_init()`: Configura LCD I2C nos `GPIO 1` e `GPIO 2` e LED de status no `GPIO 7`.
  8. Criação das Tasks FreeRTOS (`Task_ControlLoop` no Core 1, `Task_IHM` e `Task_Modbus` no Core 0).

* **Task de Controle (Core 1 - `Task_ControlLoop`):**
  * Roda a 100 Hz ($dt = 0.01\text{ s}$) utilizando `vTaskDelayUntil(&xLastWakeTime, pdMS_TO_TICKS(10))`.
  * **Fluxo de Execução no Loop:**
    1. Obter contagem do encoder via `encoder_pcnt_get_count()`.
    2. Calcular posição (`mm`) e velocidade (`mm/s`) via `kinematics_count_to_position()`.
    3. Obter `g_system_mutex` (timeout 1 ms):
       - Verificar emergência via `gpio_safety_is_emergency_active()`.
       - Se emergência ativa, forçar estado para `MACHINE_STATE_EMERGENCY`.
       - Ler `position_setpoint` e `machine_state`.
       - Escrever `g_system_data.current_position = position_mm` e `g_system_data.current_velocity = velocity_mm_s`.
       - Liberar `g_system_mutex`.
    4. Clampar `position_setpoint` no curso seguro $[0.0\text{ mm}, 424.115\text{ mm}]$.
    5. Decidir esforço de acionamento:
       - **Se `state == MACHINE_STATE_EMERGENCY` ou emergência ativa:** Resetar PID (`pid_reset()`) e forçar dever do motor para 0.0% (`motor_mcpwm_set_duty(0.0)`).
       - **Se `state == MACHINE_STATE_MOVING`:** Calcular dever PID `duty = pid_compute(&pid, setpoint, position_mm, 0.01f)` e aplicar no motor `motor_mcpwm_set_duty(duty)`.
       - **Se `state == MACHINE_STATE_IDLE`:** Resetar PID (`pid_reset()`) e forçar dever do motor para 0.0%.

* **Task da IHM (Core 0 - `Task_IHM`):**
  * Roda a 5 Hz (período de 200 ms).
  * Obtém snapshot de `g_system_data` via Mutex e chama `ihm_update()` para atualizar LCD 16x2 e piscar o LED no `GPIO 7`.

**2. Requisitos do Teste de Integração (Python):**

* No diretório `tests/`, crie o arquivo `test_system_integration.py`.
* **Cenário de Teste 1 (Sequência de Boot do Sistema):** Confirme se a inicialização deixa o sistema em `MACHINE_STATE_IDLE` com esforço 0.0% e posição 0.0 mm.
* **Cenário de Teste 2 (Malha Fechada PID em Transição MOVING):** Transicione a máquina para `MACHINE_STATE_MOVING`, injete Setpoint de $100.0\text{ mm}$ e simule 10 iterações (100 ms virtuais), verificando a elevação proporcional do esforço do motor.
* **Cenário de Teste 3 (Interrupção e Interceptação de Emergência):** Dispare a chave de Emergência e confirme que, no ciclo imediatamente seguinte da malha de controle, o dever do motor é zerado imediatamente (0.0%), o motor é desabilitado e a memória do PID é resetada.

Gere a atualização dos arquivos C do `main/main.c`, `main/CMakeLists.txt` e o script de teste de integração em Python.