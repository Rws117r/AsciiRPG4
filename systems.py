# systems.py
# Defines all the logic systems for the ECS.

import pygame
import random
from components import *
import random  # Import the 'random' module

class System:
    """A base class for systems. Systems contain logic that operates on entities with specific components."""
    def __init__(self, world):
        self.world = world

    def update(self, *args, **kwargs):
        pass

class InputSystem(System):
    """Handles player input and translates it into intents."""
    def update(self, *args, **kwargs):
        events = kwargs.get('events', [])
        game_state = kwargs.get('game_state')

        if not game_state: return

        player_entities = self.world.get_entities_with_components(PlayerControllableComponent)
        if not player_entities: return
        player_id = player_entities[0]

        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_l:
                    game_state.toggle_look_mode()
                    return
                elif event.key == pygame.K_i:
                    game_state.toggle_inventory()
                    return

                if game_state.look_mode:
                    self.handle_look_input(event, game_state)
                elif not game_state.show_inventory:  # Don't process movement when inventory is open
                    if event.key in [pygame.K_UP, pygame.K_DOWN, pygame.K_LEFT, pygame.K_RIGHT]:
                        self.handle_player_movement(event, player_id)
                    elif event.key == pygame.K_g:
                        self.handle_pickup(player_id)
                    elif event.key == pygame.K_a:
                        self.handle_attack(player_id)

    def handle_player_movement(self, event, player_id):
        dx, dy = 0, 0
        if event.key == pygame.K_UP: dy = -1
        elif event.key == pygame.K_DOWN: dy = 1
        elif event.key == pygame.K_LEFT: dx = -1
        elif event.key == pygame.K_RIGHT: dx = 1

        if dx != 0 or dy != 0:
            self.world.add_component(player_id, WantsToMoveComponent(dx, dy))

    def handle_look_input(self, event, game_state):
        cursor_id = game_state.cursor_id
        if not cursor_id: return

        dx, dy = 0, 0
        if event.key == pygame.K_UP: dy = -1
        elif event.key == pygame.K_DOWN: dy = 1
        elif event.key == pygame.K_LEFT: dx = -1
        elif event.key == pygame.K_RIGHT: dx = 1

        if dx != 0 or dy != 0:
            self.world.add_component(cursor_id, WantsToMoveComponent(dx, dy))

    def handle_pickup(self, player_id):
        player_pos = self.world.get_component(player_id, PositionComponent)
        item_id = self.world.get_item_at_position(player_pos.x, player_pos.y)
        if item_id and self.world.get_component(item_id, ItemComponent):
            self.world.add_component(player_id, WantsToPickupItemComponent(item_id))

    def handle_attack(self, player_id):
        player_pos = self.world.get_component(player_id, PositionComponent)
        
        # Check adjacent tiles for a monster
        adjacent_tiles = [
            (player_pos.x + 1, player_pos.y),
            (player_pos.x - 1, player_pos.y),
            (player_pos.x, player_pos.y + 1),
            (player_pos.x, player_pos.y - 1),
        ]
        
        for x, y in adjacent_tiles:
            target_id = self.world.get_entity_at_position(x, y)
            if target_id and self.world.get_component(target_id, FactionComponent).name == "monsters":
                # Found a monster, create an attack intent
                self.world.add_component(player_id, WantsToAttackComponent(target_id))
                return  # Attack only one monster at a time
        
        # If no monster found, you could add a "no target" message

class MovementSystem(System):
    """Processes movement requests, handling collisions and interactions."""
    def update(self, *args, **kwargs):
        game_state = kwargs.get('game_state')
        entities_to_move = self.world.get_entities_with_components(PositionComponent, WantsToMoveComponent)

        for entity_id in entities_to_move:
            pos = self.world.get_component(entity_id, PositionComponent)
            movement = self.world.get_component(entity_id, WantsToMoveComponent)

            target_x = pos.x + movement.dx
            target_y = pos.y + movement.dy

            # If the moving entity is the cursor, it's not bound by collisions
            # and can move freely around the map.
            if self.world.get_component(entity_id, CursorComponent):
                pos.x = target_x
                pos.y = target_y
                self.world.remove_component(entity_id, WantsToMoveComponent)
                continue # Skip to the next moving entity

            target_id = self.world.get_entity_at_position(target_x, target_y)

            if target_id and self.world.get_component(target_id, BlocksMovementComponent):
                # If it's the player bumping into something, create an "open" intent
                if self.world.get_component(entity_id, PlayerControllableComponent):
                    self.world.add_component(entity_id, WantsToOpenComponent(target_id))
            else:
                # Move the entity
                pos.x = target_x
                pos.y = target_y

            self.world.remove_component(entity_id, WantsToMoveComponent)

