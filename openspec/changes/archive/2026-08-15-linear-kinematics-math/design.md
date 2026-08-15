## Context

O controlador de guia linear executa a leitura da posição bruta do encoder no Core 1 do ESP32-S3. Para transformar essa leitura bruta em unidades físicas úteis para a máquina de estados e o controlador PID, é necessário um módulo cinemático desacoplado de hardware. O código da aplicação principal é escrito em C (`main.c`, `shared_data.c`), exigindo que a API do módulo cinemático forneça compatibilidade nativa C (`linear_kinematics.h` e `linear_kinematics.c`).

## Goals / Non-Goals

**Goals:**
- Prover um módulo desacoplado de hardware (`linear_kinematics.h`/`.c`) sem cabeçalhos do FreeRTOS ou ESP-IDF.
- Calcular posição linear em milímetros com constante de conversão $0.0424115$ mm/contagem.
- Calcular velocidade instantânea e filtrada (mm/s) com filtro passa-baixas EMA ($\alpha = 0.2$).
- Prover *guardrails* numéricos contra divisões por zero ($dt \le 0.0001$ s) e picos no 1º ciclo (`is_initialized`).
- Permitir calibração dinâmica (`zero_offset` e `direction`).
- Fornecer funções de conversão para registradores Modbus em ponto fixo.
- Criar suíte de testes unitários automatizados em Python (`tests/test_kinematics.py`).

**Non-Goals:**
- Não interagir diretamente com drivers de hardware PCNT ou GPIO (escopo da Spec 4).
- Não alterar a tarefa principal do FreeRTOS `main.c` nesta etapa.

## Decisions

### Decisão 1: Implementação em C Nativo com Struct de Estado (`kinematics_t`)
- **Escolha**: Criar `linear_kinematics.h`/`.c` em C puro utilizando uma estrutura de estado `kinematics_t`.
- **Alternativa Considerada**: Criar classe C++ `LinearKinematics` com wrapper `extern "C"`.
- **Razão**: Como o projeto é construído em C (`main.c`, `shared_data.c`), a implementação em C puro simplifica a compilação no ESP-IDF CMake sem sobrecarga de ligação C++.

### Decisão 2: Filtro Passa-Baixas EMA para Velocidade
- **Escolha**: Média Móvel Exponencial (EMA) $v_{\text{filt}} = \alpha \cdot v_{\text{inst}} + (1 - \alpha) \cdot v_{\text{prev}}$ com $\alpha \in (0, 1.0]$.
- **Alternativa Considerada**: Média móvel com buffer circular de $N$ amostras.
- **Razão**: O filtro EMA requer uso de memória constante $O(1)$ e tempo computacional mínimo $O(1)$, ideal para malha rápida de controle no ESP32-S3.

### Decisão 3: Guardrail de $dt$ e Prevenção de Spike
- **Escolha**: Se $dt \le 0.0001$ s, a derivada não é computada e retorna-se a velocidade anterior. Se `!is_initialized`, velocidade inicial é $0.0$.
- **Alternativa Considerada**: Retornar $0.0$ em caso de $dt \le 0$.
- **Razão**: Manter a velocidade anterior durante pequenas variações de tick evita descontinuidades bruscas na entrada do controlador PID.

## Risks / Trade-offs

- **[Precisão Single-Precision Float]** → A FPU do ESP32-S3 opera em `float32`. Para deslocamentos extremamente longos (ex: $> 100.000$ contagens), a multiplicação por `float` mantém precisão dentro de $0.001$ mm, adequada para a guia linear.
- **[Atraso de Fase do Filtro EMA]** → Valores pequenos de $\alpha$ (ex: $< 0.05$) filtram ruído mas introduzem atraso de fase na velocidade. O valor padrão de $\alpha = 0.2$ equilibra filtragem e tempo de resposta.
