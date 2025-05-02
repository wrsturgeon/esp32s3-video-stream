#pragma once

#include <nvs_flash.h>

#define ESP_WIFI_SSID "NETGEAR09" // "NETGEAR09-5G"
#define ESP_WIFI_PASS "silenthat873"
// #define DEST_IP   "192.168.1.123"  // Jetson Nano IP
// #define DEST_PORT 5005

static esp_netif_t *s_sta_netif = NULL;

// Forward declaration:
static void wifi_sta_disconnect(void);

static void handler_on_wifi_connect(void *arg, esp_event_base_t event_base,
                               int32_t event_id, void *event_data) {
    ESP_LOGI("SPECTRAL-WIFI-STA", "WiFi connected!");
}

static void handler_on_wifi_disconnect(void *arg, esp_event_base_t event_base,
                               int32_t event_id, void *event_data) {
    wifi_sta_disconnect();

    wifi_event_sta_disconnected_t *disconn = event_data;
    if (disconn->reason == WIFI_REASON_ROAMING) {
        ESP_LOGI("SPECTRAL-WIFI-STA", "station roaming, do nothing");
        return;
    }

    ESP_LOGI("SPECTRAL-WIFI-STA", "Wi-Fi disconnected (%d). Trying to reconnect...", disconn->reason);
    esp_err_t err = esp_wifi_connect();
    if (err == ESP_ERR_WIFI_NOT_STARTED) {
        ESP_LOGI("SPECTRAL-WIFI-STA", "INTERNAL ERROR: WiFi has not been started.");
        return;
    }
    ESP_ERROR_CHECK(err);
}

static void handler_on_sta_got_ip(void *arg, esp_event_base_t event_base,
                               int32_t event_id, void *event_data) {
    ESP_LOGI("SPECTRAL-WIFI-STA", "WiFi station got an IP!");

    ip_event_got_ip_t *event = (ip_event_got_ip_t *)event_data;
    ESP_LOGI("SPECTRAL-WIFI-STA", "WiFi station IP: " IPSTR, IP2STR(&event->ip_info.ip));
}

static void wifi_sta_disconnect(void) {
    ESP_ERROR_CHECK(esp_event_handler_unregister(WIFI_EVENT, WIFI_EVENT_STA_DISCONNECTED, &handler_on_wifi_disconnect));
    ESP_ERROR_CHECK(esp_event_handler_unregister(IP_EVENT, IP_EVENT_STA_GOT_IP, &handler_on_sta_got_ip));
    ESP_ERROR_CHECK(esp_event_handler_unregister(WIFI_EVENT, WIFI_EVENT_STA_CONNECTED, &handler_on_wifi_connect));
    ESP_ERROR_CHECK(esp_wifi_disconnect());
}

static void wifi_sta_connect(void) {
    ESP_ERROR_CHECK(esp_event_handler_register(WIFI_EVENT, WIFI_EVENT_STA_DISCONNECTED, &handler_on_wifi_disconnect, NULL));
    ESP_ERROR_CHECK(esp_event_handler_register(IP_EVENT, IP_EVENT_STA_GOT_IP, &handler_on_sta_got_ip, NULL));
    ESP_ERROR_CHECK(esp_event_handler_register(WIFI_EVENT, WIFI_EVENT_STA_CONNECTED, &handler_on_wifi_connect, s_sta_netif));

    wifi_config_t wifi_config = {
        .sta = {
            .ssid = ESP_WIFI_SSID,
            .password = ESP_WIFI_PASS,
            .scan_method = WIFI_ALL_CHANNEL_SCAN, // WIFI_FAST_SCAN,
            .sort_method = WIFI_CONNECT_AP_BY_SIGNAL, // WIFI_CONNECT_AP_BY_SECURITY,
            .threshold.rssi = 0, // or set higher
            .threshold.authmode = WIFI_AUTH_WPA2_PSK,
        },
    };

    ESP_LOGI("SPECTRAL-WIFI-STA", "Connecting to `%s`...", wifi_config.sta.ssid);
    ESP_ERROR_CHECK(esp_wifi_set_config(WIFI_IF_STA, &wifi_config));
    do {
        esp_err_t ret = esp_wifi_connect();
        if (ret == ESP_OK) {
            break;
        } else {
            ESP_LOGE("SPECTRAL-WIFI-STA", "WiFi connect failed! ret:%x", ret);
        }
    } while (1);
    ESP_LOGI("SPECTRAL-WIFI-STA", "Waiting for IP(s)");
}

static void wifi_start(void) {
    wifi_init_config_t cfg = WIFI_INIT_CONFIG_DEFAULT();
    ESP_ERROR_CHECK(esp_wifi_init(&cfg));

    esp_netif_inherent_config_t esp_netif_config = ESP_NETIF_INHERENT_DEFAULT_WIFI_STA();
    // Warning: the interface desc is used in tests to capture actual connection details (IP, gw, mask)
    esp_netif_config.if_desc = "spectral_netif_sta";
    esp_netif_config.route_prio = 128;
    s_sta_netif = esp_netif_create_wifi(WIFI_IF_STA, &esp_netif_config);
    esp_wifi_set_default_wifi_sta_handlers();

    ESP_ERROR_CHECK(esp_wifi_set_storage(WIFI_STORAGE_RAM));
    ESP_ERROR_CHECK(esp_wifi_set_mode(WIFI_MODE_STA));
    ESP_ERROR_CHECK(esp_wifi_start());
}

static void wifi_init_sta(void) {
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

    /*
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
    */

    wifi_start();

    wifi_sta_connect();
}
