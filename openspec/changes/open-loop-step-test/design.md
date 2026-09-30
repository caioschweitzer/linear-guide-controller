## Context

O controlador da guia linear executa em um ESP32-S3 com FreeRTOS, contando com loop determinístico de controle a 100 Hz (Core 1) e pilha Modbus TCP sobre Ethernet WIZ550io (Core 0). Para modelar matematicamente a planta dinâmica (estimar ganho $K$, constante de tempo mecânica $\tau$ e tempo morto $\theta$ via curva de reação ao degrau), é necessário aplicar um degrau de 100% de esforço em malha aberta a partir do repouso e registrar com alta fidelidade a resposta temporal de posição e velocidade.

A aquisição direta via supervisório através de polling TCP periódico (20 Hz) é inadequada para capturar o transitório de aceleração devido a jitter de rede e baixa taxa de amostragem. Portanto, a amostragem em buffer interno na RAM a 100 Hz no ESP32 e posterior download via Modbus garante dados puros e sem ruído de rede.

## Goals / Non-Goals

**Goals:**
- Implementar o estado `MACHINE_STATE_OPEN_LOOP_TEST` (código 4) e comando Modbus `CMD_OPEN_LOOP_TEST` (código 5).
- Aplicar degrau pleno (+100.0% de esforço) até atingir metade do curso total ($212.0\text{ mm}$, metade de $424.115\text{ mm}$).
- Acionar frenagem ativa instantânea (`motor_brake`) e zerar esforço ao atingir o limiar ou por timeout de segurança (2.5 s).
- Implementar intertravamento rígido de segurança: recusar partida se $|pos| > 5.0\text{ mm}$ ou se em emergência.
- Alocar buffer estático na RAM do ESP32 para até 300 amostras a 100 Hz (3.0 segundos) registrando timestamp relativo, posição e velocidade.
- Expor registradores Modbus para verificação de status (`IDLE`, `RUNNING`, `READY`, `ABORTED`), contagem de amostras e leitura indexada dos dados.
- Implementar no supervisório PyQt6 botão de disparo, validação prévia de posição, download automático do buffer ao concluir e diálogo de exportação para CSV.

**Non-Goals:**
- Implementar algoritmos de identificação paramétrica automática (ex: Mínimos Quadrados / ARX) no firmware; o objetivo é fornecer os dados brutos e confiáveis em CSV para modelagem em MATLAB/Python.
- Ensaio bidirecional ou degrau fracionário na FSM atual (foco estrito no degrau positivo de 100% do zero ao meio do curso).

## Decisions

### 1. Execução no Loop de Controle do Core 1 (100 Hz)
- **Decisão**: A lógica do teste de malha aberta é executada diretamente na função `control_loop_task` no Core 1.
- **Racional**: Garante sincronismo perfeito a cada 10 ms ($T_s = 0.01\text{ s}$) com a leitura do encoder PCNT e filtro cinemático, sem custos adicionais de troca de contexto ou filas FreeRTOS.
- **Alternativas consideradas**: Tarefa FreeRTOS dedicada (rejeitada para evitar contenção de prioridade e jitter no acionamento do MCPWM).

### 2. Estrutura do Buffer Interno em RAM
- **Decisão**: Buffer linear estático na memória interna do ESP32-S3:
  ```c
  typedef struct {
      uint32_t time_ms;
      float position;
      float velocity;
  } open_loop_sample_t;
  #define BURST_BUFFER_MAX_SAMPLES 300
  ```
  Consumo total: $300 \times 12\text{ bytes} = 3.6\text{ KB}$, perfeitamente desprezível frente aos 512 KB de SRAM do ESP32-S3.
- **Racional**: Garante ausência de alocação dinâmica (`malloc`) em tempo de execução, evitando fragmentação de heap.

### 3. Mapeamento de Registradores Modbus para Download do Buffer
- **Decisão**: Utilizar os registradores estendidos Modbus:
  - **Holding Register `0x0009`**: `burst_sample_index` (escrito pelo mestre para selecionar o índice do ponto a ler: 0 a N-1).
  - **Input Register `0x0007`**: `burst_status` (0: IDLE, 1: RUNNING, 2: READY, 3: ABORTED).
  - **Input Register `0x0008`**: `burst_sample_count` (número total de pontos capturados, até 300).
  - **Input Register `0x0009 - 0x000A`**: `sample_time_ms` (uint32_t como 2 x uint16).
  - **Input Register `0x000B - 0x000C`**: `sample_position` (float32 como 2 x uint16).
  - **Input Register `0x000D - 0x000E`**: `sample_velocity` (float32 como 2 x uint16).
- **Racional**: Mantém total compatibilidade com o padrão Modbus TCP, sem exigir funções customizadas de protocolo.

### 4. Interface com Usuário e Exportador CSV no Supervisório
- **Decisão**:
  - No `ui_main.py`, adicionar botão "🚀 ENSAIO DE MALHA ABERTA (100%)" na seção de controle.
  - Habilitar/desabilitar visualmente com base na telemetria ($|pos| \le 5.0\text{ mm}$ e estado `IDLE`).
  - No `modbus_worker.py`, adicionar rotina `download_burst_buffer()` que percorre os índices quando `burst_status == READY`.
  - Exportar CSV com cabeçalho padrão: `time_s,position_mm,velocity_mm_s,duty_pct`.

## Risks / Trade-offs

- **[Risco] Inércia e ultrapassagem após o corte a 100% de velocidade**
  → *Mitigação*: O corte ocorre aos 212.0 mm (metade da guia). A guia possui mais de 210 mm de curso livre restante. Ao atingir o limiar, o firmware aplica frenagem eletrodinâmica imediata (`motor_brake`), parando o carro em menos de 20 mm.
- **[Risco] Falha mecânica ou travamento da guia durante o ensaio**
  → *Mitigação*: Watchdog de software por tempo limite ($2.5\text{ s}$). Se a guia não atingir 212.0 mm em 2.5 segundos, o teste é abortado com `burst_status = ABORTED` e o motor é freado.
- **[Risco] Tempo de download do buffer via Modbus**
  → *Mitigação*: Transferência em lotes/páginas rápidas ou polling acelerado pela conexão Ethernet W5500 em 5 MHz, concluindo a leitura de 200 amostras em menos de 1 segundo.
