"""
Thermal Camera Color Palette Manager for the LED Matrix Canopy Simulator.
Provides professional thermal colormaps (Ironbow, Inferno, Turbo, Black-Hot, White-Hot, etc.)
and allows users to design, test, and edit their own CUSTOM color palettes in real-time,
which can then be exported directly into the Raspberry Pi thermal camera script.
"""

import numpy as np

# Standard Professional Thermal Palettes (Color stops: normalized position 0.0 to 1.0, (R, G, B))
PRESET_PALETTES = {
    "Ironbow": [
        (0.00, np.array([0, 0, 0], dtype=np.float32)),        # Cold Black background
        (0.18, np.array([35, 0, 100], dtype=np.float32)),     # Deep Indigo
        (0.40, np.array([170, 15, 95], dtype=np.float32)),    # Purple / Magenta
        (0.68, np.array([245, 120, 10], dtype=np.float32)),   # Radiant Red-Orange
        (0.88, np.array([255, 230, 40], dtype=np.float32)),   # Warm Yellow
        (1.00, np.array([255, 255, 255], dtype=np.float32)),  # White-Hot core
    ],
    "Inferno": [
        (0.00, np.array([0, 0, 4], dtype=np.float32)),
        (0.25, np.array([64, 12, 107], dtype=np.float32)),
        (0.50, np.array([187, 55, 84], dtype=np.float32)),
        (0.75, np.array([249, 142, 9], dtype=np.float32)),
        (1.00, np.array([252, 255, 164], dtype=np.float32)),
    ],
    "Turbo": [
        (0.00, np.array([48, 18, 59], dtype=np.float32)),
        (0.25, np.array([70, 134, 251], dtype=np.float32)),
        (0.50, np.array([27, 229, 181], dtype=np.float32)),
        (0.75, np.array([249, 187, 44], dtype=np.float32)),
        (1.00, np.array([122, 4, 2], dtype=np.float32)),
    ],
    "White-Hot": [
        (0.00, np.array([0, 0, 0], dtype=np.float32)),        # Cold = Black
        (1.00, np.array([255, 255, 255], dtype=np.float32)),  # Hot = White
    ],
    "Black-Hot": [
        (0.00, np.array([255, 255, 255], dtype=np.float32)),  # Cold = White
        (1.00, np.array([0, 0, 0], dtype=np.float32)),        # Hot = Black
    ],
    "Lava Fire": [
        (0.00, np.array([5, 0, 0], dtype=np.float32)),
        (0.22, np.array([130, 10, 0], dtype=np.float32)),
        (0.52, np.array([255, 70, 0], dtype=np.float32)),
        (0.80, np.array([255, 210, 10], dtype=np.float32)),
        (1.00, np.array([255, 255, 220], dtype=np.float32)),
    ],
    "Cyberpunk": [
        (0.00, np.array([8, 4, 28], dtype=np.float32)),
        (0.30, np.array([0, 220, 255], dtype=np.float32)),
        (0.65, np.array([200, 0, 255], dtype=np.float32)),
        (0.88, np.array([255, 0, 120], dtype=np.float32)),
        (1.00, np.array([255, 240, 50], dtype=np.float32)),
    ],
    "Ice & Fire": [
        (0.00, np.array([0, 15, 80], dtype=np.float32)),      # Cold Deep Blue
        (0.35, np.array([0, 210, 240], dtype=np.float32)),    # Ice Cyan
        (0.50, np.array([15, 15, 22], dtype=np.float32)),     # Neutral separator
        (0.75, np.array([255, 85, 0], dtype=np.float32)),     # Fire Orange
        (1.00, np.array([255, 255, 140], dtype=np.float32)),  # White-Hot Gold
    ],
    "Toxic Emerald": [
        (0.00, np.array([0, 10, 4], dtype=np.float32)),
        (0.30, np.array([0, 90, 35], dtype=np.float32)),
        (0.65, np.array([35, 220, 80], dtype=np.float32)),
        (0.90, np.array([170, 255, 90], dtype=np.float32)),
        (1.00, np.array([245, 255, 230], dtype=np.float32)),
    ],
    "Rainbow": [
        (0.00, np.array([0, 0, 255], dtype=np.float32)),      # Blue (Cold)
        (0.25, np.array([0, 255, 255], dtype=np.float32)),    # Cyan
        (0.50, np.array([0, 255, 0], dtype=np.float32)),      # Green
        (0.75, np.array([255, 255, 0], dtype=np.float32)),    # Yellow
        (1.00, np.array([255, 0, 0], dtype=np.float32)),      # Red (Hot)
    ],
}

PALETTE_NAMES = list(PRESET_PALETTES.keys()) + ["Custom"]

# Quick color swatches for custom palette stop editing
QUICK_SWATCHES = [
    ("Black",   (0, 0, 0)),
    ("Navy",    (10, 20, 70)),
    ("Indigo",  (60, 0, 120)),
    ("Blue",    (0, 80, 240)),
    ("Cyan",    (0, 220, 240)),
    ("Emerald", (0, 180, 70)),
    ("Green",   (40, 240, 40)),
    ("Lime",    (170, 255, 30)),
    ("Gold",    (255, 210, 0)),
    ("Orange",  (255, 100, 0)),
    ("Crimson", (200, 10, 10)),
    ("Magenta", (230, 20, 140)),
    ("Violet",  (180, 40, 240)),
    ("Pink",    (255, 110, 180)),
    ("White",   (255, 255, 255)),
]

