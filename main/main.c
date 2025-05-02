#include <esp_log.h>
#include <esp_system.h>
#include <sys/param.h>
#include <string.h>

#include <freertos/FreeRTOS.h>
#include <freertos/task.h>

#define FRAME_STATISTICS 0
#define FRAME_RATE_PRINT_PERIOD_MS 1000
#define FRAME_RATE_PERIOD_MS_MIN 50.0
#define FRAME_RATE_PERIOD_MS_MAX 1000.0

// #define SLIGHTLY_LOWER 0.995
// #define SLIGHTLY_HIGHER 1.04614593844
#define SLIGHTLY_LOWER 0.99
#define SLIGHTLY_HIGHER 1.09467008177

// support IDF 5.x
#ifndef portTICK_RATE_MS
#define portTICK_RATE_MS portTICK_PERIOD_MS
#endif

#include <esp_camera.h>
#include <esp_mac.h>
#include <esp_wifi.h>

#include "spectral_camera.h"
#include "spectral_udp.h"
// #include "spectral_wifi_ap.h"
#include "spectral_wifi_sta.h"

static char const *const TAG = "SPECTRAL-MAIN";

void app_main(void) {
    /*
    // Initialize WiFi access point:
    wifi_init_softap();
    */

    // Initialize WiFi station:
    wifi_init_sta();

    // Initialize camera:
    init_camera();

    // Initialize UDP comms:
    udp_init();

    float frame_period_ms = 50.0;

#if FRAME_STATISTICS
    uint8_t frame_success_circular_buffer[256] = { 0 };
    uint8_t frame_success_index = 0;
#endif // FRAME_STATISTICS

    // Main loop (restarts with each camera frame):
    TickType_t last_iter_start_time = xTaskGetTickCount();
    TickType_t last_frame_rate_print = 0;
    do {

        ESP_LOGD(TAG, "Capturing a frame...");
        camera_fb_t *const fb = esp_camera_fb_get();
        if (!fb) { continue; }

        int const err = send_chunked_jpeg(fb);
        esp_camera_fb_return(fb);
        uint8_t const successfully_transmitted = (err >= 0);
        frame_period_ms *= (successfully_transmitted ? SLIGHTLY_LOWER : SLIGHTLY_HIGHER);
        if (frame_period_ms < FRAME_RATE_PERIOD_MS_MIN) {
            frame_period_ms = FRAME_RATE_PERIOD_MS_MIN;
        }
        if (frame_period_ms > FRAME_RATE_PERIOD_MS_MAX) {
            frame_period_ms = FRAME_RATE_PERIOD_MS_MAX;
        }

#if FRAME_STATISTICS
        frame_success_circular_buffer[++frame_success_index] = successfully_transmitted;
#endif // FRAME_STATISTICS

        TickType_t now = xTaskGetTickCount();
        if (last_frame_rate_print < now) {
            last_frame_rate_print += pdMS_TO_TICKS(FRAME_RATE_PRINT_PERIOD_MS);

#if FRAME_STATISTICS
            {
                uint16_t sum = 0;
                uint8_t i = 0;
                do {
                    sum += frame_success_circular_buffer[i];
                } while (++i);
                ESP_LOGI(TAG, "Frame transmission success rate: %i/256 (%f%%)", sum, sum / 2.56);
            }
#endif // FRAME_STATISTICS

            if (frame_period_ms > 0.1) {
                ESP_LOGI(TAG, "Frame rate: %.1ffps", 1000.0 / frame_period_ms);
            } else {
                ESP_LOGW(TAG, "Frame rate: [absurdly high or invalid]");
            }
        }

        TickType_t frame_period_ticks = pdMS_TO_TICKS((uint8_t)frame_period_ms);
        if (now > last_iter_start_time + frame_period_ticks) {
            ESP_LOGD(TAG, "Frame rate faster than camera frame acquisition. Slowing down...");
            frame_period_ms *= SLIGHTLY_HIGHER;
            last_iter_start_time = now;
        } else {
            // Wait for the next cycle.
            vTaskDelayUntil(&last_iter_start_time, frame_period_ticks);
        }
    } while (1);
}
