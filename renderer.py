"""
PyOpenGL Renderer with Orbit/Pan/Zoom camera controls, lighting, and 2D HUD overlay.
"""

import math
import pygame
from OpenGL.GL import *
from OpenGL.GLU import *
from config import WINDOW_WIDTH, WINDOW_HEIGHT, TRUSS_LENGTH, TRUSS_WIDTH, TRUSS_HEIGHT

class Camera:
    def __init__(self):
        self.reset_isometric()

    def reset_isometric(self):
        self.target = [0.0, 0.0, 2.5]
        self.distance = 26.0
        self.yaw = 35.0      # Horizontal rotation degrees
        self.pitch = 24.0    # Vertical elevation degrees

    def set_preset(self, preset_id):
        if preset_id == 1:  # Isometric Overview
            self.reset_isometric()
        elif preset_id == 2:  # Side View (Lengthwise)
            self.target = [0.0, 0.0, 2.5]
            self.distance = 28.0
            self.yaw = 0.0
            self.pitch = 6.0
        elif preset_id == 3:  # Top-Down Plan View
            self.target = [0.0, 0.0, 4.6]
            self.distance = 24.0
            self.yaw = 0.0
            self.pitch = 89.9
        elif preset_id == 4:  # Crowd POV (Standing underneath looking UP at the P150 ceiling)
            self.target = [0.0, 0.0, 4.58]
            self.distance = 2.8
            self.yaw = 30.0
            self.pitch = -72.0  # Looking up at ceiling
        elif preset_id == 5:  # Close-up corner column & ballast
            self.target = [-TRUSS_LENGTH / 2.0, -TRUSS_WIDTH / 2.0, 2.0]
            self.distance = 6.0
            self.yaw = 45.0
            self.pitch = 15.0

    def orbit(self, dyaw, dpitch):
        self.yaw = (self.yaw + dyaw) % 360.0
        self.pitch = max(-89.9, min(89.9, self.pitch + dpitch))

    def pan(self, dx, dy):
        rad_yaw = math.radians(self.yaw)
        # Pan relative to camera orientation
        forward_x = -math.sin(rad_yaw)
        forward_y =  math.cos(rad_yaw)
        right_x   =  math.cos(rad_yaw)
        right_y   =  math.sin(rad_yaw)

        speed = self.distance * 0.0015
        self.target[0] += (-right_x * dx - forward_x * dy) * speed
        self.target[1] += (-right_y * dx - forward_y * dy) * speed

    def zoom(self, factor):
        self.distance = max(1.5, min(100.0, self.distance * factor))

    def apply_view(self):
        rad_yaw = math.radians(self.yaw)
        rad_pitch = math.radians(self.pitch)

        # Spherical coordinates
        cx = self.target[0] + self.distance * math.cos(rad_pitch) * math.sin(rad_yaw)
        cy = self.target[1] - self.distance * math.cos(rad_pitch) * math.cos(rad_yaw)
        cz = self.target[2] + self.distance * math.sin(rad_pitch)

        gluLookAt(
            cx, cy, cz,
            self.target[0], self.target[1], self.target[2],
            0.0, 0.0, 1.0
        )

