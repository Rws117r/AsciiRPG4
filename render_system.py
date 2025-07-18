# render_system.py
# Rendering system for the game

import pygame
from components import *
from core_systems import System

class RenderSystem(System):
    """Handles all rendering logic."""
    def __init__(self, world, screen, font, tile_size):
        super().__init__(world)
        self.screen = screen
        self.font = font
        self.tile_size = tile_size
        self.inventory_width = 300
        self.abilities_width = 400
        self.inventory_slide_amount = 0
        self.abilities_slide_amount = 0
        self.slide_speed = 20

    def update(self, *args, **kwargs):
        game_state = kwargs.get('game_state')
        self.screen.fill((0, 0, 0))

        # Update slide animations
        if game_state and game_state.show_inventory:
            if self.inventory_slide_amount < self.inventory_width:
                self.inventory_slide_amount = min(self.inventory_slide_amount + self.slide_speed, self.inventory_width)
        else:
            if self.inventory_slide_amount > 0:
                self.inventory_slide_amount = max(self.inventory_slide_amount - self.slide_speed, 0)

        if game_state and game_state.show_abilities:
            if self.abilities_slide_amount < self.abilities_width:
                self.abilities_slide_amount = min(self.abilities_slide_amount + self.slide_speed, self.abilities_width)
        else:
            if self.abilities_slide_amount > 0:
                self.abilities_slide_amount = max(self.abilities_slide_amount - self.slide_speed, 0)

        # Draw entities
        entities_to_render = self.world.get_entities_with_components(PositionComponent, RenderableComponent)
        for entity_id in entities_to_render:
            pos = self.world.get_component(entity_id, PositionComponent)
            if pos.x < 0 or pos.y < 0: continue

            if self.world.get_component(entity_id, CursorComponent): continue

            renderable = self.world.get_component(entity_id, RenderableComponent)
            
            # Modify color based on status effects
            color = renderable.color
            state = self.world.get_component(entity_id, StateComponent)
            if state:
                if state.dead:
                    color = renderable.color
                elif state.paralyzed or state.petrified:
                    color = (128, 128, 128)
                elif state.confused:
                    color = (255, 0, 255)
                elif state.lethally_poisoned or state.sickened:
                    color = (0, 255, 0)
            
            text_surface = self.font.render(renderable.char, True, color)
            self.screen.blit(text_surface, (pos.x * self.tile_size, pos.y * self.tile_size))

        # Draw targeting cursor if in targeting mode
        if (game_state and hasattr(game_state, 'targeting_mode') and 
            game_state.targeting_mode):
            self.draw_targeting_cursor(game_state)

        # Draw look cursor and message
        if game_state and game_state.look_mode:
            self.draw_cursor_and_description(game_state)

        # Draw game messages
        if game_state:
            self.draw_messages(game_state)

        # Draw sidebars
        if game_state and self.inventory_slide_amount > 0:
            self.draw_inventory(game_state)
        
        if game_state and self.abilities_slide_amount > 0:
            self.draw_abilities_screen(game_state)
        
        # Draw status information
        if game_state:
            self.draw_status_info(game_state)

    def draw_targeting_cursor(self, game_state):
        """Draw the targeting cursor with range indication."""
        cursor_id = game_state.cursor_id
        if not cursor_id: return
        
        cursor_pos = self.world.get_component(cursor_id, PositionComponent)
        player_entities = self.world.get_entities_with_components(PlayerControllableComponent)
        
        if not player_entities: return
        player_pos = self.world.get_component(player_entities[0], PositionComponent)
        
        # Draw range indicator
        for x in range(max(0, player_pos.x - game_state.targeting_range), 
                      player_pos.x + game_state.targeting_range + 1):
            for y in range(max(0, player_pos.y - game_state.targeting_range), 
                          player_pos.y + game_state.targeting_range + 1):
                distance = max(abs(x - player_pos.x), abs(y - player_pos.y))
                if distance <= game_state.targeting_range:
                    bg_rect = pygame.Rect(x * self.tile_size, y * self.tile_size, 
                                        self.tile_size, self.tile_size)
                    if distance == game_state.targeting_range:
                        pygame.draw.rect(self.screen, (40, 40, 0), bg_rect)  # Range edge
                    else:
                        pygame.draw.rect(self.screen, (20, 20, 0), bg_rect)  # Within range
        
        # Draw targeting cursor
        if (pygame.time.get_ticks() // 200) % 2 == 0:  # Faster flash
            cursor_rect = pygame.Rect(cursor_pos.x * self.tile_size, cursor_pos.y * self.tile_size, 
                                    self.tile_size, self.tile_size)
            pygame.draw.rect(self.screen, (255, 255, 0), cursor_rect, 3)
        
        # Draw targeting instructions
        instructions = [
            f"Targeting: {game_state.targeting_ability_id.replace('_', ' ').title()}",
            "Use arrow keys to move cursor",
            "ENTER/SPACE to confirm, ESC to cancel"
        ]
        y_offset = self.screen.get_height() - 80
        for instruction in instructions:
            inst_surface = self.font.render(instruction, True, (255, 255, 0))
            inst_rect = inst_surface.get_rect(centerx=self.screen.get_width() // 2, y=y_offset)
            self.screen.blit(inst_surface, inst_rect)
            y_offset += 20

    def draw_abilities_screen(self, game_state):
        """Draw the abilities screen showing player's available abilities."""
        # Get player entity
        player_entities = self.world.get_entities_with_components(PlayerControllableComponent)
        if not player_entities: return
        player_id = player_entities[0]
        
        abilities_comp = self.world.get_component(player_id, AbilitiesComponent)
        
        # Position on right side of screen
        abilities_x = self.screen.get_width() - self.abilities_slide_amount
        abilities_rect = pygame.Rect(abilities_x, 0, self.abilities_width, self.screen.get_height())
        
        # Draw background
        bg_surface = pygame.Surface((self.abilities_width, self.screen.get_height()))
        bg_surface.set_alpha(240)
        bg_surface.fill((30, 30, 60))
        self.screen.blit(bg_surface, (abilities_x, 0))
        
        # Draw border
        pygame.draw.rect(self.screen, (100, 100, 150), abilities_rect, 2)
        
        # Draw title
        title_surface = self.font.render("ABILITIES", True, (255, 255, 255))
        title_rect = title_surface.get_rect(centerx=abilities_x + self.abilities_width // 2, y=20)
        self.screen.blit(title_surface, title_rect)
        
        # Draw separator line
        pygame.draw.line(self.screen, (100, 100, 150), 
                        (abilities_x + 10, 50), 
                        (abilities_x + self.abilities_width - 10, 50), 2)
        
        # Draw abilities list
        y_offset = 70
        if not abilities_comp or not abilities_comp.abilities:
            empty_surface = self.font.render("(no abilities)", True, (150, 150, 150))
            empty_rect = empty_surface.get_rect(centerx=abilities_x + self.abilities_width // 2, y=y_offset)
            self.screen.blit(empty_surface, empty_rect)
        else:
            for i, ability_id in enumerate(abilities_comp.abilities):
                if ability_id in self.world.abilities:
                    ability_data = self.world.abilities[ability_id]
                    
                    # Number key
                    num_surface = self.font.render(f"{i+1}.", True, (255, 255, 100))
                    self.screen.blit(num_surface, (abilities_x + 20, y_offset))
                    
                    # Ability name
                    name = ability_data.get("name", ability_id.replace('_', ' ').title())
                    name_surface = self.font.render(name, True, (255, 255, 255))
                    self.screen.blit(name_surface, (abilities_x + 50, y_offset))
                    
                    y_offset += 25
                    
                    # Ability description
                    description = self.format_ability_description(ability_data)
                    desc_lines = self.wrap_text(description, self.abilities_width - 60)
                    
                    for line in desc_lines:
                        desc_surface = self.font.render(line, True, (200, 200, 200))
                        self.screen.blit(desc_surface, (abilities_x + 60, y_offset))
                        y_offset += 20
                    
                    y_offset += 10  # Extra space between abilities
        
        # Draw instructions at bottom
        instructions = [
            "Press number key to use ability",
            "Press 'B' to close"
        ]
        y_offset = self.screen.get_height() - 60
        for instruction in instructions:
            inst_surface = self.font.render(instruction, True, (200, 200, 200))
            inst_rect = inst_surface.get_rect(centerx=abilities_x + self.abilities_width // 2, y=y_offset)
            self.screen.blit(inst_surface, inst_rect)
            y_offset += 25

    def format_ability_description(self, ability_data):
        """Format an ability's data into a readable description."""
        # Use provided description if available
        if "description" in ability_data:
            return ability_data["description"]
        
        # Otherwise, generate description from data
        effect_type = ability_data.get("effect", "unknown")
        chance = ability_data.get("chance", 1.0)
        status_effect = ability_data.get("status_effect", {})
        
        description_parts = []
        
        # Add chance if not 100%
        if chance < 1.0:
            description_parts.append(f"{int(chance * 100)}% chance to")
        
        # Describe the effect
        if effect_type == "apply_status":
            effect_name = status_effect.get("id", "unknown effect")
            effect_name = effect_name.replace('_', ' ')
            description_parts.append(f"apply {effect_name}")
            
            # Add duration if temporary
            if status_effect.get("type") == "temporary":
                duration = status_effect.get("duration", "1")
                description_parts.append(f"for {duration} turns")
        
        elif effect_type == "apply_status_aoe":
            effect_name = status_effect.get("id", "unknown effect")
            effect_name = effect_name.replace('_', ' ')
            description_parts.append(f"apply {effect_name} to area")
            
            if status_effect.get("type") == "temporary":
                duration = status_effect.get("duration", "1")
                description_parts.append(f"for {duration} turns")
        
        return " ".join(description_parts)

    def wrap_text(self, text, max_width):
        """Wrap text to fit within a given pixel width."""
        words = text.split(' ')
        lines = []
        current_line = []
        
        for word in words:
            test_line = ' '.join(current_line + [word])
            test_surface = self.font.render(test_line, True, (255, 255, 255))
            
            if test_surface.get_width() <= max_width:
                current_line.append(word)
            else:
                if current_line:
                    lines.append(' '.join(current_line))
                    current_line = [word]
                else:
                    lines.append(word)  # Word is too long, add it anyway
        
        if current_line:
            lines.append(' '.join(current_line))
        
        return lines

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