"""
Main application entry point for the LED Matrix Canopy Simulator.
Emulates the physical LED matrix controller for the Raspberry Pi with thermal camera.
Supports both 3D Prolyte H40V Rig Stage View and Flat 2D LED Grid Mode with
real-time Thermal Color Palette Selection & Custom Palette Designer.
"""

import sys
import time
import pygame
from pygame.locals import *
from OpenGL.GL import *
import numpy as np

from config import (
    WINDOW_WIDTH, WINDOW_HEIGHT, WINDOW_TITLE, FPS_TARGET,
    UDP_HOST, UDP_PORT, GRID_WIDTH, GRID_HEIGHT, TOTAL_LEDS,
    DEFAULT_DEMO_MODE
)
from server import LEDMatrixServer
from truss_model import TrussModel
from renderer import SceneRenderer
from thermal_feeder import CrowdThermalSimulator
from thermal_palette import ThermalPaletteManager, PALETTE_NAMES
from grid_view_2d import FlatGrid2DView

import ctypes

def main():
    # Enable Native Windows High-DPI Awareness to prevent OS bitmap blurring / scaling
    if sys.platform == "win32":
        try:
            # Per-Monitor DPI Aware V2
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except Exception:
            try:
                ctypes.windll.user32.SetProcessDPIAware()
            except Exception:
                pass

    pygame.init()
    pygame.display.set_caption(WINDOW_TITLE)
    
    # Request multisampling / anti-aliasing and buffers
    try:
        pygame.display.gl_set_attribute(pygame.GL_MULTISAMPLEBUFFERS, 1)
        pygame.display.gl_set_attribute(pygame.GL_MULTISAMPLESAMPLES, 4)
    except Exception:
        pass
    pygame.display.gl_set_attribute(pygame.GL_DEPTH_SIZE, 24)
    pygame.display.gl_set_attribute(pygame.GL_DOUBLEBUFFER, 1)

    screen = pygame.display.set_mode(
        (WINDOW_WIDTH, WINDOW_HEIGHT),
        pygame.DOUBLEBUF | pygame.OPENGL | pygame.RESIZABLE
    )

    # 1. Initialize 3D Engine & Procedural Rig
    renderer = SceneRenderer(WINDOW_WIDTH, WINDOW_HEIGHT)
    model = TrussModel()
    model.build_geometry()

    # 2. Initialize 2D Flat LED Grid Mode
    grid_view_2d = FlatGrid2DView(WINDOW_WIDTH, WINDOW_HEIGHT)

    # 3. Initialize Thermal Palette Manager & Custom Palette Designer
    palette_mgr = ThermalPaletteManager(default_palette="Ironbow")

    # 4. Start Hardware Listener Server
    server = LEDMatrixServer(host=UDP_HOST, port=UDP_PORT)
    server.start()

    # 5. Initialize Built-in Thermal Crowd Generator
    mock_feeder = CrowdThermalSimulator(GRID_WIDTH, GRID_HEIGHT, num_people=14)

    # View & Feed Modes
    # view_mode: "2D" (Flat Grid & Palette Designer) or "3D" (Rig Scene)
    # source_mode: "CROWD" (Thermal camera simulation) or "PI_STREAM" (Raspberry Pi UDP packets)
    view_mode = "2D"
    source_mode = "CROWD"

    clock = pygame.time.Clock()
    running = True
    mouse_dragging_left = False
    mouse_dragging_right = False
    last_mouse_pos = (0, 0)

    print("\n" + "=" * 65)
    print("  LED MATRIX THERMAL SIMULATOR INITIALIZED")
    print(f"  Truss Rig: 17.71m x 6.00m x 5.00m (6 Columns: 3 per side, Prolyte H40V)")
    print(f"  LED Mesh: BaltLED P150 Discrete (150mm Pitch, 30mm Modules)")
    print(f"  Mounting: Underhung below upper truss at Z=4.58m | {GRID_WIDTH}x{GRID_HEIGHT} ({TOTAL_LEDS} LEDs)")
    print(f"  Modes: [Tab] / [V] Toggle Flat 2D Grid <-> 3D Scene")
    print(f"  Palettes: [P] Cycle Thermal Palette | [I] Invert | [E] Export Pi Code")
    print(f"  Listening for Raspberry Pi on UDP {UDP_HOST}:{UDP_PORT}")
    print("=" * 65 + "\n")

    while running:
        dt = clock.tick(FPS_TARGET) / 1000.0

        # Process UI Events
        for event in pygame.event.get():
            if event.type == QUIT:
                running = False
            
            elif event.type == VIDEORESIZE:
                renderer.reshape(event.w, event.h)
                grid_view_2d.reshape(event.w, event.h)

            elif event.type == MOUSEBUTTONDOWN:
                if event.button == 1:
                    if view_mode == "2D":
                        # Interactive 2D GUI click check
                        action_info = grid_view_2d.handle_mouse_click(event.pos[0], event.pos[1])
                        if action_info:
                            act = action_info["action"]
                            val = action_info["value"]
                            if act == "toggle_view":
                                view_mode = "3D" if view_mode == "2D" else "2D"
                            elif act == "set_source":
                                source_mode = val
                            elif act == "toggle_invert":
                                palette_mgr.toggle_invert()
                            elif act == "set_palette":
                                palette_mgr.set_palette(val)
                            elif act == "select_stop":
                                palette_mgr.select_stop(val)
                            elif act == "set_stop_swatch":
                                palette_mgr.set_selected_stop_color(val)
                            elif act == "adjust_channel":
                                palette_mgr.adjust_selected_stop_channel(val[0], val[1])
                            elif act == "load_preset_to_custom":
                                palette_mgr.load_preset_into_custom(val)
                            elif act == "export_code":
                                print("\n" + "=" * 55)
                                print(palette_mgr.export_pi_code())
                                print("=" * 55 + "\n")
                    else:
                        mouse_dragging_left = True

                elif event.button == 3:
                    if view_mode == "3D":
                        mouse_dragging_right = True

                elif event.button == 4:  # Scroll Wheel Up (Zoom in)
                    if view_mode == "3D":
                        renderer.camera.zoom(0.9)

                elif event.button == 5:  # Scroll Wheel Down (Zoom out)
                    if view_mode == "3D":
                        renderer.camera.zoom(1.1)

                last_mouse_pos = event.pos

            elif event.type == MOUSEBUTTONUP:
                if event.button == 1:
                    mouse_dragging_left = False
                elif event.button == 3:
                    mouse_dragging_right = False

            elif event.type == MOUSEMOTION:
                if view_mode == "2D":
                    grid_view_2d.handle_mouse_motion(event.pos[0], event.pos[1])
                else:
                    dx = event.pos[0] - last_mouse_pos[0]
                    dy = event.pos[1] - last_mouse_pos[1]
                    if mouse_dragging_left:
                        renderer.camera.orbit(dx * 0.4, -dy * 0.4)
                    elif mouse_dragging_right:
                        renderer.camera.pan(dx, dy)
                last_mouse_pos = event.pos

            elif event.type == KEYDOWN:
                if event.key == K_ESCAPE:
                    running = False
                elif event.key in [K_TAB, K_v]:
                    # Toggle between Flat 2D Grid and 3D Scene View
                    view_mode = "3D" if view_mode == "2D" else "2D"
                elif event.key == K_SPACE:
                    # Toggle feed source between Mock Crowd and Pi Stream
                    source_mode = "PI_STREAM" if source_mode == "CROWD" else "CROWD"
                elif event.key == K_p:
                    # Cycle thermal color palette
                    palette_mgr.cycle_palette(1)
                elif event.key == K_i:
                    # Invert thermal palette
                    palette_mgr.toggle_invert()
                elif event.key == K_e:
                    # Export Python code for Raspberry Pi
                    grid_view_2d.show_export_overlay = not grid_view_2d.show_export_overlay
                    print("\n" + "=" * 55)
                    print(palette_mgr.export_pi_code())
                    print("=" * 55 + "\n")
                elif event.key == K_h:
                    # Cycle 3D HUD mode: Detailed (0) -> Controls Only (1) -> No HUD (2)
                    renderer.cycle_hud_mode()
                elif event.key == K_r:
                    # Reset camera (3D)
                    renderer.camera.reset_isometric()
                elif event.key in [K_1, K_2, K_3, K_4, K_5]:
                    preset_id = event.key - K_0
                    renderer.camera.set_preset(preset_id)

        # Frame Acquisition & Thermal Palette Colorization:
        # If Raspberry Pi is actively transmitting over UDP and user selected PI_STREAM, use its feed.
        is_conn = server.is_client_connected(timeout=2.0)
        if source_mode == "PI_STREAM" and is_conn:
            raw_heat = server.get_latest_heat()
            if raw_heat is not None:
                current_heat = raw_heat
                current_frame = palette_mgr.apply(raw_heat)
            else:
                # Client sent pre-colored RGB
                current_frame = server.get_latest_frame()
                current_heat = None
            effective_demo = False
        else:
            # Built-in dynamic crowd thermal camera simulation
            current_heat = mock_feeder.generate_frame()
            current_frame = palette_mgr.apply(current_heat)
            effective_demo = True

        # Status telemetry for HUD
        client_desc = (
            f"Connected from {server.last_client_addr[0]}:{server.last_client_addr[1]} ({server.format_detected})"
            if is_conn else "Waiting for Raspberry Pi connection..."
        )

        stats = {
            "width": GRID_WIDTH,
            "height": GRID_HEIGHT,
            "total_leds": TOTAL_LEDS,
            "listen_host": UDP_HOST,
            "listen_port": UDP_PORT,
            "client_status": client_desc,
            "is_connected": is_conn,
            "packets": server.packets_received,
            "rx_fps": server.fps,
            "render_fps": clock.get_fps(),
            "colormap": palette_mgr.active_palette_name,
            "demo_mode": effective_demo,
            "source_mode": "MOCK CROWD" if effective_demo else "PI HARDWARE",
            "palette_name": palette_mgr.active_palette_name,
        }

        # Render Pipeline based on active view_mode
        if view_mode == "3D":
            renderer.begin_3d()
            model.render(current_frame)
            renderer.render_hud(stats)
        else:
            grid_view_2d.render(current_frame, current_heat, palette_mgr, source_mode, is_conn)

        pygame.display.flip()

    # Clean shutdown
    server.stop()
    pygame.quit()
    sys.exit(0)

if __name__ == "__main__":
    main()
