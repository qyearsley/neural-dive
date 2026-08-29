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
from typing import TYPE_CHECKING

from neural_dive.config import (
    DEFAULT_MAP_HEIGHT,
    DEFAULT_MAP_WIDTH,
    MAX_FLOORS,
)
from neural_dive.difficulty import DifficultyLevel, DifficultySettings

if TYPE_CHECKING:
    import random

    from neural_dive.game_builder import GameContext, GameManagers
    from neural_dive.managers.conversation_engine import ConversationEngine
    from neural_dive.managers.floor_manager import FloorManager
    from neural_dive.managers.npc_manager import NPCManager
    from neural_dive.managers.player_manager import PlayerManager
    from neural_dive.player_profile import PlayerProfile


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
        profile: PlayerProfile | None = None,
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
            profile: Cross-run question history. None means this run neither
                reads nor writes history, which is the behaviour every caller
                had before profiles existed.
        """
        from neural_dive.game_builder import GameContext, GameManagers

        ctx = GameContext.create(
            map_width=map_width,
            map_height=map_height,
            random_npcs=random_npcs,
            seed=seed,
            max_floors=max_floors,
            difficulty=difficulty,
            content_set=content_set,
            profile=profile,
        )
        self._assemble(ctx, GameManagers.create_default(ctx))

    @classmethod
    def from_context(
        cls,
        ctx: GameContext,
        managers: GameManagers,
        *,
        npcs_completed: set[str] | None = None,
        game_won: bool = False,
        message: str | None = None,
    ) -> Game:
        """Build a Game from an existing context and a specific set of managers.

        This is how a save is restored: the caller builds the restored managers
        against ``ctx`` and hands them over, so the game is assembled in one pass.
        Constructing a default game and then replacing its managers would leave
        the collaborators in :meth:`_wire_manager_dependencies` pointing at
        instances that had already been discarded.

        Args:
            ctx: Settings, content, and world state to build on
            managers: The managers this game should own
            npcs_completed: Names of NPCs already completed (None for none)
            game_won: Whether the game has already been won
            message: UI message to show (None for the welcome message)

        Returns:
            A fully assembled Game
        """
        game = cls.__new__(cls)
        game._assemble(
            ctx,
            managers,
            npcs_completed=npcs_completed,
            game_won=game_won,
            message=message,
        )
        return game

    def _assemble(
        self,
        ctx: GameContext,
        managers: GameManagers,
        *,
        npcs_completed: set[str] | None = None,
        game_won: bool = False,
        message: str | None = None,
    ) -> None:
        """Assemble the game from a context and its managers.

        The single construction path for both a new game and a restored one.
        Order matters: the managers are installed before anything that captures
        them, and floor entities are generated last and exactly once.
        """
        from neural_dive.game_builder import GameInitializer

        # Settings and content
        self.difficulty: DifficultyLevel = ctx.difficulty
        self.difficulty_settings: DifficultySettings = ctx.difficulty_settings
        self.rand: random.Random = ctx.rand
        self.seed: int | None = ctx.seed
        self.random_npcs = ctx.random_npcs
        self.content_set = ctx.content_set
        self.questions = ctx.questions
        self.npc_data = ctx.npc_data
        self.level_data = ctx.level_data
        self.snippets = ctx.snippets
        self.profile: PlayerProfile | None = ctx.profile

        # World state. The context has already put the floor manager on the
        # right floor, so the map and dimensions here match that floor.
        self.floor_manager: FloorManager = ctx.floor_manager
        self.game_map = self.floor_manager.game_map
        self.map_width = self.floor_manager.map_width
        self.map_height = self.floor_manager.map_height
        self.player = ctx.player
        self.old_player_pos: tuple[int, int] | None = None
        self.stairs, self.terminals, self.item_pickups = GameInitializer.initialize_entities()

        # Managers own the game's mutable state
        self.npc_manager: NPCManager = managers.npc_manager
        self.conversation_engine: ConversationEngine = managers.conversation_engine
        self.player_manager: PlayerManager = managers.player_manager
        self.stats_tracker = managers.stats_tracker
        self.quest_manager = managers.quest_manager

        # Collaborators that capture the managers above. Built after the managers
        # are final, so they cannot end up holding a discarded instance.
        self._wire_manager_dependencies()

        self.floor_entity_generator = GameInitializer.create_floor_entity_generator(
            level_data=self.level_data,
            snippets=self.snippets,
            rand=self.rand,
        )
        self.movement_controller = GameInitializer.create_movement_controller()
        self.event_bus = GameInitializer.create_event_bus()
        self.state_manager = GameInitializer.create_state_manager(self, self.event_bus)

        # State that isn't owned by a manager
        self.npcs_completed: set[str] = set() if npcs_completed is None else npcs_completed
        self.game_won = game_won
        self.message = (
            GameInitializer.create_welcome_message(ctx.max_floors) if message is None else message
        )

        # Floor entities, generated exactly once
        self._generate_floor()

    def _wire_manager_dependencies(self) -> None:
        """Create the collaborators that capture manager instances.

        ``AnswerProcessor`` and ``InteractionHandler`` hold direct references to
        ``player_manager``, ``npc_manager``, ``conversation_engine``,
        ``stats_tracker`` and ``quest_manager``. That makes them a construction
        detail: they are built in :meth:`_assemble` once the managers are final.
        Nothing outside construction should swap a manager on the Game -- restore
        a save with :meth:`from_context` instead, which builds the managers first.
        """
        from neural_dive.game_builder import GameInitializer

        # Answer Processor coordinates answer handling across managers
        self.answer_processor = GameInitializer.create_answer_processor(
            player_manager=self.player_manager,
            npc_manager=self.npc_manager,
            conversation_engine=self.conversation_engine,
            stats_tracker=self.stats_tracker,
            quest_manager=self.quest_manager,
            difficulty_settings=self.difficulty_settings,
            snippets=self.snippets,
            rand=self.rand,
            profile=self.profile,
        )

        # Interaction Handler handles entity interactions and floor transitions
        self.interaction_handler = GameInitializer.create_interaction_handler(
            player_manager=self.player_manager,
            conversation_engine=self.conversation_engine,
            floor_manager=self.floor_manager,
            quest_manager=self.quest_manager,
            difficulty_settings=self.difficulty_settings,
        )

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
        self.npc_manager.movement.old_positions.clear()
        self.old_player_pos = None  # Clear player's old position to prevent stale rendering

        # Generate NPCs for this floor using NPCManager
        self.npc_manager.generate_npcs_for_floor(
            floor=self.floor_manager.current_floor,
            game_map=self.game_map,
            player_pos=(self.player.x, self.player.y),
            random_placement=self.random_npcs,
            map_width=self.map_width,
            map_height=self.map_height,
        )

        # Generate all non-NPC entities using FloorEntityGenerator
        self.stairs, self.terminals, self.item_pickups = (
            self.floor_entity_generator.generate_all_entities(
                floor=self.floor_manager.current_floor,
                max_floors=self.floor_manager.max_floors,
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
            is_conversation_active=self.conversation_engine.active_conversation is not None,
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
            is_in_conversation=self.conversation_engine.active_conversation is not None,
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
            npcs=self.npc_manager.npcs,
            stairs=self.stairs,
            npc_conversations=self.npc_manager.conversations,
        )

        self.message = result.message

        # Process the interaction result
        if result.action == "terminal" and result.terminal:
            self.conversation_engine.active_terminal = result.terminal
        elif result.action == "conversation" and result.conversation:
            self.conversation_engine.active_conversation = result.conversation

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
        if not self.conversation_engine.active_conversation:
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
        if not self.conversation_engine.active_conversation:
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
                    self.conversation_engine.active_snippet = snippet_data
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
            knowledge_count=len(self.player_manager.knowledge_modules),
            npcs_completed_count=len(self.npcs_completed),
            coherence=self.player_manager.coherence,
        )
        return score

    def get_final_stats(self) -> dict:
        """Get final game statistics for victory/game over screen.

        Returns:
            Dictionary containing all game stats
        """
        stats: dict = self.stats_tracker.get_final_stats(
            npcs_completed_count=len(self.npcs_completed),
            knowledge_count=len(self.player_manager.knowledge_modules),
            final_coherence=self.player_manager.coherence,
            current_floor=self.floor_manager.current_floor,
        )
        return stats

    def exit_conversation(self) -> bool:
        """
        Exit the current conversation.

        Returns:
            True if a conversation was exited, False otherwise
        """
        if self.conversation_engine.active_conversation:
            self.conversation_engine.active_conversation = None
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
        if self.conversation_engine.active_conversation and command in ["1", "2", "3", "4"]:
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
            "npcs": [(npc.x, npc.y, npc.name) for npc in self.npc_manager.npcs],
            "message": self.message,
            "coherence": self.player_manager.coherence,
            "knowledge_modules": list(self.player_manager.knowledge_modules),
            "in_conversation": self.conversation_engine.active_conversation is not None,
            "conversation_npc": (
                self.conversation_engine.active_conversation.npc_name
                if self.conversation_engine.active_conversation
                else None
            ),
            "current_floor": self.floor_manager.current_floor,
            "quest_active": self.quest_manager.quest_active,
            "quest_completed_npcs": list(self.quest_manager.completed_npcs),
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
    def load_game(
        filepath: str | Path | None = None,
        profile: PlayerProfile | None = None,
    ) -> Game | None:
        """Load a saved game from a file.

        Args:
            filepath: Path to save file. If None, uses default location.
            profile: Cross-run question history to attach to the restored game.

        Returns:
            Loaded Game instance, or None if load failed
        """
        from neural_dive.game_serializer import GameSerializer

        return GameSerializer.load(filepath, profile=profile)
