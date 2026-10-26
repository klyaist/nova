"""
Threaded UDP/TCP Socket Server that emulates the physical LED Matrix hardware controller.
"""

import socket
import threading
import time
import numpy as np
from config import UDP_HOST, UDP_PORT, GRID_WIDTH, GRID_HEIGHT
from protocol import decode_packet, COLORMAP_NAMES

class LEDMatrixServer:
    def __init__(self, host=UDP_HOST, port=UDP_PORT):
        self.host = host
        self.port = port
        self.colormap = "ironbow"
        
        # Framebuffer storage (H, W, 3)
        self.width = GRID_WIDTH
        self.height = GRID_HEIGHT
        self._current_frame = np.zeros((self.height, self.width, 3), dtype=np.uint8)
        self._current_heat = None
        self._lock = threading.Lock()
        
        # Performance & Connection Metrics
        self.running = False
        self.packets_received = 0
        self.last_client_addr = None
        self.last_packet_time = 0.0
        self.format_detected = "None"
        
        # FPS estimation
        self._fps_counter = 0
        self._fps_time = time.time()
        self.fps = 0.0

        self._thread = None
        self._sock = None

    def start(self):
        """Starts the UDP listener thread."""
        self.running = True
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 2 * 1024 * 1024)  # 2MB buffer
        try:
            self._sock.bind((self.host, self.port))
        except OSError as e:
            print(f"[Server Warning] Could not bind UDP {self.host}:{self.port} ({e}). Another instance may be running.")
        self._sock.settimeout(0.5)

        self._thread = threading.Thread(target=self._listen_loop, daemon=True)
        self._thread.start()
        print(f"[Server] LED Matrix Hardware Listener active on UDP {self.host}:{self.port}")

    def stop(self):
        """Stops the listener thread and closes socket."""
        self.running = False
        if self._thread:
            self._thread.join(timeout=1.0)
        if self._sock:
            try:
                self._sock.close()
            except Exception:
                pass
            self._sock = None
        print("[Server] Server stopped.")

    def set_colormap(self, name):
        if name in COLORMAP_NAMES:
            self.colormap = name

    def _listen_loop(self):
        while self.running:
            try:
                data, addr = self._sock.recvfrom(65535)
                frame, heat, w, h, fmt = decode_packet(
                    data, 
                    expected_w=self.width, 
                    expected_h=self.height, 
                    colormap_name=self.colormap
                )
                
                if frame is not None:
                    with self._lock:
                        self._current_frame = frame
                        if heat is not None:
                            self._current_heat = heat
                        self.packets_received += 1
                        self.last_client_addr = addr
                        self.last_packet_time = time.time()
                        self.format_detected = fmt
                        
                        # Calculate received FPS
                        self._fps_counter += 1
                        now = time.time()
                        if now - self._fps_time >= 1.0:
                            self.fps = self._fps_counter / (now - self._fps_time)
                            self._fps_counter = 0
                            self._fps_time = now

            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    print(f"[Server] Receive error: {e}")

    def get_latest_frame(self):
        """Thread-safe retrieval of the latest RGB frame."""
        with self._lock:
            return self._current_frame.copy()

    def get_latest_heat(self):
        """Thread-safe retrieval of the latest raw thermal heat frame (0-255)."""
        with self._lock:
            return self._current_heat.copy() if self._current_heat is not None else None

    def set_frame_direct(self, frame_rgb):
        """Used by the built-in mock generator when no external client is streaming."""
        with self._lock:
            self._current_frame = frame_rgb

    def is_client_connected(self, timeout=2.0):
        """Returns True if a packet was received within `timeout` seconds."""
        return (time.time() - self.last_packet_time) < timeout
