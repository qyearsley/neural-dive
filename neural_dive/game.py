"""
Game logic and state management for Neural Dive.

This module contains the main Game class that manages:
- Game state (player, NPCs, map, floors)
- Player movement and interactions
- Conversation system
- Floor progression
- Knowledge and quest systems
"""

from __future__ import annotations

from pathlib import Path
import random
import time
from typing import TYPE_CHECKING

from neural_dive.answer_matching import match_answer
from neural_dive.config import (
    DEFAULT_MAP_HEIGHT,
    DEFAULT_MAP_WIDTH,
    MAX_FLOORS,
    NPC_PLACEMENT_ATTEMPTS,
    QUEST_COMPLETION_COHERENCE_BONUS,
    QUEST_TARGET_NPCS,
    STAIRS_DOWN_DEFAULT_X,
    STAIRS_DOWN_DEFAULT_Y,
    STAIRS_UP_DEFAULT_X,
    STAIRS_UP_DEFAULT_Y,
)
from neural_dive.data.levels import ZONE_TERMINALS
from neural_dive.difficulty import DifficultyLevel, DifficultySettings
from neural_dive.entities import Entity, InfoTerminal, Stairs
from neural_dive.enums import NPCType
from neural_dive.models import Answer, Conversation, Question
from neural_dive.question_types import QuestionType

if TYPE_CHECKING:
    from neural_dive.managers.conversation_engine import ConversationEngine
    from neural_dive.managers.floor_manager import FloorManager
    from neural_dive.managers.npc_manager import NPCManager
    from neural_dive.managers.player_manager import PlayerManager


