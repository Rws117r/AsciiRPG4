# status_systems.py
# Status effect management and AI systems

import random
import re
from components import *
from core_systems import System

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