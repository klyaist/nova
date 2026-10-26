"""
Simulated Crowd Heat Signature Generator.
Emulates a thermal camera observing people moving underneath the 17.71m x 6.0m truss canopy.
Can run standalone or embedded in the simulator loop.
"""

import time
import math
import random
import socket
import numpy as np
from config import GRID_WIDTH, GRID_HEIGHT, UDP_HOST, UDP_PORT
from protocol import encode_heat_frame

class Person:
    def __init__(self, w, h):
        self.w = w
        self.h = h
        self.reset()

    def reset(self):
        # Start at random edge
        edge = random.choice(["left", "right", "top", "bottom"])
        if edge == "left":
            self.x = -2.0
            self.y = random.uniform(5.0, self.h - 5.0)
            self.vx = random.uniform(0.3, 0.8)
            self.vy = random.uniform(-0.2, 0.2)
        elif edge == "right":
            self.x = self.w + 2.0
            self.y = random.uniform(5.0, self.h - 5.0)
            self.vx = random.uniform(-0.8, -0.3)
            self.vy = random.uniform(-0.2, 0.2)
        elif edge == "top":
            self.x = random.uniform(5.0, self.w - 5.0)
            self.y = -2.0
            self.vx = random.uniform(-0.3, 0.3)
            self.vy = random.uniform(0.2, 0.6)
        else:
            self.x = random.uniform(5.0, self.w - 5.0)
            self.y = self.h + 2.0
            self.vx = random.uniform(-0.3, 0.3)
            self.vy = random.uniform(-0.6, -0.2)

        self.radius = random.uniform(4.2, 7.8)   # Natural human heat spread (~0.7m - 1.2m)
        self.intensity = random.uniform(225, 255) # Radiant body core heat
        self.linger_timer = random.uniform(0, 10)

    def update(self, dt):
        self.x += self.vx * dt * 15.0
        self.y += self.vy * dt * 15.0
        
        # Slight organic wander
        self.vx += random.uniform(-0.02, 0.02)
        self.vy += random.uniform(-0.02, 0.02)
        self.vx = max(-1.0, min(1.0, self.vx))
        self.vy = max(-0.8, min(0.8, self.vy))

        # Check bounds
        if self.x < -10.0 or self.x > self.w + 10.0 or self.y < -10.0 or self.y > self.h + 10.0:
            self.reset()

class CrowdThermalSimulator:
    def __init__(self, width=GRID_WIDTH, height=GRID_HEIGHT, num_people=14):
        self.width = width
        self.height = height
        self.people = [Person(width, height) for _ in range(num_people)]
        self.last_time = time.time()
        
        # Coordinate grids for fast vectorized distance computation
        yy, xx = np.mgrid[0:self.height, 0:self.width]
        self.grid_x = xx.astype(np.float32)
        self.grid_y = yy.astype(np.float32)

    def generate_frame(self):
        now = time.time()
        dt = min(0.1, now - self.last_time)
        self.last_time = now

        # Update people positions
        for p in self.people:
            p.update(dt)

        # Baseline ambient thermal background (cool ground: 20-35)
        ambient = 22.0 + 3.0 * np.sin(self.grid_x * 0.05 + now * 0.5)
        heat_map = np.full((self.height, self.width), ambient, dtype=np.float32)

        # Add Gaussian heat blobs for each person
        for p in self.people:
            dx = self.grid_x - p.x
            dy = self.grid_y - p.y
            dist_sq = dx * dx + dy * dy
            blob = p.intensity * np.exp(-dist_sq / (2.0 * p.radius * p.radius))
            heat_map = np.maximum(heat_map, blob)

        # Realistic thermal camera sensor noise (subtle grain)
        noise = np.random.normal(0.0, 2.0, (self.height, self.width)).astype(np.float32)
        heat_map += noise

        # Clip to uint8 range
        heat_u8 = np.clip(heat_map, 0, 255).astype(np.uint8)
        return heat_u8

def run_standalone_streamer(target_ip="127.0.0.1", target_port=UDP_PORT, fps=30):
    """Sends mock thermal frames to the simulator over UDP."""
    sim = CrowdThermalSimulator()
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    print(f"[Mock Feeder] Streaming thermal crowd heat to {target_ip}:{target_port} at {fps} FPS...")
    
    frame_interval = 1.0 / fps
    try:
        while True:
            start_t = time.time()
            heat_frame = sim.generate_frame()
            packet = encode_heat_frame(heat_frame)
            sock.sendto(packet, (target_ip, target_port))
            
            elapsed = time.time() - start_t
            sleep_t = max(0.001, frame_interval - elapsed)
            time.sleep(sleep_t)
    except KeyboardInterrupt:
        print("[Mock Feeder] Stopped.")

if __name__ == "__main__":
    run_standalone_streamer()
