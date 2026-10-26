"""
Interactive Flat 2D LED Grid Mode with Thermal Color Palette & Custom Palette Picker.
Renders the 118x40 matrix with true 17.71m x 6.0m proportions, discrete diode modules,
interactive mouse-picking inspection, thermal temperature telemetry, and a custom
palette designer for testing color gradients before deploying to the Raspberry Pi.
"""

import math
import pygame
from OpenGL.GL import *
from OpenGL.GLU import *
import numpy as np

from config import (
    GRID_WIDTH, GRID_HEIGHT, TOTAL_LEDS,
    TRUSS_LENGTH, TRUSS_WIDTH, LED_CELL_SIZE
)
from thermal_palette import (
    ThermalPaletteManager, PALETTE_NAMES, PRESET_PALETTES, QUICK_SWATCHES
)

class FlatGrid2DView:
    def __init__(self, win_w=1280, win_h=720):
        self.win_w = win_w
        self.win_h = win_h
        self.hud_tex_id = None
        
        # Interactive hover state
        self.hovered_cell = None  # (col, row)
        self.buttons = []         # List of clickable UI elements: (rect, action_type, value)
        self.show_export_overlay = False
        self.exported_code_cache = ""

        pygame.font.init()
        font_list = ["segoeui", "tahoma", "arial", "consolas"]
        self.font_title = pygame.font.SysFont(font_list, 18, bold=True)
        self.font_main = pygame.font.SysFont(font_list, 14, bold=True)
        self.font_small = pygame.font.SysFont(font_list, 12, bold=False)
        self.font_bold = pygame.font.SysFont(font_list, 13, bold=True)
        self.font_tiny = pygame.font.SysFont(font_list, 11, bold=False)

        self._init_gl()
        self._compute_layout()

    def _init_gl(self):
        self.hud_tex_id = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, self.hud_tex_id)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)

    def reshape(self, w, h):
        self.win_w = max(1, w)
        self.win_h = max(1, h)
        self._compute_layout()

    def _compute_layout(self):
        """Calculates 2D canvas coordinates and UI button bounding boxes."""
        header_h = 50
        panel_h = 230
        avail_h = self.win_h - header_h - panel_h - 15
        avail_w = self.win_w - 60

        # Preserve matrix aspect ratio: 118 / 40 = 2.95
        aspect = GRID_WIDTH / GRID_HEIGHT
        
        if avail_w / avail_h > aspect:
            self.grid_h = max(140, int(avail_h))
            self.grid_w = int(self.grid_h * aspect)
        else:
            self.grid_w = max(380, int(avail_w))
            self.grid_h = int(self.grid_w / aspect)

        self.grid_x = (self.win_w - self.grid_w) // 2
        self.grid_y = header_h + 8

        self.cell_w = self.grid_w / float(GRID_WIDTH)
        self.cell_h = self.grid_h / float(GRID_HEIGHT)

        # Precompute 2D Quad Vertices for all 4,720 pixels
        pad_module = max(0.5, self.cell_w * 0.12)
        pad_diode = max(1.4, self.cell_w * 0.28)

        xs = np.arange(GRID_WIDTH, dtype=np.float32) * self.cell_w + self.grid_x
        ys = np.arange(GRID_HEIGHT, dtype=np.float32) * self.cell_h + self.grid_y
        xx, yy = np.meshgrid(xs, ys)
        px = xx.flatten()
        py = yy.flatten()

        # Diode Quads (TOTAL_LEDS * 4, 2)
        quads_diode = np.zeros((TOTAL_LEDS, 4, 2), dtype=np.float32)
        quads_diode[:, 0, :] = np.column_stack((px + pad_diode, py + pad_diode))
        quads_diode[:, 1, :] = np.column_stack((px + self.cell_w - pad_diode, py + pad_diode))
        quads_diode[:, 2, :] = np.column_stack((px + self.cell_w - pad_diode, py + self.cell_h - pad_diode))
        quads_diode[:, 3, :] = np.column_stack((px + pad_diode, py + self.cell_h - pad_diode))
        self.diode_vertices = np.ascontiguousarray(quads_diode.reshape(-1, 2))

        # Casing Quads (TOTAL_LEDS * 4, 2)
        quads_case = np.zeros((TOTAL_LEDS, 4, 2), dtype=np.float32)
        quads_case[:, 0, :] = np.column_stack((px + pad_module, py + pad_module))
        quads_case[:, 1, :] = np.column_stack((px + self.cell_w - pad_module, py + pad_module))
        quads_case[:, 2, :] = np.column_stack((px + self.cell_w - pad_module, py + self.cell_h - pad_module))
        quads_case[:, 3, :] = np.column_stack((px + pad_module, py + self.cell_h - pad_module))
        self.case_vertices = np.ascontiguousarray(quads_case.reshape(-1, 2))

    def handle_mouse_motion(self, mx, my):
        """Tracks hovered LED cell coordinates for real-time inspection."""
        if (self.grid_x <= mx < self.grid_x + self.grid_w and
            self.grid_y <= my < self.grid_y + self.grid_h):
            col = int((mx - self.grid_x) / self.cell_w)
            row = int((my - self.grid_y) / self.cell_h)
            col = max(0, min(GRID_WIDTH - 1, col))
            row = max(0, min(GRID_HEIGHT - 1, row))
            self.hovered_cell = (col, row)
        else:
            self.hovered_cell = None

    def handle_mouse_click(self, mx, my):
        """Processes clicks on on-screen buttons. Returns action dict or None."""
        if self.show_export_overlay:
            # Check close button on dialog
            for rect, action_type, value in self.buttons:
                if action_type == "close_export" and rect.collidepoint(mx, my):
                    self.show_export_overlay = False
                    return None
            self.show_export_overlay = False
            return None

        for rect, action_type, value in self.buttons:
            if rect.collidepoint(mx, my):
                if action_type == "export_code":
                    self.show_export_overlay = True
                return {"action": action_type, "value": value}
        return None

    def render(self, frame_rgb, heat_frame, palette_mgr, source_mode, is_connected):
        """Renders the entire 2D LED matrix canvas, diode arrays, and interactive UI."""
        # Set up 2D Orthographic Projection
        glViewport(0, 0, self.win_w, self.win_h)
        glClearColor(0.04, 0.05, 0.07, 1.0)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluOrtho2D(0, self.win_w, self.win_h, 0)

        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()

        glDisable(GL_DEPTH_TEST)
        glDisable(GL_LIGHTING)
        try:
            glDisable(GL_MULTISAMPLE)
        except Exception:
            pass
        glDisable(GL_TEXTURE_2D)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

        # 1. Background Grid Backplate
        glColor4f(0.06, 0.08, 0.11, 1.0)
        glBegin(GL_QUADS)
        glVertex2f(self.grid_x - 4, self.grid_y - 4)
        glVertex2f(self.grid_x + self.grid_w + 4, self.grid_y - 4)
        glVertex2f(self.grid_x + self.grid_w + 4, self.grid_y + self.grid_h + 4)
        glVertex2f(self.grid_x - 4, self.grid_y + self.grid_h + 4)
        glEnd()

        # 2. Draw Wire Mesh Grid Lines
        glColor4f(0.12, 0.15, 0.20, 0.7)
        glLineWidth(1.0)
        glBegin(GL_LINES)
        for col in range(GRID_WIDTH + 1):
            gx = self.grid_x + col * self.cell_w
            glVertex2f(gx, self.grid_y)
            glVertex2f(gx, self.grid_y + self.grid_h)
        for row in range(GRID_HEIGHT + 1):
            gy = self.grid_y + row * self.cell_h
            glVertex2f(self.grid_x, gy)
            glVertex2f(self.grid_x + self.grid_w, gy)
        glEnd()

        # 3. Draw Module Casings (Dark square bases)
        glColor4f(0.10, 0.12, 0.15, 1.0)
        glEnableClientState(GL_VERTEX_ARRAY)
        glVertexPointer(2, GL_FLOAT, 0, self.case_vertices)
        glDrawArrays(GL_QUADS, 0, TOTAL_LEDS * 4)
        glDisableClientState(GL_VERTEX_ARRAY)

        # 4. Draw Active Colored LED Diodes using GPU Color Array
        if frame_rgb is not None:
            flat_rgb = frame_rgb.reshape(-1, 3)
            boosted = np.clip(flat_rgb.astype(np.float32) * 1.15, 0.0, 255.0).astype(np.uint8)
            colors = np.repeat(boosted, 4, axis=0)

            glEnableClientState(GL_VERTEX_ARRAY)
            glEnableClientState(GL_COLOR_ARRAY)

            glVertexPointer(2, GL_FLOAT, 0, self.diode_vertices)
            glColorPointer(3, GL_UNSIGNED_BYTE, 0, colors)
            glDrawArrays(GL_QUADS, 0, TOTAL_LEDS * 4)

            glDisableClientState(GL_COLOR_ARRAY)
            glDisableClientState(GL_VERTEX_ARRAY)

        # 5. Highlight Hovered Cell with White Focus Ring
        if self.hovered_cell:
            hc, hr = self.hovered_cell
            hx = self.grid_x + hc * self.cell_w
            hy = self.grid_y + hr * self.cell_h
            glColor4f(1.0, 1.0, 1.0, 0.95)
            glLineWidth(2.0)
            glBegin(GL_LINE_LOOP)
            glVertex2f(hx, hy)
            glVertex2f(hx + self.cell_w, hy)
            glVertex2f(hx + self.cell_w, hy + self.cell_h)
            glVertex2f(hx, hy + self.cell_h)
            glEnd()

        # 6. Render 2D UI Overlay (Control Panel, Palettes, Custom Picker, Tooltip)
        self._render_ui_layer(frame_rgb, heat_frame, palette_mgr, source_mode, is_connected)

    def _render_ui_layer(self, frame_rgb, heat_frame, pal, source_mode, is_connected):
        """Draws the 2D UI layer and buttons onto a single texture overlay."""
        ui_surf = pygame.Surface((self.win_w, self.win_h), pygame.SRCALPHA)
        self.buttons = []

        # ---------------- HEADER SECTION ----------------
        title_surf = self.font_title.render("FLAT 2D LED MATRIX CANVAS (118 x 40)", True, (255, 220, 80))
        ui_surf.blit(title_surf, (22, 10))

        sub_text = (
            f"Rig: {TRUSS_LENGTH}m x {TRUSS_WIDTH}m | Pitch: {int(LED_CELL_SIZE*1000)}mm | "
            f"Diodes: {TOTAL_LEDS} | Active Thermal Palette: [{pal.active_palette_name}]"
        )
        ui_surf.blit(self.font_small.render(sub_text, True, (160, 180, 205)), (24, 31))

        # View Mode Toggle Button (Top Right)
        btn_view_rect = pygame.Rect(self.win_w - 230, 10, 210, 32)
        pygame.draw.rect(ui_surf, (30, 60, 100, 230), btn_view_rect, border_radius=6)
        pygame.draw.rect(ui_surf, (60, 130, 220, 255), btn_view_rect, 1, border_radius=6)
        txt_v = self.font_bold.render("SWITCH TO 3D RIG [Tab]", True, (230, 245, 255))
        ui_surf.blit(txt_v, (btn_view_rect.x + 14, btn_view_rect.y + 8))
        self.buttons.append((btn_view_rect, "toggle_view", None))

        # ---------------- FEED SOURCE & UTILITY BAR ----------------
        bx = self.grid_x
        by = self.grid_y + self.grid_h + 10

        ui_surf.blit(self.font_bold.render("FEED:", True, (200, 215, 230)), (bx, by + 4))
        bx += 48

        sources = [
            ("MOCK CROWD (THERMAL CAMERA)", "CROWD", (100, 200, 255)),
            ("PI HARDWARE STREAM (UDP)", "PI_STREAM", (120, 255, 120)),
        ]
        for label, s_val, col in sources:
            is_active = (source_mode == s_val)
            tw = self.font_small.size(label)[0] + 16
            btn_rect = pygame.Rect(bx, by, tw, 24)
            bg_col = (*col, 200) if is_active else (25, 32, 45, 200)
            border_col = (255, 255, 255, 255) if is_active else (50, 65, 85, 255)
            pygame.draw.rect(ui_surf, bg_col, btn_rect, border_radius=4)
            pygame.draw.rect(ui_surf, border_col, btn_rect, 1, border_radius=4)
            txt_col = (10, 15, 25) if is_active else (200, 210, 225)
            ui_surf.blit(self.font_small.render(label, True, txt_col), (bx + 8, by + 5))
            self.buttons.append((btn_rect, "set_source", s_val))
            bx += tw + 6

        # Invert Palette Button
        btn_inv = pygame.Rect(bx + 10, by, 115, 24)
        inv_active = pal.invert
        pygame.draw.rect(ui_surf, (80, 50, 20, 220) if inv_active else (30, 40, 55, 220), btn_inv, border_radius=4)
        pygame.draw.rect(ui_surf, (255, 160, 50, 255) if inv_active else (50, 65, 85, 255), btn_inv, 1, border_radius=4)
        inv_text = "INVERT: ON" if inv_active else "INVERT: OFF"
        ui_surf.blit(self.font_small.render(inv_text, True, (255, 200, 100) if inv_active else (180, 190, 205)), (btn_inv.x + 12, by + 5))
        self.buttons.append((btn_inv, "toggle_invert", None))

        # Export Pi Code Button
        btn_exp = pygame.Rect(self.grid_x + self.grid_w - 180, by, 180, 24)
        pygame.draw.rect(ui_surf, (20, 65, 45, 230), btn_exp, border_radius=4)
        pygame.draw.rect(ui_surf, (50, 200, 120, 255), btn_exp, 1, border_radius=4)
        ui_surf.blit(self.font_bold.render("[EXPORT PI CODE]", True, (160, 255, 190)), (btn_exp.x + 16, by + 5))
        self.buttons.append((btn_exp, "export_code", None))

        # ---------------- THERMAL PALETTE CONTROL PANEL ----------------
        panel_y = by + 30
        panel_rect = pygame.Rect(self.grid_x, panel_y, self.grid_w, 162)
        pygame.draw.rect(ui_surf, (10, 14, 22, 230), panel_rect, border_radius=6)
        pygame.draw.rect(ui_surf, (35, 50, 75, 255), panel_rect, 1, border_radius=6)

        # ROW 1: BUILT-IN PALETTE BUTTONS
        py1 = panel_y + 8
        ui_surf.blit(self.font_bold.render("PALETTES [P]:", True, (255, 215, 80)), (self.grid_x + 10, py1 + 4))
        px1 = self.grid_x + 115

        for p_name in PALETTE_NAMES:
            is_active = (pal.active_palette_name == p_name)
            pw = self.font_small.size(p_name)[0] + 16
            btn_rect = pygame.Rect(px1, py1, pw, 22)

            # Swatch sample dot
            if p_name in PRESET_PALETTES:
                sample_col = PRESET_PALETTES[p_name][min(2, len(PRESET_PALETTES[p_name])-1)][1].astype(int)
            else:
                sample_col = pal.custom_stops[1]["rgb"]
            swatch_tuple = (int(sample_col[0]), int(sample_col[1]), int(sample_col[2]))

            bg_col = (45, 75, 110, 240) if is_active else (20, 26, 38, 220)
            border_col = (255, 220, 80, 255) if is_active else (45, 60, 80, 255)
            pygame.draw.rect(ui_surf, bg_col, btn_rect, border_radius=3)
            pygame.draw.rect(ui_surf, border_col, btn_rect, 1, border_radius=3)
            
            pygame.draw.circle(ui_surf, swatch_tuple, (px1 + 7, py1 + 11), 3)
            txt_col = (255, 240, 140) if is_active else (180, 195, 215)
            ui_surf.blit(self.font_small.render(p_name, True, txt_col), (px1 + 14, py1 + 4))
            self.buttons.append((btn_rect, "set_palette", p_name))
            px1 += pw + 5

        # ROW 2: CONTINUOUS 256-COLOR GRADIENT RAMP BAR & STOP MARKERS
        py2 = panel_y + 36
        ramp_x = self.grid_x + 115
        ramp_w = self.grid_w - 130
        ramp_h = 16

        ui_surf.blit(self.font_bold.render("HEAT RAMP:", True, (180, 200, 225)), (self.grid_x + 10, py2 + 2))
        
        # Render the 256 colors of the active LUT as a smooth horizontal gradient bar
        lut = pal.lut  # (256, 3) uint8
        ramp_surf = pygame.Surface((256, 1))
        # Fill surface with the 256 colors
        for i in range(256):
            ramp_surf.set_at((i, 0), (int(lut[i, 0]), int(lut[i, 1]), int(lut[i, 2])))
        scaled_ramp = pygame.transform.scale(ramp_surf, (ramp_w, ramp_h))
        ui_surf.blit(scaled_ramp, (ramp_x, py2))
        pygame.draw.rect(ui_surf, (60, 80, 110), (ramp_x, py2, ramp_w, ramp_h), 1)

        # Draw Cold (0) and Hot (255) labels
        ui_surf.blit(self.font_tiny.render("0: Cold", True, (140, 160, 190)), (ramp_x, py2 + ramp_h + 1))
        lbl_hot = self.font_tiny.render("255: Hot", True, (255, 180, 140))
        ui_surf.blit(lbl_hot, (ramp_x + ramp_w - lbl_hot.get_width(), py2 + ramp_h + 1))

        # Overlay Stop Handles for Custom Palette
        if pal.active_palette_name == "Custom":
            for s_idx, stop in enumerate(pal.custom_stops):
                sx = int(ramp_x + stop["pos"] * ramp_w)
                is_sel = (s_idx == pal.selected_stop_idx)
                handle_rect = pygame.Rect(sx - 7, py2 - 3, 14, ramp_h + 6)
                
                # Stop color box
                scol = (stop["rgb"][0], stop["rgb"][1], stop["rgb"][2])
                pygame.draw.rect(ui_surf, scol, handle_rect, border_radius=3)
                pygame.draw.rect(ui_surf, (255, 255, 255) if is_sel else (0, 0, 0), handle_rect, 2 if is_sel else 1, border_radius=3)
                self.buttons.append((handle_rect, "select_stop", s_idx))

        # ROW 3: COLOR CUSTOMIZER FOR THE SELECTED STOP
        py3 = panel_y + 68
        curr_stop = pal.custom_stops[pal.selected_stop_idx]
        cur_rgb = curr_stop["rgb"]
        stop_title = f"CUSTOM STOP #{pal.selected_stop_idx+1} ({curr_stop['label']} @ {int(curr_stop['pos']*100)}%):"
        ui_surf.blit(self.font_bold.render(stop_title, True, (255, 215, 80)), (self.grid_x + 10, py3 + 3))

        # Active Stop Color preview box
        swatch_rect = pygame.Rect(self.grid_x + 310, py3, 26, 20)
        pygame.draw.rect(ui_surf, (cur_rgb[0], cur_rgb[1], cur_rgb[2]), swatch_rect, border_radius=3)
        pygame.draw.rect(ui_surf, (255, 255, 255), swatch_rect, 1, border_radius=3)

        hex_str = f"#{cur_rgb[0]:02X}{cur_rgb[1]:02X}{cur_rgb[2]:02X} ({cur_rgb[0]},{cur_rgb[1]},{cur_rgb[2]})"
        ui_surf.blit(self.font_small.render(hex_str, True, (220, 230, 245)), (self.grid_x + 342, py3 + 3))

        # Quick Color Swatches to click
        px3 = self.grid_x + 510
        ui_surf.blit(self.font_small.render("Pick:", True, (160, 180, 205)), (px3, py3 + 3))
        px3 += 42
        for sw_name, sw_col in QUICK_SWATCHES:
            sw_btn = pygame.Rect(px3, py3 + 1, 16, 18)
            pygame.draw.rect(ui_surf, sw_col, sw_btn, border_radius=2)
            pygame.draw.rect(ui_surf, (70, 85, 110), sw_btn, 1, border_radius=2)
            self.buttons.append((sw_btn, "set_stop_swatch", sw_col))
            px3 += 20

        # Fine-tune RGB adjustments (-10 / +10)
        px3 += 12
        for c_idx, c_name in enumerate(["R", "G", "B"]):
            ui_surf.blit(self.font_small.render(c_name, True, (220, 220, 220)), (px3, py3 + 3))
            btn_dn = pygame.Rect(px3 + 14, py3, 18, 20)
            btn_up = pygame.Rect(px3 + 34, py3, 18, 20)
            pygame.draw.rect(ui_surf, (35, 45, 65), btn_dn, border_radius=3)
            pygame.draw.rect(ui_surf, (35, 45, 65), btn_up, border_radius=3)
            ui_surf.blit(self.font_bold.render("-", True, (220, 220, 220)), (btn_dn.x + 5, btn_dn.y + 2))
            ui_surf.blit(self.font_bold.render("+", True, (220, 220, 220)), (btn_up.x + 4, btn_up.y + 2))
            self.buttons.append((btn_dn, "adjust_channel", (c_idx, -15)))
            self.buttons.append((btn_up, "adjust_channel", (c_idx, 15)))
            px3 += 62

        # Base Templates for Custom Palette
        py3_sub = panel_y + 98
        ui_surf.blit(self.font_small.render("Base Custom on:", True, (150, 170, 195)), (self.grid_x + 10, py3_sub + 2))
        px3_sub = self.grid_x + 120
        for b_name in ["Ironbow", "Inferno", "Cyberpunk", "Ice & Fire", "Lava Fire"]:
            b_btn = pygame.Rect(px3_sub, py3_sub, self.font_tiny.size(b_name)[0] + 12, 18)
            pygame.draw.rect(ui_surf, (25, 35, 50), b_btn, border_radius=3)
            pygame.draw.rect(ui_surf, (50, 70, 95), b_btn, 1, border_radius=3)
            ui_surf.blit(self.font_tiny.render(b_name, True, (190, 210, 230)), (px3_sub + 6, py3_sub + 2))
            self.buttons.append((b_btn, "load_preset_to_custom", b_name))
            px3_sub += b_btn.width + 6

        # ROW 4: LIVE HOVER INSPECTION & STATUS BAR
        py4 = panel_y + 126
        pygame.draw.line(ui_surf, (25, 35, 50), (self.grid_x + 10, py4), (self.grid_x + self.grid_w - 10, py4), 1)
        py4 += 6

        if self.hovered_cell and frame_rgb is not None:
            col, row = self.hovered_cell
            rgb = frame_rgb[row, col]
            metric_x = col * LED_CELL_SIZE
            metric_y = row * LED_CELL_SIZE

            heat_val = heat_frame[row, col] if heat_frame is not None else 0
            est_temp_c = 20.0 + (float(heat_val) / 255.0) * 18.0  # Ambient 20°C to Human Body ~38°C

            hover_str = (
                f"INSPECTION: Pixel [{col:03d}, {row:02d}] | Metric: ({metric_x:.2f}m, {metric_y:.2f}m) | "
                f"Thermal Heat: {heat_val:3d} / 255 (~{est_temp_c:.1f}°C) | "
                f"LED Color: RGB({rgb[0]:3d}, {rgb[1]:3d}, {rgb[2]:3d}) | Hex: #{rgb[0]:02X}{rgb[1]:02X}{rgb[2]:02X}"
            )
            pygame.draw.rect(ui_surf, (int(rgb[0]), int(rgb[1]), int(rgb[2])), (self.grid_x + 14, py4 + 1, 16, 16), border_radius=3)
            pygame.draw.rect(ui_surf, (255, 255, 255), (self.grid_x + 14, py4 + 1, 16, 16), 1, border_radius=3)
            ui_surf.blit(self.font_main.render(hover_str, True, (255, 255, 255)), (self.grid_x + 38, py4 + 1))
        else:
            hint_str = "Hover over any diode in the matrix to inspect exact thermal sensor reading (0-255, °C) and resulting LED RGB color."
            ui_surf.blit(self.font_small.render(hint_str, True, (130, 150, 175)), (self.grid_x + 14, py4 + 2))

        # ---------------- EXPORT DIALOG OVERLAY (IF ACTIVE) ----------------
        if self.show_export_overlay:
            self._render_export_modal(ui_surf, pal)

        # Upload single UI layer surface to OpenGL texture with pixel-perfect nearest filtering
        data = pygame.image.tostring(ui_surf, "RGBA", False)
        glBindTexture(GL_TEXTURE_2D, self.hud_tex_id)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
        glTexImage2D(
            GL_TEXTURE_2D, 0, GL_RGBA,
            self.win_w, self.win_h, 0,
            GL_RGBA, GL_UNSIGNED_BYTE, data
        )

        glEnable(GL_TEXTURE_2D)
        glColor4f(1.0, 1.0, 1.0, 1.0)
        glBegin(GL_QUADS)
        glTexCoord2f(0.0, 0.0); glVertex2f(0, 0)
        glTexCoord2f(1.0, 0.0); glVertex2f(self.win_w, 0)
        glTexCoord2f(1.0, 1.0); glVertex2f(self.win_w, self.win_h)
        glTexCoord2f(0.0, 1.0); glVertex2f(0, self.win_h)
        glEnd()
        glDisable(GL_TEXTURE_2D)

    def _render_export_modal(self, ui_surf, pal):
        """Draws modal popup displaying Raspberry Pi code snippet ready to copy."""
        modal_w = 680
        modal_h = 360
        modal_x = (self.win_w - modal_w) // 2
        modal_y = (self.win_h - modal_h) // 2

        # Dim background
        dim_surf = pygame.Surface((self.win_w, self.win_h), pygame.SRCALPHA)
        dim_surf.fill((0, 0, 0, 180))
        ui_surf.blit(dim_surf, (0, 0))

        # Box
        modal_rect = pygame.Rect(modal_x, modal_y, modal_w, modal_h)
        pygame.draw.rect(ui_surf, (15, 20, 30, 250), modal_rect, border_radius=8)
        pygame.draw.rect(ui_surf, (70, 120, 180, 255), modal_rect, 2, border_radius=8)

        # Header
        ui_surf.blit(self.font_title.render("Raspberry Pi Thermal Palette Code Snippet", True, (255, 215, 80)), (modal_x + 20, modal_y + 16))
        
        # Code text block
        code_text = pal.export_pi_code()
        lines = code_text.split("\n")
        cy = modal_y + 48
        for line in lines:
            col = (130, 220, 160) if line.startswith("#") else (220, 235, 255)
            ui_surf.blit(self.font_small.render(line, True, col), (modal_x + 24, cy))
            cy += 17

        # Close button
        btn_close = pygame.Rect(modal_x + modal_w - 120, modal_y + modal_h - 40, 100, 28)
        pygame.draw.rect(ui_surf, (40, 70, 110), btn_close, border_radius=4)
        pygame.draw.rect(ui_surf, (100, 160, 240), btn_close, 1, border_radius=4)
        ui_surf.blit(self.font_bold.render("CLOSE [X]", True, (255, 255, 255)), (btn_close.x + 18, btn_close.y + 6))
        self.buttons.append((btn_close, "close_export", None))
