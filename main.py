# main.py
# A simple ASCII roguelike foundation using Pygame and an Entity-Component-System (ECS) architecture.

import pygame
import sys
import os
import json
import copy
import components 
from systems import InputSystem, MovementSystem, RenderSystem, ActionSystem

# --- Core ECS Classes ---
class Entity:
    """A container for components. It's just an ID."""
    def __init__(self):
        if not hasattr(Entity, "next_id"):
            Entity.next_id = 0
        self.id = Entity.next_id
        Entity.next_id += 1

# --- Game World ---
class World:
    """The central hub of the ECS."""
    def __init__(self):
        self.entities = {}
        self.components = {}
        self.systems = []
        self.archetypes = {}
        self.materials = {}

    def create_entity(self):
        entity = Entity()
        self.entities[entity.id] = entity
        return entity

    def add_component(self, entity_id, component):
        component_type = type(component)
        if component_type not in self.components:
            self.components[component_type] = {}
        self.components[component_type][entity_id] = component
        return component

    def get_component(self, entity_id, component_type):
        return self.components.get(component_type, {}).get(entity_id)

    def remove_component(self, entity_id, component_type):
        if component_type in self.components and entity_id in self.components[component_type]:
            del self.components[component_type][entity_id]

    def get_entities_with_components(self, *component_types):
        if not component_types: return []
        try:
            entity_ids = set(self.components[component_types[0]].keys())
        except KeyError:
            return []
        for component_type in component_types[1:]:
            try:
                entity_ids.intersection_update(self.components[component_type].keys())
            except KeyError:
                return []
        return list(entity_ids)
    
    def get_entity_at_position(self, x, y):
        """Finds an entity at a specific grid location, ignoring items (which can be walked on)."""
        for entity_id in self.get_entities_with_components(components.PositionComponent):
            if self.get_component(entity_id, components.CursorComponent): continue
            
            pos = self.get_component(entity_id, components.PositionComponent)
            if pos.x == x and pos.y == y:
                if self.get_component(entity_id, components.ItemComponent):
                    continue
                return entity_id
        return None

    def add_system(self, system):
        self.systems.append(system)

    def update(self, *args, **kwargs):
        for system in self.systems:
            system.update(*args, **kwargs)