class Game:
    """
    Main game state and logic manager.

    Handles all game state including player position, NPCs, conversations,
    floor progression, and game mechanics like knowledge modules and quests.
    """

    def __init__(
        self,
        map_width: int = DEFAULT_MAP_WIDTH,
        map_height: int = DEFAULT_MAP_HEIGHT,
        random_npcs: bool = True,
        seed: int | None = None,
        max_floors: int = MAX_FLOORS,
        difficulty: DifficultyLevel = DifficultyLevel.NORMAL,
        content_set: str | None = None,
    ):
        """Initialize a new game.

        Args:
            map_width: Width of the game map in tiles
            map_height: Height of the game map in tiles
            random_npcs: Whether to randomize NPC and entity positions
            seed: Random seed for reproducibility (None for random)
            max_floors: Maximum number of floors/layers in the game
            difficulty: Difficulty level determining game balance
            content_set: Content set to use (None for default)
        """
        from neural_dive.game_builder import GameInitializer

        # Set up difficulty settings
        self.difficulty: DifficultyLevel
        self.difficulty_settings: DifficultySettings
        self.difficulty, self.difficulty_settings = GameInitializer.setup_difficulty(difficulty)

        # Set up randomization
        self.rand: random.Random
        self.seed: int | None
        self.rand, self.seed = GameInitializer.setup_randomization(seed)

        # Game dimensions and settings
        self.random_npcs = random_npcs

        # Load all game data
        (
            self.content_set,
            self.questions,
            self.npc_data,
            self.level_data,
            self.snippets,
        ) = GameInitializer.load_content(content_set)

        # Compute floor requirements based on loaded NPCs
        from neural_dive.data_loader import compute_floor_requirements

        floor_requirements = compute_floor_requirements(self.npc_data)

        # Initialize Floor Manager
        self.floor_manager: FloorManager = GameInitializer.create_floor_manager(
            max_floors, map_width, map_height, seed, self.level_data, floor_requirements
        )

        # Get map and dimensions from floor manager
        self.game_map = self.floor_manager.game_map
        self.map_width = self.floor_manager.map_width
        self.map_height = self.floor_manager.map_height

        # Create player entity
        self.player, self.old_player_pos = GameInitializer.create_player(self.level_data)

        # Initialize entity lists
        self.stairs, self.terminals, self.item_pickups = GameInitializer.initialize_entities()

        # Initialize NPC Manager
        self.npc_manager: NPCManager = GameInitializer.create_npc_manager(
            self.npc_data,
            self.questions,
            self.rand,
            self.difficulty_settings,
            seed,
            self.level_data,
        )

        # Initialize Conversation Engine
        self.conversation_engine: ConversationEngine = GameInitializer.create_conversation_engine()

        # Initialize Player Manager
        self.player_manager: PlayerManager = GameInitializer.create_player_manager(
            self.difficulty_settings
        )

        # Initialize statistics
        (
            self.start_time,
            self.questions_answered,
            self.questions_correct,
            self.questions_wrong,
            self.npcs_completed,
            self.game_won,
        ) = GameInitializer.initialize_stats()

        # Quest system
        self.quest_active = False

        # UI message
        self.message = GameInitializer.create_welcome_message(max_floors)

        # Generate the first floor entities
        self._generate_floor()

    def _localize(self, en_text: str, zh_text: str | None = None) -> str:
        """
        Return localized text based on content set.

        Args:
            en_text: English text (default)
            zh_text: Chinese text (optional)

        Returns:
            Localized text based on current content set
        """
        if self.content_set == "chinese-hsk6" and zh_text:
            return zh_text
        return en_text

    # Backward compatibility properties for FloorManager
    @property
    def current_floor(self) -> int:
        """Get current floor from FloorManager."""
        return self.floor_manager.current_floor

    @current_floor.setter
    def current_floor(self, value: int):
        """Set current floor on FloorManager."""
        self.floor_manager.current_floor = value

    @property
    def max_floors(self) -> int:
        """Get max floors from FloorManager."""
        return self.floor_manager.max_floors

    # Backward compatibility properties for PlayerManager
    @property
    def coherence(self) -> int:
        """Get current coherence from PlayerManager."""
        return self.player_manager.coherence

    @coherence.setter
    def coherence(self, value: int) -> None:
        """Set coherence directly on PlayerManager."""
        self.player_manager.coherence = value

    @property
    def max_coherence(self) -> int:
        """Get max coherence from PlayerManager."""
        return self.player_manager.max_coherence

    @max_coherence.setter
    def max_coherence(self, value: int) -> None:
        """Set max coherence on PlayerManager."""
        self.player_manager.max_coherence = value

    @property
    def knowledge_modules(self) -> set[str]:
        """Get knowledge modules from PlayerManager."""
        return self.player_manager.knowledge_modules

    @knowledge_modules.setter
    def knowledge_modules(self, value: set[str]) -> None:
        """Set knowledge modules on PlayerManager."""
        self.player_manager.knowledge_modules = value

    # Backward compatibility properties for NPCManager
    @property
    def npcs(self) -> list[Entity]:
        """Get current floor NPCs from NPCManager."""
        return self.npc_manager.npcs

    @property
    def all_npcs(self) -> list[Entity]:
        """Get all NPCs from NPCManager."""
        return self.npc_manager.all_npcs

    @property
    def npc_conversations(self) -> dict[str, Conversation]:
        """Get NPC conversations from NPCManager."""
        return self.npc_manager.conversations

    @property
    def npc_opinions(self) -> dict[str, int]:
        """Get NPC opinions from NPCManager."""
        return self.npc_manager.npc_opinions

    @property
    def quest_completed_npcs(self) -> set[str]:
        """Get quest completed NPCs from NPCManager."""
        return self.npc_manager.quest_completed_npcs

    @property
    def old_npc_positions(self) -> dict[str, tuple[int, int]]:
        """Get old NPC positions from NPCManager."""
        return self.npc_manager.old_positions

    # Backward compatibility properties for ConversationEngine
    @property
    def active_conversation(self):
        """Get active conversation from ConversationEngine."""
        return self.conversation_engine.active_conversation

    @active_conversation.setter
    def active_conversation(self, value):
        """Set active conversation on ConversationEngine."""
        self.conversation_engine.active_conversation = value

    @property
    def active_terminal(self):
        """Get active terminal from ConversationEngine."""
        return self.conversation_engine.active_terminal

    @active_terminal.setter
    def active_terminal(self, value):
        """Set active terminal on ConversationEngine."""
        self.conversation_engine.active_terminal = value

    @property
    def active_inventory(self) -> bool:
        """Get active inventory state from ConversationEngine."""
        return self.conversation_engine.active_inventory

    @active_inventory.setter
    def active_inventory(self, value: bool):
        """Set active inventory state on ConversationEngine."""
        self.conversation_engine.active_inventory = value

    @property
    def active_snippet(self) -> dict | None:
        """Get active snippet from ConversationEngine."""
        return self.conversation_engine.active_snippet

    @active_snippet.setter
    def active_snippet(self, value: dict | None):
        """Set active snippet on ConversationEngine."""
        self.conversation_engine.active_snippet = value

    @property
    def show_greeting(self) -> bool:
        """Get show greeting from ConversationEngine."""
        return self.conversation_engine.show_greeting

    @show_greeting.setter
    def show_greeting(self, value: bool):
        """Set show greeting on ConversationEngine."""
        self.conversation_engine.show_greeting = value

    @show_greeting.deleter
    def show_greeting(self):
        """Delete show greeting from ConversationEngine."""
        self.conversation_engine.show_greeting = False

    @property
    def last_answer_response(self) -> str | None:
        """Get last answer response from ConversationEngine."""
        return self.conversation_engine.last_answer_response

    @last_answer_response.setter
    def last_answer_response(self, value: str | None):
        """Set last answer response on ConversationEngine."""
        self.conversation_engine.last_answer_response = value

    @last_answer_response.deleter
    def last_answer_response(self):
        """Delete last answer response from ConversationEngine."""
        self.conversation_engine.last_answer_response = None

    @property
    def text_input_buffer(self) -> str:
        """Get text input buffer from ConversationEngine."""
        return self.conversation_engine.text_input_buffer

    @text_input_buffer.setter
    def text_input_buffer(self, value: str):
        """Set text input buffer on ConversationEngine."""
        self.conversation_engine.text_input_buffer = value

    @property
    def eliminated_answers(self) -> set[int]:
        """Get eliminated answers from ConversationEngine."""
        return self.conversation_engine.eliminated_answers

    def _generate_floor(self):
        """Generate all entities (NPCs, terminals, stairs, items) for the current floor.

        This method is called when entering a new floor or starting the game.
        It clears existing floor entities and creates new ones based on the current floor.
        Note: Map generation is handled by FloorManager.
        """
        # Get updated map dimensions from floor manager
        self.game_map = self.floor_manager.game_map
        self.map_width = self.floor_manager.map_width
        self.map_height = self.floor_manager.map_height

        # Clear current floor entities (non-NPC)
        self.stairs = []
        self.terminals = []
        self.item_pickups = []

        # Clear old position tracking when changing floors
        self.npc_manager.old_positions.clear()
        self.old_player_pos = None  # Clear player's old position to prevent stale rendering

        # Generate NPCs for this floor using NPCManager
        self.npc_manager.generate_npcs_for_floor(
            floor=self.current_floor,
            game_map=self.game_map,
            player_pos=(self.player.x, self.player.y),
            random_placement=self.random_npcs,
            map_width=self.map_width,
            map_height=self.map_height,
        )

        # Generate terminals for this floor
        self._generate_terminals()

        # Generate stairs
        self._generate_stairs()

        # Generate items
        self._generate_items()

    def _generate_terminals(self):
        """Generate and place info terminals for the current floor."""
        level_data = self.level_data.get(self.current_floor)

        if not level_data or "terminal_positions" not in level_data:
            # No terminals defined for this floor
            return

        terminal_positions = level_data["terminal_positions"]
        zone_terminals = ZONE_TERMINALS.get(self.current_floor, {})

        # Create zone terminals based on labels in the level
        for _zone_name, zone_data in zone_terminals.items():
            if terminal_positions:
                # Use next available terminal position
                x, y = terminal_positions.pop(0)
                terminal = InfoTerminal(x, y, zone_data["title"], zone_data["content"])  # type: ignore[arg-type]
                self.terminals.append(terminal)

    def _generate_stairs(self):
        """Generate stairs up and/or down based on current floor."""
        # Get level data for stair positions
        level_data = self.level_data.get(self.current_floor)

        if level_data:
            # Use stairs from level layout
            stairs_down_position = level_data.get("stairs_down")
            stairs_up_position = level_data.get("stairs_up")

            # Add stairs down
            if self.current_floor < self.max_floors and stairs_down_position:
                self._add_stairs_from_positions(stairs_down_position, "down")

            # Add stairs up
            if self.current_floor > 1 and stairs_up_position:
                self._add_stairs_from_positions(stairs_up_position, "up")
        else:
            # Fallback to placement strategy
            from neural_dive.placement import EntityPlacementStrategy

            strategy = EntityPlacementStrategy(
                game_map=self.game_map,
                random_mode=self.random_npcs,
                rng=self.rand,
                map_width=self.map_width,
                map_height=self.map_height,
            )

            # Stairs down (if not on bottom floor)
            if self.current_floor < self.max_floors:
                down_positions = strategy.place_entities(
                    level_positions=None,
                    default_positions=[(STAIRS_DOWN_DEFAULT_X, STAIRS_DOWN_DEFAULT_Y)],
                    num_attempts=NPC_PLACEMENT_ATTEMPTS,
                    x_range=(self.map_width // 2, self.map_width - 2),
                    y_range=(self.map_height // 2, self.map_height - 2),
                    count=1,
                    validation_fn=lambda x, y: abs(x - self.player.x) > 10,
                )
                if down_positions:
                    x, y = down_positions[0]
                    self.stairs.append(Stairs(x, y, "down"))

            # Stairs up (if not on top floor)
            if self.current_floor > 1:
                up_positions = strategy.place_entities(
                    level_positions=None,
                    default_positions=[(STAIRS_UP_DEFAULT_X, STAIRS_UP_DEFAULT_Y)],
                    num_attempts=NPC_PLACEMENT_ATTEMPTS,
                    x_range=(2, self.map_width // 3),
                    y_range=(2, self.map_height // 3),
                    count=1,
                )
                if up_positions:
                    x, y = up_positions[0]
                    self.stairs.append(Stairs(x, y, "up"))

    def _add_stairs_from_positions(self, position_data, direction: str):
        """Add stairs from position data (may be tuple or list of tuples).

        Args:
            position_data: Either a single (x, y) tuple or list of (x, y) tuples
            direction: "up" or "down"
        """
        if isinstance(position_data, tuple):
            # Single position
            x, y = position_data
            self.stairs.append(Stairs(x, y, direction))
        else:
            # List of positions
            for x, y in position_data:
                self.stairs.append(Stairs(x, y, direction))

    def _generate_items(self):
        """Generate and place item pickups for the current floor."""
        from neural_dive.items import CodeSnippet, HintToken, ItemPickup
        from neural_dive.placement import EntityPlacementStrategy

        strategy = EntityPlacementStrategy(
            game_map=self.game_map,
            random_mode=self.random_npcs,
            rng=self.rand,
            map_width=self.map_width,
            map_height=self.map_height,
        )

        # Number of items per floor (increases with floor difficulty)
        num_hint_tokens = 1 + (self.current_floor // 2)  # 1 on floor 1, 2 on floors 2-3
        num_snippets = 1 if self.current_floor >= 2 else 0  # 1 snippet starting on floor 2

        # Place hint tokens
        hint_positions = strategy.place_entities(
            level_positions=None,
            default_positions=[],
            num_attempts=50,
            x_range=(3, self.map_width - 3),
            y_range=(3, self.map_height - 3),
            count=num_hint_tokens,
            validation_fn=lambda x, y: abs(x - self.player.x) + abs(y - self.player.y) > 8,
        )

        for x, y in hint_positions:
            hint_item = HintToken()
            pickup = ItemPickup(x, y, hint_item)
            self.item_pickups.append(pickup)

        # Place code snippets
        if num_snippets > 0 and self.snippets:
            snippet_positions = strategy.place_entities(
                level_positions=None,
                default_positions=[],
                num_attempts=50,
                x_range=(3, self.map_width - 3),
                y_range=(3, self.map_height - 3),
                count=num_snippets,
                validation_fn=lambda x, y: abs(x - self.player.x) + abs(y - self.player.y) > 8,
            )

            # Pick random snippets from available ones
            available_snippet_ids = list(self.snippets.keys())
            for x, y in snippet_positions:
                if available_snippet_ids:
                    snippet_id = self.rand.choice(available_snippet_ids)
                    snippet_data = self.snippets[snippet_id]
                    snippet_item = CodeSnippet(
                        name=snippet_data["name"],
                        topic=snippet_data["topic"],
                        content=snippet_data["content"],
                    )
                    pickup = ItemPickup(x, y, snippet_item)
                    self.item_pickups.append(pickup)

    def update_npc_wandering(self):
        """
        Update NPC wandering AI.

        Delegates to NPCManager for all NPC movement logic.
        """
        self.npc_manager.update_wandering(
            game_map=self.game_map,
            player_pos=(self.player.x, self.player.y),
            is_conversation_active=self.active_conversation is not None,
        )

    def is_walkable(self, x: int, y: int) -> bool:
        """
        Check if a position is walkable.

        Args:
            x: X coordinate
            y: Y coordinate

        Returns:
            True if the position can be walked on, False otherwise
        """
        # Check bounds
        if y < 0 or y >= len(self.game_map):
            return False
        if x < 0 or x >= len(self.game_map[0]):
            return False

        # Check for walls
        return bool(self.game_map[y][x] != "#")

    def move_player(self, dx: int, dy: int) -> bool:
        """
        Attempt to move the player by a delta.

        Args:
            dx: Change in x position
            dy: Change in y position

        Returns:
            True if movement was successful, False otherwise
        """
        # Can't move during conversation
        if self.active_conversation:
            self.message = "You're in a conversation. Answer or press ESC to exit."
            return False

        new_x = self.player.x + dx
        new_y = self.player.y + dy

        # Try to move
        if self.is_walkable(new_x, new_y):
            self.old_player_pos = (self.player.x, self.player.y)
            self.player.x = new_x
            self.player.y = new_y

            # Check for item pickups
            for pickup in self.item_pickups[:]:  # Use slice to allow removal during iteration
                if self.player.x == pickup.x and self.player.y == pickup.y:
                    # Try to add to inventory
                    if self.player_manager.add_item(pickup.item):
                        self.item_pickups.remove(pickup)
                        self.message = f"Picked up {pickup.item.name}!"
                        return True
                    else:
                        self.message = "Inventory full!"
                        return True

            # Check if standing on stairs and show hint
            for stair in self.stairs:
                if self.player.x == stair.x and self.player.y == stair.y:
                    direction = "up" if stair.direction == "up" else "down"
                    self.message = f"Standing on stairs {direction}. Press Space or >/< to use."
                    return True

            self.message = ""
            return True
        else:
            self.message = self._localize("Blocked by firewall!", "被防火墙阻挡！")
            return False

    def interact(self) -> bool:
        """
        Attempt to interact with nearby entity (terminal, NPC, or stairs).
        Prioritizes closest entity. For equal distances: NPC > Terminal > Stairs.

        Returns:
            True if interaction was successful, False otherwise
        """
        player_x, player_y = self.player.x, self.player.y

        # Find all interactable entities with distances
        candidates = []

        # Check terminals
        for terminal in self.terminals:
            dist = max(abs(player_x - terminal.x), abs(player_y - terminal.y))
            if dist <= 1:
                candidates.append(("terminal", dist, terminal))

        # Check NPCs
        for npc in self.npcs:
            dist = max(abs(player_x - npc.x), abs(player_y - npc.y))
            if dist <= 1:
                candidates.append(("npc", dist, npc))  # type: ignore[arg-type]

        # Check stairs
        for stair in self.stairs:
            dist = max(abs(player_x - stair.x), abs(player_y - stair.y))
            if dist <= 1:
                candidates.append(("stairs", dist, stair))  # type: ignore[arg-type]

        if not candidates:
            self.message = "No one nearby to interact with. Look for NPCs or Terminals (▣)."
            return False

        # Sort by: distance first, then priority (npc=0, terminal=1, stairs=2)
        priority_map = {"npc": 0, "terminal": 1, "stairs": 2}
        candidates.sort(key=lambda x: (x[1], priority_map[x[0]]))

        # Interact with closest/highest priority entity
        entity_type, dist, entity = candidates[0]

        if entity_type == "terminal":
            self.active_terminal = entity
            self.message = f"Reading: {entity.title}"
            return True
        elif entity_type == "npc":
            return self._interact_with_npc(entity)  # type: ignore
        elif entity_type == "stairs":
            return self.use_stairs()

        return False

    def _interact_with_npc(self, npc: Entity) -> bool:
        """
        Handle interaction with a specific NPC.

        Args:
            npc: The NPC entity to interact with

        Returns:
            True if interaction occurred, False otherwise
        """
        npc_name = npc.name
        conversation = self.npc_conversations.get(npc_name)

        if not conversation:
            self.message = f"{npc_name}: I have nothing to say."
            return False

        # Handle helper NPCs (restore coherence)
        if conversation.npc_type == NPCType.HELPER and not conversation.completed:
            restore_amount = self.difficulty_settings.helper_restore_amount
            gained = self.player_manager.gain_coherence(restore_amount)
            conversation.completed = True
            self.message = (
                f"{npc_name}: Your coherence has been restored by {gained}. "
                f"[+{restore_amount} Coherence]"
            )
            return True

        # Handle quest NPCs
        if conversation.npc_type == NPCType.QUEST:
            return self._handle_quest_npc(npc_name, conversation)

        # Standard interaction for specialists and enemies
        if not conversation.completed:
            self.active_conversation = conversation
            self.message = conversation.greeting
            return True
        else:
            self.message = f"{npc_name}: {self._localize('You have proven yourself. We have nothing more to discuss.', '你已经证明了自己。我们没有更多可讨论的了。')}"
            return True

    def _handle_quest_npc(self, npc_name: str, conversation: Conversation) -> bool:
        """
        Handle interaction with a quest-giving NPC.

        Args:
            npc_name: Name of the quest NPC
            conversation: The NPC's conversation

        Returns:
            True if interaction occurred
        """
        if not conversation.completed:
            # Quest NPCs just give info, don't have conversations
            self.quest_active = True
            self.message = conversation.greeting
            # Mark as "completed" since quest NPCs don't have actual questions
            conversation.completed = True
            return True
        else:
            # Check quest completion
            if QUEST_TARGET_NPCS.issubset(self.quest_completed_npcs):
                self.message = (
                    f"{npc_name}: You have completed my quest! "
                    f"The knowledge is yours. [Quest Complete! "
                    f"+{QUEST_COMPLETION_COHERENCE_BONUS} Coherence]"
                )
                self.player_manager.gain_coherence(QUEST_COMPLETION_COHERENCE_BONUS)
            else:
                remaining = QUEST_TARGET_NPCS - self.quest_completed_npcs
                self.message = f"{npc_name}: Seek these guardians still: {', '.join(remaining)}"
            return True

    def is_floor_complete(self) -> bool:
        """
        Check if the current floor's objectives are complete.

        Delegates to FloorManager for floor completion logic.

        Returns:
            True if all required NPCs have been talked to, False otherwise
        """
        return self.floor_manager.is_floor_complete(self.npcs_completed, self.npc_data)

    def use_stairs(self) -> bool:
        """
        Attempt to use stairs at the player's current position.

        Returns:
            True if stairs were used successfully, False otherwise
        """
        # Check if player is standing on stairs
        for stair in self.stairs:
            if self.player.x == stair.x and self.player.y == stair.y:
                if stair.direction == "down":
                    return self._descend_stairs()
                elif stair.direction == "up":
                    return self._ascend_stairs()

        self.message = "No stairs here. Stand on stairs (> or <) and press Enter."
        return False

    def _descend_stairs(self) -> bool:
        """
        Descend to the next floor.

        Returns:
            True if descent was successful, False otherwise
        """
        if not self.floor_manager.can_use_stairs_down():
            self.message = "No deeper layers exist."
            return False

        # Check if floor objectives are complete
        if not self.is_floor_complete():
            required = self.floor_manager.floor_requirements.get(self.current_floor, set())
            incomplete = [npc for npc in required if npc not in self.npcs_completed]
            self.message = f"Cannot descend! Complete conversations with: {', '.join(incomplete)}"
            return False

        # Descend using floor manager (generates new floor map and updates position)
        self.floor_manager.move_to_next_floor(self.player)

        # Regenerate entities for the new floor (also updates map references)
        self._generate_floor()
        self.message = f"Descended to Neural Layer {self.current_floor}"
        return True

    def _ascend_stairs(self) -> bool:
        """
        Ascend to the previous floor.

        Returns:
            True if ascent was successful, False otherwise
        """
        if not self.floor_manager.can_use_stairs_up():
            self.message = "This is the top layer."
            return False

        # Ascend using floor manager (generates new floor map and updates position)
        self.floor_manager.move_to_previous_floor(self.player)

        # Regenerate entities for the new floor (also updates map references)
        self._generate_floor()
        self.message = f"Ascended to Neural Layer {self.current_floor}"
        return True

    def use_hint(self) -> tuple[bool, str]:
        """Use a hint token to eliminate wrong answers in the current question.

        Returns:
            Tuple of (success, message)
        """
        from neural_dive.items import ItemType

        # Check if we have hint tokens
        if not self.player_manager.has_item_type(ItemType.HINT_TOKEN):
            return False, "No hint tokens available"

        # Check if in a conversation
        if not self.active_conversation:
            return False, "Not in a conversation"

        # Try to use the hint
        success, message = self.conversation_engine.use_hint_token()

        if success:
            # Remove one hint token from inventory
            hint_tokens = self.player_manager.get_items_by_type(ItemType.HINT_TOKEN)
            if hint_tokens:
                self.player_manager.remove_item(hint_tokens[0])
                return True, message

        return False, message

    def view_snippet(self) -> tuple[bool, str]:
        """View a code snippet during a conversation.

        Returns:
            Tuple of (success, message)
        """
        from neural_dive.items import ItemType

        # Check if we have code snippets
        snippets = self.player_manager.get_items_by_type(ItemType.CODE_SNIPPET)
        if not snippets:
            return False, "No code snippets available"

        # Check if in a conversation
        if not self.active_conversation:
            return False, "Not in a conversation"

        # For now, show the first snippet
        # TODO: Could add a menu to choose between multiple snippets
        snippet_item = snippets[0]

        # Find the snippet data
        # CodeSnippet items have a topic attribute we can use to find the full data
        if hasattr(snippet_item, "topic"):
            # Find matching snippet in snippets data
            for _snippet_id, snippet_data in self.snippets.items():
                if snippet_data.get("topic") == snippet_item.topic:
                    self.active_snippet = snippet_data
                    return True, "Viewing snippet"

        return False, "Snippet not found"

    def _validate_conversation_state(
        self,
    ) -> tuple[bool, str, Conversation | None, Question | None, bool]:
        """Validate conversation state and return common data needed for answering.

        Returns:
            Tuple of (valid, error_message, conversation, question, is_enemy)
            If valid is False, error_message contains the reason.
        """
        if not self.active_conversation:
            return False, "Not in a conversation.", None, None, False

        conv = self.active_conversation

        # Check if conversation is already complete
        if conv.current_question_idx >= len(conv.questions):
            conv.completed = True
            self.active_conversation = None
            return False, "Conversation completed!", None, None, False

        # Get current question
        question = conv.questions[conv.current_question_idx]

        # Check if this is an enemy (harsher penalties)
        is_enemy = conv.npc_type == NPCType.ENEMY

        return True, "", conv, question, is_enemy

    def answer_question(self, answer_index: int) -> tuple[bool, str]:
        """Answer the current conversation question.

        Args:
            answer_index: Index of the selected answer (0-based)

        Returns:
            Tuple of (correct, response_message)
        """
        valid, error_msg, conv, question, is_enemy = self._validate_conversation_state()
        if not valid:
            # Return True for "Conversation completed!" as it's not an error
            return "completed" in error_msg, error_msg

        assert conv is not None and question is not None  # Type narrowing

        # Validate answer index
        if answer_index < 0 or answer_index >= len(question.answers):
            return False, "Invalid answer choice."

        answer = question.answers[answer_index]

        # Track NPC opinion
        npc_name = conv.npc_name
        if npc_name not in self.npc_opinions:
            self.npc_opinions[npc_name] = 0

        if answer.correct:
            return self._handle_correct_answer(conv, answer, npc_name, is_enemy)
        else:
            return self._handle_wrong_answer(conv, answer, npc_name, is_enemy)

    def answer_text_question(self, user_answer: str) -> tuple[bool, str]:
        """Answer the current conversation question with typed text.

        For SHORT_ANSWER and YES_NO question types.

        Args:
            user_answer: The text answer provided by the user

        Returns:
            Tuple of (correct, response_message)
        """
        valid, error_msg, conv, question, is_enemy = self._validate_conversation_state()
        if not valid:
            # Return True for "Conversation completed!" as it's not an error
            return "completed" in error_msg, error_msg

        assert conv is not None and question is not None  # Type narrowing

        # Verify this is a text-based question type
        if question.question_type == QuestionType.MULTIPLE_CHOICE:
            return False, "This is a multiple choice question. Use number keys 1-4."

        # Check if answer is correct using answer matching
        is_correct = match_answer(
            user_answer,
            question.correct_answer or "",
            match_type=question.match_type,
            case_sensitive=question.case_sensitive,
        )

        # Track NPC opinion
        npc_name = conv.npc_name
        if npc_name not in self.npc_opinions:
            self.npc_opinions[npc_name] = 0

        if is_correct:
            # Create a temporary Answer object for correct response
            temp_answer = Answer(
                text=user_answer,
                correct=True,
                response=question.correct_response or "Correct!",
                reward_knowledge=question.reward_knowledge,
            )
            return self._handle_correct_answer(conv, temp_answer, npc_name, is_enemy)
        else:
            # Create a temporary Answer object for wrong response
            temp_answer = Answer(
                text=user_answer,
                correct=False,
                response=question.incorrect_response or "Not quite.",
                enemy_penalty=self.difficulty_settings.enemy_wrong_answer_penalty,
            )
            return self._handle_wrong_answer(conv, temp_answer, npc_name, is_enemy)

    def _handle_correct_answer(
        self, conv: Conversation, answer: Answer, npc_name: str, is_enemy: bool
    ) -> tuple[bool, str]:
        """
        Handle a correct answer.

        Args:
            conv: The conversation
            answer: The correct answer
            npc_name: Name of the NPC
            is_enemy: Whether the NPC is an enemy

        Returns:
            Tuple of (True, response_message)
        """
        # Update stats
        coherence_gain = self.difficulty_settings.correct_answer_gain
        self.player_manager.gain_coherence(coherence_gain)
        self.npc_opinions[npc_name] += 1

        # Track score
        self.questions_answered += 1
        self.questions_correct += 1

        # Build response
        response = answer.response

        # Award knowledge module
        if answer.reward_knowledge:
            was_new = self.player_manager.add_knowledge(answer.reward_knowledge)
            if was_new:
                response += (
                    f"\n\n[+{coherence_gain} Coherence]\n[Gained: {answer.reward_knowledge}]"
                )
            else:
                response += f"\n\n[+{coherence_gain} Coherence]"
        else:
            response += f"\n\n[+{coherence_gain} Coherence]"

        # Move to next question
        conv.current_question_idx += 1

        # Check if conversation is complete
        if conv.current_question_idx >= len(conv.questions):
            conv.completed = True

            # Track completion
            self.npcs_completed.add(npc_name)

            # Give item rewards based on NPC type
            response = self._give_npc_rewards(conv.npc_type, response)

            # Check for victory condition on final floor
            if self.floor_manager.is_final_floor():
                # Victory bosses - defeating any of these wins the game
                victory_bosses = {"FINAL_BOSS", "RESILIENCE_BOSS", "ML_BOSS", "THEORY_BOSS"}
                if npc_name in victory_bosses:
                    self.game_won = True

            # Track quest completion for specialists
            if conv.npc_type == NPCType.SPECIALIST:
                self.quest_completed_npcs.add(npc_name)

            self.active_conversation = None

            # Add completion message
            response += f"\n\n{npc_name}: You have proven your worth. I grant you passage."

        return True, response

    def _give_npc_rewards(self, npc_type: NPCType, response: str) -> str:
        """Give item rewards when completing NPC conversations.

        Args:
            npc_type: Type of NPC being completed
            response: Current response message

        Returns:
            Updated response message with reward information
        """
        from neural_dive.items import HintToken

        # Helper NPCs give hint tokens
        if npc_type == NPCType.HELPER:
            hint = HintToken()
            if self.player_manager.add_item(hint):
                response += "\n\n[Received: Hint Token]"
        # Specialists give snippets (if available and inventory not full)
        elif npc_type == NPCType.SPECIALIST and self.snippets:
            from neural_dive.items import CodeSnippet

            # Pick a random snippet
            snippet_id = self.rand.choice(list(self.snippets.keys()))
            snippet_data = self.snippets[snippet_id]
            snippet = CodeSnippet(
                name=snippet_data["name"],
                topic=snippet_data["topic"],
                content=snippet_data["content"],
            )
            if self.player_manager.add_item(snippet):
                response += f"\n\n[Received: {snippet.name}]"

        return response

    def get_current_score(self) -> int:
        """
        Calculate the current score based on player progress.

        Returns:
            Current score value
        """
        return (
            (self.questions_correct * 100)  # Points per correct answer
            + (len(self.knowledge_modules) * 50)  # Points per knowledge module
            + (len(self.npcs_completed) * 200)  # Points per NPC completed
            + (self.coherence * 10)  # Bonus for remaining coherence
        )

    def get_final_stats(self) -> dict:
        """
        Get final game statistics for victory/game over screen.

        Returns:
            Dictionary containing all game stats
        """

        time_played = time.time() - self.start_time

        # Calculate accuracy
        accuracy = 0.0
        if self.questions_answered > 0:
            accuracy = (self.questions_correct / self.questions_answered) * 100

        # Calculate score using current score method
        score = self.get_current_score()

        return {
            "time_played": time_played,
            "questions_answered": self.questions_answered,
            "questions_correct": self.questions_correct,
            "questions_wrong": self.questions_wrong,
            "accuracy": accuracy,
            "npcs_completed": len(self.npcs_completed),
            "knowledge_modules": len(self.knowledge_modules),
            "final_coherence": self.coherence,
            "current_floor": self.current_floor,
            "score": int(score),
        }

    def _handle_wrong_answer(
        self, conv: Conversation, answer: Answer, npc_name: str, is_enemy: bool
    ) -> tuple[bool, str]:
        """
        Handle a wrong answer.

        Args:
            conv: The conversation
            answer: The wrong answer
            npc_name: Name of the NPC
            is_enemy: Whether the NPC is an enemy

        Returns:
            Tuple of (False, response_message)
        """
        # Calculate penalty based on difficulty and NPC type
        penalty = (
            self.difficulty_settings.enemy_wrong_answer_penalty
            if is_enemy
            else self.difficulty_settings.wrong_answer_penalty
        )

        # Update stats
        self.player_manager.lose_coherence(penalty)
        self.npc_opinions[npc_name] -= 1

        # Track score
        self.questions_answered += 1
        self.questions_wrong += 1

        # Build response
        if is_enemy:
            response = f"{answer.response}\n\n[CRITICAL ERROR! -{penalty} Coherence]"
        else:
            response = f"{answer.response}\n\n[-{penalty} Coherence]"

        # Check for game over
        if self.coherence <= 0:
            response += "\n\n[SYSTEM FAILURE - COHERENCE LOST]"
            self.active_conversation = None

        return False, response

    def exit_conversation(self) -> bool:
        """
        Exit the current conversation.

        Returns:
            True if a conversation was exited, False otherwise
        """
        if self.active_conversation:
            self.active_conversation = None
            self.message = "Conversation ended."
            return True
        return False

    def process_command(self, command: str) -> tuple[bool, str]:
        """
        Process a text command (primarily for testing).

        Args:
            command: The command string to process

        Returns:
            Tuple of (success, info_message)
        """
        command = command.strip().lower()

        # Handle conversation answers
        if self.active_conversation and command in ["1", "2", "3", "4"]:
            answer_idx = int(command) - 1
            correct, response = self.answer_question(answer_idx)
            return correct, response

        # Handle movement
        if command in ["up", "w"]:
            success = self.move_player(0, -1)
            return success, "moved up" if self.message == "" else self.message
        elif command in ["down", "s"]:
            success = self.move_player(0, 1)
            return success, "moved down" if self.message == "" else self.message
        elif command in ["left", "a"]:
            success = self.move_player(-1, 0)
            return success, "moved left" if self.message == "" else self.message
        elif command in ["right", "d"]:
            success = self.move_player(1, 0)
            return success, "moved right" if self.message == "" else self.message

        # Handle interactions
        elif command in ["interact", "i"]:
            return self.interact(), self.message
        elif command in ["stairs", "use", ">", "<"]:
            return self.use_stairs(), self.message
        elif command in ["exit", "esc"]:
            return self.exit_conversation(), self.message

        return False, f"Unknown command: {command}"

    def get_state(self) -> dict:
        """
        Get current game state for testing/debugging.

        Returns:
            Dictionary containing current game state
        """
        return {
            "player_pos": (self.player.x, self.player.y),
            "npcs": [(npc.x, npc.y, npc.name) for npc in self.npcs],
            "message": self.message,
            "coherence": self.coherence,
            "knowledge_modules": list(self.knowledge_modules),
            "in_conversation": self.active_conversation is not None,
            "conversation_npc": (
                self.active_conversation.npc_name if self.active_conversation else None
            ),
            "current_floor": self.current_floor,
            "quest_active": self.quest_active,
            "quest_completed_npcs": list(self.quest_completed_npcs),
        }

    def save_game(self, filepath: str | Path | None = None) -> tuple[bool, Path | None]:
        """Save the current game state to a file.

        Args:
            filepath: Path to save file. If None, uses default location.

        Returns:
            Tuple of (success, filepath) where success is True if save successful,
            and filepath is the Path where the game was saved (or None on failure)
        """
        from neural_dive.game_serializer import GameSerializer

        return GameSerializer.save(self, filepath)

    @staticmethod
    def load_game(filepath: str | Path | None = None) -> Game | None:
        """Load a saved game from a file.

        Args:
            filepath: Path to save file. If None, uses default location.

        Returns:
            Loaded Game instance, or None if load failed
        """
        from neural_dive.game_serializer import GameSerializer

        return GameSerializer.load(filepath)
