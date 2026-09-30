## 1. GPIO Configuration & Pull-Down

- [x] 1.1 Em `main/src/gpio_safety.c`, configurar `io_conf_home` com `pull_up_en = GPIO_PULLUP_DISABLE` e `pull_down_en = GPIO_PULLDOWN_ENABLE` no pino `GPIO_HOME_PIN` (GPIO 16).

## 2. Homing Control Loop Logic

- [x] 2.1 Em `main/src/main.c`, atualizar a condição de disparo em `MACHINE_STATE_HOMING` para detectar acionamento em Active-HIGH (`gpio_get_level(GPIO_HOME_PIN) != 0`).

## 3. Documentation & Schematics

- [x] 3.1 Atualizar `docs/02_hardware_and_schematics.md` e tabelas de pinagem para documentar o sensor Home como Active-HIGH com resistor de pull-down interno.

## 4. Verification & Testing

- [x] 4.1 Executar a suíte de testes com `pytest` e validar regressões.
- [x] 4.2 Compilar o firmware ESP-IDF com `idf.py build`.
