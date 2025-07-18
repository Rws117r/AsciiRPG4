# ai_system.py
# AI behavior system for non-player entities

import random
from components import *
from core_systems import System

class AISystem(System):
    """Controls the actions of non-player entities."""
    
    def update(self, *args, **kwargs):
        game_state = kwargs.get('game_state')
        
        # Only act during monster turn
        if game_state.game_state != 'MONSTER_TURN':
            return
        
        player_entity = self.world.get_entities_with_components(PlayerControllableComponent)
        if not player_entity: 
            return
        
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