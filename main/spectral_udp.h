#pragma once

#include <esp_wifi.h>
#include <esp_netif.h>

#include <lwip/err.h>
#include <lwip/sockets.h>
#include <lwip/sys.h>
#include <lwip/netdb.h>

#define SPECTRAL_ADDR "10.0.0.255" // "192.168.4.255" // Broadcast, not multicast!
#define SPECTRAL_PORT 5005 // 12345
#define CHUNK_SIZE 1400

typedef uint16_t frame_id_t; // TODO: u8 & wrap i.e. let overflow

typedef struct __attribute__((packed)) {
    frame_id_t frame_id;     // Frame ID: same for ALL chunks
    uint16_t packet_id;      // Current chunk index
    uint16_t total_packets;  // Total number of chunks
} jpeg_chunk_header_t;

static int spectral_sock = -1;
static struct sockaddr_in spectral_addr;

static void udp_init() {
    while ((spectral_sock = socket(AF_INET, SOCK_DGRAM, IPPROTO_IP)) < 0) {
        ESP_LOGE("SPECTRAL-UDP", "Failed to create socket: %s", strerror(errno));
        vTaskDelay(pdMS_TO_TICKS(1000));
    }

    {
        int enable_broadcast = 1;
        setsockopt(spectral_sock, SOL_SOCKET, SO_BROADCAST, &enable_broadcast, sizeof(enable_broadcast));
    }

    // fcntl(udp_broadcast_sock, F_SETFL, O_NONBLOCK); // Non-blocking socket

    memset(&spectral_addr, 0, sizeof(spectral_addr));
    spectral_addr.sin_family = AF_INET;
    spectral_addr.sin_port = htons(SPECTRAL_PORT);
    spectral_addr.sin_addr.s_addr = inet_addr(SPECTRAL_ADDR);  // AP mode broadcast address
    printf("UDP broadcast socket initialized on port %d\n", SPECTRAL_PORT);
}

static int send_chunked_jpeg(camera_fb_t const *const fb) {
    static jpeg_chunk_header_t header = { .frame_id = 0 };

    header.total_packets = (fb->len + CHUNK_SIZE - 1) / CHUNK_SIZE;
    ESP_LOGD("SPECTRAL-UDP", "Sending frame ID #%i (a %i-byte JPEG) in %i %i-byte chunks", header.frame_id + 1, fb->len, header.total_packets, CHUNK_SIZE);
    if (header.total_packets == 0) {
        return 0;
    }

    int err_code = 0;
    size_t offset = 0;
    header.packet_id = 0;
    do {
        ESP_LOGD("SPECTRAL-UDP", "Sending chunk #%i/%i", header.packet_id + 1, header.total_packets);

        size_t chunk_size = fb->len - offset;
        if (chunk_size > CHUNK_SIZE) { chunk_size = CHUNK_SIZE; }

        struct iovec iov[2] = {
            { .iov_base = &header, .iov_len = sizeof(header) },
            { .iov_base = (void *)(fb->buf + offset), .iov_len = chunk_size }
        };

        struct msghdr const msg = {
            .msg_name = &spectral_addr,
            .msg_namelen = sizeof(spectral_addr),
            .msg_iov = iov,
            .msg_iovlen = 2,
            .msg_control = NULL,
            .msg_controllen = 0,
            .msg_flags = 0
        };

        if (sendmsg(spectral_sock, &msg, 0) < 0) {
            if (errno == 12) {
                err_code = -1;
            } else {
                // Otherwise, UDP is inherently lossy, so
                // don't return an error (which would decrease the frame rate):
                ESP_LOGW("SPECTRAL-UDP", "sendmsg failed on chunk %u/%u with errno %i: %s", header.packet_id + 1, header.total_packets, errno, strerror(errno));
            }
            break; // Drop the rest of this frame
        }

        offset += CHUNK_SIZE;
    } while (++(header.packet_id) < header.total_packets);

    ++header.frame_id;

    return err_code;
}
