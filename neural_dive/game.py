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
from typing import TYPE_CHECKING

from neural_dive.config import (
    DEFAULT_MAP_HEIGHT,
    DEFAULT_MAP_WIDTH,
    MAX_FLOORS,
)
from neural_dive.difficulty import DifficultyLevel, DifficultySettings
from neural_dive.entities import Entity, InfoTerminal
from neural_dive.models import Conversation

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

        # Initialize Stats Tracker
        self.stats_tracker = GameInitializer.create_stats_tracker()

        # Initialize Quest Manager
        self.quest_manager = GameInitializer.create_quest_manager()

        # Initialize Answer Processor (coordinates answer handling across managers)
        self.answer_processor = GameInitializer.create_answer_processor(
            player_manager=self.player_manager,
            npc_manager=self.npc_manager,
            conversation_engine=self.conversation_engine,
            stats_tracker=self.stats_tracker,
            quest_manager=self.quest_manager,
            difficulty_settings=self.difficulty_settings,
            snippets=self.snippets,
            rand=self.rand,
        )

        # Initialize Floor Entity Generator (handles non-NPC entity generation)
        self.floor_entity_generator = GameInitializer.create_floor_entity_generator(
            level_data=self.level_data,
            snippets=self.snippets,
            rand=self.rand,
        )

        # Initialize Movement Controller (handles player movement and collision)
        self.movement_controller = GameInitializer.create_movement_controller()

        # Initialize Interaction Handler (handles entity interactions and floor transitions)
        self.interaction_handler = GameInitializer.create_interaction_handler(
            player_manager=self.player_manager,
            conversation_engine=self.conversation_engine,
            floor_manager=self.floor_manager,
            quest_manager=self.quest_manager,
            difficulty_settings=self.difficulty_settings,
        )

        # Initialize EventBus (for event-driven architecture)
        self.event_bus = GameInitializer.create_event_bus()

        # Initialize StateManager (for centralized state mutations)
        self.state_manager = GameInitializer.create_state_manager(self, self.event_bus)

        # Initialize legacy statistics (kept for save/load compatibility)
        (
            self.start_time,
            self.questions_answered,
            self.questions_correct,
            self.questions_wrong,
            self.npcs_completed,
            self.game_won,
        ) = GameInitializer.initialize_stats()

        # UI message
        self.message = GameInitializer.create_welcome_message(max_floors)

        # Generate the first floor entities
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

    # Backward compatibility properties for StatsTracker
    @property
    def questions_answered(self) -> int:
        """Get questions answered from StatsTracker."""
        val: int = self.stats_tracker.questions_answered
        return val

    @questions_answered.setter
    def questions_answered(self, value: int) -> None:
        """Set questions answered on StatsTracker."""
        self.stats_tracker.questions_answered = value

    @property
    def questions_correct(self) -> int:
        """Get questions correct from StatsTracker."""
        val: int = self.stats_tracker.questions_correct
        return val

    @questions_correct.setter
    def questions_correct(self, value: int) -> None:
        """Set questions correct on StatsTracker."""
        self.stats_tracker.questions_correct = value

    @property
    def questions_wrong(self) -> int:
        """Get questions wrong from StatsTracker."""
        val: int = self.stats_tracker.questions_wrong
        return val

    @questions_wrong.setter
    def questions_wrong(self, value: int) -> None:
        """Set questions wrong on StatsTracker."""
        self.stats_tracker.questions_wrong = value

    @property
    def start_time(self) -> float:
        """Get start time from StatsTracker."""
        val: float = self.stats_tracker.start_time
        return val

    @start_time.setter
    def start_time(self, value: float) -> None:
        """Set start time on StatsTracker."""
        self.stats_tracker.start_time = value

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
        """Get quest completed NPCs from QuestManager."""
        val: set[str] = self.quest_manager.completed_npcs
        return val

    @property
    def old_npc_positions(self) -> dict[str, tuple[int, int]]:
        """Get old NPC positions from NPCManager."""
        return self.npc_manager.old_positions

    # Backward compatibility properties for QuestManager
    @property
    def quest_active(self) -> bool:
        """Get quest active state from QuestManager."""
        val: bool = self.quest_manager.quest_active
        return val

    @quest_active.setter
    def quest_active(self, value: bool) -> None:
        """Set quest active state on QuestManager."""
        self.quest_manager.quest_active = value

    # Backward compatibility properties for ConversationEngine
    @property
    def active_conversation(self) -> Conversation | None:
        """Get active conversation from ConversationEngine."""
        return self.conversation_engine.active_conversation

    @active_conversation.setter
    def active_conversation(self, value: Conversation | None) -> None:
        """Set active conversation on ConversationEngine."""
        self.conversation_engine.active_conversation = value

    @property
    def active_terminal(self) -> InfoTerminal | None:
        """Get active terminal from ConversationEngine."""
        return self.conversation_engine.active_terminal

    @active_terminal.setter
    def active_terminal(self, value: InfoTerminal | None) -> None:
        """Set active terminal on ConversationEngine."""
        self.conversation_engine.active_terminal = value

    @property
    def active_inventory(self) -> bool:
        """Get active inventory state from ConversationEngine."""
        return self.conversation_engine.active_inventory

    @active_inventory.setter
    def active_inventory(self, value: bool) -> None:
        """Set active inventory state on ConversationEngine."""
        self.conversation_engine.active_inventory = value

    @property
    def active_snippet(self) -> dict | None:
        """Get active snippet from ConversationEngine."""
        return self.conversation_engine.active_snippet

    @active_snippet.setter
    def active_snippet(self, value: dict | None) -> None:
        """Set active snippet on ConversationEngine."""
        self.conversation_engine.active_snippet = value

    @property
    def show_greeting(self) -> bool:
        """Get show greeting from ConversationEngine."""
        return self.conversation_engine.show_greeting

    @show_greeting.setter
    def show_greeting(self, value: bool) -> None:
        """Set show greeting on ConversationEngine."""
        self.conversation_engine.show_greeting = value

    @show_greeting.deleter
    def show_greeting(self) -> None:
        """Delete show greeting from ConversationEngine."""
        self.conversation_engine.show_greeting = False

    @property
    def last_answer_response(self) -> str | None:
        """Get last answer response from ConversationEngine."""
        return self.conversation_engine.last_answer_response

    @last_answer_response.setter
    def last_answer_response(self, value: str | None) -> None:
        """Set last answer response on ConversationEngine."""
        self.conversation_engine.last_answer_response = value

    @last_answer_response.deleter
    def last_answer_response(self) -> None:
        """Delete last answer response from ConversationEngine."""
        self.conversation_engine.last_answer_response = None

    @property
    def text_input_buffer(self) -> str:
        """Get text input buffer from ConversationEngine."""
        return self.conversation_engine.text_input_buffer

    @text_input_buffer.setter
    def text_input_buffer(self, value: str) -> None:
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

        # Generate all non-NPC entities using FloorEntityGenerator
        self.stairs, self.terminals, self.item_pickups = (
            self.floor_entity_generator.generate_all_entities(
                floor=self.current_floor,
                max_floors=self.max_floors,
                game_map=self.game_map,
                map_width=self.map_width,
                map_height=self.map_height,
                player_pos=(self.player.x, self.player.y),
                random_placement=self.random_npcs,
            )
        )

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
        """Check if a position is walkable.

        Args:
            x: X coordinate
            y: Y coordinate

        Returns:
            True if the position can be walked on, False otherwise
        """
        return self.movement_controller.is_walkable(x, y, self.game_map)

    def move_player(self, dx: int, dy: int) -> bool:
        """Attempt to move the player by a delta.

        Args:
            dx: Change in x position
            dy: Change in y position

        Returns:
            True if movement was successful, False otherwise
        """
        result = self.movement_controller.move_player(
            player=self.player,
            dx=dx,
            dy=dy,
            game_map=self.game_map,
            item_pickups=self.item_pickups,
            stairs=self.stairs,
            player_manager=self.player_manager,
            is_in_conversation=self.active_conversation is not None,
        )

        # Update game message and old position
        self.message = result.message
        if result.old_position is not None:
            self.old_player_pos = result.old_position

        return result.success

    def interact(self) -> bool:
        """Attempt to interact with nearby entity (terminal, NPC, or stairs).

        Prioritizes closest entity. For equal distances: NPC > Terminal > Stairs.

        Returns:
            True if interaction was successful, False otherwise
        """
        result = self.interaction_handler.interact(
            player_pos=(self.player.x, self.player.y),
            terminals=self.terminals,
            npcs=self.npcs,
            stairs=self.stairs,
            npc_conversations=self.npc_conversations,
        )

        self.message = result.message

        # Process the interaction result
        if result.action == "terminal" and result.terminal:
            self.active_terminal = result.terminal
        elif result.action == "conversation" and result.conversation:
            self.active_conversation = result.conversation

        return result.success

    def is_floor_complete(self) -> bool:
        """Check if the current floor's objectives are complete.

        Delegates to InteractionHandler for floor completion logic.

        Returns:
            True if all required NPCs have been talked to, False otherwise
        """
        return self.interaction_handler.is_floor_complete(self.npcs_completed, self.npc_data)

    def use_stairs(self) -> bool:
        """Attempt to use stairs at the player's current position.

        Returns:
            True if stairs were used successfully, False otherwise
        """
        result = self.interaction_handler.use_stairs(
            player=self.player,
            player_pos=(self.player.x, self.player.y),
            stairs=self.stairs,
            npcs_completed=self.npcs_completed,
            npc_data=self.npc_data,
        )

        self.message = result.message

        # If floor changed, regenerate entities
        if result.floor_changed:
            self._generate_floor()

        return result.success

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

        # Show the first available snippet
        # Note: Menu selection for multiple snippets could be added if needed
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

    def answer_question(self, answer_index: int) -> tuple[bool, str]:
        """Answer the current conversation question.

        Validates the answer, updates game state (coherence, knowledge), and
        progresses the conversation. Handles both correct and incorrect answers
        with appropriate rewards/penalties.

        Args:
            answer_index: Index of the selected answer (0-based). Must be within
                range of available answers for the current question.

        Returns:
            Tuple of (success, message):
                - success (bool): True if answer was correct, False if wrong
                - message (str): Feedback message describing the result

        Example:
            >>> game.active_conversation = some_conversation
            >>> correct, msg = game.answer_question(0)
            >>> if correct:
            ...     print(f"Correct! {msg}")
        """
        # Delegate to AnswerProcessor
        success, message, game_was_won = self.answer_processor.answer_multiple_choice(
            answer_index, self.npcs_completed, self.floor_manager.is_final_floor()
        )

        # Update game state
        if game_was_won:
            self.game_won = True

        return success, message

    def answer_text_question(self, user_answer: str) -> tuple[bool, str]:
        """Answer the current conversation question with typed text.

        For SHORT_ANSWER and YES_NO question types.

        Args:
            user_answer: The text answer provided by the user

        Returns:
            Tuple of (correct, response_message)
        """
        # Delegate to AnswerProcessor
        success, message, game_was_won = self.answer_processor.answer_text_question(
            user_answer, self.npcs_completed, self.floor_manager.is_final_floor()
        )

        # Update game state
        if game_was_won:
            self.game_won = True

        return success, message

    def get_current_score(self) -> int:
        """Calculate the current score based on player progress.

        Returns:
            Current score value
        """
        score: int = self.stats_tracker.get_current_score(
            knowledge_count=len(self.knowledge_modules),
            npcs_completed_count=len(self.npcs_completed),
            coherence=self.coherence,
        )
        return score

    def get_final_stats(self) -> dict:
        """Get final game statistics for victory/game over screen.

        Returns:
            Dictionary containing all game stats
        """
        stats: dict = self.stats_tracker.get_final_stats(
            npcs_completed_count=len(self.npcs_completed),
            knowledge_count=len(self.knowledge_modules),
            final_coherence=self.coherence,
            current_floor=self.current_floor,
        )
        return stats

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
