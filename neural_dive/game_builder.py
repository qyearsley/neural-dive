"""Game initializer for Neural Dive.

This module provides helper methods for game initialization,
breaking down the complex Game.__init__ into focused, testable steps.
"""

from __future__ import annotations

import random
import time

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
        if seed is not None:
            random.seed(seed)
        # The random module itself acts as a Random instance
        return random.Random() if seed is None else random.Random(seed), seed

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

        questions, npc_data, _terminal_data, level_data, snippets = load_all_game_data(content_set)
        # terminal_data is deprecated and no longer used (all content uses ZONE_TERMINALS in levels.py)
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
