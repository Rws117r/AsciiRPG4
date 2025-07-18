# world_viewer.py
# A standalone application to view the generated world map with corrected zoom.

import pygame
import sys
import pickle
import os
from collections import Counter

class WorldViewer:
    """
    Initializes Pygame and loads a saved world map for viewing.
    Handles panning and centered zooming.
    """
    def __init__(self, world_file):
        pygame.init()
        self.WINDOW_WIDTH, self.WINDOW_HEIGHT = 1280, 720
        self.TILE_SIZE, self.FONT_SIZE = 16, 16
        self.FONT_NAME = 'JetBrainsMonoNL-Regular.ttf'
        self.FPS = 60
        self.COLORS = {"WHITE": (255, 255, 255), "YELLOW": (255, 255, 0)}

        self.screen = pygame.display.set_mode((self.WINDOW_WIDTH, self.WINDOW_HEIGHT), pygame.RESIZABLE)
        pygame.display.set_caption("World Viewer")
        self.clock = pygame.time.Clock()
        self.font = self.load_font()

        self.biomes = {
            'deep_ocean': {'char': '≈', 'color': (0, 0, 128)},
            'ocean': {'char': '~', 'color': (0, 0, 255)},
            'beach': {'char': '.', 'color': (210, 180, 140)},
            'plains': {'char': '.', 'color': (0, 128, 0)},
            'forest': {'char': '♣', 'color': (0, 100, 0)},
            'mountain': {'char': '^', 'color': (128, 128, 128)},
            'desert': {'char': '.', 'color': (210, 180, 140)},
            'swamp': {'char': ';', 'color': (128, 0, 128)},
            'river': {'char': '~', 'color': (0, 0, 255)}
        }

        self.world_map = self.load_world(world_file)
        if self.world_map is None:
            sys.exit()

        self.view_x = 0
        self.view_y = 0
        self.zoom_level = 1
        self.min_zoom = 1
        self.max_zoom = 16

    def load_font(self):
        font_path = os.path.join(os.path.dirname(__file__), self.FONT_NAME)
        try:
            return pygame.font.Font(font_path, self.FONT_SIZE)
        except pygame.error:
            return pygame.font.Font(None, self.FONT_SIZE)

    def load_world(self, filepath):
        try:
            with open(filepath, 'rb') as f:
                return pickle.load(f)
        except FileNotFoundError:
            print(f"Error: 'world.dat' not found. Please run 'world_generator.py' first.")
            return None
        except Exception as e:
            print(f"Error loading world file: {e}")
            return None

    def handle_input(self, events):
        """Handles user input for panning, zooming, and quitting."""
        for event in events:
            if event.type == pygame.QUIT:
                return False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return False

                pan_speed = self.zoom_level
                if event.key == pygame.K_UP: self.view_y -= pan_speed
                elif event.key == pygame.K_DOWN: self.view_y += pan_speed
                elif event.key == pygame.K_LEFT: self.view_x -= pan_speed
                elif event.key == pygame.K_RIGHT: self.view_x += pan_speed

                # --- Centered Zooming Logic ---
                if event.key == pygame.K_MINUS or event.key in [pygame.K_PLUS, pygame.K_EQUALS]:
                    # 1. Get world coordinate at the center of the screen BEFORE zoom
                    center_tile_x = (self.screen.get_width() // 2) // self.TILE_SIZE
                    center_tile_y = (self.screen.get_height() // 2) // self.TILE_SIZE
                    center_world_x = self.view_x + (center_tile_x * self.zoom_level)
                    center_world_y = self.view_y + (center_tile_y * self.zoom_level)
                    
                    old_zoom = self.zoom_level

                    # 2. Apply the zoom
                    if event.key == pygame.K_MINUS:
                        self.zoom_level = min(self.max_zoom, self.zoom_level * 2)
                    else: # Plus or Equals key
                        self.zoom_level = max(self.min_zoom, self.zoom_level // 2)

                    # 3. If zoom level actually changed, recalculate the view's top-left
                    #    offset to keep the center world coordinate under the cursor.
                    if old_zoom != self.zoom_level:
                        self.view_x = center_world_x - (center_tile_x * self.zoom_level)
                        self.view_y = center_world_y - (center_tile_y * self.zoom_level)

        return True

    def _get_condensed_tile(self, start_x, start_y):
        """Analyzes a block of world tiles and returns the most representative one."""
        if self.zoom_level == 1:
            if 0 <= start_x < self.world_map.shape[0] and 0 <= start_y < self.world_map.shape[1]:
                return self.world_map[start_x, start_y]
            return None

        tiles_in_block = []
        for i in range(self.zoom_level):
            for j in range(self.zoom_level):
                x, y = start_x + i, start_y + j
                if 0 <= x < self.world_map.shape[0] and 0 <= y < self.world_map.shape[1]:
                    tile = self.world_map[x, y]
                    if isinstance(tile, dict):
                        tiles_in_block.append(tuple(sorted(tile.items())))

        if not tiles_in_block: return None
        most_common_tile_tuple = Counter(tiles_in_block).most_common(1)[0][0]
        return dict(most_common_tile_tuple)

    def draw(self):
        """Draws the world map, cursor, and informational text."""
        self.screen.fill((0, 0, 0))
        if self.world_map is None: return

        screen_tiles_x = self.screen.get_width() // self.TILE_SIZE
        screen_tiles_y = self.screen.get_height() // self.TILE_SIZE
        for i in range(screen_tiles_x + 1):
            for j in range(screen_tiles_y + 1):
                world_x = self.view_x + (i * self.zoom_level)
                world_y = self.view_y + (j * self.zoom_level)
                condensed_tile = self._get_condensed_tile(world_x, world_y)

                if condensed_tile and isinstance(condensed_tile, dict):
                    char = condensed_tile.get('char', '?')
                    color = condensed_tile.get('color', self.COLORS["WHITE"])
                    self.screen.blit(self.font.render(char, True, color), (i * self.TILE_SIZE, j * self.TILE_SIZE))

        cursor_screen_tile_x = (self.screen.get_width() // 2) // self.TILE_SIZE
        cursor_screen_tile_y = (self.screen.get_height() // 2) // self.TILE_SIZE
        cursor_px_x = cursor_screen_tile_x * self.TILE_SIZE
        cursor_px_y = cursor_screen_tile_y * self.TILE_SIZE

        if (pygame.time.get_ticks() // 400) % 2 == 0:
            cursor_rect = pygame.Rect(cursor_px_x, cursor_px_y, self.TILE_SIZE, self.TILE_SIZE)
            pygame.draw.rect(self.screen, self.COLORS["YELLOW"], cursor_rect, 2)

        cursor_world_x = self.view_x + (cursor_screen_tile_x * self.zoom_level)
        cursor_world_y = self.view_y + (cursor_screen_tile_y * self.zoom_level)
        tile_info_text = f"Coords: ({cursor_world_x}, {cursor_world_y})"
        biome_name = "Out of Bounds"

        tile_data = self._get_condensed_tile(cursor_world_x, cursor_world_y)
        if tile_data:
            for name, data in self.biomes.items():
                if data == tile_data:
                    biome_name = name.replace('_', ' ').title()
                    break
        tile_info_text += f" | Biome: {biome_name}"

        info_surface = self.font.render(tile_info_text, True, self.COLORS["WHITE"])
        info_rect = info_surface.get_rect(centerx=self.screen.get_width() // 2, y=self.screen.get_height() - 80)
        self.screen.blit(info_surface, info_rect)
        
        instructions = [
            f"World Viewer | Zoom: {self.zoom_level}x",
            "Use arrow keys to pan. Use +/- to zoom. ESC to quit."
        ]
        y_offset = self.screen.get_height() - 60
        for instruction in instructions:
            inst_surface = self.font.render(instruction, True, self.COLORS["YELLOW"])
            inst_rect = inst_surface.get_rect(centerx=self.screen.get_width() // 2, y=y_offset)
            self.screen.blit(inst_surface, inst_rect)
            y_offset += 20

        pygame.display.flip()

    def run(self):
        """The main loop for the viewer application."""
        running = True
        while running:
            self.draw()
            running = self.handle_input(pygame.event.get())
            self.clock.tick(self.FPS)
        pygame.quit()

if __name__ == '__main__':
    viewer = WorldViewer('world.dat')
    viewer.run()