#!/usr/bin/env python3

import cv2
import numpy as np
import socket
import struct
import sys
import time

from . import ml

PORT = 5005
HEADER_FORMAT = '<HHH'
CHUNK_SIZE = 1400

HEADER_SIZE = struct.calcsize(HEADER_FORMAT)

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(('', PORT))
# sock.settimeout(1.0)

while True:
    while True:
        packet, addr = sock.recvfrom(2048)
        frame_id, chunk_id, total_chunks = struct.unpack(HEADER_FORMAT, packet[:HEADER_SIZE])
        if chunk_id == 0:
            break

    jpeg_buffer = bytearray(total_chunks * CHUNK_SIZE)

    for i in range(0, total_chunks):
        data = packet[HEADER_SIZE:]
        data_len = len(data)
        if i == total_chunks - 1:
            if data_len > CHUNK_SIZE:
                print(f"Invalid data size (expected <={CHUNK_SIZE} but found {data_len}) for chunk #{i}/{total_chunks} of frame #{frame_id}. Skipping.")
                break
            jpeg_buffer[(CHUNK_SIZE * i):((CHUNK_SIZE * i) + data_len)] = data
            print(f"Successfully received frame #{frame_id}!")

            arr = np.asarray(jpeg_buffer, dtype="uint8")
            im = cv2.imdecode(arr, cv2.IMREAD_COLOR)
            ml.show(im)

            break

        if data_len != CHUNK_SIZE:
            print(f"Invalid data size (expected {CHUNK_SIZE} but found {data_len}) for chunk #{i}/{total_chunks} of frame #{frame_id}. Skipping.")
            break
        jpeg_buffer[(CHUNK_SIZE * i):(CHUNK_SIZE * (i + 1))] = data

        packet, addr = sock.recvfrom(2048)
        this_frame_id, chunk_id, this_total_chunks = struct.unpack(HEADER_FORMAT, packet[:HEADER_SIZE])
        if this_frame_id != frame_id:
            print(f"Lost frame #{frame_id} ({i}/{total_chunks}); continuing on frame #{this_frame_id}.")
            frame_id = this_frame_id
            total_chunks = this_total_chunks
            break
        if this_total_chunks != total_chunks:
            print(f"Different total chunks for frame #{total_chunks} (was {total_chunks}, now {this_total_chunks}). Skipping.")
            break
        if chunk_id != i + 1:
            print(f"In frame #{frame_id}, expected chunk #{i} but got chunk #{chunk_id}.")
            break
