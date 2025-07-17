# factory.py
# Contains functions for procedurally generating entities in the game world.

import uuid
import random

def create_locked_container_and_key(game, container_archetype_name, key_archetype_name, container_pos, key_pos):
    """
    Creates a container with a unique lock and a matching key, then places them in the world.

    Args:
        game: The main game instance.
        container_archetype_name (str): The name of the container archetype (e.g., "Wooden Chest").
        key_archetype_name (str): The name of the key archetype (e.g., "Silver Key").
        container_pos (tuple): The (x, y) coordinates to place the container.
        key_pos (tuple): The (x, y) coordinates to place the key.
    """
    # 1. Generate a unique ID for the lock and key pair.
    # Using UUID ensures that we'll never have a key collision.
    new_key_id = str(uuid.uuid4())

    # 2. Create the locked container.
    # We now call the method on the game object.
    game.create_entity_from_archetype(
        archetype_name=container_archetype_name,
        component_overrides={
            'PositionComponent': {'x': container_pos[0], 'y': container_pos[1]},
            'LockableComponent': {'is_locked': True, 'key_id': new_key_id}
        }
    )

    # 3. Create the matching key.
    # We now call the method on the game object.
    game.create_entity_from_archetype(
        archetype_name=key_archetype_name,
        component_overrides={
            'PositionComponent': {'x': key_pos[0], 'y': key_pos[1]},
            'KeyComponent': {'key_id': new_key_id}
        }
    )

    print(f"Factory created '{container_archetype_name}' at {container_pos} linked to '{key_archetype_name}' at {key_pos} with key_id: {new_key_id}")
