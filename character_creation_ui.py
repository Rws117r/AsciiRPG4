# character_creation.py
# Character creation and class selection system

import random
import json
from components import *

class CharacterCreationState:
    """Manages the character creation workflow state."""
    def __init__(self):
        self.stage = 'ROLL_STATS'  # ROLL_STATS, SELECT_CLASS, FINALIZE
        self.rolled_stats = {}
        self.selected_class = None
        self.character_name = ""
        self.available_classes = []
        
class CharacterClass:
    """Represents a character class with all its properties."""
    def __init__(self, class_data):
        self.name = class_data['name']
        self.requirements = class_data.get('requirements', {})
        self.prime_requisite = class_data.get('prime_requisite', [])
        self.hit_die = class_data.get('hit_dice', '1d6')
        self.max_level = class_data.get('max_level', 14)
        self.armor_allowed = class_data.get('armor', [])
        self.weapons_allowed = class_data.get('weapons', [])
        self.abilities = class_data.get('abilities', [])
        self.spell_progression = class_data.get('spells', {})
        self.level_progression = class_data.get('progression', [])
        self.description = class_data.get('description', '')
        
    def meets_requirements(self, stats):
        """Check if the given stats meet class requirements."""
        for stat, min_value in self.requirements.items():
            if stats.get(stat.lower(), 0) < min_value:
                return False
        return True
    
    def get_level_data(self, level):
        """Get progression data for a specific level."""
        if level <= 0 or level > len(self.level_progression):
            return None
        return self.level_progression[level - 1]

