"""
Network protocol and color mapping for the LED Matrix Simulator.
Supports:
1. Raw RGB24 frames (14,160 bytes for 118x40x3)
2. Raw Thermal/Heatmap frames (4,720 bytes for 118x40x1)
3. Header-tagged frames (b'LMRG' for RGB, b'LMHT' for Thermal, b'LMCH' for chunked)
"""

import struct
import numpy as np
from config import GRID_WIDTH, GRID_HEIGHT

MAGIC_RGB = b"LMRG"    # 4B magic + uint16 W + uint16 H + W*H*3 bytes
MAGIC_HEAT = b"LMHT"   # 4B magic + uint16 W + uint16 H + W*H bytes
MAGIC_CHUNK = b"LMCH"  # Chunked transport for constrained MTU

# 256-level Ironbow Thermal Palette (FLIR style: black -> dark blue/purple -> red -> yellow -> white)
def _build_ironbow():
    palette = np.zeros((256, 3), dtype=np.uint8)
    for i in range(256):
        t = i / 255.0
        if t < 0.2:
            s = t / 0.2
            r, g, b = int(30 * s), 0, int(90 * s)
        elif t < 0.4:
            s = (t - 0.2) / 0.2
            r, g, b = int(30 + 130 * s), int(10 * s), int(90 * (1 - s) + 20)
        elif t < 0.7:
            s = (t - 0.4) / 0.3
            r, g, b = int(160 + 80 * s), int(10 + 120 * s), int(10 * (1 - s))
        elif t < 0.9:
            s = (t - 0.7) / 0.2
            r, g, b = int(240 + 15 * s), int(130 + 105 * s), int(40 * s)
        else:
            s = (t - 0.9) / 0.1
            r, g, b = 255, int(235 + 20 * s), int(40 + 215 * s)
        palette[i] = [min(255, max(0, r)), min(255, max(0, g)), min(255, max(0, b))]
    return palette

# 256-level Inferno Palette
def _build_inferno():
    palette = np.zeros((256, 3), dtype=np.uint8)
    for i in range(256):
        t = i / 255.0
        if t < 0.25:
            s = t / 0.25
            r, g, b = int(20 * s), int(10 * s), int(80 * s)
        elif t < 0.5:
            s = (t - 0.25) / 0.25
            r, g, b = int(20 + 140 * s), int(10 + 30 * s), int(80 + 20 * s)
        elif t < 0.75:
            s = (t - 0.5) / 0.25
            r, g, b = int(160 + 80 * s), int(40 + 100 * s), int(100 * (1 - s))
        else:
            s = (t - 0.75) / 0.25
            r, g, b = 240 + int(15 * s), int(140 + 110 * s), int(50 + 200 * s)
        palette[i] = [min(255, max(0, r)), min(255, max(0, g)), min(255, max(0, b))]
    return palette

# 256-level Turbo/Rainbow Palette
def _build_turbo():
    palette = np.zeros((256, 3), dtype=np.uint8)
    for i in range(256):
        t = i / 255.0
        r = int(255 * max(0.0, min(1.0, 1.5 - abs(3.0 * t - 2.0))))
        g = int(255 * max(0.0, min(1.0, 1.5 - abs(3.0 * t - 1.0))))
        b = int(255 * max(0.0, min(1.0, 1.5 - abs(3.0 * t - 0.0))))
        palette[i] = [r, g, b]
    return palette

COLORMAPS = {
    "ironbow": _build_ironbow(),
    "inferno": _build_inferno(),
    "turbo": _build_turbo(),
}

COLORMAP_NAMES = list(COLORMAPS.keys())

def apply_colormap(heat_array, colormap_name="ironbow"):
    """
    Applies selected colormap to a 2D or 1D array of heat values (0-255).
    Returns (H, W, 3) uint8 array.
    """
    palette = COLORMAPS.get(colormap_name, COLORMAPS["ironbow"])
    clipped = np.clip(heat_array, 0, 255).astype(np.uint8)
    return palette[clipped]

def decode_packet(data, expected_w=GRID_WIDTH, expected_h=GRID_HEIGHT, colormap_name="ironbow"):
    """
    Decodes an incoming UDP/TCP payload into an (H, W, 3) uint8 RGB array and raw heat array.
    Returns (rgb_frame, heat_frame, width, height, format_type) or (None, None, None, None, "UNKNOWN").
    """
    total_len = len(data)
    expected_rgb_len = expected_w * expected_h * 3
    expected_heat_len = expected_w * expected_h

    # 1. Check for Magic Header
    if total_len >= 8:
        magic = data[:4]
        if magic == MAGIC_RGB:
            w, h = struct.unpack("!HH", data[4:8])
            payload = data[8:]
            if len(payload) == w * h * 3:
                frame = np.frombuffer(payload, dtype=np.uint8).reshape((h, w, 3))
                return frame, None, w, h, "HEADER_RGB"
        elif magic == MAGIC_HEAT:
            w, h = struct.unpack("!HH", data[4:8])
            payload = data[8:]
            if len(payload) == w * h:
                heat = np.frombuffer(payload, dtype=np.uint8).reshape((h, w))
                frame = apply_colormap(heat, colormap_name)
                return frame, heat, w, h, "HEADER_HEAT"

    # 2. Raw unformatted fallback: exact RGB length
    if total_len == expected_rgb_len:
        frame = np.frombuffer(data, dtype=np.uint8).reshape((expected_h, expected_w, 3))
        return frame, None, expected_w, expected_h, "RAW_RGB"

    # 3. Raw unformatted fallback: exact Heat length
    if total_len == expected_heat_len:
        heat = np.frombuffer(data, dtype=np.uint8).reshape((expected_h, expected_w))
        frame = apply_colormap(heat, colormap_name)
        return frame, heat, expected_w, expected_h, "RAW_HEAT"

    return None, None, None, None, "UNKNOWN"

def encode_rgb_frame(rgb_array):
    """Encodes an (H, W, 3) uint8 array into a MAGIC_RGB packet."""
    h, w, _ = rgb_array.shape
    header = MAGIC_RGB + struct.pack("!HH", w, h)
    return header + rgb_array.tobytes()

def encode_heat_frame(heat_array):
    """Encodes an (H, W) uint8 array into a MAGIC_HEAT packet."""
    h, w = heat_array.shape
    header = MAGIC_HEAT + struct.pack("!HH", w, h)
    return header + heat_array.tobytes()
