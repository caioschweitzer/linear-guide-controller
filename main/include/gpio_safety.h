#ifndef GPIO_SAFETY_H
#define GPIO_SAFETY_H

#ifndef HOST_TEST
#include "esp_err.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#else
typedef int esp_err_t;
#define ESP_OK 0
#define ESP_FAIL -1
typedef void* TaskHandle_t;
#endif

#include "shared_data.h"

#ifdef __cplusplus
extern "C" {
#endif

// Set handle of control task to notify upon Emergency interrupt
void gpio_safety_set_control_task_handle(TaskHandle_t task_handle);

// Initialize GPIO 11 (Start) and GPIO 12 (Emergency ISR)
esp_err_t gpio_safety_init(void);

// Software simulation helper for automated testing (triggers Emergency flow)
void gpio_safety_trigger_emergency_software(void);

// Query if emergency state is currently active
bool gpio_safety_is_emergency_active(void);

#ifdef __cplusplus
}
#endif

#endif // GPIO_SAFETY_H
