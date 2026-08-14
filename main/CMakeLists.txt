idf_component_register(SRCS "main.c" "shared_data.c" "modbus_slave.c"
                    INCLUDE_DIRS "."
                    REQUIRES freertos espressif__esp-modbus driver log)

