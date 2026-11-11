## Context

O supervisório SCADA da guia linear (implementado em PyQt6 e PyQtGraph) recebe telemetria do ESP32 a 10 Hz via Modbus TCP. Atualmente, os valores instantâneos de posição, velocidade e esforço são desenhados diretamente em 3 curvas gráficas temporais, mas não possuem mostradores numéricos de leitura rápida na tela. O operador precisa aproximar os valores observando as linhas dos gráficos.
Além disso, o tamanho do buffer de pontos dos gráficos é fixo no código (`self.max_points = 300`), sem controle interativo para o usuário expandir ou reduzir a janela temporal observada e sem indicação explícita da capacidade de circulação contínua FIFO.

## Goals / Non-Goals

**Goals:**
- Criar componentes dedicados de mostradores digitais (`DigitalDisplayCard`) com tipografia de alta legibilidade, cores temáticas Catppuccin Mocha e formatação numérica com unidades de engenharia.
- Exibir em tempo real:
  - **Posição Atual ($PV$)**: em milímetros (`mm`), 2 casas decimais.
  - **Setpoint Alvo ($SP$)**: em milímetros (`mm`), 2 casas decimais.
  - **Erro de Posição ($e = SP - PV$)**: em milímetros (`mm`), com sinal e indicação de proximidade do alvo.
  - **Velocidade Linear ($v$)**: em `mm/s`, 1 casa decimal.
  - **Esforço do Motor ($u$)**: em `%` de PWM com sinal.
- Adicionar controle interativo de tamanho máximo de buffer dos gráficos (QSpinBox de 50 a 3000 pontos, padrão 300 ou 500) e botão de limpeza manual do histórico.
- Implementar circulação suave (janela deslizante FIFO) nos deques de histórico, garantindo que o gráfico role continuamente sem travamentos e adaptando a capacidade automaticamente quando o ensaio de malha aberta transferir conjuntos maiores de amostras (burst de 550 pontos).

**Non-Goals:**
- Alterar o protocolo Modbus TCP ou a taxa de polling do worker (10 Hz).
- Substituir o framework PyQtGraph.
- Alterar a lógica do firmware do ESP32.

## Decisions

### 1. Mostradores Digitais como Cards no Topo do Painel de Telemetria
- **Decisão**: Organizar os mostradores numéricos em uma barra horizontal de 5 cards diretamente acima da área de gráficos no painel direito.
- **Racional**: Agrupa toda a informação de monitoramento dinâmico em uma mesma região visual. O operador visualiza os números exatos e a tendência gráfica simultaneamente com mínimo movimento ocular.

### 2. Gerenciamento do Buffer Circular Dinâmico via `deque(maxlen=N)`
- **Decisão**: Utilizar `collections.deque(maxlen=self.max_points)` conectado a um `QSpinBox` de controle de pontos. Ao alterar o spinbox:
  ```python
  self.max_points = new_size
  self.time_history = deque(self.time_history, maxlen=new_size)
  self.setpoint_history = deque(self.setpoint_history, maxlen=new_size)
  # ... repete para posição, velocidade e duty
  ```
- **Racional**: O `deque` de Python com `maxlen` realiza a rotação circular em $O(1)$ nativamente em C, descartando automaticamente o elemento mais antigo ao receber novos dados. Preserva o histórico existente sem perda ao aumentar a capacidade.

### 3. Adaptação Automática de Escala no Ensaio de Malha Aberta
- **Decisão**: Quando o worker Modbus descarregar um pacote de burst buffer de malha aberta (ex: 550 amostras), se `len(samples) > self.max_points`, o supervisório ajusta automaticamente o spinbox de pontos para comportar todas as amostras, evitando que o início da curva seja truncado.

## Risks / Trade-offs

- **[Risk] Quedas de FPS ao definir um buffer muito grande (ex: > 3000 pontos)** → **Mitigation**: Limitar o teto do `QSpinBox` a 3000 pontos (equivalente a 5 minutos contínuos a 10 Hz), faixa em que o PyQtGraph renderiza a 60 FPS sem latência perceptível.
- **[Risk] Ruído visual por atualização rápida dos números (10 Hz)** → **Mitigation**: Formatação numérica com largura e casas decimais fixas previne trepidação dos layouts.
