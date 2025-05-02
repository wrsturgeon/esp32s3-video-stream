#pragma once

#include <nvs_flash.h>

#define ESP_WIFI_SSID "XIAO ESP32S3 Sense"
#define ESP_WIFI_PASS "" // "spectral"
#define ESP_WIFI_CHANNEL 11 // 6 // 1
#define ESP_MAX_STA_CONN 4

static void wifi_init_softap(void)
{
    // Initialize non-volatile storage to use for WiFi:
    {
        esp_err_t err = nvs_flash_init();
        switch (err) {
            case ESP_ERR_NVS_NO_FREE_PAGES:
            case ESP_ERR_NVS_NEW_VERSION_FOUND:
                ESP_ERROR_CHECK(nvs_flash_erase());
                err = nvs_flash_init();
                break;
            default:
                break;
        }
        ESP_ERROR_CHECK(err);
    }

    ESP_ERROR_CHECK(esp_netif_init());
    ESP_ERROR_CHECK(esp_event_loop_create_default());
    esp_netif_create_default_wifi_ap();

    wifi_init_config_t cfg = WIFI_INIT_CONFIG_DEFAULT();
    ESP_ERROR_CHECK(esp_wifi_init(&cfg));

    // Set up an access point instead of connecting to an existing network:
    ESP_ERROR_CHECK(esp_wifi_set_mode(WIFI_MODE_AP));

    // Disable power-saving mode:
    ESP_ERROR_CHECK(esp_wifi_set_ps(WIFI_PS_NONE));

    {
        wifi_config_t ap_config = {
            .ap = {
                .ssid = ESP_WIFI_SSID,
                .ssid_len = strlen(ESP_WIFI_SSID),
                .channel = ESP_WIFI_CHANNEL,
                .password = ESP_WIFI_PASS,
                .max_connection = ESP_MAX_STA_CONN,
                .authmode = ((strlen(ESP_WIFI_PASS) == 0) ? WIFI_AUTH_OPEN : WIFI_AUTH_WPA2_PSK),
                /*
                .pmf_cfg = {
                        .required = true,
                },
#ifdef CONFIG_ESP_WIFI_BSS_MAX_IDLE_SUPPORT
                .bss_max_idle_cfg = {
                    .period = WIFI_AP_DEFAULT_MAX_IDLE_PERIOD,
                    .protected_keep_alive = 1,
                },
#endif
                */
            },
        };
        ESP_ERROR_CHECK(esp_wifi_set_config(WIFI_IF_AP, &ap_config));
    }

    ESP_ERROR_CHECK(esp_wifi_start());

    /*
    ESP_ERROR_CHECK(esp_event_handler_instance_register(WIFI_EVENT,
                                                        ESP_EVENT_ANY_ID,
                                                        &wifi_event_handler,
                                                        NULL,
                                                        NULL));
    */

    ESP_LOGI("SPECTRAL-WIFI-AP", "wifi_init_softap finished. SSID:%s password:%s channel:%d",
             ESP_WIFI_SSID, ESP_WIFI_PASS, ESP_WIFI_CHANNEL);
}
