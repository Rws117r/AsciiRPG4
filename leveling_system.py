# leveling_system.py
# Handles character advancement and level-up mechanics

import random
from components import *
from core_systems import System

class LevelingSystem(System):
    """Manages character leveling and progression."""
    
    def __init__(self, world, character_creation_system):
        super().__init__(world)
        self.creation_system = character_creation_system
        
    def check_level_up(self, entity_id, game_state):
        """Check if an entity has enough XP to level up."""
        xp_comp = self.world.get_component(entity_id, ExperienceComponent)
        class_comp = self.world.get_component(entity_id, ClassComponent)
        
        if not xp_comp or not class_comp:
            return False
        
        # Get next level XP requirement
        next_level = xp_comp.level + 1
        char_class = self.creation_system.classes.get(class_comp.class_name)
        
        if not char_class or next_level > char_class.max_level:
            return False
        
        level_data = char_class.get_level_data(next_level)
        if not level_data:
            return False
        
        required_xp = level_data.get('xp', float('inf'))
        
        # Check if player has enough XP
        if xp_comp.current_xp >= required_xp:
            self.level_up(entity_id, xp_comp, class_comp, char_class, game_state)
            return True
        
        return False
    
    def level_up(self, entity_id, xp_comp, class_comp, char_class, game_state):
        """Handle the actual level-up process."""
        old_level = xp_comp.level
        new_level = old_level + 1
        
        # Update level
        xp_comp.level = new_level
        
        # Get level data
        level_data = char_class.get_level_data(new_level)
        if not level_data:
            return
        
        # Update XP to next level
        next_level_data = char_class.get_level_data(new_level + 1)
        if next_level_data:
            xp_comp.xp_to_next_level = next_level_data.get('xp', float('inf'))
        else:
            xp_comp.xp_to_next_level = float('inf')  # Max level reached
        
        # Roll for HP increase
        hp_gain = self.roll_hit_points(char_class.hit_die, entity_id)
        combat = self.world.get_component(entity_id, CombatComponent)
        if combat:
            combat.max_hp += hp_gain
            combat.hp += hp_gain  # Heal to full on level up
        
        # Update THAC0
        new_thac0 = level_data.get('thac0', combat.thac0)
        if combat and new_thac0 < combat.thac0:
            combat.thac0 = new_thac0
        
        # Update saving throws
        new_saves = level_data.get('saves', {})
        if new_saves:
            stats = self.world.get_component(entity_id, StatsComponent)
            if stats:
                stats.save_death = new_saves.get('death', stats.save_death)
                stats.save_wands = new_saves.get('wands', stats.save_wands)
                stats.save_paralysis = new_saves.get('paralysis', stats.save_paralysis)
                stats.save_breath = new_saves.get('breath', stats.save_breath)
                stats.save_spells = new_saves.get('spells', stats.save_spells)
        
        # Check for new abilities
        self.grant_level_abilities(entity_id, char_class, new_level, game_state)
        
        # Check for new spells
        self.update_spell_slots(entity_id, char_class, new_level, game_state)
        
        # Announce level up
        game_state.add_message(f"*** LEVEL UP! ***")
        game_state.add_message(f"Welcome to level {new_level}!")
        game_state.add_message(f"You gain {hp_gain} hit points!")
        
        if new_thac0 < combat.thac0:
            game_state.add_message(f"Your combat skills improve! (THAC0: {new_thac0})")
        
        # Check for max level
        if new_level >= char_class.max_level:
            game_state.add_message(f"You have reached the maximum level for {char_class.name}!")
    
    def roll_hit_points(self, hit_die_str, entity_id):
        """Roll hit points for level up."""
        # Parse hit die (e.g., "1d8" -> 8)
        if 'd' in hit_die_str:
            die_size = int(hit_die_str.split('d')[1])
        else:
            die_size = 6
        
        # Roll the die
        roll = random.randint(1, die_size)
        
        # Apply constitution modifier
        stats = self.world.get_component(entity_id, StatsComponent)
        if stats:
            con_mod = self.creation_system.get_ability_modifier(stats.constitution)
            roll = max(1, roll + con_mod)  # Minimum 1 HP per level
        
        return roll
    
    def grant_level_abilities(self, entity_id, char_class, level, game_state):
        """Grant any abilities gained at this level."""
        # This is a placeholder - you would implement specific ability grants here
        # based on class and level
        
        # Example: Thieves get better at their skills
        if char_class.name == "Thief" and hasattr(char_class, 'skills'):
            game_state.add_message("Your thieving skills improve!")
        
        # Example: Clerics get Turn Undead at level 1 (already granted at creation)
        # But might get improvements at higher levels
        
    def update_spell_slots(self, entity_id, char_class, level, game_state):
        """Update spell slots for spellcasting classes."""
        if not hasattr(char_class, 'spells') or not char_class.spells:
            return
        
        # Get or create spell slots component
        spell_slots = self.world.get_component(entity_id, SpellSlotsComponent)
        if not spell_slots:
            spell_slots = SpellSlotsComponent()
            self.world.add_component(entity_id, spell_slots)
        
        # Update slots based on level
        spells_changed = False
        for spell_level, slots_by_level in char_class.spells.items():
            if level <= len(slots_by_level):
                new_slots = slots_by_level[level - 1]
                old_slots = spell_slots.slots.get(spell_level, 0)
                
                if new_slots > old_slots:
                    spell_slots.slots[spell_level] = new_slots
                    spell_slots.slots_used[spell_level] = 0
                    spells_changed = True
        
        if spells_changed:
            game_state.add_message("You gain new spell slots!")
            # Show current spell slots
            slot_info = []
            for level in sorted(spell_slots.slots.keys()):
                if spell_slots.slots[level] > 0:
                    slot_info.append(f"Level {level}: {spell_slots.slots[level]}")
            if slot_info:
                game_state.add_message(f"Spell slots: {', '.join(slot_info)}")


class SpellSlotsComponent(Component):
    """Tracks spell slots for spellcasting characters."""
    def __init__(self):
        self.slots = {}  # {spell_level: max_slots}
        self.slots_used = {}  # {spell_level: used_slots}
        
    def can_cast(self, spell_level):
        """Check if can cast a spell of given level."""
        max_slots = self.slots.get(spell_level, 0)
        used_slots = self.slots_used.get(spell_level, 0)
        return used_slots < max_slots
    
    def use_slot(self, spell_level):
        """Use a spell slot of given level."""
        if self.can_cast(spell_level):
            self.slots_used[spell_level] = self.slots_used.get(spell_level, 0) + 1
            return True
        return False
    
    def rest(self):
        """Restore all spell slots (after rest)."""
        for level in self.slots:
            self.slots_used[level] = 0