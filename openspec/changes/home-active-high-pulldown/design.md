## Context

O controlador de guia linear utiliza o pino `GPIO 16` (`GPIO_HOME_PIN`) para detectar a posição mecânica de referência (*datum / zero absoluto*). Na especificação anterior, o pino foi configurado com resistor de *pull-up* interno assumindo um sensor NF (*Normally Closed*) ou lógica Active-LOW.

Entretanto, o sensor instalado fisicamente na bancada é do tipo **Active-HIGH** (sensor NA / saída PNP ou push-pull com acionamento em 3.3V / nível ALTO). Consequentemente, na ausência de acionamento mecânico, o sinal de entrada permanece em 0V (nível BAIXO), e quando o batente mecânico atinge o sensor, ele vai para 3.3V (nível ALTO).

## Goals / Non-Goals

**Goals:**
- Configurar o pino `GPIO 16` no subsistema de segurança com resistor de **pull-down interno habilitado** (`pull_down_en = GPIO_PULLDOWN_ENABLE`) e pull-up desabilitado (`pull_up_en = GPIO_PULLUP_DISABLE`).
- Atualizar o algoritmo de parada da máquina de estados no loop de controle (`MACHINE_STATE_HOMING` em `main/src/main.c`) para detectar o batente quando `gpio_get_level(GPIO_HOME_PIN) != 0` (Active-HIGH).
- Garantir coerência na telemetria Modbus (registrador de Discrete Inputs Bit 3 = 1 quando acionado/HIGH).
- Atualizar diagramas de hardware e esquemáticos em `docs/02_hardware_and_schematics.md`.
- Validar a compilação do firmware e a suíte de testes automatizados (`pytest`).

**Non-Goals:**
- Alterar a lógica do botão de emergência (`GPIO 12`), que permanece estritamente Active-LOW com pull-up e interrupção IRAM por requisitos de segurança intrínseca (*fail-safe* para botões NF).
- Modificar a velocidade de aproximação de homing (`-15.0%` de esforço).

## Decisions

### 1. Configuração do Resistor Interno
- **Decisão**: Utilizar `pull_down_en = GPIO_PULLDOWN_ENABLE` e `pull_up_en = GPIO_PULLUP_DISABLE` na estrutura `gpio_config_t` de `main/src/gpio_safety.c`.
- **Alternativa Considerada**: Deixar o pino flutuante sem resistores internos (dependendo de resistor externo). Rejeitada porque se o sensor for do tipo contato seco aberto para VCC, o pino flutuaria em alta impedância, gerando falsos disparos. O pull-down interno do ESP32 (~45 kΩ) garante nível estável 0V em repouso.

### 2. Condição Lógica de Gatilho no Loop de Controle
- **Decisão**: Avaliar `if (gpio_get_level(GPIO_HOME_PIN) != 0)` em `main/src/main.c`.
- **Alternativa Considerada**: `== 1`. A comparação `!= 0` é preferida como boa prática de programação em C para valores booleanos provenientes de drivers ESP-IDF.

### 3. Mapeamento de Registradores Modbus
- **Decisão**: O registrador de Discrete Inputs Bit 3 (`1 << 3`) em `modbus_slave.c` já avalia `if (gpio_get_level(GPIO_HOME_PIN) != 0) discrete_bits |= (1 << 3);`. Com o sensor Active-HIGH, esse mapeamento torna-se 100% direto: bit 3 = 1 significa sensor fisicamente acionado (3.3V).

## Risks / Trade-offs

- **[Ruído Elétrico em Linha de Fim de Curso]** → A amostragem é realizada no ciclo da `control_loop_task` (100 Hz / período de 10 ms), funcionando naturalmente como um filtro anti-repique digital (qualquer pulso espúrio de sub-milissegundo não sustenta o acionamento). Além disso, a velocidade de homing é reduzida (-15%), garantindo frenagem suave e segura.
