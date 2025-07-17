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
    def __init__(self, strength, intelligence, wisdom, dexterity, constitution, charisma):
        self.strength = strength
        self.intelligence = intelligence
        self.wisdom = wisdom
        self.dexterity = dexterity
        self.constitution = constitution
        self.charisma = charisma

class CombatComponent(Component):
    """Stores combat-related stats for an entity."""
    def __init__(self, hp, ac, thac0):
        self.hp = hp
        self.ac = ac
        self.thac0 = thac0

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

class ItemComponent(Component):
    """A component for items, defining their material properties."""
    def __init__(self, material):
        self.material = material

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
