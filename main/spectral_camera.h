#pragma once

#define IMAGE_SIZE FRAMESIZE_128X128 // FRAMESIZE_240X240 // FRAMESIZE_QVGA // FRAMESIZE_UXGA
#define IMAGE_FORMAT PIXFORMAT_JPEG // PIXFORMAT_GRAYSCALE
#define JPEG_QUALITY 63 // 24 // 12 // verbatim: 0-63, for OV series camera sensors, lower number means higher quality
#define CONTINUOUS_CAPTURE 1

#define CAM_PIN_PWDN     -1
#define CAM_PIN_RESET    -1
#define CAM_PIN_XCLK     10
#define CAM_PIN_SIOD     40
#define CAM_PIN_SIOC     39

#define CAM_PIN_Y9       48
#define CAM_PIN_Y8       11
#define CAM_PIN_Y7       12
#define CAM_PIN_Y6       14
#define CAM_PIN_Y5       16
#define CAM_PIN_Y4       18
#define CAM_PIN_Y3       17
#define CAM_PIN_Y2       15
#define CAM_PIN_VSYNC    38
#define CAM_PIN_HREF     47
#define CAM_PIN_PCLK     13

#define CAM_PIN_LED      21

#define CAM_PIN_D7 CAM_PIN_Y9
#define CAM_PIN_D6 CAM_PIN_Y8
#define CAM_PIN_D5 CAM_PIN_Y7
#define CAM_PIN_D4 CAM_PIN_Y6
#define CAM_PIN_D3 CAM_PIN_Y5
#define CAM_PIN_D2 CAM_PIN_Y4
#define CAM_PIN_D1 CAM_PIN_Y3
#define CAM_PIN_D0 CAM_PIN_Y2

static camera_config_t const camera_config = {
    .pin_pwdn = CAM_PIN_PWDN,
    .pin_reset = CAM_PIN_RESET,
    .pin_xclk = CAM_PIN_XCLK,
    .pin_sccb_sda = CAM_PIN_SIOD,
    .pin_sccb_scl = CAM_PIN_SIOC,

    .pin_d7 = CAM_PIN_D7,
    .pin_d6 = CAM_PIN_D6,
    .pin_d5 = CAM_PIN_D5,
    .pin_d4 = CAM_PIN_D4,
    .pin_d3 = CAM_PIN_D3,
    .pin_d2 = CAM_PIN_D2,
    .pin_d1 = CAM_PIN_D1,
    .pin_d0 = CAM_PIN_D0,
    .pin_vsync = CAM_PIN_VSYNC,
    .pin_href = CAM_PIN_HREF,
    .pin_pclk = CAM_PIN_PCLK,

    //XCLK 20MHz or 10MHz for OV2640 double FPS (Experimental)
    .xclk_freq_hz = 20000000,
    .ledc_timer = LEDC_TIMER_0,
    .ledc_channel = LEDC_CHANNEL_0,

    .pixel_format = IMAGE_FORMAT,
    .frame_size = IMAGE_SIZE,    //QQVGA-UXGA, For ESP32, do not use sizes above QVGA when not JPEG. The performance of the ESP32-S series has improved a lot, but JPEG mode always gives better frame rates.

    .jpeg_quality = JPEG_QUALITY, //0-63, for OV series camera sensors, lower number means higher quality
    .fb_location = CAMERA_FB_IN_PSRAM,
#if CONTINUOUS_CAPTURE
    .fb_count = 2, //When jpeg mode is used, if fb_count more than one, the driver will work in continuous mode.
    .grab_mode = CAMERA_GRAB_LATEST,
#else // CONTINUOUS_CAPTURE
    .fb_count = 1, //When jpeg mode is used, if fb_count more than one, the driver will work in continuous mode.
    .grab_mode = CAMERA_GRAB_WHEN_EMPTY,
#endif // CONTINUOUS_CAPTURE
};

static void init_camera() {
    ESP_ERROR_CHECK(esp_camera_init(&camera_config));

    sensor_t *sensor = esp_camera_sensor_get();
    // sensor->set_hmirror(sensor, 1);
    sensor->set_vflip(sensor, 1);
}
