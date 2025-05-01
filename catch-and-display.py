import socket
import struct
import time
from collections import defaultdict
import cv2
import numpy as np

# Settings
PORT = 12345
HEADER_FORMAT = '<HHH'  # frame_id (uint16), packet_id (uint16), total_packets (uint16)
HEADER_SIZE = struct.calcsize(HEADER_FORMAT)
RECEIVE_TIMEOUT = 5  # seconds before discarding incomplete frame

# Frame buffer: frame_id -> {'total': int, 'chunks': dict, 'timestamp': float}
frames = defaultdict(lambda: {'chunks': {}, 'total': 0, 'timestamp': time.time()})

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(('', PORT))
sock.settimeout(1.0)

last_packet_time = None

print(f"🎥 Listening for JPEG chunks on port {PORT}...")

try:
    while True:
        try:
            packet, addr = sock.recvfrom(2048)
            now = time.time()
            if last_packet_time is not None:
                since = now - last_packet_time
                if since > 0.02:
                    print(f"Time since last packet: {since}")
            last_packet_time = now
        except socket.timeout:
            # Clean up stale frames
            now = time.time()
            for fid in list(frames):
                if now - frames[fid]['timestamp'] > RECEIVE_TIMEOUT:
                    print(f"⚠️  Discarding stale frame {fid}")
                    del frames[fid]
            continue

        if len(packet) < HEADER_SIZE:
            print("❌ Packet too small, skipping.")
            continue

        # Unpack header
        frame_id, packet_id, total_packets = struct.unpack(HEADER_FORMAT, packet[:HEADER_SIZE])
        payload = packet[HEADER_SIZE:]

        # Store chunk
        frame = frames[frame_id]
        frame['chunks'][packet_id] = payload
        frame['total'] = total_packets
        frame['timestamp'] = time.time()

        # Check if complete
        if len(frame['chunks']) == total_packets:
            # Assemble frame
            ordered_chunks = [frame['chunks'][i] for i in range(total_packets)]
            jpeg_data = b''.join(ordered_chunks)

            # Decode JPEG
            np_arr = np.frombuffer(jpeg_data, dtype=np.uint8)
            img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

            if img is not None:
                cv2.imshow('Live JPEG Stream', img)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
            else:
                print("⚠️  Failed to decode JPEG.")

            del frames[frame_id]

except KeyboardInterrupt:
    print("\n🛑 Shutting down...")

finally:
    sock.close()
    cv2.destroyAllWindows()