# --- Main Game Class ---
class Game:
    """Initializes Pygame, sets up the game world, and runs the main game loop."""
    def __init__(self):
        pygame.init()
        self.WINDOW_WIDTH, self.WINDOW_HEIGHT = 1280, 720
        self.TILE_SIZE, self.FONT_SIZE = 24, 24
        self.FONT_NAME = 'JetBrainsMonoNL-Regular.ttf'
        self.FPS = 60
        self.COLORS = {"BLACK": (0,0,0), "WHITE": (255,255,255), "GREEN": (0,255,0), "YELLOW": (255,255,0)}
        self.fullscreen = False
        self.look_mode = False
        self.cursor_id = None
        self.message_log = []
        self.screen = pygame.display.set_mode((self.WINDOW_WIDTH, self.WINDOW_HEIGHT), pygame.RESIZABLE)
        pygame.display.set_caption("ASCII Roguelike")
        self.clock = pygame.time.Clock()
        self.font = self.load_font()
        self.world = World()

    def add_message(self, message):
        self.message_log.append(message)
        if len(self.message_log) > 5:
            self.message_log.pop(0)

    def load_font(self):
        font_path = os.path.join(os.path.dirname(__file__), self.FONT_NAME)
        try:
            return pygame.font.Font(font_path, self.FONT_SIZE)
        except pygame.error:
            print(f"Font '{self.FONT_NAME}' not found. Using default.")
            return pygame.font.Font(None, self.FONT_SIZE)

    def load_json_file(self, file_path):
        """Helper to load a single JSON file."""
        try:
            with open(file_path, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"Error loading or parsing {file_path}: {e}")
            return None

    def get_archetype_data(self, archetype_name):
        """Recursively gathers component data from a single archetype and its parent chain."""
        if archetype_name not in self.world.archetypes:
            print(f"Warning: Archetype '{archetype_name}' not found.")
            return {}

        archetype = self.world.archetypes[archetype_name]
        
        parent_components = {}
        if "inherits" in archetype:
            parent_names = archetype["inherits"]
            if not isinstance(parent_names, list):
                parent_names = [parent_names]
            
            for name in parent_names:
                components_from_parent = self.get_archetype_data(name)
                for comp_name, comp_args in components_from_parent.items():
                    if comp_name in parent_components and isinstance(parent_components.get(comp_name), dict) and isinstance(comp_args, dict):
                         parent_components[comp_name].update(comp_args)
                    else:
                        parent_components[comp_name] = comp_args

        final_components = copy.deepcopy(parent_components)
        for comp_name, comp_args in archetype.get("components", {}).items():
            if comp_name in final_components and isinstance(final_components.get(comp_name), dict) and isinstance(comp_args, dict):
                final_components[comp_name].update(comp_args)
            else:
                final_components[comp_name] = comp_args
            
        return final_components

    def create_entities_from_definitions(self, entity_definitions):
        """Creates entities in the world based on a list of definitions."""
        for entity_def in entity_definitions:
            final_components = {}
            
            inherits_list = entity_def.get("inherits", "Abstract")
            if not isinstance(inherits_list, list):
                inherits_list = [inherits_list]

            for archetype_name in inherits_list:
                archetype_data = self.get_archetype_data(archetype_name)
                final_components.update(archetype_data)
            
            for comp_name, comp_args in entity_def.get("components", {}).items():
                if comp_name in final_components and isinstance(final_components.get(comp_name), dict) and isinstance(comp_args, dict):
                    final_components[comp_name].update(comp_args)
                else:
                    final_components[comp_name] = comp_args

            entity = self.world.create_entity()
            print(f"Created entity '{entity_def.get('name', 'Unnamed')}' with ID {entity.id}")
            
            for comp_name, comp_args in final_components.items():
                try:
                    comp_class = getattr(components, comp_name)
                    if comp_name == "RenderableComponent" and "color" in comp_args:
                        comp_args["color"] = self.COLORS.get(comp_args["color"].upper(), self.COLORS["WHITE"])
                    
                    component_instance = comp_class(**copy.deepcopy(comp_args))
                    self.world.add_component(entity.id, component_instance)
                except AttributeError:
                    print(f"Warning: Component class '{comp_name}' not found in components module.")
                except TypeError as e:
                    print(f"Warning: Could not create component '{comp_name}' with args {comp_args}. Error: {e}")

    def setup(self):
        """Load all game data and initialize systems."""
        self.world.materials = self.load_json_file('materials.json') or {}
        self.world.archetypes = self.load_json_file('archetypes.json') or {}
        creatures_data = self.load_json_file('creatures.json') or {"entities": []}
        items_data = self.load_json_file('items.json') or {"entities": []}

        if creatures_data: self.create_entities_from_definitions(creatures_data["entities"])
        if items_data: self.create_entities_from_definitions(items_data["entities"])
        
        self.world.add_system(InputSystem(self.world))
        self.world.add_system(MovementSystem(self.world))
        self.world.add_system(ActionSystem(self.world))
        self.world.add_system(RenderSystem(self.world, self.screen, self.font, self.TILE_SIZE))
        
        self.create_cursor()

    def create_cursor(self):
        """Creates the look cursor entity."""
        cursor = self.world.create_entity()
        self.cursor_id = cursor.id
        self.world.add_component(cursor.id, components.PositionComponent(-1, -1))
        self.world.add_component(cursor.id, components.RenderableComponent('X', self.COLORS["YELLOW"]))
        self.world.add_component(cursor.id, components.CursorComponent())

    def toggle_look_mode(self):
        """Activates or deactivates the look mode."""
        self.look_mode = not self.look_mode
        if self.look_mode:
            player_entities = self.world.get_entities_with_components(components.PlayerControllableComponent)
            if player_entities:
                player_id = player_entities[0]
                player_pos = self.world.get_component(player_id, components.PositionComponent)
                cursor_pos = self.world.get_component(self.cursor_id, components.PositionComponent)
                cursor_pos.x, cursor_pos.y = player_pos.x, player_pos.y
        print(f"Look mode: {'ON' if self.look_mode else 'OFF'}")

    def run(self):
        running = True
        while running:
            events = pygame.event.get()
            for event in events:
                if event.type == pygame.QUIT:
                    running = False
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_f:
                        self.fullscreen = not self.fullscreen
                        if self.fullscreen: self.screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
                        else: self.screen = pygame.display.set_mode((self.WINDOW_WIDTH, self.WINDOW_HEIGHT), pygame.RESIZABLE)
                        for system in self.world.systems:
                            if isinstance(system, RenderSystem): system.screen = self.screen
                    elif event.key == pygame.K_ESCAPE:
                        if self.look_mode: self.toggle_look_mode()
                        else: running = False
            
            self.world.update(events=events, game_state=self)
            pygame.display.flip()
            self.clock.tick(self.FPS)

        pygame.quit()
        sys.exit()

if __name__ == '__main__':
    game = Game()
    game.setup()
    game.run()
