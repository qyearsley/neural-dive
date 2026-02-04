"""Game initializer for Neural Dive.

This module provides helper methods for game initialization,
breaking down the complex Game.__init__ into focused, testable steps.
"""

from __future__ import annotations

import random
import time
from typing import Any

from neural_dive.config import PLAYER_START_X, PLAYER_START_Y
from neural_dive.data_loader import get_default_content_set, load_all_game_data
from neural_dive.difficulty import DifficultyLevel, DifficultySettings, get_difficulty_settings
from neural_dive.entities import Entity, InfoTerminal, Stairs
from neural_dive.items import ItemPickup


class GameInitializer:
    """Helper class for Game initialization logic.

    This class contains static methods for various initialization steps,
    making Game.__init__ cleaner and more testable.
    """

    @staticmethod
    def setup_difficulty(difficulty: DifficultyLevel) -> tuple[DifficultyLevel, DifficultySettings]:
        """Set up difficulty settings.

        Args:
            difficulty: Difficulty level

        Returns:
            Tuple of (difficulty, difficulty_settings)
        """
        difficulty_settings = get_difficulty_settings(difficulty)
        return difficulty, difficulty_settings

    @staticmethod
    def setup_randomization(seed: int | None) -> tuple[random.Random, int | None]:
        """Set up random number generator.

        Args:
            seed: Random seed (None for random)

        Returns:
            Tuple of (rng, seed)
        """
        return random.Random(seed), seed

    @staticmethod
    def load_content(content_set: str | None) -> tuple[str, dict, dict, dict, dict]:
        """Load game content data.

        Args:
            content_set: Content set identifier (None for default)

        Returns:
            Tuple of (content_set, questions, npc_data, level_data, snippets)
        """
        if content_set is None:
            content_set = get_default_content_set()

        questions, npc_data, level_data, snippets = load_all_game_data(content_set)
        return content_set, questions, npc_data, level_data, snippets

    @staticmethod
    def create_floor_manager(
        max_floors: int,
        map_width: int,
        map_height: int,
        seed: int | None,
        level_data: dict,
        floor_requirements: dict[int, set[str]] | None = None,
    ):
        """Create and initialize FloorManager.

        Args:
            max_floors: Maximum number of floors
            map_width: Map width
            map_height: Map height
            seed: Random seed
            level_data: Parsed level data
            floor_requirements: Dictionary mapping floor numbers to required NPC names

        Returns:
            Initialized FloorManager instance
        """
        from neural_dive.managers.floor_manager import FloorManager

        return FloorManager(
            max_floors=max_floors,
            map_width=map_width,
            map_height=map_height,
            seed=seed,
            level_data=level_data,
            floor_requirements=floor_requirements,
        )

    @staticmethod
    def create_player(level_data: dict) -> tuple[Entity, tuple[int, int] | None]:
        """Create player entity.

        Args:
            level_data: Level data for floor 1

        Returns:
            Tuple of (player entity, old_player_pos)
        """
        # Get player start position
        floor_1_data = level_data.get(1)
        if floor_1_data and "player_start" in floor_1_data and floor_1_data["player_start"]:
            player_start = floor_1_data["player_start"]
        else:
            player_start = (PLAYER_START_X, PLAYER_START_Y)

        player = Entity(player_start[0], player_start[1], "@", "cyan", "Data Runner")
        return player, None

    @staticmethod
    def create_npc_manager(
        npc_data: dict,
        questions: dict,
        rng: random.Random,
        difficulty_settings: DifficultySettings,
        seed: int | None,
        level_data: dict,
    ):
        """Create and initialize NPCManager.

        Args:
            npc_data: NPC definitions
            questions: Question database
            rng: Random number generator
            difficulty_settings: Difficulty settings
            seed: Random seed
            level_data: Parsed level data

        Returns:
            Initialized NPCManager instance
        """
        from neural_dive.managers.npc_manager import NPCManager

        return NPCManager(
            npc_data=npc_data,
            questions=questions,
            rng=rng,
            difficulty_settings=difficulty_settings,
            seed=seed,
            level_data=level_data,
        )

    @staticmethod
    def create_conversation_engine():
        """Create and initialize ConversationEngine.

        Returns:
            Initialized ConversationEngine instance
        """
        from neural_dive.managers.conversation_engine import ConversationEngine

        return ConversationEngine()

    @staticmethod
    def create_player_manager(difficulty_settings: DifficultySettings):
        """Create and initialize PlayerManager.

        Args:
            difficulty_settings: Difficulty settings

        Returns:
            Initialized PlayerManager instance
        """
        from neural_dive.managers.player_manager import PlayerManager

        return PlayerManager(
            coherence=difficulty_settings.starting_coherence,
            max_coherence=difficulty_settings.max_coherence,
        )

    @staticmethod
    def create_stats_tracker() -> Any:
        """Create a StatsTracker for game statistics.

        Returns:
            Initialized StatsTracker instance
        """
        from neural_dive.managers.stats_tracker import StatsTracker

        return StatsTracker()

    @staticmethod
    def create_quest_manager() -> Any:
        """Create a QuestManager for quest tracking.

        Returns:
            Initialized QuestManager instance
        """
        from neural_dive.managers.quest_manager import QuestManager

        return QuestManager()

    @staticmethod
    def create_answer_processor(
        player_manager: Any,
        npc_manager: Any,
        conversation_engine: Any,
        stats_tracker: Any,
        quest_manager: Any,
        difficulty_settings: DifficultySettings,
        snippets: dict,
        rand: Any,
    ) -> Any:
        """Create an AnswerProcessor for handling question answers.

        Args:
            player_manager: PlayerManager instance
            npc_manager: NPCManager instance
            conversation_engine: ConversationEngine instance
            stats_tracker: StatsTracker instance
            quest_manager: QuestManager instance
            difficulty_settings: Difficulty settings
            snippets: Code snippets dictionary
            rand: Random number generator

        Returns:
            Initialized AnswerProcessor instance
        """
        from neural_dive.managers.answer_processor import AnswerProcessor

        return AnswerProcessor(
            player_manager=player_manager,
            npc_manager=npc_manager,
            conversation_engine=conversation_engine,
            stats_tracker=stats_tracker,
            quest_manager=quest_manager,
            difficulty_settings=difficulty_settings,
            snippets=snippets,
            rand=rand,
        )

    @staticmethod
    def create_floor_entity_generator(level_data: dict, snippets: dict, rand: random.Random) -> Any:
        """Create a FloorEntityGenerator for entity generation.

        Args:
            level_data: Level layouts and entity positions
            snippets: Available code snippets
            rand: Random number generator

        Returns:
            Initialized FloorEntityGenerator instance
        """
        from neural_dive.managers.floor_entity_generator import FloorEntityGenerator

        return FloorEntityGenerator(
            level_data=level_data,
            snippets=snippets,
            rand=rand,
        )

    @staticmethod
    def create_movement_controller() -> Any:
        """Create a MovementController for player movement.

        Returns:
            Initialized MovementController instance
        """
        from neural_dive.managers.movement_controller import MovementController

        return MovementController()

    @staticmethod
    def create_interaction_handler(
        player_manager: Any,
        conversation_engine: Any,
        floor_manager: Any,
        quest_manager: Any,
        difficulty_settings: DifficultySettings,
    ) -> Any:
        """Create an InteractionHandler for entity interactions.

        Args:
            player_manager: PlayerManager instance
            conversation_engine: ConversationEngine instance
            floor_manager: FloorManager instance
            quest_manager: QuestManager instance
            difficulty_settings: Difficulty settings

        Returns:
            Initialized InteractionHandler instance
        """
        from neural_dive.managers.interaction_handler import InteractionHandler

        return InteractionHandler(
            player_manager=player_manager,
            conversation_engine=conversation_engine,
            floor_manager=floor_manager,
            quest_manager=quest_manager,
            difficulty_settings=difficulty_settings,
        )

    @staticmethod
    def initialize_stats() -> tuple[float, int, int, int, set[str], bool]:
        """Initialize game statistics.

        Returns:
            Tuple of (start_time, questions_answered, questions_correct,
                     questions_wrong, npcs_completed, game_won)
        """
        return (
            time.time(),  # start_time
            0,  # questions_answered
            0,  # questions_correct
            0,  # questions_wrong
            set(),  # npcs_completed
            False,  # game_won
        )

    @staticmethod
    def initialize_entities() -> tuple[list[Stairs], list[InfoTerminal], list[ItemPickup]]:
        """Initialize entity lists.

        Returns:
            Tuple of (stairs, terminals, item_pickups)
        """
        return [], [], []

    @staticmethod
    def create_welcome_message(max_floors: int) -> str:
        """Create welcome message.

        Args:
            max_floors: Maximum number of floors

        Returns:
            Welcome message string
        """
        return (
            f"Welcome to Neural Dive! Descend through {max_floors} neural layers. "
            "Answer questions to gain knowledge and progress."
        )

    @staticmethod
    def create_event_bus() -> Any:
        """Create an EventBus for event-driven architecture.

        Returns:
            Initialized EventBus instance
        """
        from neural_dive.events import EventBus

        return EventBus()

    @staticmethod
    def create_state_manager(game: Any, event_bus: Any) -> Any:
        """Create a StateManager for centralized state mutations.

        Args:
            game: Game instance
            event_bus: EventBus instance

        Returns:
            Initialized StateManager instance
        """
        from neural_dive.managers.state_manager import StateManager

        return StateManager(game, event_bus)


