idf_component_register(SRCS "src/ihm_display.c" "src/pid_controller.c" "src/motor_mcpwm.c" "src/encoder_pcnt.c" "src/linear_kinematics.c" "src/gpio_safety.c" "src/main.c" "src/shared_data.c" "src/modbus_slave.c"
                    INCLUDE_DIRS "include"
                    REQUIRES freertos espressif__esp-modbus espressif__w5500 driver esp_driver_gpio esp_driver_mcpwm esp_driver_pcnt esp_driver_i2c esp_eth esp_netif esp_event log)


