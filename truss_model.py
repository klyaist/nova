"""
Procedural 3D model generator for the Prolyte H40V truss rig and BaltLED P150 mesh.
Rig: 17.71m x 6.00m x 5.00m with 3 columns on each side (6 columns total).
Mesh: BaltLED P150 Transparent Mesh hung under the roof trusses at Z = 4.58m.
Atmosphere: Nocturnal stage environment with volumetric aluminum chords,
cull-tested ground (fully visible from below ground level), and pronounced
multi-tier additive optical bloom.
"""

import math
import numpy as np
from OpenGL.GL import *
from OpenGL.GLU import *
from config import (
    TRUSS_LENGTH, TRUSS_WIDTH, TRUSS_HEIGHT,
    TRUSS_PROFILE_SIZE, BALLAST_WIDTH, BALLAST_LENGTH, BALLAST_HEIGHT,
    NUM_COL_PAIRS, COL_Y_FRONT, COL_Y_BACK,
    LED_CELL_SIZE, LED_MODULE_SIZE, LED_EMITTER_SIZE, LED_UNDERHANG_Z,
    NIGHT_GLOW_CORE, NIGHT_GLOW_AURA, NIGHT_GLOW_INTENSITY,
    GRID_WIDTH, GRID_HEIGHT, TOTAL_LEDS
)

