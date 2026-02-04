"""State management for Neural Dive.

This module provides centralized state mutation management with event emission.
All game state changes should go through the StateManager to ensure consistency
and enable features like undo/redo, replay, and analytics.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from neural_dive.events import (
    CoherenceChanged,
    ConversationStateChanged,
    EventBus,
    FloorChanged,
    GameOver,
    GameWon,
    NPCDefeated,
    PlayerMoved,
    QuestActivated,
    QuestCompleted,
)

if TYPE_CHECKING:
    from neural_dive.game import Game


class StateManager:
    """Central coordinator for all game state mutations.

    The StateManager ensures that all state changes:
    1. Are validated before being applied
    2. Emit appropriate events for tracking/analytics
    3. Maintain game consistency

    This enables features like:
    - Achievement tracking via event listeners
    - Replay recording/playback
    - Undo/redo functionality
    - Analytics and telemetry
    """

    def __init__(self, game: Game, event_bus: EventBus):
        """Initialize state manager.

        Args:
            game: Game instance to manage
            event_bus: Event bus for publishing state change events
        """
        self.game = game
        self.event_bus = event_bus

    # Player mutations
    def move_player(self, dx: int, dy: int) -> bool:
        """Move player with validation and event emission.

        Args:
            dx: X delta (-1, 0, or 1)
            dy: Y delta (-1, 0, or 1)

        Returns:
            True if move succeeded, False otherwise
        """
        # Validate move using MovementController
        move_result = self.game.movement_controller.move_player(
            self.game.player,
            dx,
            dy,
            self.game.game_map,
            self.game.item_pickups,
            self.game.stairs,
            self.game.player_manager,
            bool(self.game.active_conversation),
        )

        if not move_result.success:
            return False

        # Emit event
        old_pos = move_result.old_position
        new_pos = (self.game.player.x, self.game.player.y)
        self.event_bus.publish(PlayerMoved(old_pos, new_pos))

        # Update message if any
        if move_result.message:
            self.game.message = move_result.message

        return True

    def change_coherence(self, amount: int, reason: str) -> int:
        """Change coherence with event emission.

        Args:
            amount: Amount to add (positive) or subtract (negative)
            reason: Why coherence changed (for analytics)

        Returns:
            Actual amount changed (may be capped)
        """
        old = self.game.coherence
        self.game.coherence = max(0, min(self.game.max_coherence, self.game.coherence + amount))
        actual_change = self.game.coherence - old

        if actual_change != 0:
            self.event_bus.publish(CoherenceChanged(old, self.game.coherence, reason))

        # Check for game over
        if self.game.coherence <= 0:
            self.event_bus.publish(GameOver("coherence_lost"))

        return actual_change

    # Conversation mutations
    def start_conversation(self, npc_name: str) -> bool:
        """Start conversation with validation.

        Args:
            npc_name: Name of NPC to talk to

        Returns:
            True if conversation started, False otherwise
        """
        conversation = self.game.npc_conversations.get(npc_name)
        if not conversation or conversation.completed:
            return False

        # Perform mutations
        self.game.active_conversation = conversation
        self.game.show_greeting = True
        self.game.last_answer_response = None
        self.game.text_input_buffer = ""
        # Clear eliminated answers
        self.game.conversation_engine.eliminated_answers = set()

        # Emit event
        self.event_bus.publish(ConversationStateChanged("started", npc_name))

        return True

    def end_conversation(self) -> bool:
        """End conversation and cleanup.

        Returns:
            True if conversation was active, False otherwise
        """
        if not self.game.active_conversation:
            return False

        npc_name = self.game.active_conversation.npc_name

        # Perform mutations
        self.game.active_conversation = None
        self.game.show_greeting = False
        self.game.last_answer_response = None
        self.game.text_input_buffer = ""
        # Clear eliminated answers
        self.game.conversation_engine.eliminated_answers = set()

        # Emit event
        self.event_bus.publish(ConversationStateChanged("ended", npc_name))

        return True

    def complete_conversation(
        self, npc_name: str, correct_answers: int, total_questions: int
    ) -> None:
        """Mark conversation as completed and emit defeat event.

        Args:
            npc_name: Name of NPC whose conversation completed
            correct_answers: Number of correct answers
            total_questions: Total questions answered
        """
        # Get NPC type for event
        npc_info = self.game.npc_data.get(npc_name, {})
        npc_type = npc_info.get("type", "specialist")

        # Emit NPC defeated event
        self.event_bus.publish(NPCDefeated(npc_name, npc_type, correct_answers, total_questions))

    # Overlay mutations
    def toggle_inventory(self) -> None:
        """Toggle inventory overlay."""
        self.game.active_inventory = not self.game.active_inventory

    def close_all_overlays(self) -> None:
        """Close all overlays."""
        self.game.active_inventory = False
        self.game.active_terminal = None
        self.game.active_snippet = None

    def show_terminal(self, terminal_id: str) -> None:
        """Show terminal overlay.

        Args:
            terminal_id: ID of terminal to show
        """
        self.game.active_terminal = terminal_id

    def show_snippet(self, snippet_id: str) -> None:
        """Show code snippet overlay.

        Args:
            snippet_id: ID of snippet to show
        """
        self.game.active_snippet = snippet_id

    # Floor transitions
    def change_floor(self, new_floor: int, direction: str) -> None:
        """Change to a different floor with event emission.

        Args:
            new_floor: Floor number to move to
            direction: "up" or "down"
        """
        old_floor = self.game.current_floor

        # Update floor
        self.game.current_floor = new_floor

        # Emit event
        self.event_bus.publish(FloorChanged(old_floor, new_floor, direction))

    # Quest mutations
    def activate_quest(self) -> tuple[bool, str]:
        """Activate the main quest.

        Returns:
            Tuple of (success, message)
        """
        # Let QuestManager handle the logic
        success, message = self.game.quest_manager.activate_quest()

        if success:
            # Emit event (quest manager tracks required NPCs internally)
            self.event_bus.publish(QuestActivated("main_quest", []))

        return success, message

    def complete_quest(self) -> int:
        """Complete the active quest and award bonus.

        Returns:
            Bonus coherence awarded
        """
        # Get bonus from QuestManager
        bonus = self.game.quest_manager.get_completion_bonus()

        # Award bonus
        self.change_coherence(bonus, "quest_completed")

        # Emit event
        self.event_bus.publish(QuestCompleted("main_quest", bonus))

        return bonus

    # Game end states
    def trigger_victory(self) -> None:
        """Trigger game victory."""
        self.game.game_won = True

        # Get final stats
        final_score = self.game.stats_tracker.get_current_score(
            len(self.game.knowledge_modules),
            len(self.game.npcs_completed),
            self.game.coherence,
        )
        time_played = self.game.stats_tracker.get_time_played()

        # Emit event
        self.event_bus.publish(GameWon(final_score, time_played))

    def trigger_game_over(self, reason: str) -> None:
        """Trigger game over.

        Args:
            reason: Why game ended (e.g., "quit", "coherence_lost")
        """
        # Emit event
        self.event_bus.publish(GameOver(reason))

    # State queries (read-only)
    def is_in_conversation(self) -> bool:
        """Check if player is in conversation.

        Returns:
            True if in conversation, False otherwise
        """
        return self.game.active_conversation is not None

    def is_overlay_active(self) -> bool:
        """Check if any overlay is active.

        Returns:
            True if any overlay is showing, False otherwise
        """
        return (
            self.game.active_inventory
            or self.game.active_terminal is not None
            or self.game.active_snippet is not None
        )

    def can_move(self) -> bool:
        """Check if player can move.

        Returns:
            True if movement is allowed, False otherwise
        """
        return not self.is_in_conversation() and not self.is_overlay_active()
