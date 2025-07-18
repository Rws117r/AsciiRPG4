# components.py
# Defines all the data components for the ECS.

class Component:
    """A base class for components. Components hold data."""
    pass

class PositionComponent(Component):
    """Stores the (x, y) grid coordinates of an entity."""
    def __init__(self, x, y):
        self.x = x
        self.y = y

class RenderableComponent(Component):
    """Stores the visual representation of an entity: a character and its color."""
    def __init__(self, char, color, open_char=None, closed_char=None):
        self.char = char
        self.color = color
        self.open_char = open_char
        self.closed_char = closed_char

class PlayerControllableComponent(Component):
    """A tag component to identify the entity controlled by the player."""
    pass

class WantsToMoveComponent(Component):
    """Stores the intended movement direction (dx, dy) for an entity."""
    def __init__(self, dx, dy):
        self.dx = dx
        self.dy = dy

class DescriptionComponent(Component):
    """Stores the descriptive text for an entity."""
    def __init__(self, text):
        self.text = text

class CursorComponent(Component):
    """A tag component to identify the look cursor."""
    pass

class StatsComponent(Component):
    """Stores the core ability scores of an entity."""
    def __init__(self, strength, intelligence, wisdom, dexterity, constitution, charisma, 
                 save_death=16, save_wands=16, save_paralysis=16, save_breath=16, save_spells=16):
        self.strength = strength
        self.intelligence = intelligence
        self.wisdom = wisdom
        self.dexterity = dexterity
        self.constitution = constitution
        self.charisma = charisma
        # Saving Throws
        self.save_death = save_death
        self.save_wands = save_wands
        self.save_paralysis = save_paralysis
        self.save_breath = save_breath
        self.save_spells = save_spells

class CombatComponent(Component):
    """Stores combat-related stats for an entity."""
    def __init__(self, hp, ac, thac0, max_hp=None, xp_value=0):
        self.hp = hp
        self.max_hp = max_hp if max_hp is not None else hp
        self.ac = ac
        self.thac0 = thac0
        self.xp_value = xp_value

class CanEquipComponent(Component):
    """A tag component for entities that can equip items."""
    pass

class EquippableComponent(Component):
    """A component for items that can be equipped."""
    def __init__(self, slot):
        self.slot = slot # e.g., "weapon", "armor", "amulet"

class EquipmentComponent(Component):
    """A component to track an entity's equipped items."""
    def __init__(self):
        self.slots = {"weapon": None, "armor": None, "amulet": None}

class MaterialComponent(Component):
    """Defines the material an entity is made of."""
    def __init__(self, name):
        self.name = name

class ItemComponent(Component):
    """A tag component for items that can be picked up."""
    pass

class FactionComponent(Component):
    """A component to define an entity's faction."""
    def __init__(self, name):
        self.name = name

class ContainerComponent(Component):
    """A component for entities that can hold other items."""
    def __init__(self, contents=None):
        self.contents = contents if contents is not None else []

class LockableComponent(Component):
    """A component for entities that can have a lock attached."""
    def __init__(self, is_locked=True, key_id=None):
        self.is_locked = is_locked
        self.key_id = key_id

class KeyComponent(Component):
    """A component for key items."""
    def __init__(self, key_id=None):
        self.key_id = key_id

class PadlockComponent(Component):
    """A component for lock items."""
    def __init__(self, is_locked=True, key_id=None, attached_to=None):
        self.is_locked = is_locked
        self.key_id = key_id
        self.attached_to = attached_to

class OpenableComponent(Component):
    """A component for things that can be opened and closed."""
    def __init__(self, is_open=False):
        self.is_open = is_open

class BlocksMovementComponent(Component):
    """A tag component for entities that block movement."""
    pass

class InventoryComponent(Component):
    """Holds a list of entity IDs that an entity is carrying."""
    def __init__(self, items=None):
        self.items = items if items is not None else []

class WantsToPickupItemComponent(Component):
    """Intent to pick up an item."""
    def __init__(self, item_id):
        self.item_id = item_id

class WantsToOpenComponent(Component):
    """Intent to open a container or door."""
    def __init__(self, target_id):
        self.target_id = target_id

class WantsToAttackComponent(Component):
    """Intent to attack another entity."""
    def __init__(self, target_id):
        self.target_id = target_id

# New components for status effects and abilities

class AbilitiesComponent(Component):
    """Stores a list of ability IDs that an entity possesses."""
    def __init__(self, abilities=None):
        self.abilities = abilities if abilities is not None else []

class StatusEffectsComponent(Component):
    """Stores active status effects on an entity."""
    def __init__(self, effects=None):
        self.effects = effects if effects is not None else []
        # Each effect is a dict with: id, name, duration, type, effects_data, turns_remaining

class StateComponent(Component):
    """Stores state flags and temporary modifiers for an entity."""
    def __init__(self):
        # State flags
        self.dead = False
        self.paralyzed = False
        self.blinded = False
        self.charmed = False
        self.confused = False
        self.deafened = False
        self.fascinated = False
        self.feebleminded = False
        self.petrified = False
        self.slowed = False
        self.stunned = False
        self.unconscious = False
        self.cursed_stat_reduction = False
        self.mummy_rot = False
        self.diseased = False
        self.lethally_poisoned = False
        self.sickened = False
        self.possessed = False
        self.swallowed_whole = False
        
        # Numerical modifiers
        self.energy_drained = 0  # Energy drain levels
        
        # Combat modifiers
        self.thac0_modifier = 0
        self.ac_modifier = 0
        self.damage_modifier = 0
        self.save_penalty = 0

class WantsToApplyStatusComponent(Component):
    """Intent to apply a status effect to an entity."""
    def __init__(self, status_effect_data, source_entity_id=None):
        self.status_effect_data = status_effect_data
        self.source_entity_id = source_entity_id

class WantsToTriggerAbilityComponent(Component):
    """Intent to trigger an ability."""
    def __init__(self, ability_id, target_id=None, trigger_type="on_attack"):
        self.ability_id = ability_id
        self.target_id = target_id
        self.trigger_type = trigger_type

class WantsToMakeSavingThrowComponent(Component):
    """Intent for an entity to make a saving throw against an effect."""
    def __init__(self, save_type, dc, effect_data, source_entity_id):
        self.save_type = save_type
        self.dc = dc
        self.effect_data = effect_data
        self.source_entity_id = source_entity_id

class DeadComponent(Component):
    """A tag component for dead entities, to prevent them from being targeted."""
    pass

class ExperienceComponent(Component):
    """Stores experience and level information for an entity."""
    def __init__(self, current_xp=0, level=1):
        self.current_xp = current_xp
        self.level = level
        self.xp_to_next_level = self.calculate_xp_needed(level + 1)

    def calculate_xp_needed(self, for_level):
        """
        Calculates XP needed for a given level (based on OSE Fighter progression).
        e.g., Level 2: 2,000, Level 3: 4,000, etc.
        """
        if for_level <= 1: return 0
        return 2000 * (2 ** (for_level - 2))

# Phase 1 Addition: New component for ability usage
class WantsToUseAbilityComponent(Component):
    """Intent to use an ability with optional targeting."""
    def __init__(self, ability_id, target_id=None, target_position=None):
        self.ability_id = ability_id
        self.target_id = target_id
        self.target_position = target_position  # For ground-targeted abilities