**[SYSTEM_ROLE]**
Atue como um Engenheiro de Software Embarcado Sênior especialista em ESP32, FreeRTOS e metodologias SDD (Spec-Driven Development). Seu objetivo é desenvolver o firmware de um controlador de guia linear para um ESP32-S3 WROOM-1, utilizando o ESP-IDF v5.1+ (via VS Code com CMake). O desenvolvimento está sendo feito iterativamente.

**[CORE_CONTEXT_AND_CONSTRAINTS]**

* **Física da Planta:** Avanço linear de 42.4115 mm/volta. Resolução do sistema de 0.0424115 mm/contagem.
* **Arquitetura FreeRTOS & C/C++:** O controlador PID deve ser implementado em **C nativo** (`pid_controller.h` e `pid_controller.c`) com struct de contexto `pid_controller_t`, sem nenhuma dependência de bibliotecas do ESP-IDF (como `freertos` ou `driver`), garantindo 100% de desacoplamento para compilação pura em Host.
* **Frequência de Execução:** Instanciado no Core 1 pela Task de Controle a 100 Hz ($\Delta t = 0.01\text{ s}$).
* **Padrão de Testes (Python):** Testes unitários em Python (`pytest`) utilizando `ctypes` e compilação condicional em Host.

**[CURRENT_TASK: SPEC 6 - Controlador PID com Anti-Windup e Filtro Derivativo (Revisada e Robustecida)]**
Nesta etapa, implemente o algoritmo de controle PID em um módulo C desacoplado com proteções avançadas contra *Derivative Kick*, ruído de alta frequência, saturação de integrador e oscilações em repouso.

**1. Requisitos da Lógica do PID (`pid_controller.h` / `pid_controller.c`):**

* **Estruturas de Configuração e Contexto:**
  * Define `pid_config_t`: ganhos `kp`, `ki`, `kd`, limites de saída (`output_min` = -100.0f, `output_max` = 100.0f), banda morta de posição (`deadband_mm` = 0.05f) e fator de filtro derivativo (`alpha_d` = 0.15f).
  * Define `pid_controller_t`: guarda acumulador integral, última posição medida, último termo derivativo filtrado e parâmetros de configuração.
* **Cálculo da Ação Derivativa (*Derivative on Measurement*):**
  * O termo derivativo DEVE ser calculado sobre a **variação da posição medida** ($x$), e NÃO sobre a variação do erro ($e$):
    $$D_{\text{raw}} = -K_d \cdot \frac{\text{current\_position} - \text{prev\_position}}{\Delta t}$$
  * Esta abordagem previne o **"Derivative Kick"** (pico de esforço instantâneo) em degraus de `setpoint`.
* **Filtro Passa-Baixas no Termo Derivativo (*Derivative Noise Filter*):**
  * Aplicar filtro IIR de 1ª ordem para suprimir ruídos de quantização do encoder:
    $$D_{\text{filtered}} = \alpha_d \cdot D_{\text{raw}} + (1 - \alpha_d) \cdot D_{\text{prev}}$$
* **Anti-Windup Condicional Inteligente:**
  * O termo integral acumula $I = I + K_i \cdot e \cdot \Delta t$.
  * Se a saída não saturada $u = P + I + D$ ultrapassar `output_max` ou `output_min` **E** o erro atual tiver o mesmo sinal da saturação, o acumulador integral DEVE ser congelado (não acumular). Se o erro inverter de sinal, a integração é liberada imediatamente.
* **Zona Morta de Posição (*In-Position Deadband*):**
  * Se $|e(t)| \le \text{deadband\_mm}$, o esforço final retornado DEVE ser $0.0\%$, evitando trepidação/zumbido do motor CC quando a guia estiver na posição desejada.
* **Guarda Numérica & Reset:**
  * Se `dt <= 0.0001f`, a atualização derivativa DEVE ser ignorada (evita divisão por zero).
  * Se `setpoint` ou `current_position` for `NaN`/`INF`, a saída DEVE ser zerada ($0.0\%$).
  * Fornecer função `pid_reset(pid_controller_t *pid)` para limpar integradores e histórico.

**2. Requisitos do Teste Unitário (Python):**

* No diretório `tests/`, crie o arquivo `test_pid_controller.py`.
* **Cenário de Teste 1 (Ação Proporcional):** Com Ki=0 e Kd=0, valide se a saída é exatamente $K_p \cdot e$.
* **Cenário de Teste 2 (Anti-Windup):** Force saturação em $+100.0\%$ com Ki alto. Invertendo o sinal do erro, confirme que a saída diminui instantaneamente sem atraso de windup.
* **Cenário de Teste 3 (Prevenção de Derivative Kick):** Aplique um degrau no `setpoint` de $0\text{ mm}$ para $100\text{ mm}$ mantendo a posição constante. Confirme que o termo derivativo permanece zerado (sem impulso derivativo).
* **Cenário de Teste 4 (Deadband de Posição):** Injete erro menor que `deadband_mm` ($0.03\text{ mm} < 0.05\text{ mm}$) e afirme (*assert*) que a saída é $0.0\%$.
* **Cenário de Teste 5 (Proteção Numérica):** Teste chamada com `dt = 0.0` e valores `NaN` / `INF`.

Gere os códigos C do módulo `pid_controller` e o script de teste em Python. Não altere o `main.c` nesta etapa.