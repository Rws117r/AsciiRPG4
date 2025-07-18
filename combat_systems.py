# combat_systems.py
# Combat, abilities, and saving throw systems

import random
import re
from components import *
from core_systems import System

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

class AbilitySystem(System):
    """Handles WantsToUseAbility intents created by the new UI."""
    
    def update(self, *args, **kwargs):
        game_state = kwargs.get('game_state')
        
        for entity_id in self.world.get_entities_with_components(WantsToUseAbilityComponent):
            ability_intent = self.world.get_component(entity_id, WantsToUseAbilityComponent)
            ability_id = ability_intent.ability_id
            target_id = ability_intent.target_id
            target_position = ability_intent.target_position
            
            if ability_id not in self.world.abilities:
                print(f"Warning: Ability '{ability_id}' not found")
                self.world.remove_component(entity_id, WantsToUseAbilityComponent)
                continue
            
            ability_data = self.world.abilities[ability_id]
            effect_type = ability_data.get("effect")
            chance = ability_data.get("chance", 1.0)
            
            # Roll for ability success
            if random.random() <= chance:
                if effect_type == "heal":
                    self.apply_healing(entity_id, target_id, ability_data, game_state)
                elif effect_type == "damage":
                    self.apply_damage(entity_id, target_id, ability_data, game_state)
                elif effect_type == "damage_aoe":
                    self.apply_damage_aoe(entity_id, target_position, ability_data, game_state)
                elif effect_type == "damage_line":
                    self.apply_damage_line(entity_id, target_position, ability_data, game_state)
                elif effect_type == "apply_status":
                    self.apply_single_status(entity_id, target_id, ability_data, game_state)
                elif effect_type == "apply_status_aoe":
                    self.apply_aoe_status_effect(entity_id, ability_data, game_state)
                elif effect_type == "cure_status":
                    self.cure_status_effects(entity_id, target_id, ability_data, game_state)
                else:
                    game_state.add_message(f"Unknown ability effect type: {effect_type}")
            else:
                # Ability failed its chance roll
                user_name = "You" if self.world.get_component(entity_id, PlayerControllableComponent) else "The creature"
                ability_name = ability_data.get("name", ability_id.replace('_', ' '))
                game_state.add_message(f"{user_name} {'try' if user_name == 'You' else 'tries'} to use {ability_name} but {'fail' if user_name == 'You' else 'fails'}!")
            
            self.world.remove_component(entity_id, WantsToUseAbilityComponent)
    
    def parse_dice_damage(self, damage_str):
        """Parse damage strings like '1d8+1', '6d6', or plain numbers."""
        if isinstance(damage_str, int):
            return damage_str
        
        damage_str = str(damage_str)
        
        # Handle dice notation with modifier (e.g., "1d8+1", "3d6-2")
        dice_match = re.match(r'(\d+)d(\d+)([+-]\d+)?', damage_str)
        if dice_match:
            num_dice = int(dice_match.group(1))
            die_size = int(dice_match.group(2))
            modifier = int(dice_match.group(3)) if dice_match.group(3) else 0
            
            total = 0
            for _ in range(num_dice):
                total += random.randint(1, die_size)
            return total + modifier
        
        # Handle plain numbers
        try:
            return int(damage_str)
        except ValueError:
            return 1  # Default damage
    
    def apply_healing(self, caster_id, target_id, ability_data, game_state):
        """Apply healing to a target."""
        if not target_id:
            game_state.add_message("No valid target for healing!")
            return
        
        target_combat = self.world.get_component(target_id, CombatComponent)
        if not target_combat:
            game_state.add_message("Target cannot be healed!")
            return
        
        healing_amount = self.parse_dice_damage(ability_data.get("healing", "1d8"))
        
        # Apply healing
        old_hp = target_combat.hp
        target_combat.hp = min(target_combat.max_hp, target_combat.hp + healing_amount)
        actual_healing = target_combat.hp - old_hp
        
        # Generate message
        caster_name = "You" if self.world.get_component(caster_id, PlayerControllableComponent) else "The creature"
        target_name = "yourself" if target_id == caster_id else ("you" if self.world.get_component(target_id, PlayerControllableComponent) else "the target")
        
        ability_name = ability_data.get("name", "heal")
        
        if actual_healing > 0:
            game_state.add_message(f"{caster_name} {'use' if caster_name == 'You' else 'uses'} {ability_name} and {'heal' if caster_name == 'You' else 'heals'} {target_name} for {actual_healing} HP!")
        else:
            game_state.add_message(f"{target_name.capitalize()} {'are' if target_name == 'you' else 'is'} already at full health!")
    
    def apply_damage(self, caster_id, target_id, ability_data, game_state):
        """Apply damage to a single target."""
        if not target_id:
            game_state.add_message("No valid target for damage!")
            return
        
        target_combat = self.world.get_component(target_id, CombatComponent)
        if not target_combat:
            game_state.add_message("Target cannot be damaged!")
            return
        
        damage_amount = self.parse_dice_damage(ability_data.get("damage", "1d4"))
        
        # Apply damage
        target_combat.hp -= damage_amount
        
        # Generate message
        caster_name = "You" if self.world.get_component(caster_id, PlayerControllableComponent) else "The creature"
        target_name = "you" if self.world.get_component(target_id, PlayerControllableComponent) else "the target"
        
        ability_name = ability_data.get("name", "attack")
        game_state.add_message(f"{caster_name} {'use' if caster_name == 'You' else 'uses'} {ability_name} and {'deal' if caster_name == 'You' else 'deals'} {damage_amount} damage to {target_name}!")
        
        # Check for death
        if target_combat.hp <= 0:
            from combat_systems import CombatSystem
            combat_system = self.world.get_system(CombatSystem)
            if combat_system:
                combat_system.handle_death(target_id, caster_id, game_state)
    
    def apply_damage_aoe(self, caster_id, target_position, ability_data, game_state):
        """Apply area of effect damage around a target position."""
        if not target_position:
            game_state.add_message("No valid target position!")
            return
        
        target_x, target_y = target_position
        aoe_radius = ability_data.get("aoe_radius", 1)
        damage_amount = self.parse_dice_damage(ability_data.get("damage", "1d6"))
        
        affected_entities = []
        for entity_id in self.world.get_entities_with_components(PositionComponent, CombatComponent):
            entity_pos = self.world.get_component(entity_id, PositionComponent)
            distance = max(abs(entity_pos.x - target_x), abs(entity_pos.y - target_y))
            
            if distance <= aoe_radius:
                # Apply damage
                combat = self.world.get_component(entity_id, CombatComponent)
                combat.hp -= damage_amount
                affected_entities.append(entity_id)
                
                # Check for death
                if combat.hp <= 0:
                    from combat_systems import CombatSystem
                    combat_system = self.world.get_system(CombatSystem)
                    if combat_system:
                        combat_system.handle_death(entity_id, caster_id, game_state)
        
        # Generate message
        caster_name = "You" if self.world.get_component(caster_id, PlayerControllableComponent) else "The creature"
        ability_name = ability_data.get("name", "area attack")
        game_state.add_message(f"{caster_name} {'use' if caster_name == 'You' else 'uses'} {ability_name}, dealing {damage_amount} damage to {len(affected_entities)} targets!")
    
    def apply_damage_line(self, caster_id, target_position, ability_data, game_state):
        """Apply damage in a line from caster to target position."""
        caster_pos = self.world.get_component(caster_id, PositionComponent)
        if not caster_pos or not target_position:
            game_state.add_message("Invalid line target!")
            return
        
        target_x, target_y = target_position
        damage_amount = self.parse_dice_damage(ability_data.get("damage", "1d6"))
        
        # Calculate line path (simple implementation)
        affected_entities = []
        dx = 1 if target_x > caster_pos.x else (-1 if target_x < caster_pos.x else 0)
        dy = 1 if target_y > caster_pos.y else (-1 if target_y < caster_pos.y else 0)
        
        x, y = caster_pos.x + dx, caster_pos.y + dy  # Start from first tile after caster
        
        # Trace the line to the target
        while (x != target_x or y != target_y) and abs(x - caster_pos.x) <= 10 and abs(y - caster_pos.y) <= 10:
            entity_id = self.world.get_entity_at_position(x, y)
            if entity_id:
                combat = self.world.get_component(entity_id, CombatComponent)
                if combat:
                    combat.hp -= damage_amount
                    affected_entities.append(entity_id)
                    
                    # Check for death
                    if combat.hp <= 0:
                        from combat_systems import CombatSystem
                        combat_system = self.world.get_system(CombatSystem)
                        if combat_system:
                            combat_system.handle_death(entity_id, caster_id, game_state)
            
            x += dx
            y += dy
        
        # Generate message
        caster_name = "You" if self.world.get_component(caster_id, PlayerControllableComponent) else "The creature"
        ability_name = ability_data.get("name", "line attack")
        game_state.add_message(f"{caster_name} {'use' if caster_name == 'You' else 'uses'} {ability_name}, dealing {damage_amount} damage to {len(affected_entities)} targets in a line!")
    
    def apply_single_status(self, caster_id, target_id, ability_data, game_state):
        """Apply a status effect to a single target."""
        if not target_id:
            game_state.add_message("No valid target for status effect!")
            return
        
        status_effect = ability_data.get("status_effect")
        if not status_effect:
            return
        
        save_type = self.get_save_type_for_effect(status_effect.get("id"))
        if save_type:
            # Create saving throw intent
            self.world.add_component(target_id, WantsToMakeSavingThrowComponent(
                save_type=save_type,
                dc=15,
                effect_data=status_effect,
                source_entity_id=caster_id
            ))
        else:
            # No save allowed, apply directly
            self.world.add_component(target_id, WantsToApplyStatusComponent(
                status_effect_data=status_effect,
                source_entity_id=caster_id
            ))
    
    def apply_aoe_status_effect(self, caster_id, ability_data, game_state):
        """Apply area of effect status effects around the caster."""
        caster_pos = self.world.get_component(caster_id, PositionComponent)
        if not caster_pos:
            return
        
        status_effect = ability_data.get("status_effect")
        if not status_effect:
            return
        
        # Get AOE range (default to 1 tile radius)
        aoe_range = ability_data.get("range", 1)
        
        # Find all entities within range
        affected_entities = []
        for entity_id in self.world.get_entities_with_components(PositionComponent):
            if entity_id == caster_id:
                continue  # Don't affect self unless specified
                
            entity_pos = self.world.get_component(entity_id, PositionComponent)
            distance = max(abs(entity_pos.x - caster_pos.x), abs(entity_pos.y - caster_pos.y))
            
            if distance <= aoe_range:
                # Check if this entity can be affected (has combat component)
                if self.world.get_component(entity_id, CombatComponent):
                    affected_entities.append(entity_id)
        
        # Apply status effect to all affected entities
        for target_id in affected_entities:
            save_type = self.get_save_type_for_effect(status_effect.get("id"))
            if save_type:
                self.world.add_component(target_id, WantsToMakeSavingThrowComponent(
                    save_type=save_type,
                    dc=15,
                    effect_data=status_effect,
                    source_entity_id=caster_id
                ))
            else:
                self.world.add_component(target_id, WantsToApplyStatusComponent(
                    status_effect_data=status_effect,
                    source_entity_id=caster_id
                ))
        
        # Message about AOE effect
        caster_name = "You" if self.world.get_component(caster_id, PlayerControllableComponent) else "The creature"
        ability_name = ability_data.get("name", "ability")
        game_state.add_message(f"{caster_name} {'use' if caster_name == 'You' else 'uses'} {ability_name}, affecting {len(affected_entities)} targets!")
    
    def cure_status_effects(self, caster_id, target_id, ability_data, game_state):
        """Cure specific status effects from a target."""
        if not target_id:
            game_state.add_message("No valid target for cure!")
            return
        
        cures = ability_data.get("cures", [])
        if not cures:
            return
        
        status_effects_comp = self.world.get_component(target_id, StatusEffectsComponent)
        if not status_effects_comp:
            game_state.add_message("Target has no status effects to cure!")
            return
        
        cured_effects = []
        effects_to_remove = []
        
        for i, effect in enumerate(status_effects_comp.effects):
            if effect["id"] in cures:
                cured_effects.append(effect["name"])
                effects_to_remove.append(i)
                
                # Remove the effect's mechanical changes
                state_comp = self.world.get_component(target_id, StateComponent)
                if state_comp:
                    from status_systems import StatusEffectSystem
                    status_system = self.world.get_system(StatusEffectSystem)
                    if status_system:
                        status_system.remove_effect_mechanics(target_id, effect, state_comp)
        
        # Remove cured effects (in reverse order to maintain indices)
        for i in reversed(effects_to_remove):
            del status_effects_comp.effects[i]
        
        # Generate message
        caster_name = "You" if self.world.get_component(caster_id, PlayerControllableComponent) else "The creature"
        target_name = "yourself" if target_id == caster_id else ("you" if self.world.get_component(target_id, PlayerControllableComponent) else "the target")
        ability_name = ability_data.get("name", "cure")
        
        if cured_effects:
            effects_str = ", ".join(cured_effects)
            game_state.add_message(f"{caster_name} {'use' if caster_name == 'You' else 'uses'} {ability_name} and {'cure' if caster_name == 'You' else 'cures'} {target_name} of {effects_str}!")
        else:
            game_state.add_message(f"{target_name.capitalize()} {'have' if target_name == 'you' else 'has'} no curable effects!")
    
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
            "deafness": "spells",
            "slowness": "spells",
            "unconsciousness": "spells",
            "ability_drain_strength": None, # No save
            "ability_drain_wisdom": None,
            "ability_drain_charisma": None,
        }
        return save_mapping.get(effect_id, "spells")  # Default to spells save