class ThermalPaletteManager:
    def __init__(self, default_palette="Ironbow"):
        self.active_palette_name = default_palette
        self.invert = False
        
        # 4 customizable stops for the 'Custom' palette
        # (position 0.0 to 1.0, [R, G, B])
        self.custom_stops = [
            {"pos": 0.00, "rgb": [10, 15, 35],   "label": "Cold / Bg"},
            {"pos": 0.33, "rgb": [0, 140, 220],  "label": "Low Heat"},
            {"pos": 0.66, "rgb": [255, 100, 20], "label": "Body Heat"},
            {"pos": 1.00, "rgb": [255, 255, 180],"label": "Peak Hot"},
        ]
        self.selected_stop_idx = 0  # Currently selected stop in the UI for color picking
        
        # 256-entry uint8 lookup table cache
        self.lut = np.zeros((256, 3), dtype=np.uint8)
        self._rebuild_lut()

    def set_palette(self, name):
        if name in PALETTE_NAMES:
            self.active_palette_name = name
            self._rebuild_lut()

    def cycle_palette(self, step=1):
        idx = PALETTE_NAMES.index(self.active_palette_name)
        new_idx = (idx + step) % len(PALETTE_NAMES)
        self.set_palette(PALETTE_NAMES[new_idx])

    def toggle_invert(self):
        self.invert = not self.invert
        self._rebuild_lut()

    # --- Custom Stop Operations ---
    def select_stop(self, idx):
        if 0 <= idx < len(self.custom_stops):
            self.selected_stop_idx = idx

    def set_selected_stop_color(self, rgb):
        """Sets the RGB color [0-255] of the currently selected stop and switches to Custom."""
        self.custom_stops[self.selected_stop_idx]["rgb"] = [
            max(0, min(255, int(rgb[0]))),
            max(0, min(255, int(rgb[1]))),
            max(0, min(255, int(rgb[2]))),
        ]
        self.active_palette_name = "Custom"
        self._rebuild_lut()

    def adjust_selected_stop_channel(self, channel_idx, delta):
        """Adjusts R (0), G (1), or B (2) of current stop by delta."""
        rgb = self.custom_stops[self.selected_stop_idx]["rgb"]
        rgb[channel_idx] = max(0, min(255, rgb[channel_idx] + delta))
        self.active_palette_name = "Custom"
        self._rebuild_lut()

    def load_preset_into_custom(self, preset_name):
        """Copies an existing preset into the custom stops so user can tweak it."""
        if preset_name in PRESET_PALETTES:
            stops = PRESET_PALETTES[preset_name]
            new_stops = []
            for i, (pos, col) in enumerate(stops):
                lbl = "Cold / Bg" if i == 0 else ("Peak Hot" if i == len(stops)-1 else f"Mid Heat {i}")
                new_stops.append({"pos": float(pos), "rgb": [int(col[0]), int(col[1]), int(col[2])], "label": lbl})
            self.custom_stops = new_stops
            self.selected_stop_idx = 0
            self.active_palette_name = "Custom"
            self._rebuild_lut()

    def _rebuild_lut(self):
        """Recomputes the 256x3 lookup table using vectorized linear interpolation."""
        if self.active_palette_name == "Custom":
            stops = [(s["pos"], np.array(s["rgb"], dtype=np.float32)) for s in self.custom_stops]
        else:
            stops = PRESET_PALETTES.get(self.active_palette_name, PRESET_PALETTES["Ironbow"])

        positions = [s[0] for s in stops]
        colors = [s[1] for s in stops]

        # Interpolate each of R, G, B across 256 values
        t = np.linspace(0.0, 1.0, 256)
        r = np.interp(t, positions, [c[0] for c in colors])
        g = np.interp(t, positions, [c[1] for c in colors])
        b = np.interp(t, positions, [c[2] for c in colors])

        lut = np.column_stack((r, g, b))
        if self.invert:
            lut = lut[::-1]
            
        self.lut = np.clip(lut, 0, 255).astype(np.uint8)

    def apply(self, heat_matrix_u8):
        """
        Fast lookup mapping (H, W) uint8 heat values to (H, W, 3) RGB.
        Takes < 0.05 ms.
        """
        clipped = np.clip(heat_matrix_u8, 0, 255).astype(np.uint8)
        return self.lut[clipped]

    def export_pi_code(self):
        """
        Generates Python code snippet representing the active palette
        ready to copy & paste into the Raspberry Pi script.
        """
        stops = self.custom_stops if self.active_palette_name == "Custom" else [
            {"pos": s[0], "rgb": [int(s[1][0]), int(s[1][1]), int(s[1][2])]}
            for s in PRESET_PALETTES.get(self.active_palette_name, PRESET_PALETTES["Ironbow"])
        ]
        
        lines = [
            f"# Thermal Color Palette: {self.active_palette_name}",
            "PALETTE_STOPS = ["
        ]
        for s in stops:
            r, g, b = s["rgb"]
            lines.append(f"    ({s['pos']:.2f}, ({r:3d}, {g:3d}, {b:3d})),")
        lines.append("]")
        lines.append("")
        lines.append("# NumPy 256-color LUT builder for Raspberry Pi:")
        lines.append("def build_thermal_lut(stops):")
        lines.append("    t = np.linspace(0.0, 1.0, 256)")
        lines.append("    pos = [s[0] for s in stops]")
        lines.append("    r = np.interp(t, pos, [s[1][0] for s in stops])")
        lines.append("    g = np.interp(t, pos, [s[1][1] for s in stops])")
        lines.append("    b = np.interp(t, pos, [s[1][2] for s in stops])")
        lines.append("    return np.column_stack((r, g, b)).clip(0, 255).astype(np.uint8)")
        return "\n".join(lines)
