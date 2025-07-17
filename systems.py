# systems.py
# Defines all the logic systems for the ECS.

import pygame
import random
import re
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
                    elif event.key == pygame.K_a:
                        self.handle_attack(player_id, game_state)

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

    def handle_attack(self, player_id, game_state):
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
            if target_id:
                target_faction = self.world.get_component(target_id, FactionComponent)
                target_state = self.world.get_component(target_id, StateComponent)
                
                # Don't attack dead entities
                if target_state and target_state.dead:
                    continue
                    
                if target_faction and target_faction.name == "monsters":
                    # Found a monster, create an attack intent
                    self.world.add_component(player_id, WantsToAttackComponent(target_id))
                    game_state.player_acted = True  # Attack ends turn
                    return  # Attack only one monster at a time
        
        # If no monster found, add a message
        game_state.add_message("There's nothing to attack here.")

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

class SavingThrowSystem(System):
    """Handles saving throws against various effects."""
    
    def update(self, *args, **kwargs):
        game_state = kwargs.get('game_state')
        
        for entity_id in self.world.get_entities_with_components(WantsToMakeSavingThrowComponent):
            save_intent = self.world.get_component(entity_id, WantsToMakeSavingThrowComponent)
            stats = self.world.get_component(entity_id, StatsComponent)
            state = self.world.get_component(entity_id, StateComponent)
            
            if not stats:
                # Can't make saves without stats
                self.world.remove_component(entity_id, WantsToMakeSavingThrowComponent)
                continue
            
            # Get the appropriate save value
            save_value = 20  # Default
            if save_intent.save_type == "death":
                save_value = stats.save_death
            elif save_intent.save_type == "wands":
                save_value = stats.save_wands
            elif save_intent.save_type == "paralysis":
                save_value = stats.save_paralysis
            elif save_intent.save_type == "breath":
                save_value = stats.save_breath
            elif save_intent.save_type == "spells":
                save_value = stats.save_spells
            
            # Apply save penalty from status effects
            if state:
                save_value += state.save_penalty
            
            # Roll the save
            save_roll = random.randint(1, 20)
            save_successful = save_roll >= save_value
            
            # Generate message
            entity_name = "You" if self.world.get_component(entity_id, PlayerControllableComponent) else None
            if not entity_name:
                desc = self.world.get_component(entity_id, DescriptionComponent)
                entity_name = f"The {desc.text}" if desc else "The creature"
            
            if save_successful:
                if entity_name == "You":
                    game_state.add_message(f"You resist the effect! (rolled {save_roll}, needed {save_value})")
                else:
                    game_state.add_message(f"{entity_name} resists the effect!")
            else:
                if entity_name == "You":
                    game_state.add_message(f"You fail to resist! (rolled {save_roll}, needed {save_value})")
                else:
                    game_state.add_message(f"{entity_name} fails to resist!")
                
                # Apply the effect if save failed
                if save_intent.effect_data:
                    self.world.add_component(entity_id, WantsToApplyStatusComponent(
                        status_effect_data=save_intent.effect_data,
                        source_entity_id=save_intent.source_entity_id
                    ))
            
            self.world.remove_component(entity_id, WantsToMakeSavingThrowComponent)

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

            # Skip if target is already dead
            target_state = self.world.get_component(target_id, StateComponent)
            if target_state and target_state.dead:
                self.world.remove_component(attacker_id, WantsToAttackComponent)
                continue

            # Get state components for status effect modifiers
            attacker_state = self.world.get_component(attacker_id, StateComponent)
            defender_state = self.world.get_component(target_id, StateComponent)

            # Determine names for messaging
            attacker_name = "You" if self.world.get_component(attacker_id, PlayerControllableComponent) else attacker_desc.text
            defender_name = "you" if self.world.get_component(target_id, PlayerControllableComponent) else f"the {defender_desc.text}"

            # Calculate attack modifiers from status effects
            attack_thac0 = attacker_combat.thac0
            if attacker_state:
                attack_thac0 += attacker_state.thac0_modifier

            # Resolve attack using OSE rules (THAC0 system)
            attack_roll = random.randint(1, 20)
            hit_ac = attack_thac0 - attack_roll
            
            # Enhanced combat messaging
            if hit_ac <= defender_combat.ac:
                # Calculate damage with modifiers
                base_damage = random.randint(1, 6)  # 1d6 damage for now
                final_damage = base_damage
                if attacker_state:
                    final_damage += attacker_state.damage_modifier
                final_damage = max(1, final_damage)  # Minimum 1 damage
                
                defender_combat.hp -= final_damage
                
                # Enhanced hit message
                game_state.add_message(f"{attacker_name} attack{'' if attacker_name == 'You' else 's'} {defender_name} and roll{'' if attacker_name == 'You' else 's'} a {attack_roll}, hitting for {final_damage} damage!")

                if defender_combat.hp <= 0:
                    # Handle death
                    self.handle_death(target_id, attacker_id, game_state)
                else:
                    # Check for and trigger abilities after successful attack
                    abilities_comp = self.world.get_component(attacker_id, AbilitiesComponent)
                    if abilities_comp:
                        for ability_id in abilities_comp.abilities:
                            if ability_id in self.world.abilities:
                                ability_data = self.world.abilities[ability_id]
                                if ability_data.get("type") == "on_attack":
                                    # Roll for chance
                                    chance = ability_data.get("chance", 0.0)
                                    if random.random() <= chance:
                                        # Check if the effect allows a saving throw
                                        status_effect = ability_data.get("status_effect")
                                        if status_effect:
                                            save_type = self.get_save_type_for_effect(status_effect.get("id"))
                                            if save_type:
                                                # Create saving throw intent
                                                self.world.add_component(target_id, WantsToMakeSavingThrowComponent(
                                                    save_type=save_type,
                                                    dc=15,  # Default DC, could be customized
                                                    effect_data=status_effect,
                                                    source_entity_id=attacker_id
                                                ))
                                            else:
                                                # No save allowed, apply directly
                                                self.world.add_component(target_id, WantsToApplyStatusComponent(
                                                    status_effect_data=status_effect,
                                                    source_entity_id=attacker_id
                                                ))
            else:
                # Enhanced miss message
                game_state.add_message(f"{attacker_name} attack{'' if attacker_name == 'You' else 's'} {defender_name} and roll{'' if attacker_name == 'You' else 's'} a {attack_roll}, but miss{'!' if attacker_name == 'You' else 'es!'}")

            self.world.remove_component(attacker_id, WantsToAttackComponent)

    def get_save_type_for_effect(self, effect_id):
        """Determine the appropriate saving throw type for an effect."""
        # Map status effects to appropriate saves
        save_mapping = {
            "paralysis": "paralysis",
            "petrification": "spells",
            "charm": "spells",
            "confusion": "spells",
            "blindness": "spells",
            "disease_mummy_rot": "death",
            "disease_generic": "death",
            "energy_drain_1": "death",
            "energy_drain_2": "death",
            "poison_lethal": "death",
            "poison_sickness": "death",
            # Some effects don't allow saves
            "ability_drain_strength": None,
            "ability_drain_wisdom": None,
            "ability_drain_charisma": None,
        }
        return save_mapping.get(effect_id, "spells")  # Default to spells save

    def handle_death(self, dead_entity_id, killer_id, game_state):
        """Handle entity death, XP rewards, and cleanup."""
        defender_desc = self.world.get_component(dead_entity_id, DescriptionComponent)
        defender_combat = self.world.get_component(dead_entity_id, CombatComponent)
        
        # Mark as dead
        state = self.world.get_component(dead_entity_id, StateComponent)
        if not state:
            state = StateComponent()
            self.world.add_component(dead_entity_id, state)
        state.dead = True
        
        # Add dead component for easy identification
        self.world.add_component(dead_entity_id, DeadComponent())
        
        # Award XP if the killer is the player
        if self.world.get_component(killer_id, PlayerControllableComponent):
            xp_comp = self.world.get_component(killer_id, ExperienceComponent)
            if not xp_comp:
                xp_comp = ExperienceComponent()
                self.world.add_component(killer_id, xp_comp)
            
            if defender_combat and defender_combat.xp_value > 0:
                old_xp = xp_comp.current_xp
                xp_comp.current_xp += defender_combat.xp_value
                game_state.add_message(f"You gain {defender_combat.xp_value} experience points!")
                
                # Check for level up
                if xp_comp.current_xp >= xp_comp.xp_to_next_level:
                    self.handle_level_up(killer_id, xp_comp, game_state)
        
        # Death message
        entity_name = "You" if self.world.get_component(dead_entity_id, PlayerControllableComponent) else f"The {defender_desc.text}"
        if self.world.get_component(dead_entity_id, PlayerControllableComponent):
            game_state.add_message("You have died! Game Over.")
            # TODO: Handle player death (restart, etc.)
        else:
            game_state.add_message(f"{entity_name} dies!")
        
        # Change appearance to corpse
        renderable = self.world.get_component(dead_entity_id, RenderableComponent)
        if renderable:
            renderable.char = '%'
            renderable.color = (100, 100, 100)  # Gray corpse

    def handle_level_up(self, entity_id, xp_comp, game_state):
        """Handle leveling up."""
        old_level = xp_comp.level
        xp_comp.level += 1
        xp_comp.xp_to_next_level = xp_comp.calculate_xp_needed(xp_comp.level + 1)
        
        # Increase HP
        combat = self.world.get_component(entity_id, CombatComponent)
        if combat:
            hp_gain = random.randint(1, 6)  # 1d6 HP per level
            combat.max_hp += hp_gain
            combat.hp += hp_gain  # Heal to full on level up
        
        game_state.add_message(f"Congratulations! You reached level {xp_comp.level}!")
        if combat:
            game_state.add_message(f"You gain {hp_gain} hit points!")


