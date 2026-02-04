"""Event system for Neural Dive.

This module provides an event-driven architecture for tracking game state changes.
Events are dispatched through an EventBus, allowing decoupled components to react
to state changes (e.g., for achievements, logging, analytics, replay systems).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass


class GameEvent:
    """Base class for all game events."""

    pass


@dataclass
class PlayerMoved(GameEvent):
    """Event fired when player moves.

    Attributes:
        old_pos: Previous (x, y) position
        new_pos: New (x, y) position
    """

    old_pos: tuple[int, int]
    new_pos: tuple[int, int]


@dataclass
class CoherenceChanged(GameEvent):
    """Event fired when coherence changes.

    Attributes:
        old: Previous coherence value
        new: New coherence value
        reason: Why coherence changed (e.g., "correct_answer", "wrong_answer", "helper")
    """

    old: int
    new: int
    reason: str


@dataclass
class ConversationStateChanged(GameEvent):
    """Event fired when conversation state changes.

    Attributes:
        stage: Conversation stage ("started", "greeting", "answering", "response", "ended")
        npc_name: Name of NPC in conversation (None if not in conversation)
    """

    stage: str
    npc_name: str | None


@dataclass
class ItemPickedUp(GameEvent):
    """Event fired when player picks up an item.

    Attributes:
        item_name: Name of the item
        item_type: Type of the item (e.g., "hint_token", "code_snippet")
    """

    item_name: str
    item_type: str


@dataclass
class FloorChanged(GameEvent):
    """Event fired when player changes floors.

    Attributes:
        old_floor: Previous floor number
        new_floor: New floor number
        direction: "up" or "down"
    """

    old_floor: int
    new_floor: int
    direction: str


@dataclass
class GameWon(GameEvent):
    """Event fired when player wins the game.

    Attributes:
        final_score: Player's final score
        time_played: Total time played in seconds
    """

    final_score: int
    time_played: float


@dataclass
class GameOver(GameEvent):
    """Event fired when game ends (loss).

    Attributes:
        reason: Why game ended (e.g., "coherence_lost", "quit")
    """

    reason: str


@dataclass
class NPCDefeated(GameEvent):
    """Event fired when player defeats an NPC (completes conversation).

    Attributes:
        npc_name: Name of defeated NPC
        npc_type: Type of NPC (specialist, helper, enemy, quest)
        correct_answers: Number of correct answers
        total_questions: Total questions answered
    """

    npc_name: str
    npc_type: str
    correct_answers: int
    total_questions: int


@dataclass
class QuestActivated(GameEvent):
    """Event fired when quest is activated.

    Attributes:
        quest_id: ID of activated quest
        required_npcs: List of NPC names required for quest
    """

    quest_id: str
    required_npcs: list[str]


@dataclass
class QuestCompleted(GameEvent):
    """Event fired when quest is completed.

    Attributes:
        quest_id: ID of completed quest
        bonus_coherence: Bonus coherence awarded
    """

    quest_id: str
    bonus_coherence: int


class EventBus:
    """Event dispatcher for game events.

    The EventBus allows components to subscribe to specific event types and be
    notified when those events occur. This enables loose coupling between game
    systems (e.g., achievements, analytics, replay recording).
    """

    def __init__(self):
        """Initialize event bus with empty listener registry."""
        self._listeners: dict[type, list[Callable[[GameEvent], None]]] = {}

    def subscribe(self, event_type: type[GameEvent], handler: Callable[[GameEvent], None]) -> None:
        """Register an event listener.

        Args:
            event_type: Type of event to listen for (e.g., PlayerMoved)
            handler: Callback function to invoke when event occurs
        """
        if event_type not in self._listeners:
            self._listeners[event_type] = []
        self._listeners[event_type].append(handler)

    def unsubscribe(
        self, event_type: type[GameEvent], handler: Callable[[GameEvent], None]
    ) -> None:
        """Remove an event listener.

        Args:
            event_type: Type of event to stop listening for
            handler: Callback function to remove
        """
        if event_type in self._listeners:
            self._listeners[event_type].remove(handler)

    def publish(self, event: GameEvent) -> None:
        """Dispatch an event to all registered listeners.

        Args:
            event: Event instance to dispatch
        """
        event_type = type(event)
        for handler in self._listeners.get(event_type, []):
            handler(event)

    def clear_all(self) -> None:
        """Remove all event listeners.

        Useful for testing or resetting event system.
        """
        self._listeners.clear()

    def get_listener_count(self, event_type: type[GameEvent]) -> int:
        """Get number of listeners for an event type.

        Args:
            event_type: Type of event

        Returns:
            Number of registered listeners
        """
        return len(self._listeners.get(event_type, []))
