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
    def save(cls, game: Game, filepath: str | Path | None = None) -> bool:
        """Save game state to a file.

        Args:
            game: Game instance to save
            filepath: Path to save file (None for default location)

        Returns:
            True if save successful, False otherwise
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

            return True
        except Exception as e:
            print(f"Error saving game: {e}")
            return False

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
            # Player position
            "player_x": game.player.x,
            "player_y": game.player.y,
            # NPC state (delegated to NPCManager)
            "npc_manager": game.npc_manager.to_dict(),
            # Conversation state (delegated to ConversationEngine)
            "conversation_engine": game.conversation_engine.to_dict(),
            # Statistics
            "start_time": game.start_time,
            "questions_answered": game.questions_answered,
            "questions_correct": game.questions_correct,
            "questions_wrong": game.questions_wrong,
            "npcs_completed": list(game.npcs_completed),
            "game_won": game.game_won,
            # Quest state
            "quest_active": game.quest_active,
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
        from neural_dive.difficulty import DifficultyLevel
        from neural_dive.game import Game
        from neural_dive.managers.conversation_engine import ConversationEngine
        from neural_dive.managers.npc_manager import NPCManager
        from neural_dive.managers.player_manager import PlayerManager

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
