#!/usr/bin/env python3

import cv2
import fcntl
import numpy as np
import os
import socket
import struct
import sys
import time

import ml

PORT = 5005
HEADER_FORMAT = '<HHH'
CHUNK_SIZE = 1400

HEADER_SIZE = struct.calcsize(HEADER_FORMAT)

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(('', PORT))
fcntl.fcntl(sock, fcntl.F_SETFL, os.O_NONBLOCK)
# sock.settimeout(1.0)

PACKET_TIMEOUT_SECONDS = 1

def get_next_packet():
    packet = None

    start_time = time.time()
    while packet is None:
        try:
            return sock.recv(2048)
        except BlockingIOError:
            if time.time() > start_time + PACKET_TIMEOUT_SECONDS:
                print("Waiting for wireless communication...")
                start_time += PACKET_TIMEOUT_SECONDS

def get_latest_packet():
    packet = get_next_packet()

    # Then keep going until we have the *most recent* packet:
    while True:
        try:
            packet = sock.recv(2048)
            print("Skipped a packet...")
        except BlockingIOError:
            return packet

while True:
    while True:
        packet = get_latest_packet()
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
            ml.process(im)

            break

        if data_len != CHUNK_SIZE:
            print(f"Invalid data size (expected {CHUNK_SIZE} but found {data_len}) for chunk #{i}/{total_chunks} of frame #{frame_id}. Skipping.")
            break
        jpeg_buffer[(CHUNK_SIZE * i):(CHUNK_SIZE * (i + 1))] = data

        packet = get_next_packet()
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