class SceneRenderer:
    def __init__(self, width=WINDOW_WIDTH, height=WINDOW_HEIGHT):
        self.width = width
        self.height = height
        self.camera = Camera()
        self.hud_font = None
        self.hud_mode = 0  # 0: Detailed, 1: Controls Only, 2: No HUD
        self._init_gl()

    def cycle_hud_mode(self):
        """Cycles between Detailed (0), Controls Only (1), and No HUD (2)."""
        self.hud_mode = (self.hud_mode + 1) % 3

    def _init_gl(self):
        glEnable(GL_DEPTH_TEST)
        glDepthFunc(GL_LEQUAL)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        
        # Dark nocturnal night sky
        glClearColor(0.010, 0.012, 0.018, 1.0)
        
        # Smooth shading
        glShadeModel(GL_SMOOTH)
        glEnable(GL_NORMALIZE)

        # Nocturnal lighting setup (LEDs are the primary light source)
        glEnable(GL_LIGHTING)
        glEnable(GL_LIGHT0)
        glEnable(GL_LIGHT1)

        # Soft cool moonlight from overhead
        glLightfv(GL_LIGHT0, GL_POSITION, [15.0, -10.0, 30.0, 1.0])
        glLightfv(GL_LIGHT0, GL_DIFFUSE,  [0.28, 0.32, 0.42, 1.0])
        glLightfv(GL_LIGHT0, GL_SPECULAR, [0.65, 0.68, 0.75, 1.0])

        # Subtle ground bounce fill
        glLightfv(GL_LIGHT1, GL_POSITION, [-15.0, 10.0, 5.0, 1.0])
        glLightfv(GL_LIGHT1, GL_DIFFUSE,  [0.10, 0.12, 0.16, 1.0])

        glLightModelfv(GL_LIGHT_MODEL_AMBIENT, [0.10, 0.12, 0.15, 1.0])

        # Initialize Pygame font for HUD (ClearType-optimized fonts)
        pygame.font.init()
        font_list = ["segoeui", "tahoma", "arial", "consolas"]
        self.hud_font = pygame.font.SysFont(font_list, 14)
        self.hud_font_large = pygame.font.SysFont(font_list, 16, bold=True)

        # Initialize persistent HUD texture with GL_NEAREST for razor-sharp pixel rendering
        self.hud_tex_id = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, self.hud_tex_id)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)

    def reshape(self, width, height):
        self.width = max(1, width)
        self.height = max(1, height)
        glViewport(0, 0, self.width, self.height)

    def begin_3d(self):
        glViewport(0, 0, self.width, self.height)
        glClearColor(0.010, 0.012, 0.018, 1.0)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glEnable(GL_DEPTH_TEST)
        glEnable(GL_LIGHTING)
        glDisable(GL_TEXTURE_2D)
        
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluPerspective(45.0, float(self.width) / float(self.height), 0.1, 200.0)

        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
        self.camera.apply_view()

    def render_hud(self, stats):
        """
        Renders 2D text overlay based on active hud_mode:
        - Mode 0: Detailed (Full diagnostic telemetry & structure stats)
        - Mode 1: Controls Only (Minimalist floating control bar)
        - Mode 2: No HUD (Clean unobstructed screen)
        """
        if self.hud_mode == 2 or not self.hud_font:
            return  # No HUD

        # Setup 2D Orthographic Projection
        glMatrixMode(GL_PROJECTION)
        glPushMatrix()
        glLoadIdentity()
        gluOrtho2D(0, self.width, self.height, 0)

        glMatrixMode(GL_MODELVIEW)
        glPushMatrix()
        glLoadIdentity()

        glDisable(GL_DEPTH_TEST)
        glDisable(GL_LIGHTING)
        try:
            glDisable(GL_MULTISAMPLE)
        except Exception:
            pass
        glEnable(GL_TEXTURE_2D)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

        if self.hud_mode == 0:
            # MODE 0: DETAILED TELEMETRY HUD (Top-Left)
            panel_w = 680
            panel_h = 325
            panel_x = 12
            panel_y = 12

            source_str = stats.get('source_mode', 'CROWD')
            pal_str = stats.get('palette_name', 'Ironbow')

            lines = [
                ("=== LED MATRIX 3D SIMULATOR ===", True, (255, 215, 0)),
                ("Structure: 17.71m x 6.0m x 5.0m (6 Columns: 3 per side, Prolyte H40V)", False, (200, 220, 255)),
                ("LED Mesh: BaltLED P150 Discrete (150mm Pitch, 34mm Modules)", False, (200, 220, 255)),
                (f"Resolution: {stats['width']}x{stats['height']} ({stats['total_leds']} pixels) | Hung at Z=4.58m", False, (180, 210, 240)),
                (f"Hardware UDP Listener: {stats['listen_host']}:{stats['listen_port']}", False, (180, 255, 180)),
                (f"Client Status: {stats['client_status']}", False, (50, 255, 100) if stats['is_connected'] else (255, 150, 50)),
                (f"Rx Packets: {stats['packets']} | Rx FPS: {stats['rx_fps']:.1f} | Display FPS: {stats['render_fps']:.1f}", False, (220, 220, 220)),
                (f"Thermal Camera Feed: [{source_str}] | Active Palette [P]: {pal_str}", False, (255, 205, 110)),
                (f"Lighting: Night Stage | Multi-Tier Optical Bloom", False, (200, 215, 235)),
                ("", False, (255, 255, 255)),
                ("View Modes: [Tab] / [V] Toggle Flat 2D LED Grid (Palette Designer) vs 3D Scene", False, (120, 230, 255)),
                ("Navigation: [L-Drag] Orbit | [R-Drag] Pan | [Wheel] Zoom | [1-5] POV | [R] Reset", False, (160, 180, 200)),
                ("Palettes:   [P] Cycle Thermal Palette | [I] Invert | [Space] Toggle Mock Crowd", False, (255, 225, 140)),
                ("HUD Toggle: [H] Detailed (Press H for 'Controls Only')", False, (255, 220, 100)),
            ]

            hud_surface = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
            hud_surface.fill((8, 11, 18, 225))
            pygame.draw.rect(hud_surface, (45, 65, 95, 255), (0, 0, panel_w, panel_h), 1)

            y_offset = 10
            for text, is_header, color in lines:
                if not text:
                    y_offset += 5
                    continue
                font = self.hud_font_large if is_header else self.hud_font
                text_surf = font.render(text, True, color)
                hud_surface.blit(text_surf, (14, y_offset))
                y_offset += 21

        else:
            # MODE 1: JUST WITH CONTROLS (Clean floating bottom bar)
            panel_w = 840
            panel_h = 56
            panel_x = 12
            panel_y = max(10, self.height - panel_h - 12)

            lines = [
                ("3D Controls: [L-Drag] Orbit | [R-Drag] Pan | [Wheel] Zoom | [1-5] Views | [R] Reset", False, (220, 230, 250)),
                ("Hotkeys:     [Tab] Flat 2D Grid & Custom Palette Picker | [P] Palette | [I] Invert | [H] HUD", False, (255, 215, 100)),
            ]

            hud_surface = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
            hud_surface.fill((8, 11, 18, 210))
            pygame.draw.rect(hud_surface, (50, 75, 110, 255), (0, 0, panel_w, panel_h), 1)

            y_offset = 7
            for text, is_header, color in lines:
                text_surf = self.hud_font.render(text, True, color)
                hud_surface.blit(text_surf, (14, y_offset))
                y_offset += 22

        # Upload exact-sized surface to OpenGL texture (prevents any stride skew)
        data = pygame.image.tostring(hud_surface, "RGBA", False)
        glBindTexture(GL_TEXTURE_2D, self.hud_tex_id)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
        glTexImage2D(
            GL_TEXTURE_2D, 0, GL_RGBA,
            panel_w, panel_h, 0,
            GL_RGBA, GL_UNSIGNED_BYTE, data
        )

        # Draw single quad for HUD panel with matching UV coordinates
        glColor4f(1.0, 1.0, 1.0, 1.0)
        glBegin(GL_QUADS)
        glTexCoord2f(0.0, 0.0); glVertex2f(panel_x, panel_y)
        glTexCoord2f(1.0, 0.0); glVertex2f(panel_x + panel_w, panel_y)
        glTexCoord2f(1.0, 1.0); glVertex2f(panel_x + panel_w, panel_y + panel_h)
        glTexCoord2f(0.0, 1.0); glVertex2f(panel_x, panel_y + panel_h)
        glEnd()

        glDisable(GL_TEXTURE_2D)
        glEnable(GL_DEPTH_TEST)
        glEnable(GL_LIGHTING)

        glMatrixMode(GL_PROJECTION)
        glPopMatrix()
        glMatrixMode(GL_MODELVIEW)
        glPopMatrix()
