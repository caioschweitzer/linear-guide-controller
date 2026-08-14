idf_component_register(SRCS "gpio_safety.c" "main.c" "shared_data.c" "modbus_slave.c"
                    INCLUDE_DIRS "."
                    REQUIRES freertos espressif__esp-modbus driver esp_driver_gpio log)
