"""Game serialization for Neural Dive.

This module handles saving and loading game state to/from JSON files.
"""

from __future__ import annotations

import json
from pathlib import Path
import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from neural_dive.game import Game
    from neural_dive.game_builder import GameContext
    from neural_dive.managers.conversation_engine import ConversationEngine
    from neural_dive.managers.npc_manager import NPCManager
    from neural_dive.managers.player_manager import PlayerManager
    from neural_dive.managers.quest_manager import QuestManager
    from neural_dive.managers.stats_tracker import StatsTracker


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
        except (OSError, TypeError) as e:
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
        except (OSError, json.JSONDecodeError, KeyError, ValueError) as e:
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
            "max_floors": game.floor_manager.max_floors,
            "current_floor": game.floor_manager.current_floor,
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
            "start_time": time.time() - game.stats_tracker.get_time_played(),
            "questions_answered": game.stats_tracker.questions_answered,
            "questions_correct": game.stats_tracker.questions_correct,
            "questions_wrong": game.stats_tracker.questions_wrong,
            # Other game state
            "npcs_completed": list(game.npcs_completed),
            "game_won": game.game_won,
            # Message
            "message": game.message,
        }

    @classmethod
    def _deserialize_game_state(cls, save_data: dict) -> Game:
        """Deserialize game state from dictionary.

        Builds the restored managers first, then assembles the Game once via
        :meth:`Game.from_context`. Constructing a default Game and replacing its
        managers afterwards left collaborators holding discarded instances and
        generated the floor twice.

        Args:
            save_data: Dictionary containing game state

        Returns:
            Restored Game instance
        """
        from neural_dive.difficulty import DifficultyLevel
        from neural_dive.game import Game
        from neural_dive.game_builder import GameContext, GameManagers

        # Built on the saved floor, so the map and the player's start position
        # belong to that floor rather than to floor 1.
        ctx = GameContext.create(
            map_width=save_data["map_width"],
            map_height=save_data["map_height"],
            random_npcs=save_data["random_npcs"],
            seed=save_data["seed"],
            max_floors=save_data["max_floors"],
            difficulty=DifficultyLevel(save_data["difficulty"]),
            content_set=save_data.get("content_set"),
            start_floor=save_data["current_floor"],
        )

        npc_manager = cls._restore_npc_manager(save_data, ctx)
        managers = GameManagers(
            npc_manager=npc_manager,
            conversation_engine=cls._restore_conversation_engine(save_data, npc_manager),
            player_manager=cls._restore_player_manager(save_data),
            stats_tracker=cls._restore_stats_tracker(save_data),
            quest_manager=cls._restore_quest_manager(save_data),
        )

        game = Game.from_context(
            ctx,
            managers,
            npcs_completed=set(save_data["npcs_completed"]),
            game_won=save_data["game_won"],
            message=save_data["message"],
        )

        # The saved position, which overrides the floor's default start position.
        game.player.x = save_data["player_x"]
        game.player.y = save_data["player_y"]

        return game

    @classmethod
    def _restore_npc_manager(cls, save_data: dict, ctx: GameContext) -> NPCManager:
        """Rebuild the NPCManager from a save."""
        from neural_dive.managers.npc_manager import NPCManager

        return NPCManager.from_dict(
            save_data["npc_manager"],
            npc_data=ctx.npc_data,
            questions=ctx.questions,
            rng=ctx.rand,
            difficulty_settings=ctx.difficulty_settings,
            seed=ctx.seed,
            level_data=ctx.level_data,
        )

    @classmethod
    def _restore_conversation_engine(
        cls, save_data: dict, npc_manager: NPCManager
    ) -> ConversationEngine:
        """Rebuild the ConversationEngine from a save.

        Takes the restored NPCManager so an in-progress conversation is restored
        as the same object the NPCManager holds, not a separate copy.
        """
        from neural_dive.managers.conversation_engine import ConversationEngine

        return ConversationEngine.from_dict(
            save_data["conversation_engine"],
            npc_conversations=npc_manager.conversations,
        )

    @classmethod
    def _restore_player_manager(cls, save_data: dict) -> PlayerManager:
        """Rebuild the PlayerManager from a save."""
        from neural_dive.managers.player_manager import PlayerManager

        return PlayerManager.from_dict(save_data["player_manager"])

    @classmethod
    def _restore_stats_tracker(cls, save_data: dict) -> StatsTracker:
        """Rebuild the StatsTracker from a save, tolerating pre-StatsTracker saves."""
        from neural_dive.managers.stats_tracker import StatsTracker

        if "stats_tracker" in save_data:
            return StatsTracker.from_dict(save_data["stats_tracker"])

        # Backward compatibility: older saves kept these as top-level fields
        # under the same names, so the same reader handles them. Their
        # wall-clock `start_time` is ignored -- see StatsTracker.from_dict.
        return StatsTracker.from_dict(save_data)

    @classmethod
    def _restore_quest_manager(cls, save_data: dict) -> QuestManager:
        """Rebuild the QuestManager from a save, tolerating pre-QuestManager saves."""
        from neural_dive.managers.quest_manager import QuestManager

        if "quest_manager" in save_data:
            return QuestManager.from_dict(save_data["quest_manager"])

        # Backward compatibility: older saves kept quest state at the top level
        # and the completed-NPC set inside the NPCManager blob.
        manager = QuestManager()
        manager.quest_active = save_data.get("quest_active", False)
        npc_blob = save_data.get("npc_manager", {})
        if "quest_completed_npcs" in npc_blob:
            manager.completed_npcs = set(npc_blob["quest_completed_npcs"])
        return manager