class CharacterCreationSystem:
    """Handles the character creation process."""
    
    def __init__(self, world):
        self.world = world
        self.classes = self.load_classes()
        self.creation_state = CharacterCreationState()
        
    def load_classes(self):
        """Load character class definitions from JSON."""
        try:
            with open('classes.json', 'r') as f:
                data = json.load(f)
                return {name: CharacterClass(class_data) 
                       for name, class_data in data.items()}
        except FileNotFoundError:
            print("Warning: classes.json not found!")
            return {}
    
    def roll_ability_scores(self):
        """Roll 3d6 for each ability score."""
        abilities = ['strength', 'intelligence', 'wisdom', 
                    'dexterity', 'constitution', 'charisma']
        rolled = {}
        
        for ability in abilities:
            # Roll 3d6
            rolls = [random.randint(1, 6) for _ in range(3)]
            rolled[ability] = sum(rolls)
            
        self.creation_state.rolled_stats = rolled
        return rolled
    
    def get_available_classes(self, stats):
        """Get list of classes the character qualifies for."""
        available = []
        for class_name, char_class in self.classes.items():
            if char_class.meets_requirements(stats):
                available.append(class_name)
        
        self.creation_state.available_classes = available
        return available
    
    def select_class(self, class_name):
        """Select a class for the character."""
        if class_name in self.classes and class_name in self.creation_state.available_classes:
            self.creation_state.selected_class = class_name
            return True
        return False
    
    def calculate_hit_points(self, class_name, constitution):
        """Calculate starting hit points based on class and constitution."""
        char_class = self.classes.get(class_name)
        if not char_class:
            return 4
        
        # Parse hit die (e.g., "1d8" -> 8)
        hit_die = char_class.hit_die
        if 'd' in hit_die:
            die_size = int(hit_die.split('d')[1])
        else:
            die_size = 6
        
        # Roll hit die
        hp = random.randint(1, die_size)
        
        # Apply constitution modifier
        con_modifier = self.get_ability_modifier(constitution)
        hp = max(1, hp + con_modifier)  # Minimum 1 HP
        
        return hp
    
    def get_ability_modifier(self, score):
        """Get the OSE ability score modifier."""
        if score <= 3:
            return -3
        elif score <= 5:
            return -2
        elif score <= 8:
            return -1
        elif score <= 12:
            return 0
        elif score <= 15:
            return 1
        elif score <= 17:
            return 2
        else:
            return 3
    
    def get_saving_throws(self, class_name, level=1):
        """Get saving throw values for a class at a given level."""
        char_class = self.classes.get(class_name)
        if not char_class:
            return {
                'death': 16,
                'wands': 16,
                'paralysis': 16,
                'breath': 16,
                'spells': 16
            }
        
        level_data = char_class.get_level_data(level)
        if level_data and 'saves' in level_data:
            return level_data['saves']
        
        # Default saves
        return {
            'death': 16,
            'wands': 16,
            'paralysis': 16,
            'breath': 16,
            'spells': 16
        }
    
    def get_thac0(self, class_name, level=1):
        """Get THAC0 for a class at a given level."""
        char_class = self.classes.get(class_name)
        if not char_class:
            return 19
        
        level_data = char_class.get_level_data(level)
        if level_data and 'thac0' in level_data:
            return level_data['thac0']
        
        return 19
    
    def get_class_abilities(self, class_name):
        """Get starting abilities for a class."""
        char_class = self.classes.get(class_name)
        if not char_class:
            return []
        
        # Return ability IDs that should be granted at level 1
        return [ability for ability in char_class.abilities 
                if isinstance(ability, str)]  # Simple string IDs for now
    
    def create_character(self, name="Player"):
        """Create the final character entity based on selections."""
        if not self.creation_state.selected_class:
            print("No class selected!")
            return None
        
        # Remove any existing player entity
        player_entities = self.world.get_entities_with_components(PlayerControllableComponent)
        for entity_id in player_entities:
            # Remove the entity properly
            for comp_type in list(self.world.components.keys()):
                if entity_id in self.world.components[comp_type]:
                    del self.world.components[comp_type][entity_id]
            if entity_id in self.world.entities:
                del self.world.entities[entity_id]
        
        # Create new player entity
        entity = self.world.create_entity()
        
        # Get class data
        class_name = self.creation_state.selected_class
        char_class = self.classes[class_name]
        stats = self.creation_state.rolled_stats
        
        # Calculate derived values
        hp = self.calculate_hit_points(class_name, stats['constitution'])
        ac = 9 - self.get_ability_modifier(stats['dexterity'])  # Base AC with DEX modifier
        thac0 = self.get_thac0(class_name, 1)
        saves = self.get_saving_throws(class_name, 1)
        
        # Add components
        self.world.add_component(entity.id, PositionComponent(5, 5))
        self.world.add_component(entity.id, RenderableComponent('@', (255, 255, 255)))
        self.world.add_component(entity.id, PlayerControllableComponent())
        self.world.add_component(entity.id, DescriptionComponent(f"{name} the {class_name}"))
        
        self.world.add_component(entity.id, StatsComponent(
            strength=stats['strength'],
            intelligence=stats['intelligence'],
            wisdom=stats['wisdom'],
            dexterity=stats['dexterity'],
            constitution=stats['constitution'],
            charisma=stats['charisma'],
            save_death=saves.get('death', 16),
            save_wands=saves.get('wands', 16),
            save_paralysis=saves.get('paralysis', 16),
            save_breath=saves.get('breath', 16),
            save_spells=saves.get('spells', 16)
        ))
        
        self.world.add_component(entity.id, CombatComponent(
            hp=hp,
            ac=ac,
            thac0=thac0,
            max_hp=hp,
            xp_value=0
        ))
        
        self.world.add_component(entity.id, FactionComponent("player"))
        self.world.add_component(entity.id, StateComponent())
        self.world.add_component(entity.id, InventoryComponent())
        self.world.add_component(entity.id, CanEquipComponent())
        self.world.add_component(entity.id, EquipmentComponent())
        
        # Add class component to track character class
        class_comp = ClassComponent(class_name)
        self.world.add_component(entity.id, class_comp)
        
        # Add experience component
        xp_comp = ExperienceComponent(current_xp=0, level=1)
        xp_comp.xp_to_next_level = self.get_xp_for_level(class_name, 2)
        self.world.add_component(entity.id, xp_comp)
        
        # Add class abilities
        abilities = self.get_class_abilities(class_name)
        if abilities:
            self.world.add_component(entity.id, AbilitiesComponent(abilities))
        
        print(f"Created {name} the {class_name}!")
        return entity.id
    
    def get_xp_for_level(self, class_name, level):
        """Get XP required for a specific level in a class."""
        char_class = self.classes.get(class_name)
        if not char_class or level <= 1:
            return 0
        
        level_data = char_class.get_level_data(level)
        if level_data and 'xp' in level_data:
            return level_data['xp']
        
        # Default Fighter progression if not specified
        return 2000 * (2 ** (level - 2))


class ClassComponent(Component):
    """Tracks the character's class."""
    def __init__(self, class_name):
        self.class_name = class_name


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