"""Game serialization for Neural Dive.

This module handles saving and loading game state to/from JSON files.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from neural_dive.game import Game


class GameSerializer:
    """Handles game save/load operations.

    Separates serialization logic from the Game class for better
    testability and maintainability.
    """

    DEFAULT_SAVE_DIR = Path.home() / ".neural_dive"
    DEFAULT_SAVE_FILE = "save.json"

    @classmethod
    def get_default_save_path(cls) -> Path:
        """Get the default save file path.

        Returns:
            Path to default save file
        """
        return cls.DEFAULT_SAVE_DIR / cls.DEFAULT_SAVE_FILE

    @classmethod
    def save(cls, game: Game, filepath: str | Path | None = None) -> tuple[bool, Path | None]:
        """Save game state to a file.

        Args:
            game: Game instance to save
            filepath: Path to save file (None for default location)

        Returns:
            Tuple of (success, filepath) where success is True if save successful,
            and filepath is the Path where the game was saved (or None on failure)
        """
        # Resolve filepath
        if filepath is None:
            filepath = cls.get_default_save_path()
            filepath.parent.mkdir(exist_ok=True)
        else:
            filepath = Path(filepath)

        try:
            # Collect game state
            save_data = cls._serialize_game_state(game)

            # Write to file
            with open(filepath, "w") as f:
                json.dump(save_data, f, indent=2)

            return True, filepath
        except Exception as e:
            print(f"Error saving game: {e}")
            return False, None

    @classmethod
    def load(cls, filepath: str | Path | None = None) -> Game | None:
        """Load game state from a file.

        Args:
            filepath: Path to save file (None for default location)

        Returns:
            Loaded Game instance, or None if load failed
        """
        # Resolve filepath
        filepath = cls.get_default_save_path() if filepath is None else Path(filepath)

        if not filepath.exists():
            return None

        try:
            # Read save data
            with open(filepath) as f:
                save_data = json.load(f)

            # Deserialize into game instance
            return cls._deserialize_game_state(save_data)
        except Exception as e:
            print(f"Error loading game: {e}")
            return None

    @classmethod
    def _serialize_game_state(cls, game: Game) -> dict:
        """Serialize game state to dictionary.

        Args:
            game: Game instance

        Returns:
            Dictionary containing all game state
        """
        return {
            # Game settings
            "difficulty": game.difficulty.value,
            "seed": game.seed,
            "content_set": game.content_set,
            "map_width": game.map_width,
            "map_height": game.map_height,
            "max_floors": game.max_floors,
            "current_floor": game.current_floor,
            "random_npcs": game.random_npcs,
            # Player state (delegated to PlayerManager)
            "player_manager": game.player_manager.to_dict(),
            # Stats tracking (delegated to StatsTracker)
            "stats_tracker": game.stats_tracker.to_dict(),
            # Player position
            "player_x": game.player.x,
            "player_y": game.player.y,
            # NPC state (delegated to NPCManager)
            "npc_manager": game.npc_manager.to_dict(),
            # Conversation state (delegated to ConversationEngine)
            "conversation_engine": game.conversation_engine.to_dict(),
            # Quest state (delegated to QuestManager)
            "quest_manager": game.quest_manager.to_dict(),
            # Legacy statistics (kept for backward compatibility with old saves)
            "start_time": game.start_time,
            "questions_answered": game.questions_answered,
            "questions_correct": game.questions_correct,
            "questions_wrong": game.questions_wrong,
            # Other game state
            "npcs_completed": list(game.npcs_completed),
            "game_won": game.game_won,
            # Message
            "message": game.message,
        }

    @classmethod
    def _deserialize_game_state(cls, save_data: dict) -> Game:
        """Deserialize game state from dictionary.

        Args:
            save_data: Dictionary containing game state

        Returns:
            Restored Game instance
        """
        import time

        from neural_dive.difficulty import DifficultyLevel
        from neural_dive.game import Game
        from neural_dive.managers.conversation_engine import ConversationEngine
        from neural_dive.managers.npc_manager import NPCManager
        from neural_dive.managers.player_manager import PlayerManager
        from neural_dive.managers.quest_manager import QuestManager
        from neural_dive.managers.stats_tracker import StatsTracker

        # Create new game with saved settings
        difficulty = DifficultyLevel(save_data["difficulty"])
        game = Game(
            map_width=save_data["map_width"],
            map_height=save_data["map_height"],
            random_npcs=save_data["random_npcs"],
            seed=save_data["seed"],
            max_floors=save_data["max_floors"],
            difficulty=difficulty,
            content_set=save_data.get("content_set"),
        )

        # Restore game state
        game.current_floor = save_data["current_floor"]

        # Restore player state from PlayerManager
        game.player_manager = PlayerManager.from_dict(save_data["player_manager"])

        # Restore stats from StatsTracker (with backward compatibility for old saves)
        if "stats_tracker" in save_data:
            game.stats_tracker = StatsTracker.from_dict(save_data["stats_tracker"])
        else:
            # Backward compatibility: load from legacy fields
            game.stats_tracker = StatsTracker(
                questions_answered=save_data.get("questions_answered", 0),
                questions_correct=save_data.get("questions_correct", 0),
                questions_wrong=save_data.get("questions_wrong", 0),
                start_time=save_data.get("start_time", time.time()),
            )

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
            level_data=game.level_data,
        )

        # Restore conversation state from ConversationEngine
        game.conversation_engine = ConversationEngine.from_dict(
            save_data["conversation_engine"], npc_conversations=game.npc_conversations
        )

        # Restore quest state from QuestManager (with backward compatibility)
        if "quest_manager" in save_data:
            game.quest_manager = QuestManager.from_dict(save_data["quest_manager"])
        else:
            # Backward compatibility: load from legacy fields or NPCManager
            game.quest_manager = QuestManager()
            game.quest_manager.quest_active = save_data.get("quest_active", False)
            # Try to get quest_completed_npcs from npc_manager if available
            if "npc_manager" in save_data:
                npc_data = save_data["npc_manager"]
                if "quest_completed_npcs" in npc_data:
                    game.quest_manager.completed_npcs = set(npc_data["quest_completed_npcs"])

        # Restore other game state
        game.npcs_completed = set(save_data["npcs_completed"])
        game.game_won = save_data["game_won"]

        # Restore message
        game.message = save_data["message"]

        # Recreate EventBus and StateManager (not serialized)
        from neural_dive.game_builder import GameInitializer

        game.event_bus = GameInitializer.create_event_bus()
        game.state_manager = GameInitializer.create_state_manager(game, game.event_bus)

        # Regenerate the current floor (map and entities)
        game._generate_floor()

        return game
