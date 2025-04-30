#pragma once

#include <esp_wifi.h>
#include <esp_netif.h>

#include <lwip/err.h>
#include <lwip/sockets.h>
#include <lwip/sys.h>
#include <lwip/netdb.h>

#define NETIF_DESC_STA "example_netif_sta"
#define MULTICAST_ADDR "239.1.2.3" // "232.10.11.12"
#define MULTICAST_PORT 12345
#define CHUNK_SIZE 1024

typedef uint16_t frame_id_t; // TODO: u8 & wrap i.e. let overflow

typedef struct __attribute__((packed)) {
    frame_id_t frame_id;     // Frame ID: same for ALL chunks
    uint16_t packet_id;      // Current chunk index
    uint16_t total_packets;  // Total number of chunks
} jpeg_chunk_header_t;

static int create_multicast_socket() {
    int sock = socket(AF_INET, SOCK_DGRAM, IPPROTO_IP);
    if (sock < 0) {
        ESP_LOGE("SPECTRAL-UDP", "Failed to create socket: %s", strerror(errno));
        return -1;
    }

    // Set TTL for multicast packets
    uint8_t ttl = 1; // Stay within local network
    if (setsockopt(sock, IPPROTO_IP, IP_MULTICAST_TTL, &ttl, sizeof(ttl)) < 0) {
        ESP_LOGE("SPECTRAL-UDP", "Failed to set TTL: %s", strerror(errno));
        close(sock);
        return -1;
    }

    return sock;
}

static int send_chunked_jpeg(int const sock, camera_fb_t const *const pic) {
    static jpeg_chunk_header_t header = { .frame_id = 0 };

    struct sockaddr_in dest_addr = {
        .sin_family = AF_INET,
        .sin_port = htons(MULTICAST_PORT),
    };
    inet_pton(AF_INET, MULTICAST_ADDR, &dest_addr.sin_addr);

    header.total_packets = (pic->len + CHUNK_SIZE - 1) / CHUNK_SIZE;
    ESP_LOGI("UDP", "Sending frame ID #%i (a %i-byte JPEG) in %i %i-byte chunks", header.frame_id, pic->len, header.total_packets, CHUNK_SIZE);

    int err_code = 0;
    size_t offset = 0;
    for (uint16_t packet_id = 0; packet_id < header.total_packets; ++packet_id) {
        header.packet_id = packet_id;
        // ESP_LOGI("UDP", "Sending chunk #%i/%i", packet_id, header.total_packets);

        size_t copy_len = pic->len - offset;
        if (copy_len > CHUNK_SIZE) { copy_len = CHUNK_SIZE; }

        struct iovec iov[2] = {
            { .iov_base = &header, .iov_len = sizeof(header) },
            { .iov_base = (void *)(pic->buf + offset), .iov_len = copy_len }
        };

        struct msghdr const msg = {
            .msg_name = &dest_addr,
            .msg_namelen = sizeof(dest_addr),
            .msg_iov = iov,
            .msg_iovlen = 2,
        };

        ssize_t sent = sendmsg(sock, &msg, 0);
        if (sent < 0) {
            ESP_LOGW("UDP", "sendmsg failed on chunk %u/%u: %s", header.packet_id, header.total_packets, strerror(errno));
            err_code = -1;
            break; // Drop the rest of this frame
        }

        /*
        memcpy(TODO_DATA_FIELD, pic->buf + offset, copy_len);

        ssize_t sent = sendto(
            sock,
            &chunk,
            sizeof(jpeg_chunk_t),
            0,
            (struct sockaddr const *const)(&dest_addr),
            sizeof(dest_addr)
        );
        if (sent < 0) {
            ESP_LOGE("UDP", "`sendto` failed: %s", strerror(errno));
            break;
        }
        */

        offset += CHUNK_SIZE;
    }

    ++header.frame_id;

    return err_code;
}
