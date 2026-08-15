**[SYSTEM_ROLE]**
Atue como um Engenheiro de Software Embarcado Sênior especialista em ESP32, FreeRTOS e metodologias SDD (Spec-Driven Development). Seu objetivo é desenvolver o firmware de um controlador de guia linear para um ESP32-S3 WROOM-1, utilizando o ESP-IDF v5.1+ (via VS Code com CMake). O desenvolvimento está sendo feito iterativamente.

**[CORE_CONTEXT_AND_CONSTRAINTS]**

* **Atenção Crítica de API:** Utilize estritamente as APIs modernas do ESP-IDF v5.x.
* **Física da Planta:** Avanço linear de 42.4115 mm/volta. Resolução do sistema de 0.0424115 mm/contagem (1000 contagens/volta).
* **Arquitetura FreeRTOS & C/C++:** O projeto utiliza C como linguagem base (`main.c`, `shared_data.c`). O módulo de cinemática deve fornecer compatibilidade direta com C (`extern "C"` ou API C pura) para integração perfeita no loop de controle do Core 1.
* **Padrão de Testes (Python):** Os testes unitários não rodarão no ESP32. Eles serão escritos em Python (utilizando `pytest`) para validação externa da lógica matemática e comportamental via simulação.

**[CURRENT_TASK: SPEC 3 - Matemática e Cinemática (Revisada e Robustecida)]**
Nesta etapa, implemente o módulo matemático de conversão sensorial e cinemática, garantindo que ele seja 100% independente de hardware e do FreeRTOS.

**1. Requisitos do Módulo Cinemático (`linear_kinematics.h` / `linear_kinematics.c` ou `LinearKinematics` C++ com wrapper C):**

* **Desacoplamento de Hardware:** Não inclua nenhum cabeçalho do `freertos` ou do `driver` do ESP-IDF.
* **Calibração e Estado Interno:**
  * Suportar `zero_offset` (contagem acumulada de referência para homing/zeramento) e `direction` ($\pm 1$).
  * Manter o estado interno da última posição, última velocidade calculada, e flag de inicialização `is_initialized` para evitar surtos de velocidade (*spikes*) no 1º ciclo de cálculo.
* **Cálculo de Posição Absoluta (mm):**
  * Receber a contagem acumulada do encoder (`int32_t`).
  * Aplicar a fórmula calibrada: 
    $$\text{posição (mm)} = (\text{contagem} - \text{zero\_offset}) \times \text{direção} \times 0.0424115\text{ f}$$
* **Cálculo de Velocidade Instantânea e Filtrada (mm/s):**
  * Receber a nova posição em mm (ou contagem) e o delta de tempo decorrido ($dt$ em segundos).
  * **Proteção Contra Divisão por Zero ($dt$ Guardrail):** Se $dt \le 0.0001\text{ s}$, o cálculo de derivada deve ser ignorado e a última velocidade válida deve ser mantida, prevenindo retornos `NaN` ou `+INF`.
  * **Tratamento do 1º Ciclo:** No primeiro cálculo de velocidade após a inicialização ou reset (`!is_initialized`), definir velocidade instântanea como $0.0\text{ mm/s}$ e atualizar a posição anterior.
  * **Filtro Passa-Baixas (EMA):** Suportar filtragem de Média Móvel Exponencial da velocidade derivada:
    $$v_{\text{filtrada}} = \alpha \cdot v_{\text{inst}} + (1 - \alpha) \cdot v_{\text{anterior}}$$
    onde $\alpha$ (fator de suavização, $0 < \alpha \le 1.0$) pode ser configurado (padrão $\alpha = 0.2$).
* **Serialização e Mapeamento Modbus:**
  * Fornecer funções utilitárias para converter `float` de posição/velocidade para inteiros de ponto fixo (ex: milímetros $\times 100$ em `int16_t` / `int32_t`) prontos para escrita nos registradores da `shared_data.h`.

**2. Requisitos do Teste Unitário (Python):**

* No diretório `tests/`, crie o arquivo `test_kinematics.py`.
* **Cenário de Teste 1 (Posição Absoluta e Calibração):** Valide $1000$ contagens $= 42.4115\text{ mm}$ (via `pytest.approx`). Valide também o comportamento com `zero_offset = 100` e inversão de sentido (`direction = -1`).
* **Cenário de Teste 2 (Proteção contra $dt \le 0$ e Prevenção de Spike):** Simule injeção de posição inicial alta ($10.000$ contagens) e confirme que a velocidade inicial no 1º ciclo é $0.0\text{ mm/s}$. Simule chamadas com $dt = 0.0\text{ s}$ e afirme que não retorna `NaN` ou `INF`.
* **Cenário de Teste 3 (Cinemática Diferencial e Filtro EMA):** Simule deslocamento constante de $500$ contagens a cada $0.1\text{ s}$ e verifique a convergência da velocidade filtrada para o valor teórico em mm/s.
* **Cenário de Teste 4 (Conversão de Escala Modbus):** Valide a conversão de ponto flutuante para registradores de ponto fixo.

Gere a atualização dos códigos do módulo `linear_kinematics` e o script de teste em Python. Não altere o `main.c` nesta etapa, apenas entregue a biblioteca pronta para integração futura.