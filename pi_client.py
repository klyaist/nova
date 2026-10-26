"""
Raspberry Pi Thermal Camera Client & Sender.
Run this script on your Raspberry Pi (or locally for testing) to capture thermal camera
frames, resize/interpolate them to the 118x40 matrix resolution, and stream them
to the LED Matrix Simulator host PC over UDP.
"""

import sys
import time
import math
import socket
import numpy as np

# Change this to your PC's local IP address when running on the physical Raspberry Pi!
# e.g., TARGET_HOST = "192.168.1.100"
TARGET_HOST = "127.0.0.1"
TARGET_PORT = 7777

MATRIX_WIDTH = 118
MATRIX_HEIGHT = 40

MAGIC_HEAT = b"LMHT"
MAGIC_RGB = b"LMRG"

class ThermalCameraSender:
    def __init__(self, target_host=TARGET_HOST, target_port=TARGET_PORT):
        self.target_host = target_host
        self.target_port = target_port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        print(f"[Pi Client] Configured target simulator at {self.target_host}:{self.target_port}")

    def send_heat_frame(self, heat_array):
        """
        Sends an (H, W) uint8 thermal intensity array (0-255).
        heat_array must have shape (MATRIX_HEIGHT, MATRIX_WIDTH) or will be resized.
        """
        if heat_array.shape != (MATRIX_HEIGHT, MATRIX_WIDTH):
            heat_array = self._resize_nearest(heat_array, MATRIX_WIDTH, MATRIX_HEIGHT)

        heat_u8 = np.clip(heat_array, 0, 255).astype(np.uint8)
        header = MAGIC_HEAT + (MATRIX_WIDTH).to_bytes(2, "big") + (MATRIX_HEIGHT).to_bytes(2, "big")
        packet = header + heat_u8.tobytes()
        self.sock.sendto(packet, (self.target_host, self.target_port))

    def send_rgb_frame(self, rgb_array):
        """
        Sends an (H, W, 3) uint8 RGB array directly.
        """
        if rgb_array.shape[:2] != (MATRIX_HEIGHT, MATRIX_WIDTH):
            rgb_array = self._resize_nearest(rgb_array, MATRIX_WIDTH, MATRIX_HEIGHT)
        rgb_u8 = np.clip(rgb_array, 0, 255).astype(np.uint8)
        header = MAGIC_RGB + (MATRIX_WIDTH).to_bytes(2, "big") + (MATRIX_HEIGHT).to_bytes(2, "big")
        packet = header + rgb_u8.tobytes()
        self.sock.sendto(packet, (self.target_host, self.target_port))

    def _resize_nearest(self, img, new_w, new_h):
        """Lightweight pure-numpy nearest neighbor resize without requiring OpenCV."""
        h, w = img.shape[:2]
        x_idx = (np.arange(new_w) * (w / new_w)).astype(int)
        y_idx = (np.arange(new_h) * (h / new_h)).astype(int)
        return img[np.ix_(y_idx, x_idx)]

def run_test_stream(target_host=TARGET_HOST, target_port=TARGET_PORT):
    """Generates synthetic thermal waves to demonstrate Pi client streaming."""
    sender = ThermalCameraSender(target_host=target_host, target_port=target_port)
    fps = 30
    frame_delay = 1.0 / fps
    print(f"[Pi Client] Streaming live test thermal patterns at {fps} FPS...")
    
    t0 = time.time()
    try:
        while True:
            t = time.time() - t0
            # Generate moving thermal heat patterns
            yy, xx = np.mgrid[0:MATRIX_HEIGHT, 0:MATRIX_WIDTH]
            
            # Simulated person walking diagonally
            cx1 = (t * 12.0) % (MATRIX_WIDTH + 20) - 10
            cy1 = (MATRIX_HEIGHT / 2.0) + math.sin(t * 1.5) * 12.0
            dist1 = np.sqrt((xx - cx1)**2 + (yy - cy1)**2)
            blob1 = 240.0 * np.exp(-dist1**2 / (2 * 4.0**2))

            # Second person walking opposite direction
            cx2 = MATRIX_WIDTH - ((t * 8.0) % (MATRIX_WIDTH + 20) - 10)
            cy2 = (MATRIX_HEIGHT / 2.0) - math.cos(t * 1.2) * 10.0
            dist2 = np.sqrt((xx - cx2)**2 + (yy - cy2)**2)
            blob2 = 230.0 * np.exp(-dist2**2 / (2 * 5.0**2))

            ambient = 25.0 + 5.0 * np.sin(xx * 0.1 + t)
            heat = np.maximum(ambient, np.maximum(blob1, blob2))
            
            sender.send_heat_frame(heat)
            time.sleep(frame_delay)

    except KeyboardInterrupt:
        print("[Pi Client] Stream stopped.")

if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else TARGET_HOST
    port = int(sys.argv[2]) if len(sys.argv) > 2 else TARGET_PORT
    print(f"Usage: python pi_client.py [TARGET_IP] [PORT]")
    run_test_stream(target_host=target, target_port=port)
