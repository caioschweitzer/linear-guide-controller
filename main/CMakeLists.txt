idf_component_register(SRCS "ihm_display.c" "pid_controller.c" "motor_mcpwm.c" "encoder_pcnt.c" "linear_kinematics.c" "gpio_safety.c" "main.c" "shared_data.c" "modbus_slave.c"
                    INCLUDE_DIRS "."
                    REQUIRES freertos espressif__esp-modbus driver esp_driver_gpio log)