class TrussModel:
    def __init__(self):
        self.truss_display_list = None
        self.mesh_structure_display_list = None
        self.glow_texture_id = None
        self.bounce_texture_id = None
        
        self._init_column_positions()
        self._init_led_geometry()
        self._init_glow_texture()

    def _init_column_positions(self):
        """
        Coordinates for 3 columns on each side (6 columns total).
        x in {-8.855, 0.0, +8.855}
        """
        half_len = TRUSS_LENGTH / 2.0
        self.x_positions = [
            -half_len + i * (TRUSS_LENGTH / (NUM_COL_PAIRS - 1))
            for i in range(NUM_COL_PAIRS)
        ]
        self.columns = []
        for x in self.x_positions:
            self.columns.append((x, COL_Y_FRONT))  # Front row (-3.0m)
            self.columns.append((x, COL_Y_BACK))   # Back row (+3.0m)

    def _init_led_geometry(self):
        """
        Pre-computes vertex arrays for:
        1. Discrete LED core emitter pucks (26mm x 26mm)
        2. Inner intense flare halos (80mm x 80mm)
        3. Outer atmospheric bloom halos (220mm x 220mm)
        """
        half_len = TRUSS_LENGTH / 2.0
        half_wid = TRUSS_WIDTH / 2.0
        
        xs = np.linspace(-half_len + LED_CELL_SIZE / 2.0, half_len - LED_CELL_SIZE / 2.0, GRID_WIDTH, dtype=np.float32)
        ys = np.linspace(-half_wid + LED_CELL_SIZE / 2.0, half_wid - LED_CELL_SIZE / 2.0, GRID_HEIGHT, dtype=np.float32)
        
        xx, yy = np.meshgrid(xs, ys)
        centers_x = xx.flatten()
        centers_y = yy.flatten()
        z_mesh = float(LED_UNDERHANG_Z)
        
        # 1. Core Diode Quads (26mm x 26mm)
        he = LED_EMITTER_SIZE / 2.0
        quads_core = np.zeros((TOTAL_LEDS, 4, 3), dtype=np.float32)
        quads_core[:, 0, :] = np.column_stack((centers_x - he, centers_y - he, np.full(TOTAL_LEDS, z_mesh)))
        quads_core[:, 1, :] = np.column_stack((centers_x + he, centers_y - he, np.full(TOTAL_LEDS, z_mesh)))
        quads_core[:, 2, :] = np.column_stack((centers_x + he, centers_y + he, np.full(TOTAL_LEDS, z_mesh)))
        quads_core[:, 3, :] = np.column_stack((centers_x - he, centers_y + he, np.full(TOTAL_LEDS, z_mesh)))
        self.led_vertices = np.ascontiguousarray(quads_core.reshape(-1, 3))

        # 2. Inner Hot Flare Halos (80mm x 80mm)
        h_core = NIGHT_GLOW_CORE / 2.0
        quads_flare = np.zeros((TOTAL_LEDS, 4, 3), dtype=np.float32)
        quads_flare[:, 0, :] = np.column_stack((centers_x - h_core, centers_y - h_core, np.full(TOTAL_LEDS, z_mesh - 0.003)))
        quads_flare[:, 1, :] = np.column_stack((centers_x + h_core, centers_y - h_core, np.full(TOTAL_LEDS, z_mesh - 0.003)))
        quads_flare[:, 2, :] = np.column_stack((centers_x + h_core, centers_y + h_core, np.full(TOTAL_LEDS, z_mesh - 0.003)))
        quads_flare[:, 3, :] = np.column_stack((centers_x - h_core, centers_y + h_core, np.full(TOTAL_LEDS, z_mesh - 0.003)))
        self.flare_vertices = np.ascontiguousarray(quads_flare.reshape(-1, 3))

        # 3. Outer Atmospheric Bloom Aura (220mm x 220mm)
        h_aura = NIGHT_GLOW_AURA / 2.0
        quads_aura = np.zeros((TOTAL_LEDS, 4, 3), dtype=np.float32)
        quads_aura[:, 0, :] = np.column_stack((centers_x - h_aura, centers_y - h_aura, np.full(TOTAL_LEDS, z_mesh - 0.006)))
        quads_aura[:, 1, :] = np.column_stack((centers_x + h_aura, centers_y - h_aura, np.full(TOTAL_LEDS, z_mesh - 0.006)))
        quads_aura[:, 2, :] = np.column_stack((centers_x + h_aura, centers_y + h_aura, np.full(TOTAL_LEDS, z_mesh - 0.006)))
        quads_aura[:, 3, :] = np.column_stack((centers_x - h_aura, centers_y + h_aura, np.full(TOTAL_LEDS, z_mesh - 0.006)))
        self.aura_vertices = np.ascontiguousarray(quads_aura.reshape(-1, 3))

        # Shared UV Texture Coordinates for Halos
        uv_single = np.array([[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0]], dtype=np.float32)
        self.halo_uvs = np.ascontiguousarray(np.tile(uv_single, (TOTAL_LEDS, 1)))

        self.grid_centers_x = centers_x
        self.grid_centers_y = centers_y

    def _init_glow_texture(self):
        """Creates a smooth radial Gaussian bloom sprite for additive blending."""
        res = 64
        y, x = np.mgrid[-1:1:complex(0, res), -1:1:complex(0, res)]
        r = np.sqrt(x*x + y*y)
        # Smooth natural falloff
        alpha = np.clip(1.0 - r, 0.0, 1.0) ** 2.0
        alpha_u8 = (alpha * 255.0).astype(np.uint8)

        glow_rgba = np.zeros((res, res, 4), dtype=np.uint8)
        glow_rgba[:, :, :3] = 255
        glow_rgba[:, :, 3] = alpha_u8

        self.glow_texture_id = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, self.glow_texture_id)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)
        glTexImage2D(
            GL_TEXTURE_2D, 0, GL_RGBA,
            res, res, 0,
            GL_RGBA, GL_UNSIGNED_BYTE, glow_rgba
        )

        # Ground Bounce Texture (floor reflection)
        self.bounce_texture_id = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, self.bounce_texture_id)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        blank = np.zeros((GRID_HEIGHT, GRID_WIDTH, 3), dtype=np.uint8)
        glTexImage2D(
            GL_TEXTURE_2D, 0, GL_RGB,
            GRID_WIDTH, GRID_HEIGHT, 0,
            GL_RGB, GL_UNSIGNED_BYTE, blank
        )

    def build_geometry(self):
        """Compiles the static 6-column truss, ballast, and mesh wires into display lists."""
        self.truss_display_list = glGenLists(1)
        glNewList(self.truss_display_list, GL_COMPILE)
        self._draw_night_ground()
        self._draw_ballast_blocks()
        self._draw_vertical_columns()
        self._draw_roof_frame()
        glEndList()

        self.mesh_structure_display_list = glGenLists(1)
        glNewList(self.mesh_structure_display_list, GL_COMPILE)
        self._draw_mesh_suspension_and_housings()
        glEndList()

    def _draw_night_ground(self):
        """
        Renders the ground plane with back-face culling enabled so that
        when viewed from BELOW ground level (Z < 0), the ground is 100% transparent
        and does not obstruct the view of the structure and LED ceiling!
        """
        glDisable(GL_LIGHTING)
        
        # 1. Solid Asphalt Top-Surface (Culled when looking from below ground)
        glEnable(GL_CULL_FACE)
        glCullFace(GL_BACK)
        glColor4f(0.035, 0.042, 0.055, 1.0)
        glBegin(GL_QUADS)
        # Counter-clockwise winding when viewed from above (+Z)
        glVertex3f(-30.0, -20.0, 0.0)
        glVertex3f( 30.0, -20.0, 0.0)
        glVertex3f( 30.0,  20.0, 0.0)
        glVertex3f(-30.0,  20.0, 0.0)
        glEnd()
        glDisable(GL_CULL_FACE)

        # 2. Stage reference grid lines (Visible from both above and below ground)
        glColor4f(0.12, 0.15, 0.20, 0.6)
        glLineWidth(1.0)
        glBegin(GL_LINES)
        for x in np.arange(-24.0, 24.1, 2.0):
            glVertex3f(x, -18.0, 0.001)
            glVertex3f(x,  18.0, 0.001)
        for y in np.arange(-18.0, 18.1, 2.0):
            glVertex3f(-24.0, y, 0.001)
            glVertex3f( 24.0, y, 0.001)
        glEnd()
        glEnable(GL_LIGHTING)

    def _draw_box(self, cx, cy, cz, sx, sy, sz, color):
        """Draws a solid 3D box centered at (cx, cy, cz) with dimensions (sx, sy, sz)."""
        hx, hy, hz = sx / 2.0, sy / 2.0, sz / 2.0
        glMaterialfv(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE, color)

        glBegin(GL_QUADS)
        # Top (+Z)
        glNormal3f(0.0, 0.0, 1.0)
        glVertex3f(cx - hx, cy - hy, cz + hz); glVertex3f(cx + hx, cy - hy, cz + hz)
        glVertex3f(cx + hx, cy + hy, cz + hz); glVertex3f(cx - hx, cy + hy, cz + hz)
        # Bottom (-Z)
        glNormal3f(0.0, 0.0, -1.0)
        glVertex3f(cx - hx, cy - hy, cz - hz); glVertex3f(cx - hx, cy + hy, cz - hz)
        glVertex3f(cx + hx, cy + hy, cz - hz); glVertex3f(cx + hx, cy - hy, cz - hz)
        # Front (+Y)
        glNormal3f(0.0, 1.0, 0.0)
        glVertex3f(cx - hx, cy + hy, cz - hz); glVertex3f(cx - hx, cy + hy, cz + hz)
        glVertex3f(cx + hx, cy + hy, cz + hz); glVertex3f(cx + hx, cy + hy, cz - hz)
        # Back (-Y)
        glNormal3f(0.0, -1.0, 0.0)
        glVertex3f(cx - hx, cy - hy, cz - hz); glVertex3f(cx + hx, cy - hy, cz - hz)
        glVertex3f(cx + hx, cy - hy, cz + hz); glVertex3f(cx - hx, cy - hy, cz + hz)
        # Right (+X)
        glNormal3f(1.0, 0.0, 0.0)
        glVertex3f(cx + hx, cy - hy, cz - hz); glVertex3f(cx + hx, cy + hy, cz - hz)
        glVertex3f(cx + hx, cy + hy, cz + hz); glVertex3f(cx + hx, cy - hy, cz + hz)
        # Left (-X)
        glNormal3f(-1.0, 0.0, 0.0)
        glVertex3f(cx - hx, cy - hy, cz - hz); glVertex3f(cx - hx, cy - hy, cz + hz)
        glVertex3f(cx - hx, cy + hy, cz + hz); glVertex3f(cx - hx, cy + hy, cz - hz)
        glEnd()

    def _draw_ballast_blocks(self):
        """Draws the ballast blocks with top mounting plates for the 6 vertical columns."""
        ballast_color = [0.12, 0.13, 0.16, 1.0]
        plate_color = [0.45, 0.48, 0.52, 1.0]
        base_z = BALLAST_HEIGHT / 2.0

        for col_x, col_y in self.columns:
            # 1. Main concrete/steel ballast block
            self._draw_box(
                col_x, col_y, base_z,
                BALLAST_WIDTH, BALLAST_LENGTH, BALLAST_HEIGHT,
                ballast_color
            )
            # 2. Top aluminum coupler baseplate connecting to column chords
            self._draw_box(
                col_x, col_y, BALLAST_HEIGHT + 0.015,
                TRUSS_PROFILE_SIZE * 1.15, TRUSS_PROFILE_SIZE * 1.15, 0.03,
                plate_color
            )

    def _draw_solid_chord_tube(self, cx, cy, z1, z2, radius=0.024):
        """Draws a solid 4-sided prismatic chord tube with metallic lighting normals."""
        r = radius
        # 4 faces around local (cx, cy)
        glBegin(GL_QUADS)
        # Face 1 (+X)
        glNormal3f(1.0, 0.0, 0.0)
        glVertex3f(cx + r, cy - r, z1); glVertex3f(cx + r, cy + r, z1)
        glVertex3f(cx + r, cy + r, z2); glVertex3f(cx + r, cy - r, z2)
        # Face 2 (-X)
        glNormal3f(-1.0, 0.0, 0.0)
        glVertex3f(cx - r, cy + r, z1); glVertex3f(cx - r, cy - r, z1)
        glVertex3f(cx - r, cy - r, z2); glVertex3f(cx - r, cy + r, z2)
        # Face 3 (+Y)
        glNormal3f(0.0, 1.0, 0.0)
        glVertex3f(cx + r, cy + r, z1); glVertex3f(cx - r, cy + r, z1)
        glVertex3f(cx - r, cy + r, z2); glVertex3f(cx + r, cy + r, z2)
        # Face 4 (-Y)
        glNormal3f(0.0, -1.0, 0.0)
        glVertex3f(cx - r, cy - r, z1); glVertex3f(cx + r, cy - r, z1)
        glVertex3f(cx + r, cy - r, z2); glVertex3f(cx - r, cy - r, z2)
        glEnd()

    def _draw_vertical_columns(self):
        """Draws the 6 vertical H40V columns with solid volumetric 48mm chords and lacing."""
        z_start = BALLAST_HEIGHT + 0.03
        z_end = TRUSS_HEIGHT - TRUSS_PROFILE_SIZE  # 4.60m
        hw = TRUSS_PROFILE_SIZE / 2.0
        corners = [(-hw, -hw), (hw, -hw), (hw, hw), (-hw, hw)]

        aluminum_chord = [0.85, 0.88, 0.94, 1.0]
        aluminum_lacing = [0.72, 0.75, 0.80, 1.0]

        for col_x, col_y in self.columns:
            # 1. Four solid volumetric chords (48mm diameter)
            glMaterialfv(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE, aluminum_chord)
            glMaterialfv(GL_FRONT_AND_BACK, GL_SPECULAR, [0.7, 0.7, 0.8, 1.0])
            glMaterialf(GL_FRONT_AND_BACK, GL_SHININESS, 48.0)

            for cx, cy in corners:
                self._draw_solid_chord_tube(col_x + cx, col_y + cy, z_start, z_end, radius=0.024)

            # 2. Diagonal lacing between chords
            glLineWidth(2.0)
            glMaterialfv(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE, aluminum_lacing)
            glBegin(GL_LINES)
            height = z_end - z_start
            num_bays = max(1, int(round(height / TRUSS_PROFILE_SIZE)))
            dz_bay = height / num_bays
            for i in range(num_bays):
                z0 = z_start + i * dz_bay
                z1 = z_start + (i + 1) * dz_bay
                for j in range(4):
                    c0 = corners[j]
                    c1 = corners[(j + 1) % 4]
                    if i % 2 == 0:
                        glVertex3f(col_x + c0[0], col_y + c0[1], z0)
                        glVertex3f(col_x + c1[0], col_y + c1[1], z1)
                    else:
                        glVertex3f(col_x + c1[0], col_y + c1[1], z0)
                        glVertex3f(col_x + c0[0], col_y + c0[1], z1)
                    glVertex3f(col_x + c0[0], col_y + c0[1], z1)
                    glVertex3f(col_x + c1[0], col_y + c1[1], z1)
            glEnd()

    def _draw_horizontal_truss_segment(self, p1, p2, width=TRUSS_PROFILE_SIZE):
        """Draws a horizontal square truss segment with 4 chords and lacing."""
        dx = p2[0] - p1[0]
        dy = p2[1] - p1[1]
        dz = p2[2] - p1[2]
        length = math.sqrt(dx * dx + dy * dy + dz * dz)
        if length < 1e-4:
            return

        hw = width / 2.0
        chord_color = [0.84, 0.87, 0.92, 1.0]
        lacing_color = [0.70, 0.73, 0.78, 1.0]

        glPushMatrix()
        glTranslatef(p1[0], p1[1], p1[2])

        azimuth = math.degrees(math.atan2(dy, dx))
        elevation = math.degrees(math.atan2(math.sqrt(dx * dx + dy * dy), dz))

        glRotatef(azimuth, 0, 0, 1)
        glRotatef(elevation, 0, 1, 0)

        # 4 Main Chords
        glLineWidth(3.0)
        glMaterialfv(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE, chord_color)
        glMaterialfv(GL_FRONT_AND_BACK, GL_SPECULAR, [0.6, 0.6, 0.7, 1.0])
        glMaterialf(GL_FRONT_AND_BACK, GL_SHININESS, 32.0)

        glBegin(GL_LINES)
        corners = [(-hw, -hw), (hw, -hw), (hw, hw), (-hw, hw)]
        for cx, cy in corners:
            glVertex3f(cx, cy, 0.0)
            glVertex3f(cx, cy, length)
        glEnd()

        # Diagonal lacing
        bay_step = width
        num_bays = max(1, int(round(length / bay_step)))
        dz_bay = length / num_bays

        glLineWidth(1.6)
        glMaterialfv(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE, lacing_color)
        glBegin(GL_LINES)
        for i in range(num_bays):
            z0 = i * dz_bay
            z1 = (i + 1) * dz_bay
            for j in range(4):
                c0 = corners[j]
                c1 = corners[(j + 1) % 4]
                if i % 2 == 0:
                    glVertex3f(c0[0], c0[1], z0); glVertex3f(c1[0], c1[1], z1)
                else:
                    glVertex3f(c1[0], c1[1], z0); glVertex3f(c0[0], c0[1], z1)
                glVertex3f(c0[0], c0[1], z1); glVertex3f(c1[0], c1[1], z1)
        glEnd()

        glPopMatrix()

    def _draw_roof_frame(self):
        """Draws the roof perimeter trusses and cross-beams at height 4.80m."""
        z_roof = TRUSS_HEIGHT - TRUSS_PROFILE_SIZE / 2.0  # Centerline at 4.80m
        half_w = TRUSS_WIDTH / 2.0

        # Longitudinal perimeter trusses along front and back rows (2 spans of 8.85m)
        for row_y in [COL_Y_FRONT, COL_Y_BACK]:
            for i in range(len(self.x_positions) - 1):
                x1 = self.x_positions[i]
                x2 = self.x_positions[i + 1]
                self._draw_horizontal_truss_segment(
                    (x1, row_y, z_roof),
                    (x2, row_y, z_roof)
                )

        # Transverse cross-beams connecting each column pair across the 6.0m span
        for col_x in self.x_positions:
            self._draw_horizontal_truss_segment(
                (col_x, -half_w, z_roof),
                (col_x, half_w, z_roof)
            )

        # Intermediate roof support cross-trusses at quarter spans
        for x_mid in [-TRUSS_LENGTH / 4.0, TRUSS_LENGTH / 4.0]:
            self._draw_horizontal_truss_segment(
                (x_mid, -half_w, z_roof),
                (x_mid, half_w, z_roof)
            )

        # Corner / Junction cubes (Prolyte Box-40V) at the 6 column tops
        box_size = TRUSS_PROFILE_SIZE * 1.05
        box_color = [0.86, 0.89, 0.94, 1.0]
        for col_x, col_y in self.columns:
            self._draw_box(col_x, col_y, z_roof, box_size, box_size, box_size, box_color)

    def _draw_mesh_suspension_and_housings(self):
        """Draws the stainless-steel tension wires and black module backings."""
        half_len = TRUSS_LENGTH / 2.0
        half_wid = TRUSS_WIDTH / 2.0
        z_mesh = LED_UNDERHANG_Z
        z_truss_bottom = TRUSS_HEIGHT - TRUSS_PROFILE_SIZE  # 4.60m

        glDisable(GL_LIGHTING)

        # Tension mount wires running along Y (width) at 150mm intervals
        glColor4f(0.40, 0.44, 0.50, 0.5)
        glLineWidth(1.0)
        glBegin(GL_LINES)
        xs = np.linspace(-half_len + LED_CELL_SIZE / 2.0, half_len - LED_CELL_SIZE / 2.0, GRID_WIDTH)
        for x in xs:
            glVertex3f(x, -half_wid, z_mesh)
            glVertex3f(x,  half_wid, z_mesh)

        # Horizontal flexible connector ribbons along X (length)
        glColor4f(0.15, 0.17, 0.20, 0.4)
        ys = np.linspace(-half_wid + LED_CELL_SIZE / 2.0, half_wid - LED_CELL_SIZE / 2.0, GRID_HEIGHT)
        for y in ys:
            glVertex3f(-half_len, y, z_mesh)
            glVertex3f( half_len, y, z_mesh)

        # Vertical hanger wires suspending mesh from roof trusses
        glColor4f(0.55, 0.58, 0.65, 0.7)
        for col_x in list(self.x_positions) + [-TRUSS_LENGTH / 4.0, TRUSS_LENGTH / 4.0]:
            for y_hang in np.linspace(-half_wid, half_wid, 9):
                glVertex3f(col_x, y_hang, z_truss_bottom)
                glVertex3f(col_x, y_hang, z_mesh)
        glEnd()

        # 34mm x 34mm Black Module Backing Casings (BaltLED P150)
        hm = LED_MODULE_SIZE / 2.0
        glColor4f(0.08, 0.09, 0.11, 1.0)
        glBegin(GL_QUADS)
        for cx, cy in zip(self.grid_centers_x, self.grid_centers_y):
            zb = z_mesh + 0.002
            glVertex3f(cx - hm, cy - hm, zb); glVertex3f(cx + hm, cy - hm, zb)
            glVertex3f(cx + hm, cy + hm, zb); glVertex3f(cx - hm, cy + hm, zb)
        glEnd()

        glEnable(GL_LIGHTING)

    def render(self, frame_rgb):
        """Renders the nocturnal scene with realistic pronounced additive LED bloom."""
        # 1. Render static truss rig and ballast
        if self.truss_display_list:
            glCallList(self.truss_display_list)

        # 2. Render dynamic ground light bounce (reflection of LED canopy on ground at night)
        self._render_ground_bounce(frame_rgb)

        # 3. Render mesh suspension wires & module housings
        if self.mesh_structure_display_list:
            glCallList(self.mesh_structure_display_list)

        # 4. Render discrete glowing LED diodes with pronounced additive night bloom
        self._render_discrete_leds_with_bloom(frame_rgb)

    def _render_ground_bounce(self, frame_rgb):
        """Renders soft colored bounce light onto the ground beneath the canopy."""
        if frame_rgb is None or not self.bounce_texture_id:
            return

        glBindTexture(GL_TEXTURE_2D, self.bounce_texture_id)
        h, w, _ = frame_rgb.shape
        glTexSubImage2D(GL_TEXTURE_2D, 0, 0, 0, w, h, GL_RGB, GL_UNSIGNED_BYTE, frame_rgb)

        half_len = TRUSS_LENGTH / 2.0 + 2.0
        half_wid = TRUSS_WIDTH / 2.0 + 2.0

        glDisable(GL_LIGHTING)
        glEnable(GL_TEXTURE_2D)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE)  # Additive bounce

        # Soft ground illumination
        glColor4f(0.40, 0.40, 0.45, 0.55)
        glBegin(GL_QUADS)
        glTexCoord2f(0.0, 1.0); glVertex3f(-half_len, -half_wid, 0.01)
        glTexCoord2f(1.0, 1.0); glVertex3f( half_len, -half_wid, 0.01)
        glTexCoord2f(1.0, 0.0); glVertex3f( half_len,  half_wid, 0.01)
        glTexCoord2f(0.0, 0.0); glVertex3f(-half_len,  half_wid, 0.01)
        glEnd()

        glDisable(GL_TEXTURE_2D)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glEnable(GL_LIGHTING)

    def _render_discrete_leds_with_bloom(self, frame_rgb):
        """
        Three-Tier Nighttime LED Rendering:
        Tier 1: Solid discrete 26mm LED emitter faces with high vibrance & hot-center boost.
        Tier 2: Inner hot flare halo (80mm) with intense additive gain.
        Tier 3: Outer atmospheric bloom aura (220mm) that creates authentic cinematic
                glowing clouds around people's heat signatures at night.
        """
        if frame_rgb is None:
            return

        flat_rgb = frame_rgb.reshape(-1, 3).astype(np.float32)

        # Dynamic high-contrast thermal vibrance boost
        # Active thermal areas are amplified so they shine brightly against the dark night
        intensity = np.max(flat_rgb, axis=1, keepdims=True)
        # S-curve gain for radiant core
        gain = 1.2 + 0.9 * (intensity / 255.0) ** 1.5
        boosted_core = np.clip(flat_rgb * gain, 0.0, 255.0).astype(np.uint8)
        core_colors = np.repeat(boosted_core, 4, axis=0)

        glDisable(GL_LIGHTING)
        glDisable(GL_CULL_FACE)  # Double-sided visibility

        # TIER 1: Solid Discrete LED Emitter Faces
        glDisable(GL_TEXTURE_2D)
        glEnableClientState(GL_VERTEX_ARRAY)
        glEnableClientState(GL_COLOR_ARRAY)

        glVertexPointer(3, GL_FLOAT, 0, self.led_vertices)
        glColorPointer(3, GL_UNSIGNED_BYTE, 0, core_colors)
        glDrawArrays(GL_QUADS, 0, TOTAL_LEDS * 4)

        glDisableClientState(GL_COLOR_ARRAY)
        glDisableClientState(GL_VERTEX_ARRAY)

        # ADDITIVE BLOOM PASSES (Tiers 2 & 3)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE)  # Additive optical accumulation
        glDepthMask(GL_FALSE)               # Glow halos don't occlude each other
        glEnable(GL_TEXTURE_2D)
        glBindTexture(GL_TEXTURE_2D, self.glow_texture_id)

        glEnableClientState(GL_VERTEX_ARRAY)
        glEnableClientState(GL_COLOR_ARRAY)
        glEnableClientState(GL_TEXTURE_COORD_ARRAY)

        # TIER 2: Inner Hot Flare Halos (80mm)
        flare_colors = (flat_rgb * (NIGHT_GLOW_INTENSITY * 0.75)).clip(0, 255).astype(np.uint8)
        flare_colors_repeated = np.repeat(flare_colors, 4, axis=0)

        glVertexPointer(3, GL_FLOAT, 0, self.flare_vertices)
        glColorPointer(3, GL_UNSIGNED_BYTE, 0, flare_colors_repeated)
        glTexCoordPointer(2, GL_FLOAT, 0, self.halo_uvs)
        glDrawArrays(GL_QUADS, 0, TOTAL_LEDS * 4)

        # TIER 3: Outer Atmospheric Bloom Aura (220mm)
        # Larger soft cloud around heat signatures
        aura_colors = (flat_rgb * (NIGHT_GLOW_INTENSITY * 0.40)).clip(0, 255).astype(np.uint8)
        aura_colors_repeated = np.repeat(aura_colors, 4, axis=0)

        glVertexPointer(3, GL_FLOAT, 0, self.aura_vertices)
        glColorPointer(3, GL_UNSIGNED_BYTE, 0, aura_colors_repeated)
        glDrawArrays(GL_QUADS, 0, TOTAL_LEDS * 4)

        glDisableClientState(GL_TEXTURE_COORD_ARRAY)
        glDisableClientState(GL_COLOR_ARRAY)
        glDisableClientState(GL_VERTEX_ARRAY)

        glDepthMask(GL_TRUE)
        glDisable(GL_TEXTURE_2D)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glEnable(GL_LIGHTING)
