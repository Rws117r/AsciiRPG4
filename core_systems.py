# core_systems.py
# Core game systems: Input, Movement, Action, and Render

import pygame
import random
from components import *

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
        
        # Only process input during player turn
        if game_state.game_state != 'PLAYER_TURN':
            return

        player_entities = self.world.get_entities_with_components(PlayerControllableComponent)
        if not player_entities: return
        player_id = player_entities[0]

        # Check if player is affected by status effects that prevent action
        state = self.world.get_component(player_id, StateComponent)
        if state and (state.paralyzed or state.petrified or state.unconscious or state.stunned or state.dead):
            return  # Player cannot act

        for event in events:
            if event.type == pygame.KEYDOWN:
                # Handle global toggles first
                if event.key == pygame.K_l:
                    game_state.toggle_look_mode()
                    return
                elif event.key == pygame.K_i:
                    game_state.toggle_inventory()
                    return
                elif event.key == pygame.K_b:  # 'b' for abilities
                    game_state.toggle_abilities()
                    return

                # Handle targeting mode input
                if hasattr(game_state, 'targeting_mode') and game_state.targeting_mode:
                    self.handle_targeting_input(event, game_state)
                    return

                if game_state.look_mode:
                    self.handle_look_input(event, game_state)
                elif not game_state.show_inventory and not game_state.show_abilities:
                    if event.key in [pygame.K_UP, pygame.K_DOWN, pygame.K_LEFT, pygame.K_RIGHT]:
                        # Check for confusion
                        if state and state.confused:
                            # Confused movement is random
                            if random.random() < 0.5:  # 50% chance to move in random direction
                                dx, dy = random.choice([(0, 1), (0, -1), (1, 0), (-1, 0)])
                                self.world.add_component(player_id, WantsToMoveComponent(dx, dy))
                                game_state.player_acted = True
                                game_state.add_message("You stumble around confused!")
                                return
                        
                        self.handle_player_movement(event, player_id, game_state)
                    elif event.key == pygame.K_g:
                        self.handle_pickup(player_id, game_state)
                elif game_state.show_abilities:
                    self.handle_abilities_input(event, game_state, player_id)

    def handle_abilities_input(self, event, game_state, player_id):
        """Handle input in the abilities screen."""
        if event.key >= pygame.K_1 and event.key <= pygame.K_9:
            # Get ability number (1-9)
            ability_num = event.key - pygame.K_1
            
            # Get player's abilities
            abilities_comp = self.world.get_component(player_id, AbilitiesComponent)
            if abilities_comp and ability_num < len(abilities_comp.abilities):
                ability_id = abilities_comp.abilities[ability_num]
                
                if ability_id in self.world.abilities:
                    ability_data = self.world.abilities[ability_id]
                    
                    # Check if this is a player-activated ability
                    if ability_data.get("type") == "on_special":
                        self.activate_ability(player_id, ability_id, ability_data, game_state)

    def activate_ability(self, player_id, ability_id, ability_data, game_state):
        """Activate a player ability, handling targeting if needed."""
        effect_type = ability_data.get("effect")
        
        if effect_type == "apply_status_aoe":
            # AOE abilities don't need targeting, apply immediately
            self.world.add_component(player_id, WantsToUseAbilityComponent(
                ability_id=ability_id,
                target_id=player_id
            ))
            game_state.player_acted = True
            game_state.show_abilities = False
            game_state.add_message(f"You use {ability_id.replace('_', ' ').title()}!")
            
        elif effect_type in ["apply_status", "damage", "heal"]:
            # Single target abilities need targeting
            targeting_range = ability_data.get("range", 1)  # Default range of 1
            game_state.enter_targeting_mode(ability_id, ability_data, targeting_range)
        
        else:
            # Self-target or immediate effect
            self.world.add_component(player_id, WantsToUseAbilityComponent(
                ability_id=ability_id,
                target_id=player_id
            ))
            game_state.player_acted = True
            game_state.show_abilities = False
            game_state.add_message(f"You use {ability_id.replace('_', ' ').title()}!")

    def handle_targeting_input(self, event, game_state):
        """Handle input during targeting mode."""
        cursor_id = game_state.cursor_id
        if not cursor_id: return

        if event.key in [pygame.K_UP, pygame.K_DOWN, pygame.K_LEFT, pygame.K_RIGHT]:
            # Move cursor
            dx, dy = 0, 0
            if event.key == pygame.K_UP: dy = -1
            elif event.key == pygame.K_DOWN: dy = 1
            elif event.key == pygame.K_LEFT: dx = -1
            elif event.key == pygame.K_RIGHT: dx = 1
            
            self.world.add_component(cursor_id, WantsToMoveComponent(dx, dy))
            
        elif event.key == pygame.K_RETURN or event.key == pygame.K_SPACE:
            # Confirm target
            cursor_pos = self.world.get_component(cursor_id, PositionComponent)
            target_id = self.world.get_entity_at_position(cursor_pos.x, cursor_pos.y)
            
            # Get player
            player_entities = self.world.get_entities_with_components(PlayerControllableComponent)
            if player_entities:
                player_id = player_entities[0]
                
                # Create ability use intent with target
                self.world.add_component(player_id, WantsToUseAbilityComponent(
                    ability_id=game_state.targeting_ability_id,
                    target_id=target_id,
                    target_position=(cursor_pos.x, cursor_pos.y)
                ))
                
                game_state.exit_targeting_mode()
                game_state.player_acted = True
                game_state.add_message(f"You use {game_state.targeting_ability_id.replace('_', ' ').title()}!")
                
        elif event.key == pygame.K_ESCAPE:
            # Cancel targeting
            game_state.exit_targeting_mode()

    def handle_player_movement(self, event, player_id, game_state):
        dx, dy = 0, 0
        if event.key == pygame.K_UP: dy = -1
        elif event.key == pygame.K_DOWN: dy = 1
        elif event.key == pygame.K_LEFT: dx = -1
        elif event.key == pygame.K_RIGHT: dx = 1

        if dx != 0 or dy != 0:
            self.world.add_component(player_id, WantsToMoveComponent(dx, dy))
            game_state.player_acted = True  # Movement ends turn

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

    def handle_pickup(self, player_id, game_state):
        player_pos = self.world.get_component(player_id, PositionComponent)
        item_id = self.world.get_item_at_position(player_pos.x, player_pos.y)
        if item_id and self.world.get_component(item_id, ItemComponent):
            self.world.add_component(player_id, WantsToPickupItemComponent(item_id))
            game_state.player_acted = True  # Pickup ends turn

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
                # In targeting mode, constrain cursor movement by range
                if hasattr(game_state, 'targeting_mode') and game_state.targeting_mode:
                    player_entities = self.world.get_entities_with_components(PlayerControllableComponent)
                    if player_entities:
                        player_pos = self.world.get_component(player_entities[0], PositionComponent)
                        distance = max(abs(target_x - player_pos.x), abs(target_y - player_pos.y))
                        if distance <= game_state.targeting_range:
                            pos.x = target_x
                            pos.y = target_y
                else:
                    pos.x = target_x
                    pos.y = target_y
                self.world.remove_component(entity_id, WantsToMoveComponent)
                continue

            target_id = self.world.get_entity_at_position(target_x, target_y)

            # Check if this is a player trying to move into a monster (bump-to-attack)
            if (self.world.get_component(entity_id, PlayerControllableComponent) and 
                target_id):
                
                target_faction = self.world.get_component(target_id, FactionComponent)
                target_state = self.world.get_component(target_id, StateComponent)
                
                # Don't attack dead entities
                if target_state and target_state.dead:
                    pass  # Continue with normal movement logic
                elif target_faction and target_faction.name == "monsters":
                    # Create attack intent instead of trying to open
                    self.world.add_component(entity_id, WantsToAttackComponent(target_id))
                    self.world.remove_component(entity_id, WantsToMoveComponent)
                    continue
                elif self.world.get_component(target_id, BlocksMovementComponent):
                    # If it's not a monster but blocks movement, try to open it
                    self.world.add_component(entity_id, WantsToOpenComponent(target_id))
                    self.world.remove_component(entity_id, WantsToMoveComponent)
                    continue
            elif target_id and self.world.get_component(target_id, BlocksMovementComponent):
                # If it's the player bumping into something, create an "open" intent
                if self.world.get_component(entity_id, PlayerControllableComponent):
                    self.world.add_component(entity_id, WantsToOpenComponent(target_id))
            else:
                # Move the entity
                
                # Check if the moving entity is a monster, and if the target is the player
                moving_faction = self.world.get_component(entity_id, FactionComponent)
                target_faction = self.world.get_component(target_id, FactionComponent) if target_id else None
                
                if (moving_faction and moving_faction.name == "monsters" and
                    target_faction and target_faction.name == "player"):
                    # Monster can't move through the player, so skip this move.
                    pass
                else:
                    # Either the player is moving (and can move through monsters), or it's a 
                    # monster moving to an empty space or another monster (which is allowed now).
                    pos.x = target_x
                    pos.y = target_y
            
            # In either case (move or blocked), we remove the movement intent
            # because the movement has been handled in this turn.
            self.world.remove_component(entity_id, WantsToMoveComponent)

class ActionSystem(System):
    """Processes complex actions like picking up items and unlocking things."""
    def update(self, *args, **kwargs):
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