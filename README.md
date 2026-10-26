# Nova

## Features

- **Dual View Modes:** Toggle between a 3D view and a flat 2D pixel canvas.
- **Thermal Palette Suite & Designer:** 10 built-in thermal colormaps (*Ironbow*, *Inferno*, *Turbo*, *White-Hot*, *Black-Hot*, *Lava*, *Cyberpunk*, *Ice & Fire*, *Emerald*, *Rainbow*) plus an interactive custom gradient designer with Python code export for Raspberry Pi scripts.
- **Diode Telemetry & Inspection:** Hover over any LED in 2D mode to inspect matrix coordinates, physical metric positioning, raw heat level (0–255), estimated body temperature, and output RGB/Hex color.
- **Embedded Mock Feeder:** Test animations without physical hardware by toggling the built-in synthetic walking crowd simulator (`[Space]`).
- **Low-Latency Network Protocol:** Accepts raw 8-bit thermal arrays (`LMHT`) or pre-colored RGB buffers (`LMRG`) over UDP.

---

## Prerequisites

- **Python:** 3.10 or higher
- **GPU:** OpenGL 3.0+ compatible graphics hardware and drivers

---

## Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/klyaist/nova.git
   cd nova
   ```

2. **Create and activate a virtual environment:**
   ```bash
   # Windows (PowerShell)
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1

   # macOS / Linux
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

---

## Quick Start

### 1. Launch the 3D Simulator
```bash
python main.py
```

### 2. Stream Mock Thermal Data (Optional)
Run the test client from a separate terminal to simulate external streaming:
```bash
python pi_client.py 127.0.0.1 7777
```
*(Alternatively, press `[Space]` within the simulator to toggle internal crowd generation)*

---

## Controls Reference

| Category | Action | Shortcut / Control |
| :--- | :--- | :--- |
| **View Modes** | **Toggle 2D Matrix $\leftrightarrow$ 3D Rig View** | `Tab` or `V` (or click on-screen toggle) |
| **Palettes** | **Cycle Thermal Colormap** | `P` |
| | **Invert Active Colormap** | `I` |
| | **Export Pi Palette Code** | `E` (or click `[EXPORT PI CODE]`) |
| **Feed Source** | **Toggle Mock Crowd $\leftrightarrow$ UDP Network** | `Space` |
| **HUD & Camera** | **Cycle HUD Detail** | `H` |
| | **Orbit Camera (3D)** | `Left Mouse Button` + Drag |
| | **Pan Camera (3D)** | `Right Mouse Button` + Drag |
| | **Zoom Camera** | `Mouse Wheel` |
| | **Camera View Presets** | `1` (Iso), `2` (Side), `3` (Plan), `4` (Crowd POV), `5` (Column) |
| | **Reset View** | `R` |
| | **Exit** | `Esc` |

---

## Hardware Specifications

| Component | Specification |
| :--- | :--- |
| **Truss Structure** | Prolyte H40V ($17.71\,\text{m} \times 6.00\,\text{m} \times 5.00\,\text{m}$), 6 vertical columns on ballast blocks |
| **Mesh Model** | BaltLED P150 Transparent LED Mesh ($\ge 92\%$ open transparency) |
| **Pixel Pitch** | $150\,\text{mm} \times 150\,\text{mm}$ |
| **Resolution** | $118 \times 40$ diodes ($4,720$ individual discrete RGB LEDs) |
| **Mounting Height** | Underhung beneath upper roof framework at $Z = 4.58\,\text{m}$ |

---

## Network Protocol (UDP Port 7777)

The simulator accepts binary UDP datagrams in two primary formats:

### 1. Raw Heat Values (`LMHT` — Recommended)
Send an 8-bit heat intensity grid ($118 \times 40$, values `0`–`255`). The simulator maps values via the active palette:

```python
import socket
import numpy as np

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
heat_data = np.zeros((40, 118), dtype=np.uint8)

# Header: b"LMHT" + Width (uint16 big-endian) + Height (uint16 big-endian)
packet = b"LMHT" + (118).to_bytes(2, "big") + (40).to_bytes(2, "big") + heat_data.tobytes()
sock.sendto(packet, ("127.0.0.1", 7777))
```

### 2. Pre-Colored RGB Buffers (`LMRG`)
Send packed 24-bit RGB pixel data ($118 \times 40 \times 3$ bytes):

```python
# Header: b"LMRG" + Width (uint16) + Height (uint16) + raw RGB bytes
packet = b"LMRG" + (118).to_bytes(2, "big") + (40).to_bytes(2, "big") + rgb_bytes
sock.sendto(packet, ("127.0.0.1", 7777))
```

---

## License

This project is licensed under the [MIT License](LICENSE).
