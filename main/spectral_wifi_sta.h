#pragma once

#include <nvs_flash.h>

#define ESP_WIFI_SSID "NETGEAR09-5G"
#define ESP_WIFI_PASS "silenthat873"
#define DEST_IP   "192.168.1.123"  // Jetson Nano IP
#define DEST_PORT 5005

static void wifi_init_sta(void)
{
    ESP_ERROR_CHECK(esp_netif_init());
    ESP_ERROR_CHECK(esp_event_loop_create_default());
    esp_netif_create_default_wifi_sta();

    wifi_init_config_t cfg = WIFI_INIT_CONFIG_DEFAULT();
    ESP_ERROR_CHECK(esp_wifi_init(&cfg));

    // Connect to an existing network instead of setting up an access point:
    ESP_ERROR_CHECK(esp_wifi_set_mode(WIFI_MODE_STA));

    // Disable power-saving mode:
    ESP_ERROR_CHECK(esp_wifi_set_ps(WIFI_PS_NONE));

    {
        wifi_config_t sta_config = {
            .sta = {
                .ssid = ESP_WIFI_SSID,
                .password = ESP_WIFI_PASS,
            },
        };
        ESP_ERROR_CHECK(esp_wifi_set_config(WIFI_IF_STA, &sta_config));
    }

    ESP_ERROR_CHECK(esp_wifi_start());

    ESP_ERROR_CHECK(esp_wifi_connect());
}
