## Why

Atualmente, o supervisório SCADA em PyQt6 exibe as variáveis dinâmicas de movimento (posição atual, setpoint de referência, velocidade e esforço PWM) apenas em gráficos temporais contínuos. O operador não possui mostradores numéricos de leitura rápida em destaque para visualizar instantaneamente as grandezas físicas sem precisar interpolar ou aproximar visualmente os eixos dos gráficos. Além disso, os gráficos utilizam um tamanho de buffer fixo sem controle de ajuste dinâmico na interface para gerenciar a janela temporal de visualização contínua (buffer circular FIFO).

Adicionar mostradores digitais destacados de telemetria e controle configurável de janela de pontos/circulação do buffer aprimora expressivamente a ergonomia de operação, a precisão na tomada de decisão em tempo real e a flexibilidade de diagnóstico.

## What Changes

- **Mostradores Digitais de Telemetria em Destaque (Digital Value Displays / KPI Cards)**:
  - Criação de um painel de mostradores numéricos destacados no topo da área de telemetria contendo:
    - **Posição Atual**: Valor numérico em `mm` com 2 casas decimais e destaque visual em verde `#A6E3A1`.
    - **Setpoint Alvo**: Valor de referência em `mm` em azul `#89B4FA`.
    - **Erro de Posição ($e = SP - PV$)**: Desvio instantâneo em `mm` com indicação de sinal e cor dinâmica (verde quando próximo de zero, amarelo/laranja em movimento).
    - **Velocidade Linear**: Velocidade instantânea filtrada em `mm/s` em âmbar `#FAB387`.
    - **Esforço do Motor**: Ciclo de trabalho efetivo em `%` com sinal em roxo `#CBA6F7`.
- **Limite Máximo de Pontos Configurável e Circulação Contínua do Gráfico**:
  - Adição de controle na interface (QSpinBox / seletor de "Buffer Gráfico") permitindo ao operador definir o limite de pontos em tempo real (ex: entre 100 e 2000 pontos, default 300 ou 500).
  - Circulação contínua e suave dos dados (buffer circular FIFO baseado em `deque(maxlen=N)`), descartando os pontos mais antigos e rolando a escala temporal automaticamente sem acúmulo infinito de memória ou engasgos na renderização.
  - Atualização dinâmica da capacidade dos deques quando o usuário altera o limite no spinbox sem resetar o histórico existente desnecessariamente.

## Capabilities

### New Capabilities
- `modbus-supervisory-ui`: Interface de supervisão com mostradores numéricos digitais para telemetria instantânea e controle dinâmico da janela temporal de buffer circular nos gráficos PyQtGraph.

### Modified Capabilities
<!-- No modified core specs -->

## Impact

- **Interface do Supervisório (`tools/supervisory/`)**:
  - `tools/supervisory/ui_main.py`: Adição dos widgets de mostradores digitais (`DigitalDisplayCard`), seletor de buffer máximo de pontos e lógica de redimensionamento dinâmico dos deques de histórico.
- **Testes Automatizados (`tests/`)**:
  - `tests/test_supervisory_ui.py`: Testes unitários para o cálculo de erro de setpoint, dimensionamento dinâmico do buffer circular e formatação dos mostradores numéricos.
