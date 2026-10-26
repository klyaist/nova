"""
Configuration parameters for the LED Matrix & Truss Simulator.
"""

# Physical Structure Dimensions (in meters)
TRUSS_LENGTH = 17.71       # Total length (X-axis)
TRUSS_WIDTH = 6.00         # Total width (Y-axis)
TRUSS_HEIGHT = 5.00        # Height to top of canopy (Z-axis)

# Truss Construction (Prolyte H40V specifications)
TRUSS_PROFILE_SIZE = 0.40  # 40cm x 40cm square truss profile
CHORD_RADIUS = 0.024       # Main tube radius (48.3mm outer diameter)
LACING_RADIUS = 0.010      # Diagonal bracing tube radius
BALLAST_WIDTH = 0.85       # Ballast block width (X)
BALLAST_LENGTH = 0.85      # Ballast block length (Y)
BALLAST_HEIGHT = 0.60      # Ballast block height (Z)

# Bay Configuration: 3 columns on each side = 6 columns total
NUM_COL_PAIRS = 3          # 3 columns along length on each side
COL_Y_FRONT = -TRUSS_WIDTH / 2.0  # -3.00 m
COL_Y_BACK = TRUSS_WIDTH / 2.0    # +3.00 m

# BaltLED P150 Transparent LED Mesh Specifications (from datasheet)
LED_CELL_SIZE = 0.15       # 150mm x 150mm pixel pitch (0.15 m)
LED_MODULE_SIZE = 0.034    # 34mm x 34mm pixel module casing
LED_EMITTER_SIZE = 0.026   # 26mm x 26mm active diode emitter face
LED_UNDERHANG_Z = TRUSS_HEIGHT - TRUSS_PROFILE_SIZE - 0.02  # 4.58m (right below upper truss)

# Realistic Night Rendering & Glow Parameters
NIGHT_GLOW_CORE = 0.08     # 80mm inner hot flare diameter
NIGHT_GLOW_AURA = 0.22     # 220mm outer atmospheric bloom halo
NIGHT_GLOW_INTENSITY = 2.4 # Emissive bloom boost for vibrant nocturnal lighting

# Grid Resolution: 17.71m / 0.15m = ~118 columns, 6.0m / 0.15m = 40 rows
GRID_WIDTH = round(TRUSS_LENGTH / LED_CELL_SIZE)   # 118 pixels
GRID_HEIGHT = round(TRUSS_WIDTH / LED_CELL_SIZE)   # 40 pixels
TOTAL_LEDS = GRID_WIDTH * GRID_HEIGHT              # 4,720 pixels

# Network Configuration (for Raspberry Pi communication)
UDP_HOST = "0.0.0.0"       # Listen on all interfaces
UDP_PORT = 7777            # Default UDP port
TCP_PORT = 7778            # Optional TCP port

# Display & Window (Crisp High-DPI default)
WINDOW_WIDTH = 1440
WINDOW_HEIGHT = 820
WINDOW_TITLE = "LED Matrix Canopy Simulator (17.71m x 6.0m)"
FPS_TARGET = 60

# Default Simulator Mode
DEFAULT_DEMO_MODE = True   # Start with simulated crowd heat signatures enabled