class ActionSystem(System):
    """Processes complex actions like picking up items and unlocking things."""
    def update(self, *args, **kwargs):
        self.player_acted = False
        self.monster_acting = False
        game_state = kwargs.get('game_state')

        # Process pickup intents
        for entity_id in self.world.get_entities_with_components(WantsToPickupItemComponent, InventoryComponent):
            pickup_intent = self.world.get_component(entity_id, WantsToPickupItemComponent)
            inventory = self.world.get_component(entity_id, InventoryComponent)

            item_id = pickup_intent.item_id
            item_pos = self.world.get_component(item_id, PositionComponent)

            # Remove item from the map by moving it off-screen
            item_pos.x, item_pos.y = -1, -1
            inventory.items.append(item_id)

            item_desc = self.world.get_component(item_id, DescriptionComponent)
            if item_desc:
                game_state.add_message(f"You pick up the {item_desc.text}.")

            self.world.remove_component(entity_id, WantsToPickupItemComponent)
            if self.world.get_component(entity_id, PlayerControllableComponent):
                self.player_acted = True


        # Process open intents
        for entity_id in self.world.get_entities_with_components(WantsToOpenComponent):
            open_intent = self.world.get_component(entity_id, WantsToOpenComponent)
            target_id = open_intent.target_id

            lockable = self.world.get_component(target_id, LockableComponent)
            openable = self.world.get_component(target_id, OpenableComponent)

            if lockable and lockable.is_locked:
                self.try_unlock(entity_id, target_id, lockable, game_state)
            elif openable:
                self.open_target(target_id, openable, game_state)

            if self.world.get_component(entity_id, PlayerControllableComponent):
                self.player_acted = True

            self.world.remove_component(entity_id, WantsToOpenComponent)

    def try_unlock(self, actor_id, target_id, lockable, game_state):
        """Logic for an actor trying to unlock a target."""
        inventory = self.world.get_component(actor_id, InventoryComponent)
        if not inventory: return

        has_key = False
        for item_id in inventory.items:
            key = self.world.get_component(item_id, KeyComponent)
            if key and key.key_id == lockable.key_id:
                has_key = True
                break

        if has_key:
            lockable.is_locked = False
            game_state.add_message("You unlock it.")
            # Now that it's unlocked, try to open it
            openable = self.world.get_component(target_id, OpenableComponent)
            if openable:
                self.open_target(target_id, openable, game_state)
        else:
            game_state.add_message("It's locked, and you don't have the key.")

    def open_target(self, target_id, openable, game_state):
        """Logic for opening a target."""
        if openable.is_open:
            game_state.add_message("It's already open.")
            return

        openable.is_open = True
        self.world.remove_component(target_id, BlocksMovementComponent)

        target_desc = self.world.get_component(target_id, DescriptionComponent)
        game_state.add_message(f"You open the {target_desc.text}.")

        container = self.world.get_component(target_id, ContainerComponent)
        if container and container.contents:
            contents_str = ", ".join(container.contents)
            game_state.add_message(f"Inside you see: {contents_str}.")

        # Change character on open
        renderable = self.world.get_component(target_id, RenderableComponent)
        if renderable and renderable.open_char:
            renderable.char = renderable.open_char


class CombatSystem(System):
    """Handles combat between entities."""
    def update(self, *args, **kwargs):
        game_state = kwargs.get('game_state')

        for attacker_id in self.world.get_entities_with_components(WantsToAttackComponent):
            intent = self.world.get_component(attacker_id, WantsToAttackComponent)
            target_id = intent.target_id

            # Get components for attacker and defender
            attacker_desc = self.world.get_component(attacker_id, DescriptionComponent)
            defender_desc = self.world.get_component(target_id, DescriptionComponent)
            attacker_combat = self.world.get_component(attacker_id, CombatComponent)
            defender_combat = self.world.get_component(target_id, CombatComponent)

            if not all([attacker_desc, defender_desc, attacker_combat, defender_combat]):
                self.world.remove_component(attacker_id, WantsToAttackComponent)
                continue

            # Determine names for messaging
            attacker_name = "You" if self.world.get_component(attacker_id, PlayerControllableComponent) else attacker_desc.text
            defender_name = "you" if self.world.get_component(target_id, PlayerControllableComponent) else f"the {defender_desc.text}"

            # Resolve attack
            attack_roll = random.randint(1, 20)
            if attack_roll >= (attacker_combat.thac0 - defender_combat.ac):
                damage = random.randint(1, 6)  # 1d6 damage for now
                defender_combat.hp -= damage
                game_state.add_message(f"{attacker_name} hit {defender_name} for {damage} damage!")

                if defender_combat.hp <= 0:
                    game_state.add_message(f"The {defender_desc.text} dies!")
                    # TODO: Implement proper entity death (remove entity, leave corpse, etc.)
            else:
                game_state.add_message(f"{attacker_name} miss {defender_name}.")

            # An attack is an action, so we mark it for the turn-based system
            if self.world.get_component(attacker_id, PlayerControllableComponent):
                self.world.get_system(ActionSystem).player_acted = True

            self.world.remove_component(attacker_id, WantsToAttackComponent)
        # Monster actions (simplified for now - just move randomly)  
        if game_state.game_state == 'MONSTER_TURN':
            monster_entities = self.world.get_entities_with_components(
                PositionComponent, CombatComponent, FactionComponent
            )

            for entity_id in monster_entities:
                if self.world.get_component(entity_id, PlayerControllableComponent):
                    continue  # Skip player
                if self.world.get_component(entity_id, FactionComponent).name != "monsters":
                    continue
                self.monster_acting = True
                dx, dy = random.choice([(0, 1), (0, -1), (1, 0), (-1, 0), (0,0)])  # Simple random movement
                if dx != 0 or dy != 0:
                    self.world.add_component(entity_id, WantsToMoveComponent(dx, dy))