class GameBuilder:
    """Builder for Game instances with fluent interface.

    Provides a clean, chainable API for configuring and constructing Game objects.
    Useful for testing different configurations and making initialization explicit.

    Example:
        >>> game = (GameBuilder()
        ...     .with_difficulty(DifficultyLevel.HARD)
        ...     .with_seed(42)
        ...     .with_floors(10)
        ...     .with_fixed_positions()
        ...     .build())
    """

    def __init__(self):
        """Initialize builder with default configuration."""
        from neural_dive.config import DEFAULT_MAP_HEIGHT, DEFAULT_MAP_WIDTH, MAX_FLOORS

        # Defaults
        self._map_width = DEFAULT_MAP_WIDTH
        self._map_height = DEFAULT_MAP_HEIGHT
        self._max_floors = MAX_FLOORS
        self._difficulty = DifficultyLevel.NORMAL
        self._seed: int | None = None
        self._content_set: str | None = None
        self._random_npcs = True

    def with_map_size(self, width: int, height: int) -> GameBuilder:
        """Set map dimensions.

        Args:
            width: Map width in tiles
            height: Map height in tiles

        Returns:
            Self for method chaining
        """
        self._map_width = width
        self._map_height = height
        return self

    def with_floors(self, max_floors: int) -> GameBuilder:
        """Set maximum number of floors.

        Args:
            max_floors: Maximum floors in the game

        Returns:
            Self for method chaining
        """
        self._max_floors = max_floors
        return self

    def with_difficulty(self, difficulty: DifficultyLevel) -> GameBuilder:
        """Set difficulty level.

        Args:
            difficulty: Difficulty level

        Returns:
            Self for method chaining
        """
        self._difficulty = difficulty
        return self

    def with_seed(self, seed: int) -> GameBuilder:
        """Set random seed for reproducibility.

        Args:
            seed: Random seed

        Returns:
            Self for method chaining
        """
        self._seed = seed
        return self

    def with_content_set(self, content_set: str) -> GameBuilder:
        """Set content set (question topics).

        Args:
            content_set: Content set name

        Returns:
            Self for method chaining
        """
        self._content_set = content_set
        return self

    def with_fixed_positions(self) -> GameBuilder:
        """Disable random NPC/entity placement (use fixed positions from level data).

        Returns:
            Self for method chaining
        """
        self._random_npcs = False
        return self

    def with_random_positions(self) -> GameBuilder:
        """Enable random NPC/entity placement.

        Returns:
            Self for method chaining
        """
        self._random_npcs = True
        return self

    def build(self) -> Any:
        """Build Game instance with configured settings.

        Returns:
            Configured Game instance
        """
        # Import here to avoid circular dependency
        from neural_dive.game import Game

        return Game(
            map_width=self._map_width,
            map_height=self._map_height,
            random_npcs=self._random_npcs,
            seed=self._seed,
            max_floors=self._max_floors,
            difficulty=self._difficulty,
            content_set=self._content_set,
        )
