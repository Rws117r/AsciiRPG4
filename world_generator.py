# world_generator.py
# Generates and saves a world map with large continents.

import noise
import numpy as np
import random
import pickle

class WorldGenerator:
    """
    Generates a world map using Perlin noise, shaped by a radial
    gradient to create large, distinct continents.
    """
    def __init__(self, width, height, seed=None):
        self.width = width
        self.height = height
        self.seed = seed if seed is not None else random.randint(0, 100)

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

    def generate_world(self):
        """Generates the full world map with shaped continents."""
        height_map_scale = 10.0
        humidity_map_scale = 5.0
        temperature_map_scale = 7.0

        # Generate the base noise maps
        base_height_map = self._generate_noise_map(scale=height_map_scale, octaves=8, persistence=0.5, lacunarity=2.0)
        humidity_map = self._generate_noise_map(scale=humidity_map_scale, octaves=4, persistence=0.6, lacunarity=2.0, offset=1000)
        temperature_map = self._generate_noise_map(scale=temperature_map_scale, octaves=6, persistence=0.4, lacunarity=2.0, offset=2000)

        # --- Continent Shaping Logic ---
        # Create a radial gradient to form continents
        center_x, center_y = self.width / 2, self.height / 2
        radial_grad = np.zeros_like(base_height_map)
        for x in range(self.width):
            for y in range(self.height):
                # Calculate distance from center, normalized to a 0-1 range
                dist_x = abs(x - center_x)
                dist_y = abs(y - center_y)
                dist = np.sqrt(dist_x**2 + dist_y**2)
                
                # Invert distance and clamp to create an "island" mask
                # The 'clamping' creates a falloff effect towards the edges.
                radial_grad[x, y] = 1.0 - (dist / (self.width / 2))
                radial_grad[x, y] = max(0, radial_grad[x, y])

        # Combine the base height map with the radial gradient
        # This pushes down the edges to create oceans and raises the center for land
        height_map = base_height_map * radial_grad

        # Re-normalize the map to ensure values are roughly between -1 and 1
        height_map = (height_map - np.min(height_map)) / (np.max(height_map) - np.min(height_map)) * 2 - 1


        # Create biomes from the final shaped height map
        world_map = self._create_biomes(height_map, humidity_map, temperature_map)
        world_map = self._add_rivers(world_map, height_map)

        return world_map

    def _generate_noise_map(self, scale, octaves, persistence, lacunarity, offset=0):
        """Generates a 2D Perlin noise map."""
        world = np.zeros((self.width, self.height))
        for i in range(self.width):
            for j in range(self.height):
                nx = i / self.width * scale
                ny = j / self.height * scale
                world[i][j] = noise.pnoise2(nx, ny,
                                             octaves=octaves,
                                             persistence=persistence,
                                             lacunarity=lacunarity,
                                             repeatx=self.width,
                                             repeaty=self.height,
                                             base=self.seed + offset)
        return world

    def _create_biomes(self, height_map, humidity_map, temperature_map):
        """Assigns a biome to each map tile based on its properties."""
        world_map = np.empty((self.width, self.height), dtype=object)
        for i in range(self.width):
            for j in range(self.height):
                elevation = height_map[i][j]
                humidity = humidity_map[i][j]
                temperature = temperature_map[i][j]

                # Adjust thresholds to be more suitable for the shaped map
                if elevation < -0.5:
                    world_map[i][j] = self.biomes['deep_ocean']
                elif elevation < 0.0:
                    world_map[i][j] = self.biomes['ocean']
                elif elevation < 0.05:
                    world_map[i][j] = self.biomes['beach']
                elif elevation < 0.4:
                    if humidity < -0.3 and temperature > 0.3:
                        world_map[i][j] = self.biomes['desert']
                    elif humidity > 0.3:
                        world_map[i][j] = self.biomes['swamp']
                    else:
                        world_map[i][j] = self.biomes['plains']
                elif elevation < 0.7:
                    world_map[i][j] = self.biomes['forest']
                else:
                    world_map[i][j] = self.biomes['mountain']
        return world_map

    def _add_rivers(self, world_map, height_map, num_rivers=25):
        """Carves river paths from high-elevation points down to the sea."""
        for _ in range(num_rivers):
            start_x, start_y = -1, -1
            for _ in range(100):
                x, y = random.randint(0, self.width - 1), random.randint(0, self.height - 1)
                if world_map[x, y] == self.biomes['mountain']:
                    start_x, start_y = x, y
                    break
            if start_x == -1: continue

            px, py = start_x, start_y
            path = []
            for _ in range(250):
                path.append((px, py))
                if world_map[px, py] in [self.biomes['ocean'], self.biomes['deep_ocean'], self.biomes['river']]:
                    break

                neighbors = []
                for nx in range(px - 1, px + 2):
                    for ny in range(py - 1, py + 2):
                        if 0 <= nx < self.width and 0 <= ny < self.height and (nx, ny) != (px, py):
                            if height_map[nx, ny] < height_map[px, py]:
                                neighbors.append((nx, ny))
                if not neighbors: break
                px, py = min(neighbors, key=lambda n: height_map[n[0], n[1]])

            for pos_x, pos_y in path:
                if world_map[pos_x, pos_y] not in [self.biomes['ocean'], self.biomes['deep_ocean']]:
                    world_map[pos_x, pos_y] = self.biomes['river']
        return world_map

def save_world(world_map, filepath):
    """Saves the generated world map to a file."""
    try:
        with open(filepath, 'wb') as f:
            pickle.dump(world_map, f)
        print(f"World map successfully saved to '{filepath}'")
    except Exception as e:
        print(f"Error: Could not save world map. {e}")

if __name__ == '__main__':
    print("Generating continental world map...")
    generator = WorldGenerator(1000, 1000)
    new_world = generator.generate_world()
    save_world(new_world, 'world.dat')