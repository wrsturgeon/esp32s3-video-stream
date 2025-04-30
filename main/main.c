#include <esp_log.h>
#include <esp_system.h>
#include <nvs_flash.h>
#include <sys/param.h>
#include <string.h>

#include <freertos/FreeRTOS.h>
#include <freertos/task.h>

#define FRAME_STATISTICS 1

// support IDF 5.x
#ifndef portTICK_RATE_MS
#define portTICK_RATE_MS portTICK_PERIOD_MS
#endif

#include <esp_camera.h>
#include <esp_mac.h>
#include <esp_wifi.h>

#include "spectral_camera.h"
#include "spectral_udp.h"
#include "spectral_wifi_ap.h"

static char const *const TAG = "main:video_stream";

void app_main(void) {
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

    float frame_period_ms = 20.0;

    // Main loop (restarts with each UDP connection):
    do {
        int sock;

        sock = create_multicast_socket();
        if (sock < 0) {
            ESP_LOGE(TAG, "Failed to create IPv4 multicast socket");
        }

        if (sock < 0) {
            // Nothing to do!
            vTaskDelay(pdMS_TO_TICKS(5));
            continue;
        }

#if FRAME_STATISTICS
        uint8_t frame_success_circular_buffer[256] = { 0 };
        uint8_t frame_success_index = 0;
#endif // FRAME_STATISTICS

        // Main loop (restarts with each camera frame):
        TickType_t last_iter_start_time = xTaskGetTickCount();
        do {
            ESP_LOGI(TAG, "Taking picture...");
            camera_fb_t *const pic = esp_camera_fb_get();
            if (pic) {
                int const err = send_chunked_jpeg(sock, pic);
                esp_camera_fb_return(pic);
                uint8_t const successfully_transmitted = (err >= 0);
#if FRAME_STATISTICS
                frame_success_circular_buffer[frame_success_index] = successfully_transmitted;
#endif // FRAME_STATISTICS
                frame_period_ms *= (successfully_transmitted ? 0.999 : 1.01);
                if (frame_period_ms < 20.0) {
                    frame_period_ms = 20.0;
                }
                /*
                if (!successfully_transmitted) {
                    vTaskDelayUntil(&last_iter_start_time, pdMS_TO_TICKS((uint8_t)frame_period_ms));
                }
                */
            }

#if FRAME_STATISTICS
            {
                uint16_t sum = 0;
                uint8_t i = 0;
                do {
                    sum += frame_success_circular_buffer[i];
                } while (++i);
                ESP_LOGI(TAG, "Frame transmission success rate: %i/256 (%f%%)", sum, sum / 2.56);
                ESP_LOGI(TAG, "Frame rate: %ffps", 1000.0 / frame_period_ms);
            }
            ++frame_success_index;
#endif // FRAME_STATISTICS

            TickType_t frame_period_ticks = pdMS_TO_TICKS((uint8_t)frame_period_ms);
            if (xTaskGetTickCount() > last_iter_start_time + frame_period_ticks) {
                ESP_LOGW(TAG, "Frame rate faster than camera frame acquisition. Slowing down...");
                frame_period_ms *= 1.01;
            }

            // Wait for the next cycle.
            vTaskDelayUntil(&last_iter_start_time, frame_period_ticks);
        } while (1);

        ESP_LOGE(TAG, "Shutting down socket and restarting...");
        shutdown(sock, 0);
        close(sock);
    } while (1);
}
