#include <esp_log.h>
#include <esp_system.h>
#include <nvs_flash.h>
#include <sys/param.h>
#include <string.h>

#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

// support IDF 5.x
#ifndef portTICK_RATE_MS
#define portTICK_RATE_MS portTICK_PERIOD_MS
#endif

#include "esp_camera.h"
#include "esp_mac.h"
#include "esp_wifi.h"

#include "spectral_camera.h"
#include "spectral_wifi_ap.h"

void app_main(void)
{
    // Initialize NVS for WiFi:
    {
        esp_err_t ret = nvs_flash_init();
        if (ret == ESP_ERR_NVS_NO_FREE_PAGES || ret == ESP_ERR_NVS_NEW_VERSION_FOUND) {
          ESP_ERROR_CHECK(nvs_flash_erase());
          ret = nvs_flash_init();
        }
        ESP_ERROR_CHECK(ret);
    }

    // Initialize WiFi access point:
    ESP_LOGI(TAG, "ESP_WIFI_MODE_AP");
    wifi_init_softap();

    // Initialize camera:
    ESP_ERROR_CHECK(esp_camera_init(&camera_config));

    // Main loop:
    do {
        ESP_LOGI(TAG, "Taking picture...");
        camera_fb_t *pic = esp_camera_fb_get();

        // use pic->buf to access the image
        ESP_LOGI(TAG, "Picture taken! Its size was: %zu bytes", pic->len);
        esp_camera_fb_return(pic);

        // vTaskDelay(5000 / portTICK_RATE_MS);
    } while (1);
}
