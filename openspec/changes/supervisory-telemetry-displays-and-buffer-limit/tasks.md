## 1. Criação dos Mostradores Digitais de Telemetria

- [x] 1.1 Criar a classe de componente `DigitalDisplayCard(QFrame)` com título, valor numérico em destaque, unidade de engenharia e estilo dark moderno em `tools/supervisory/ui_main.py`.
- [x] 1.2 Montar a barra horizontal de 5 mostradores (Posição Atual, Setpoint, Erro $SP - PV$, Velocidade e Esforço PWM) no topo do painel de telemetria em `tools/supervisory/ui_main.py`.
- [x] 1.3 Conectar a atualização em tempo real dos mostradores digitais no slot `on_telemetry_updated` em `tools/supervisory/ui_main.py`.

## 2. Implementação do Limite de Pontos e Circulação dos Gráficos

- [x] 2.1 Adicionar barra de controles dos gráficos com `QSpinBox` para limite de pontos (50 a 3000, padrão 300) e botão de reset/limpeza em `tools/supervisory/ui_main.py`.
- [x] 2.2 Implementar redimensionamento dinâmico dos deques de histórico preservando a circulação contínua FIFO em `tools/supervisory/ui_main.py`.
- [x] 2.3 Garantir que o recebimento de dados de burst buffer do ensaio de malha aberta ajuste automaticamente o buffer para acomodar todas as amostras sem truncamento em `tools/supervisory/ui_main.py`.

## 3. Validação e Testes Automatizados

- [x] 3.1 Adicionar testes em `tests/test_supervisory_ui.py` para validar cálculo de erro, formatação dos cards digitais e redimensionamento dinâmico do buffer circular.
- [x] 3.2 Executar a suíte de testes com `pytest` e verificar aprovação completa.

