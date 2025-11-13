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

import json
from pathlib import Path
import random
import time

from neural_dive.answer_matching import match_answer
from neural_dive.config import (
    DEFAULT_MAP_HEIGHT,
    DEFAULT_MAP_WIDTH,
    FLOOR_REQUIRED_NPCS,
    MAX_FLOORS,
    NPC_PLACEMENT_ATTEMPTS,
    PLAYER_START_X,
    PLAYER_START_Y,
    QUEST_COMPLETION_COHERENCE_BONUS,
    QUEST_TARGET_NPCS,
    STAIRS_DOWN_DEFAULT_X,
    STAIRS_DOWN_DEFAULT_Y,
    STAIRS_UP_DEFAULT_X,
    STAIRS_UP_DEFAULT_Y,
    TERMINAL_PLACEMENT_ATTEMPTS,
    TERMINAL_X_OFFSET,
    TERMINAL_Y_OFFSET,
)
from neural_dive.data.levels import PARSED_LEVELS, ZONE_TERMINALS
from neural_dive.data_loader import load_all_game_data
from neural_dive.difficulty import DifficultyLevel, get_difficulty_settings
from neural_dive.entities import Entity, InfoTerminal, Stairs
from neural_dive.enums import NPCType
from neural_dive.managers.player_manager import PlayerManager
from neural_dive.models import Answer, Conversation
from neural_dive.question_types import QuestionType


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
        """
        Initialize a new game.

        Args:
            map_width: Width of the game map in tiles
            map_height: Height of the game map in tiles
            random_npcs: Whether to randomize NPC and entity positions
            seed: Random seed for reproducibility (None for random)
            max_floors: Maximum number of floors/layers in the game
            difficulty: Difficulty level determining game balance
            content_set: Content set to use (None for default)
        """
        # Set up difficulty settings
        self.difficulty = difficulty
        self.difficulty_settings = get_difficulty_settings(difficulty)
        # Set up randomization
        if seed is not None:
            random.seed(seed)
        self.rand = random
        self.seed = seed

        # Game dimensions and settings
        self.random_npcs = random_npcs

        # Store content set
        if content_set is None:
            from neural_dive.data_loader import get_default_content_set
            content_set = get_default_content_set()
        self.content_set = content_set

        # Load all game data from JSON files
        self.questions, self.npc_data, self.terminal_data = load_all_game_data(content_set)

        # Initialize Floor Manager
        from neural_dive.managers.floor_manager import FloorManager

        self.floor_manager = FloorManager(
            max_floors=max_floors,
            map_width=map_width,
            map_height=map_height,
            seed=seed,
        )

        # Get map and dimensions from floor manager
        self.game_map = self.floor_manager.game_map
        self.map_width = self.floor_manager.map_width
        self.map_height = self.floor_manager.map_height

        # Get player start position
        level_data = PARSED_LEVELS.get(1)
        if level_data and "player_start" in level_data and level_data["player_start"]:
            player_start = level_data["player_start"]
        else:
            player_start = (PLAYER_START_X, PLAYER_START_Y)

        # Create player entity
        self.player = Entity(player_start[0], player_start[1], "@", "cyan", "Data Runner")
        self.old_player_pos: tuple[int, int] | None = None

        # Current floor entities (non-NPC)
        self.stairs: list[Stairs] = []
        self.terminals: list[InfoTerminal] = []

        # Initialize NPC Manager
        from neural_dive.managers.npc_manager import NPCManager

        self.npc_manager = NPCManager(
            npc_data=self.npc_data,
            questions=self.questions,
            rng=self.rand,
            difficulty_settings=self.difficulty_settings,
            seed=seed,
        )

        # Initialize Conversation Engine
        from neural_dive.managers.conversation_engine import ConversationEngine

        self.conversation_engine = ConversationEngine()

        # Player stats (managed by PlayerManager with difficulty-based settings)
        self.player_manager = PlayerManager(
            coherence=self.difficulty_settings.starting_coherence,
            max_coherence=self.difficulty_settings.max_coherence,
        )

        # Score tracking
        self.start_time = time.time()
        self.questions_answered = 0
        self.questions_correct = 0
        self.questions_wrong = 0
        self.npcs_completed: set[str] = set()  # NPCs with completed conversations
        self.game_won = False

        # Quest system
        self.quest_active = False

        # UI message.
        self.message = (
            f"Welcome to Neural Dive! Descend through {max_floors} neural layers. "
            "Answer questions to gain knowledge and progress."
        )

        # Generate the first floor entities.
        self._generate_floor()

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
    def _show_greeting(self) -> bool:
        """Get show greeting from ConversationEngine."""
        return self.conversation_engine.show_greeting

    @_show_greeting.setter
    def _show_greeting(self, value: bool):
        """Set show greeting on ConversationEngine."""
        self.conversation_engine.show_greeting = value

    @property
    def _last_answer_response(self) -> str | None:
        """Get last answer response from ConversationEngine."""
        return self.conversation_engine.last_answer_response

    @_last_answer_response.setter
    def _last_answer_response(self, value: str | None):
        """Set last answer response on ConversationEngine."""
        self.conversation_engine.last_answer_response = value

    @property
    def _text_input_buffer(self) -> str:
        """Get text input buffer from ConversationEngine."""
        return self.conversation_engine.text_input_buffer

    @_text_input_buffer.setter
    def _text_input_buffer(self, value: str):
        """Set text input buffer on ConversationEngine."""
        self.conversation_engine.text_input_buffer = value

    def _generate_floor(self):
        """
        Generate all entities (NPCs, terminals, stairs) for the current floor.

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

    def _generate_terminals(self):
        """Generate and place info terminals for the current floor."""
        # Get level data for terminal positions
        level_data = PARSED_LEVELS.get(self.current_floor)

        if level_data and "terminal_positions" in level_data:
            # Use positions from level layout
            terminal_positions = level_data["terminal_positions"]
            zone_terminals = ZONE_TERMINALS.get(self.current_floor, {})

            # Create zone terminals based on labels in the level
            for _zone_name, zone_data in zone_terminals.items():
                if terminal_positions:
                    # Use next available terminal position
                    x, y = terminal_positions.pop(0)
                    terminal = InfoTerminal(x, y, zone_data["title"], zone_data["content"])  # type: ignore[arg-type]
                    self.terminals.append(terminal)
        else:
            # Fallback: Use old terminal system from terminal_data
            terminal_defs = {
                1: [("big_o_hint", 8, 8), ("lore_layer1", 12, 10)],
                2: [
                    ("data_structures", 8, 8),
                    ("tcp_hint", 12, 10),
                    ("devops_guide", 15, 8),
                    ("lore_layer2", 8, 12),
                ],
                3: [("concurrency_hint", 8, 8), ("database_basics", 12, 8)],
            }

            if self.current_floor not in terminal_defs:
                return

            # Use EntityPlacementStrategy for random or default placement
            from neural_dive.placement import EntityPlacementStrategy

            strategy = EntityPlacementStrategy(
                game_map=self.game_map,
                random_mode=self.random_npcs,
                rng=self.rand,
                map_width=self.map_width,
                map_height=self.map_height,
            )

            # Extract default positions from terminal_defs
            default_positions = [(x, y) for _, x, y in terminal_defs[self.current_floor]]

            # Place terminals
            positions = strategy.place_entities(
                level_positions=None,
                default_positions=default_positions,
                num_attempts=TERMINAL_PLACEMENT_ATTEMPTS,
                x_range=(TERMINAL_X_OFFSET, self.map_width - 2),
                y_range=(TERMINAL_Y_OFFSET, self.map_height - 2),
            )

            # Create terminals at the placed positions
            for i, (x, y) in enumerate(positions):
                if i < len(terminal_defs[self.current_floor]):
                    terminal_key, _, _ = terminal_defs[self.current_floor][i]
                    if terminal_key in self.terminal_data:
                        data = self.terminal_data[terminal_key]
                        terminal = InfoTerminal(x, y, data["title"], data["content"])
                        self.terminals.append(terminal)

    def _generate_stairs(self):
        """Generate stairs up and/or down based on current floor."""
        # Get level data for stair positions
        level_data = PARSED_LEVELS.get(self.current_floor)

        if level_data:
            # Use stairs from level layout
            stairs_down_positions = level_data.get("stairs_down", [])
            stairs_up_positions = level_data.get("stairs_up", [])

            # Add stairs down
            if self.current_floor < self.max_floors and stairs_down_positions:
                for x, y in stairs_down_positions:
                    self.stairs.append(Stairs(x, y, "down"))

            # Add stairs up
            if self.current_floor > 1 and stairs_up_positions:
                for x, y in stairs_up_positions:
                    self.stairs.append(Stairs(x, y, "up"))
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

            # Check if standing on stairs and show hint
            for stair in self.stairs:
                if self.player.x == stair.x and self.player.y == stair.y:
                    direction = "up" if stair.direction == "up" else "down"
                    self.message = f"Standing on stairs {direction}. Press Space or >/< to use."
                    return True

            self.message = ""
            return True
        else:
            self.message = "Blocked by firewall!"
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
            self.message = f"{npc_name}: You have proven yourself. We have nothing more to discuss."
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
            required = FLOOR_REQUIRED_NPCS.get(self.current_floor, set())
            incomplete = [
                npc
                for npc in required
                if not self.npc_conversations.get(npc) or not self.npc_conversations[npc].completed
            ]
            self.message = f"Cannot descend! Complete conversations with: {', '.join(incomplete)}"
            return False

        # Descend using floor manager
        self.floor_manager.move_to_next_floor(self.player)
        self.game_map = self.floor_manager.game_map
        self.map_width = self.floor_manager.map_width
        self.map_height = self.floor_manager.map_height

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

        # Ascend using floor manager
        self.floor_manager.move_to_previous_floor(self.player)
        self.game_map = self.floor_manager.game_map
        self.map_width = self.floor_manager.map_width
        self.map_height = self.floor_manager.map_height

        self._generate_floor()
        self.message = f"Ascended to Neural Layer {self.current_floor}"
        return True

    def answer_question(self, answer_index: int) -> tuple[bool, str]:
        """
        Answer the current conversation question.

        Args:
            answer_index: Index of the selected answer (0-based)

        Returns:
            Tuple of (correct, response_message)
        """
        if not self.active_conversation:
            return False, "Not in a conversation."

        conv = self.active_conversation

        # Check if conversation is already complete
        if conv.current_question_idx >= len(conv.questions):
            conv.completed = True
            self.active_conversation = None
            return True, "Conversation completed!"

        # Get current question
        question = conv.questions[conv.current_question_idx]

        # Validate answer index
        if answer_index < 0 or answer_index >= len(question.answers):
            return False, "Invalid answer choice."

        answer = question.answers[answer_index]

        # Track NPC opinion
        npc_name = conv.npc_name
        if npc_name not in self.npc_opinions:
            self.npc_opinions[npc_name] = 0

        # Check if this is an enemy (harsher penalties)
        is_enemy = conv.npc_type == NPCType.ENEMY

        if answer.correct:
            return self._handle_correct_answer(conv, answer, npc_name, is_enemy)
        else:
            return self._handle_wrong_answer(conv, answer, npc_name, is_enemy)

    def answer_text_question(self, user_answer: str) -> tuple[bool, str]:
        """
        Answer the current conversation question with typed text.

        For SHORT_ANSWER and YES_NO question types.

        Args:
            user_answer: The text answer provided by the user

        Returns:
            Tuple of (correct, response_message)
        """
        if not self.active_conversation:
            return False, "Not in a conversation."

        conv = self.active_conversation

        # Check if conversation is already complete
        if conv.current_question_idx >= len(conv.questions):
            conv.completed = True
            self.active_conversation = None
            return True, "Conversation completed!"

        # Get current question
        question = conv.questions[conv.current_question_idx]

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

        # Check if this is an enemy (harsher penalties)
        is_enemy = conv.npc_type == NPCType.ENEMY

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

            # Check for victory condition on final floor
            if self.floor_manager.is_final_floor():
                # Victory bosses - defeating any of these wins the game
                victory_bosses = {"VIRUS_HUNTER", "THEORY_ORACLE", "AI_CONSCIOUSNESS"}
                if npc_name in victory_bosses:
                    self.game_won = True

            # Track quest completion for specialists
            if conv.npc_type == NPCType.SPECIALIST:
                self.quest_completed_npcs.add(npc_name)

            self.active_conversation = None

            # Add completion message
            response += f"\n\n{npc_name}: You have proven your worth. I grant you passage."

        return True, response

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

        # Calculate score (simple formula - can be enhanced)
        score = (
            (self.questions_correct * 100)  # Points per correct answer
            + (len(self.knowledge_modules) * 50)  # Points per knowledge module
            + (len(self.npcs_completed) * 200)  # Points per NPC completed
            + (self.coherence * 10)  # Bonus for remaining coherence
        )

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

    def save_game(self, filepath: str | Path | None = None) -> bool:
        """
        Save the current game state to a file.

        Args:
            filepath: Path to save file. If None, uses default location.

        Returns:
            True if save successful, False otherwise
        """
        if filepath is None:
            # Default save location: ~/.neural_dive/save.json
            save_dir = Path.home() / ".neural_dive"
            save_dir.mkdir(exist_ok=True)
            filepath = save_dir / "save.json"
        else:
            filepath = Path(filepath)

        try:
            # Collect all game state
            save_data = {
                # Game settings
                "difficulty": self.difficulty.value,
                "seed": self.seed,
                "content_set": self.content_set,
                "map_width": self.map_width,
                "map_height": self.map_height,
                "max_floors": self.max_floors,
                "current_floor": self.current_floor,
                "random_npcs": self.random_npcs,
                # Player state (delegated to PlayerManager)
                "player_manager": self.player_manager.to_dict(),
                # Player position
                "player_x": self.player.x,
                "player_y": self.player.y,
                # NPC state (delegated to NPCManager)
                "npc_manager": self.npc_manager.to_dict(),
                # Conversation state (delegated to ConversationEngine)
                "conversation_engine": self.conversation_engine.to_dict(),
                # Statistics
                "start_time": self.start_time,
                "questions_answered": self.questions_answered,
                "questions_correct": self.questions_correct,
                "questions_wrong": self.questions_wrong,
                "npcs_completed": list(self.npcs_completed),
                "game_won": self.game_won,
                # Quest state
                "quest_active": self.quest_active,
                # Message
                "message": self.message,
            }

            # Write to file
            with open(filepath, "w") as f:
                json.dump(save_data, f, indent=2)

            return True
        except Exception as e:
            print(f"Error saving game: {e}")
            return False

    @staticmethod
    def load_game(filepath: str | Path | None = None) -> Game | None:
        """
        Load a saved game from a file.

        Args:
            filepath: Path to save file. If None, uses default location.

        Returns:
            Loaded Game instance, or None if load failed
        """
        if filepath is None:
            # Default save location
            filepath = Path.home() / ".neural_dive" / "save.json"
        else:
            filepath = Path(filepath)

        if not filepath.exists():
            return None

        try:
            # Read save data
            with open(filepath) as f:
                save_data = json.load(f)

            # Create new game with saved settings
            from neural_dive.difficulty import DifficultyLevel
            from neural_dive.managers.conversation_engine import ConversationEngine
            from neural_dive.managers.npc_manager import NPCManager

            difficulty = DifficultyLevel(save_data["difficulty"])
            game = Game(
                map_width=save_data["map_width"],
                map_height=save_data["map_height"],
                random_npcs=save_data["random_npcs"],
                seed=save_data["seed"],
                max_floors=save_data["max_floors"],
                difficulty=difficulty,
                content_set=save_data.get("content_set"),  # Use .get() for backwards compatibility
            )

            # Restore game state
            game.current_floor = save_data["current_floor"]

            # Restore player state from PlayerManager
            game.player_manager = PlayerManager.from_dict(save_data["player_manager"])

            # Restore player position
            game.player.x = save_data["player_x"]
            game.player.y = save_data["player_y"]

            # Restore NPC state from NPCManager
            game.npc_manager = NPCManager.from_dict(
                save_data["npc_manager"],
                npc_data=game.npc_data,
                questions=game.questions,
                rng=game.rand,
                difficulty_settings=game.difficulty_settings,
                seed=game.seed,
            )

            # Restore conversation state from ConversationEngine
            game.conversation_engine = ConversationEngine.from_dict(
                save_data["conversation_engine"], npc_conversations=game.npc_conversations
            )

            # Restore statistics
            game.start_time = save_data["start_time"]
            game.questions_answered = save_data["questions_answered"]
            game.questions_correct = save_data["questions_correct"]
            game.questions_wrong = save_data["questions_wrong"]
            game.npcs_completed = set(save_data["npcs_completed"])
            game.game_won = save_data["game_won"]

            # Restore quest state
            game.quest_active = save_data["quest_active"]

            # Restore message
            game.message = save_data["message"]

            # Regenerate the current floor (map and entities)
            game._generate_floor()

            return game
        except Exception as e:
            print(f"Error loading game: {e}")
            return None