class StatusEffectSystem(System):
    """Handles application and management of status effects."""
    
    def update(self, *args, **kwargs):
        game_state = kwargs.get('game_state')
        
        # Apply new status effects
        self.apply_new_status_effects(game_state)
        
        # Update existing status effects (reduce duration, check for expiry)
        self.update_existing_status_effects(game_state)
    
    def apply_new_status_effects(self, game_state):
        """Apply new status effects from WantsToApplyStatusComponent."""
        for entity_id in self.world.get_entities_with_components(WantsToApplyStatusComponent):
            intent = self.world.get_component(entity_id, WantsToApplyStatusComponent)
            status_data = intent.status_effect_data
            
            # Get or create StatusEffectsComponent
            status_effects_comp = self.world.get_component(entity_id, StatusEffectsComponent)
            if not status_effects_comp:
                status_effects_comp = StatusEffectsComponent()
                self.world.add_component(entity_id, status_effects_comp)
            
            # Get or create StateComponent
            state_comp = self.world.get_component(entity_id, StateComponent)
            if not state_comp:
                state_comp = StateComponent()
                self.world.add_component(entity_id, state_comp)
            
            # Look up the status effect definition
            effect_id = status_data.get("id")
            if effect_id not in self.world.status_effects:
                print(f"Warning: Status effect '{effect_id}' not found in status_effects.json")
                self.world.remove_component(entity_id, WantsToApplyStatusComponent)
                continue
            
            effect_definition = self.world.status_effects[effect_id]
            
            # Create the status effect entry
            effect_entry = {
                "id": effect_id,
                "name": effect_definition.get("name", effect_id),
                "type": status_data.get("type", "temporary"),
                "effects_data": effect_definition.get("effects", []),
                "turns_remaining": self.parse_duration(status_data.get("duration", "1"))
            }
            
            # Add to active effects
            status_effects_comp.effects.append(effect_entry)
            
            # Apply the mechanical effects immediately
            self.apply_effect_mechanics(entity_id, effect_entry, state_comp)
            
            # Show the application message
            target_name = "You" if self.world.get_component(entity_id, PlayerControllableComponent) else "The creature"
            message = status_data.get("on_apply_message", f"{target_name} is affected by {effect_entry['name']}!")
            if self.world.get_component(entity_id, PlayerControllableComponent):
                message = f"You {message}"
            else:
                desc = self.world.get_component(entity_id, DescriptionComponent)
                creature_name = desc.text if desc else "creature"
                message = f"The {creature_name} {message}"
            
            game_state.add_message(message)
            
            self.world.remove_component(entity_id, WantsToApplyStatusComponent)
    
    def parse_duration(self, duration_str):
        """Parse duration strings like '1d6', '2d4', or plain numbers."""
        if isinstance(duration_str, int):
            return duration_str
        
        duration_str = str(duration_str)
        
        # Handle dice notation (e.g., "1d6", "2d4")
        dice_match = re.match(r'(\d+)d(\d+)', duration_str)
        if dice_match:
            num_dice = int(dice_match.group(1))
            die_size = int(dice_match.group(2))
            total = 0
            for _ in range(num_dice):
                total += random.randint(1, die_size)
            return total
        
        # Handle plain numbers
        try:
            return int(duration_str)
        except ValueError:
            return 1  # Default duration
    
    def apply_effect_mechanics(self, entity_id, effect_entry, state_comp):
        """Apply the mechanical changes of a status effect."""
        effects_data = effect_entry["effects_data"]
        
        for effect in effects_data:
            target = effect.get("target")
            attribute = effect.get("attribute")
            flag = effect.get("flag")
            value = effect.get("value")
            
            if target == "state":
                # Apply state flags
                if flag and hasattr(state_comp, flag):
                    setattr(state_comp, flag, value)
            
            elif target == "StatsComponent":
                # Apply stat modifications
                stats_comp = self.world.get_component(entity_id, StatsComponent)
                if stats_comp and attribute and hasattr(stats_comp, attribute):
                    current_value = getattr(stats_comp, attribute)
                    setattr(stats_comp, attribute, current_value + value)
            
            elif target == "CombatComponent":
                # Apply combat modifications
                combat_comp = self.world.get_component(entity_id, CombatComponent)
                if combat_comp and attribute and hasattr(combat_comp, attribute):
                    current_value = getattr(combat_comp, attribute)
                    setattr(combat_comp, attribute, current_value + value)
                elif attribute in ["thac0", "damage_modifier", "save_penalty"]:
                    # Apply to state component modifiers
                    if attribute == "thac0":
                        state_comp.thac0_modifier += value
                    elif attribute == "damage_modifier":
                        state_comp.damage_modifier += value
                    elif attribute == "save_penalty":
                        state_comp.save_penalty += value
    
    def update_existing_status_effects(self, game_state):
        """Update durations and remove expired effects."""
        for entity_id in self.world.get_entities_with_components(StatusEffectsComponent):
            status_effects_comp = self.world.get_component(entity_id, StatusEffectsComponent)
            state_comp = self.world.get_component(entity_id, StateComponent)
            
            effects_to_remove = []
            
            for i, effect in enumerate(status_effects_comp.effects):
                if effect["type"] == "temporary":
                    effect["turns_remaining"] -= 1
                    
                    if effect["turns_remaining"] <= 0:
                        effects_to_remove.append(i)
                        # Remove the effect's mechanical changes
                        self.remove_effect_mechanics(entity_id, effect, state_comp)
                        
                        # Show expiry message
                        target_name = "You" if self.world.get_component(entity_id, PlayerControllableComponent) else "The creature"
                        if self.world.get_component(entity_id, PlayerControllableComponent):
                            message = f"You are no longer {effect['name'].lower()}."
                        else:
                            desc = self.world.get_component(entity_id, DescriptionComponent)
                            creature_name = desc.text if desc else "creature"
                            message = f"The {creature_name} is no longer {effect['name'].lower()}."
                        
                        game_state.add_message(message)
            
            # Remove expired effects (in reverse order to maintain indices)
            for i in reversed(effects_to_remove):
                del status_effects_comp.effects[i]
    
    def remove_effect_mechanics(self, entity_id, effect_entry, state_comp):
        """Remove the mechanical changes of an expired status effect."""
        effects_data = effect_entry["effects_data"]
        
        for effect in effects_data:
            target = effect.get("target")
            attribute = effect.get("attribute")
            flag = effect.get("flag")
            value = effect.get("value")
            
            if target == "state":
                # Remove state flags
                if flag and hasattr(state_comp, flag):
                    setattr(state_comp, flag, False)
            
            elif target == "StatsComponent":
                # Reverse stat modifications
                stats_comp = self.world.get_component(entity_id, StatsComponent)
                if stats_comp and attribute and hasattr(stats_comp, attribute):
                    current_value = getattr(stats_comp, attribute)
                    setattr(stats_comp, attribute, current_value - value)
            
            elif target == "CombatComponent":
                # Reverse combat modifications
                combat_comp = self.world.get_component(entity_id, CombatComponent)
                if combat_comp and attribute and hasattr(combat_comp, attribute):
                    current_value = getattr(combat_comp, attribute)
                    setattr(combat_comp, attribute, current_value - value)
                elif attribute in ["thac0", "damage_modifier", "save_penalty"]:
                    # Remove from state component modifiers
                    if attribute == "thac0":
                        state_comp.thac0_modifier -= value
                    elif attribute == "damage_modifier":
                        state_comp.damage_modifier -= value
                    elif attribute == "save_penalty":
                        state_comp.save_penalty -= value


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
            
            # Modify color based on status effects
            color = renderable.color
            state = self.world.get_component(entity_id, StateComponent)
            if state:
                if state.dead:
                    # Dead entities are already handled by death system (gray corpse)
                    color = renderable.color
                elif state.paralyzed or state.petrified:
                    color = (128, 128, 128)  # Gray for paralyzed/petrified
                elif state.confused:
                    color = (255, 0, 255)    # Magenta for confused
                elif state.lethally_poisoned or state.sickened:
                    color = (0, 255, 0)      # Green for poisoned
            
            text_surface = self.font.render(renderable.char, True, color)
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
        
        # Draw status information
        if game_state:
            self.draw_status_info(game_state)

    def draw_cursor_and_description(self, game_state):
        cursor_id = game_state.cursor_id
        if not cursor_id: return
        cursor_pos = self.world.get_component(cursor_id, PositionComponent)

        # Flashing cursor background
        if (pygame.time.get_ticks() // 400) % 2 == 0:
            bg_rect = pygame.Rect(cursor_pos.x * self.tile_size, cursor_pos.y * self.tile_size, self.tile_size, self.tile_size)
            pygame.draw.rect(self.screen, (50, 50, 0), bg_rect)

        # Get entity at cursor position and draw its description
        entity_id = self.world.get_entity_at_position(cursor_pos.x, cursor_pos.y)
        if not entity_id:
            entity_id = self.world.get_item_at_position(cursor_pos.x, cursor_pos.y)

        if entity_id:
            desc = self.world.get_component(entity_id, DescriptionComponent)
            material = self.world.get_component(entity_id, MaterialComponent)
            combat = self.world.get_component(entity_id, CombatComponent)
            
            # Add status effect info to description
            status_info = ""
            status_effects_comp = self.world.get_component(entity_id, StatusEffectsComponent)
            if status_effects_comp and status_effects_comp.effects:
                status_names = [effect["name"] for effect in status_effects_comp.effects]
                status_info = f" [{', '.join(status_names)}]"
            
            # Add HP info for living creatures
            hp_info = ""
            if combat and not self.world.get_component(entity_id, DeadComponent):
                hp_info = f" (HP: {combat.hp}/{combat.max_hp})"
            
            if desc:
                description_text = desc.text.format(material=material.name if material else "unknown") + status_info + hp_info
                description_surface = self.font.render(description_text, True, (255, 255, 255))
                description_rect = description_surface.get_rect(centerx=self.screen.get_width() // 2, y=self.screen.get_height() - 40)
                self.screen.blit(description_surface, description_rect)

    def draw_messages(self, game_state):
        y_offset = self.screen.get_height() - 20
        for message in reversed(game_state.message_log[-5:]):
            msg_surface = self.font.render(message, True, (255, 255, 255))
            msg_rect = msg_surface.get_rect(centerx=self.screen.get_width() / 2, bottom=y_offset)
            self.screen.blit(msg_surface, msg_rect)
            y_offset -= 20

    def draw_status_info(self, game_state):
        """Draw player status information in the top-left corner."""
        player_entities = self.world.get_entities_with_components(PlayerControllableComponent)
        if not player_entities: return
        player_id = player_entities[0]
        
        combat = self.world.get_component(player_id, CombatComponent)
        xp_comp = self.world.get_component(player_id, ExperienceComponent)
        status_effects_comp = self.world.get_component(player_id, StatusEffectsComponent)
        
        y_offset = 10
        
        # HP
        if combat:
            hp_text = f"HP: {combat.hp}/{combat.max_hp}"
            hp_surface = self.font.render(hp_text, True, (255, 255, 255))
            self.screen.blit(hp_surface, (10, y_offset))
            y_offset += 25
        
        # Level and XP
        if xp_comp:
            level_text = f"Level: {xp_comp.level}"
            level_surface = self.font.render(level_text, True, (255, 255, 255))
            self.screen.blit(level_surface, (10, y_offset))
            y_offset += 20
            
            xp_text = f"XP: {xp_comp.current_xp}/{xp_comp.xp_to_next_level}"
            xp_surface = self.font.render(xp_text, True, (255, 255, 255))
            self.screen.blit(xp_surface, (10, y_offset))
            y_offset += 25
        
        # Active status effects
        if status_effects_comp and status_effects_comp.effects:
            effects_text = "Status:"
            effects_surface = self.font.render(effects_text, True, (255, 255, 255))
            self.screen.blit(effects_surface, (10, y_offset))
            y_offset += 20
            
            for effect in status_effects_comp.effects:
                duration_text = ""
                if effect["type"] == "temporary":
                    duration_text = f" ({effect['turns_remaining']})"
                effect_text = f"  {effect['name']}{duration_text}"
                effect_surface = self.font.render(effect_text, True, (255, 255, 0))
                self.screen.blit(effect_surface, (10, y_offset))
                y_offset += 20

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
        game_state = kwargs.get('game_state')
        
        # Only act during monster turn
        if game_state.game_state != 'MONSTER_TURN':
            return
        
        player_entity = self.world.get_entities_with_components(PlayerControllableComponent)
        if not player_entity: return
        player_id = player_entity[0]
        player_pos = self.world.get_component(player_id, PositionComponent)

        for entity_id in self.world.get_entities_with_components(FactionComponent, PositionComponent, CombatComponent):
            faction = self.world.get_component(entity_id, FactionComponent)
            if faction.name != "monsters":
                continue  # Only control monsters
            
            # Skip dead monsters
            state = self.world.get_component(entity_id, StateComponent)
            if state and state.dead:
                continue

            # Check for status effects that prevent action
            if state and (state.paralyzed or state.petrified or state.unconscious or state.stunned):
                continue  # Monster cannot act

            monster_pos = self.world.get_component(entity_id, PositionComponent)

            # Check if player is within sight (10 tiles for now)
            distance = max(abs(player_pos.x - monster_pos.x), abs(player_pos.y - monster_pos.y))
            
            if distance <= 10:
                # Check for adjacency
                if distance == 1:
                    # Attack the player
                    self.world.add_component(entity_id, WantsToAttackComponent(player_id))
                else:
                    # Move towards the player (simple pathfinding)
                    dx, dy = 0, 0
                    
                    # Check for confusion
                    if state and state.confused:
                        # Confused movement is random
                        if random.random() < 0.5:  # 50% chance to move randomly
                            dx, dy = random.choice([(0, 1), (0, -1), (1, 0), (-1, 0)])
                        else:
                            # Normal movement toward player
                            if player_pos.x > monster_pos.x:
                                dx = 1
                            elif player_pos.x < monster_pos.x:
                                dx = -1
                            if player_pos.y > monster_pos.y:
                                dy = 1
                            elif player_pos.y < monster_pos.y:
                                dy = -1
                    else:
                        # Normal movement toward player
                        if player_pos.x > monster_pos.x:
                            dx = 1
                        elif player_pos.x < monster_pos.x:
                            dx = -1
                        if player_pos.y > monster_pos.y:
                            dy = 1
                        elif player_pos.y < monster_pos.y:
                            dy = -1
                    
                    # Only move if not blocked
                    target_x, target_y = monster_pos.x + dx, monster_pos.y + dy
                    target_entity = self.world.get_entity_at_position(target_x, target_y)
                    
                    if not target_entity or not self.world.get_component(target_entity, BlocksMovementComponent):
                        self.world.add_component(entity_id, WantsToMoveComponent(dx, dy))
            else:
                # Player not in sight - do nothing or wander randomly
                pass