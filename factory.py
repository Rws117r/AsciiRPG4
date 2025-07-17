# factory.py
# Contains functions for procedurally generating entities in the game world.

import uuid
import random

def create_locked_container_and_key(game, container_pos, key_pos, container_material="wood", key_material="steel"):
    """
    Creates a container with a unique lock and a matching key, then places them in the world.

    Args:
        game: The main game instance.
        container_pos (tuple): The (x, y) coordinates to place the container.
        key_pos (tuple): The (x, y) coordinates to place the key.
        container_material (str): Material for the container (affects description).
        key_material (str): Material for the key (affects description).
    """
    # 1. Generate a unique ID for the lock and key pair.
    new_key_id = str(uuid.uuid4())

    # 2. Create the locked container
    container_archetype = "Chest"  # Use "Chest" archetype for all chests, regardless of material
    description = f"A sturdy {container_material} chest."  # Dynamic description
    game.create_entity_from_archetype(
        archetype_name=container_archetype,
        component_overrides={
            'PositionComponent': {'x': container_pos[0], 'y': container_pos[1]},
            'LockableComponent': {'is_locked': True, 'key_id': new_key_id},
            'MaterialComponent': {'name': container_material},
            'DescriptionComponent': {'text': description},
            'RenderableComponent': {'char': '=', 'color': game.COLORS["WHITE"]}
        }
    )

    # 4. Create the matching key using base Key archetype
    key_archetype = "Key"
    key_description_text = f"A {key_material} key."

    key_description = {
        "steel": "A small iron key.",
        "brass": "A polished brass key.",
        "silver": "An ornate silver key.",
        "gold": "A gleaming golden key."
    }
    
    game.create_entity_from_archetype(
        archetype_name=key_archetype,
        component_overrides={
            'PositionComponent': {'x': key_pos[0], 'y': key_pos[1]},
            'KeyComponent': {'key_id': new_key_id},
            'MaterialComponent': {'name': key_material},
            'DescriptionComponent': {'text': key_description.get(key_material, key_description_text)},
            'RenderableComponent': {'char': "'", 'color': game.COLORS["YELLOW"] if key_material in ["brass", "gold"] else game.COLORS["WHITE"]}
        }
    )

    print(f"Factory created {container_material} container at {container_pos} with {key_material} key at {key_pos} (key_id: {new_key_id[:8]}...)")


def create_random_locked_containers_with_keys(game, num_pairs=3):
    """
    Creates multiple random locked container and key pairs throughout the map.
    
    Args:
        game: The main game instance.
        num_pairs: Number of container-key pairs to create.
    """
    container_materials = ["wood", "steel"]
    key_materials = ["steel", "brass", "silver", "gold"]
    
    # Define map bounds (adjust based on your map size)
    map_width = 20
    map_height = 15
    
    for i in range(num_pairs):
        # Randomly select materials
        container_material = random.choice(container_materials)
        key_material = random.choice(key_materials)
        
        # Generate random positions (make sure they don't overlap with existing entities)
        container_pos = (random.randint(2, map_width-2), random.randint(2, map_height-2))
        key_pos = (random.randint(2, map_width-2), random.randint(2, map_height-2))
        
        # Make sure positions are different
        while key_pos == container_pos:
            key_pos = (random.randint(2, map_width-2), random.randint(2, map_height-2))
        
        create_locked_container_and_key(game, container_pos, key_pos, container_material, key_material)


def create_locked_door_with_key(game, door_pos, key_pos, door_material="wood", key_material="steel"):
    """
    Creates a locked door with a matching key.
    
    Args:
        game: The main game instance.
        door_pos (tuple): The (x, y) coordinates to place the door.
        key_pos (tuple): The (x, y) coordinates to place the key.
        door_material (str): Material for the door.
        key_material (str): Material for the key.
    """
    # Generate a unique ID for the lock and key pair
    new_key_id = str(uuid.uuid4())
    
    # Create the locked door
    game.create_entity_from_archetype(
        archetype_name="Door",
        component_overrides={
            'PositionComponent': {'x': door_pos[0], 'y': door_pos[1]},
            'LockableComponent': {'is_locked': True, 'key_id': new_key_id},
            'DescriptionComponent': {'text': f"A locked {door_material} door."}, # Assuming description is static for doors
            'RenderableComponent': {'char': '+', 'color': game.COLORS["WHITE"], 'open_char': '-'}
        }
    )
    
    # Create the matching key
    game.create_entity_from_archetype(
        archetype_name="Key",
        component_overrides={
            'PositionComponent': {'x': key_pos[0], 'y': key_pos[1]},
            'KeyComponent': {'key_id': new_key_id},
            'MaterialComponent': {'name': key_material},
            'DescriptionComponent': {'text': f"A {key_material} door key."},
            'RenderableComponent': {'char': "'", 'color': game.COLORS["YELLOW"] if key_material in ["brass", "gold"] else game.COLORS["WHITE"]}
        }
    )
    
    print(f"Factory created locked {door_material} door at {door_pos} with {key_material} key at {key_pos}")