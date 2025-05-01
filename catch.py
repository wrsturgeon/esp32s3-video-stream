import socket
import struct
import os
import time
from collections import defaultdict

# Settings
PORT = 12345
CHUNK_SIZE = 1024
HEADER_FORMAT = '<HHH'  # frame_id (uint16), packet_id (uint16), total_packets (uint16)
HEADER_SIZE = struct.calcsize(HEADER_FORMAT)
DATA_SIZE = CHUNK_SIZE - HEADER_SIZE
RECEIVE_TIMEOUT = 5  # seconds before discarding incomplete frame

# Frame storage: frame_id -> {'total': int, 'chunks': dict, 'timestamp': float}
frames = defaultdict(lambda: {'chunks': {}, 'total': 0, 'timestamp': time.time()})
frame_counter = 0

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(('', PORT))
sock.settimeout(1.0)

print(f"Listening for UDP JPEG chunks on port {PORT}...")

try:
    while True:
        try:
            packet, addr = sock.recvfrom(2048)
        except socket.timeout:
            now = time.time()
            print(f"Socket timed out at {now}")
            # Clean up stale frames
            for fid in list(frames):
                if now - frames[fid]['timestamp'] > RECEIVE_TIMEOUT:
                    print(f"⚠️  Discarding stale frame {fid}")
                    del frames[fid]
            continue

        if len(packet) < HEADER_SIZE:
            print("❌ Packet too small, skipping.")
            continue

        # Unpack header
        header = struct.unpack(HEADER_FORMAT, packet[:HEADER_SIZE])
        print(f"Header: {header}")
        frame_id, packet_id, total_packets = header
        payload = packet[HEADER_SIZE:]

        # Store chunk
        frame = frames[frame_id]
        frame['chunks'][packet_id] = payload
        frame['total'] = total_packets
        frame['timestamp'] = time.time()

        # Check if complete
        if len(frame['chunks']) == total_packets:
            ordered_chunks = [frame['chunks'][i] for i in range(total_packets)]
            jpeg_data = b''.join(ordered_chunks)
            filename = f"frame_{frame_counter:05}.jpg"
            with open(filename, 'wb') as f:
                f.write(jpeg_data)
            print(f"✅ Reconstructed frame {frame_id} -> {filename} ({len(jpeg_data)} bytes)")
            frame_counter += 1
            del frames[frame_id]

except KeyboardInterrupt:
    print("Shutting down...")