class RenderSystem(System):
    """Handles all rendering logic."""
    def __init__(self, world, screen, font, tile_size):
        super().__init__(world)
        self.screen = screen
        self.font = font
        self.tile_size = tile_size
        self.inventory_width = 300
        self.inventory_slide_amount = 0
        self.inventory_slide_speed = 20

    def update(self, *args, **kwargs):
        game_state = kwargs.get('game_state')
        self.screen.fill((0, 0, 0))

        # Update inventory slide animation
        if game_state and game_state.show_inventory:
            if self.inventory_slide_amount < self.inventory_width:
                self.inventory_slide_amount = min(self.inventory_slide_amount + self.inventory_slide_speed, self.inventory_width)
        else:
            if self.inventory_slide_amount > 0:
                self.inventory_slide_amount = max(self.inventory_slide_amount - self.inventory_slide_speed, 0)

        # Draw entities
        entities_to_render = self.world.get_entities_with_components(PositionComponent, RenderableComponent)
        for entity_id in entities_to_render:
            pos = self.world.get_component(entity_id, PositionComponent)
            if pos.x < 0 or pos.y < 0: continue # Don't draw off-screen entities

            if self.world.get_component(entity_id, CursorComponent): continue

            renderable = self.world.get_component(entity_id, RenderableComponent)
            text_surface = self.font.render(renderable.char, True, renderable.color)
            self.screen.blit(text_surface, (pos.x * self.tile_size, pos.y * self.tile_size))

        # Draw look cursor and message
        if game_state and game_state.look_mode:
            self.draw_cursor_and_description(game_state)

        # Draw game messages
        if game_state:
            self.draw_messages(game_state)

        # Draw inventory sidebar
        if game_state and self.inventory_slide_amount > 0:
            self.draw_inventory(game_state)

    def draw_cursor_and_description(self, game_state):
        cursor_id = game_state.cursor_id
        if not cursor_id: return
        cursor_pos = self.world.get_component(cursor_id, PositionComponent)

        # Flashing cursor background
        if (pygame.time.get_ticks() // 400) % 2 == 0:
            bg_rect = pygame.Rect(cursor_pos.x * self.tile_size, cursor_pos.y * self.tile_size, self.tile_size, self.tile_size)
            pygame.draw.rect(self.screen, (50, 50, 0), bg_rect)

        # Get entity at cursor position and draw its description
        # Check for non-item entities first
        entity_id = self.world.get_entity_at_position(cursor_pos.x, cursor_pos.y)
        # If no entity, check for an item
        if not entity_id:
            entity_id = self.world.get_item_at_position(cursor_pos.x, cursor_pos.y)

        if entity_id:
            desc = self.world.get_component(entity_id, DescriptionComponent)
            material = self.world.get_component(entity_id, MaterialComponent)
            if desc:
                description_text = desc.text.format(material=material.name if material else "unknown")
                description_surface = self.font.render(description_text, True, (255, 255, 255))
                # Center the description at the bottom of the screen
                description_rect = description_surface.get_rect(centerx=self.screen.get_width() // 2, y=self.screen.get_height() - 40)
                self.screen.blit(description_surface, description_rect)

    def draw_messages(self, game_state):
        y_offset = self.screen.get_height() - 20
        # Iterate over the last 5 messages, starting from the most recent.
        for message in reversed(game_state.message_log[-5:]):
            msg_surface = self.font.render(message, True, (255, 255, 255))
            # Position messages from the bottom of the screen up.
            msg_rect = msg_surface.get_rect(centerx=self.screen.get_width() / 2, bottom=y_offset)
            self.screen.blit(msg_surface, msg_rect)
            y_offset -= 20 # Move up for the next message

    def draw_inventory(self, game_state):
        # Get player entity
        player_entities = self.world.get_entities_with_components(PlayerControllableComponent)
        if not player_entities: return
        player_id = player_entities[0]
        
        inventory = self.world.get_component(player_id, InventoryComponent)
        if not inventory: return

        # Draw semi-transparent background
        inventory_x = self.screen.get_width() - self.inventory_slide_amount
        inventory_rect = pygame.Rect(inventory_x, 0, self.inventory_width, self.screen.get_height())
        
        # Draw background
        bg_surface = pygame.Surface((self.inventory_width, self.screen.get_height()))
        bg_surface.set_alpha(230)
        bg_surface.fill((20, 20, 20))
        self.screen.blit(bg_surface, (inventory_x, 0))
        
        # Draw border
        pygame.draw.rect(self.screen, (100, 100, 100), inventory_rect, 2)
        
        # Draw title
        title_surface = self.font.render("INVENTORY", True, (255, 255, 255))
        title_rect = title_surface.get_rect(centerx=inventory_x + self.inventory_width // 2, y=20)
        self.screen.blit(title_surface, title_rect)
        
        # Draw separator line
        pygame.draw.line(self.screen, (100, 100, 100), 
                        (inventory_x + 10, 50), 
                        (inventory_x + self.inventory_width - 10, 50), 2)
        
        # Draw inventory items
        y_offset = 70
        if not inventory.items:
            empty_surface = self.font.render("(empty)", True, (150, 150, 150))
            empty_rect = empty_surface.get_rect(centerx=inventory_x + self.inventory_width // 2, y=y_offset)
            self.screen.blit(empty_surface, empty_rect)
        else:
            for item_id in inventory.items:
                # Get item components
                desc = self.world.get_component(item_id, DescriptionComponent)
                renderable = self.world.get_component(item_id, RenderableComponent)
                
                if desc and renderable:
                    # Draw item character
                    char_surface = self.font.render(renderable.char, True, renderable.color)
                    self.screen.blit(char_surface, (inventory_x + 20, y_offset))
                    
                    # Draw item description (truncate if too long)
                    text = desc.text
                    if len(text) > 25:
                        text = text[:22] + "..."
                    text_surface = self.font.render(text, True, (255, 255, 255))
                    self.screen.blit(text_surface, (inventory_x + 50, y_offset))
                    
                    # Check if it's a key and show key_id
                    key_comp = self.world.get_component(item_id, KeyComponent)
                    if key_comp and key_comp.key_id:
                        key_info = f"[Key: {key_comp.key_id[:8]}...]"
                        key_surface = self.font.render(key_info, True, (150, 150, 150))
                        self.screen.blit(key_surface, (inventory_x + 50, y_offset + 20))
                        y_offset += 20
                    
                    y_offset += 30
        
        # Draw instructions at bottom
        instructions = ["Press 'I' to close"]
        y_offset = self.screen.get_height() - 60
        for instruction in instructions:
            inst_surface = self.font.render(instruction, True, (200, 200, 200))
            inst_rect = inst_surface.get_rect(centerx=inventory_x + self.inventory_width // 2, y=y_offset)
            self.screen.blit(inst_surface, inst_rect)
            y_offset += 25


class AISystem(System):
    """Controls the actions of non-player entities."""
    def update(self, *args, **kwargs):
        game_state = kwargs['game_state']
        if game_state.game_state != 'MONSTER_TURN':
            return  # Only act on monster turn

        player_entity = self.world.get_entities_with_components(PlayerControllableComponent)
        if not player_entity: return
        player_id = player_entity[0]
        player_pos = self.world.get_component(player_id, PositionComponent)

        for entity_id in self.world.get_entities_with_components(FactionComponent, PositionComponent):
            faction = self.world.get_component(entity_id, FactionComponent)
            if faction.name != "monsters":
                continue  # Only control monsters

            monster_pos = self.world.get_component(entity_id, PositionComponent)

            # Check if player is within sight (10 tiles for now)
            distance = max(abs(player_pos.x - monster_pos.x), abs(player_pos.y - monster_pos.y))
            if distance <= 10:
                # Check for adjacency
                if distance == 1:
                    # Attack the player
                    self.world.add_component(entity_id, WantsToAttackComponent(player_id))
                else:
                    # Move towards the player (very basic movement for now)
                    dx, dy = 0, 0
                    if player_pos.x > monster_pos.x:
                        dx = 1
                    elif player_pos.x < monster_pos.x:
                        dx = -1
                    if player_pos.y > monster_pos.y:
                        dy = 1
                    elif player_pos.y < monster_pos.y:
                        dy = -1
                    self.world.add_component(entity_id, WantsToMoveComponent(dx, dy))
            # If the player is not in sight, monsters will continue with random movement from ActionSystem
            # (or we could add more complex "wandering" behavior here later).