class CombatSystem(System):
    """Handles combat between entities and ability processing."""
    
    def update(self, *args, **kwargs):
        game_state = kwargs.get('game_state')
        
        # Process ability triggers first
        self.process_ability_triggers(game_state)
        
        # Then process regular attacks
        self.process_attacks(game_state)

    def process_ability_triggers(self, game_state):
        """Process WantsToTriggerAbilityComponent intents."""
        for entity_id in self.world.get_entities_with_components(WantsToTriggerAbilityComponent):
            trigger_intent = self.world.get_component(entity_id, WantsToTriggerAbilityComponent)
            ability_id = trigger_intent.ability_id
            target_id = trigger_intent.target_id
            
            if ability_id not in self.world.abilities:
                print(f"Warning: Ability '{ability_id}' not found")
                self.world.remove_component(entity_id, WantsToTriggerAbilityComponent)
                continue
            
            ability_data = self.world.abilities[ability_id]
            effect_type = ability_data.get("effect")
            chance = ability_data.get("chance", 1.0)
            
            # Roll for ability success
            if random.random() <= chance:
                if effect_type == "apply_status":
                    # Single target status effect
                    if target_id:
                        status_effect = ability_data.get("status_effect")
                        if status_effect:
                            save_type = self.get_save_type_for_effect(status_effect.get("id"))
                            if save_type:
                                # Create saving throw intent
                                self.world.add_component(target_id, WantsToMakeSavingThrowComponent(
                                    save_type=save_type,
                                    dc=15,
                                    effect_data=status_effect,
                                    source_entity_id=entity_id
                                ))
                            else:
                                # No save allowed, apply directly
                                self.world.add_component(target_id, WantsToApplyStatusComponent(
                                    status_effect_data=status_effect,
                                    source_entity_id=entity_id
                                ))
                    else:
                        game_state.add_message("No valid target for ability!")
                        
                elif effect_type == "apply_status_aoe":
                    # Area of effect status application
                    self.apply_aoe_status_effect(entity_id, ability_data, game_state)
                    
                else:
                    game_state.add_message(f"Unknown ability effect type: {effect_type}")
            else:
                # Ability failed its chance roll
                user_name = "You" if self.world.get_component(entity_id, PlayerControllableComponent) else "The creature"
                game_state.add_message(f"{user_name} {'try' if user_name == 'You' else 'tries'} to use {ability_id.replace('_', ' ')} but {'fail' if user_name == 'You' else 'fails'}!")
            
            self.world.remove_component(entity_id, WantsToTriggerAbilityComponent)

    def apply_aoe_status_effect(self, caster_id, ability_data, game_state):
        """Apply area of effect status effects around the caster."""
        caster_pos = self.world.get_component(caster_id, PositionComponent)
        if not caster_pos:
            return
        
        status_effect = ability_data.get("status_effect")
        if not status_effect:
            return
        
        # Get AOE range (default to 1 tile radius)
        aoe_range = ability_data.get("range", 1)
        
        # Find all entities within range
        affected_entities = []
        for entity_id in self.world.get_entities_with_components(PositionComponent):
            if entity_id == caster_id:
                continue  # Don't affect self unless specified
                
            entity_pos = self.world.get_component(entity_id, PositionComponent)
            distance = max(abs(entity_pos.x - caster_pos.x), abs(entity_pos.y - caster_pos.y))
            
            if distance <= aoe_range:
                # Check if this entity can be affected (has combat component)
                if self.world.get_component(entity_id, CombatComponent):
                    affected_entities.append(entity_id)
        
        # Apply status effect to all affected entities
        for target_id in affected_entities:
            save_type = self.get_save_type_for_effect(status_effect.get("id"))
            if save_type:
                self.world.add_component(target_id, WantsToMakeSavingThrowComponent(
                    save_type=save_type,
                    dc=15,
                    effect_data=status_effect,
                    source_entity_id=caster_id
                ))
            else:
                self.world.add_component(target_id, WantsToApplyStatusComponent(
                    status_effect_data=status_effect,
                    source_entity_id=caster_id
                ))
        
        # Message about AOE effect
        caster_name = "You" if self.world.get_component(caster_id, PlayerControllableComponent) else "The creature"
        ability_name = ability_data.get("name", "ability")
        game_state.add_message(f"{caster_name} {'use' if caster_name == 'You' else 'uses'} {ability_name}, affecting {len(affected_entities)} targets!")

    def process_attacks(self, game_state):
        """Process regular attack intents."""
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
            "deafness": "spells",
            "slowness": "spells",
            "unconsciousness": "spells",
            "ability_drain_strength": None, # No save
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