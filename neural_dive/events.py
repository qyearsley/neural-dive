"""Event system for Neural Dive.

Events are dispatched through an EventBus. Only ItemPickedUp exists today.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TypeVar, cast


class GameEvent:
    """Base class for all game events."""

    pass


@dataclass
class ItemPickedUp(GameEvent):
    """Event fired when player picks up an item.

    Attributes:
        item_name: Name of the item
        item_type: Type of the item (e.g., "hint_token", "code_snippet")
    """

    item_name: str
    item_type: str


E = TypeVar("E", bound=GameEvent)


class EventBus:
    """Event dispatcher for game events.

    The EventBus allows components to subscribe to specific event types and be
    notified when those events occur. This enables loose coupling between game
    systems (e.g., achievements, analytics, replay recording).
    """

    def __init__(self):
        """Initialize event bus with empty listener registry."""
        self._listeners: dict[type, list[Callable[[GameEvent], None]]] = {}

    def subscribe(self, event_type: type[E], handler: Callable[[E], None]) -> None:
        """Register an event listener.

        Args:
            event_type: Type of event to listen for (e.g., ItemPickedUp)
            handler: Callback function to invoke when event occurs
        """
        if event_type not in self._listeners:
            self._listeners[event_type] = []
        self._listeners[event_type].append(cast(Callable[[GameEvent], None], handler))

    def publish(self, event: GameEvent) -> None:
        """Dispatch an event to all registered listeners.

        Args:
            event: Event instance to dispatch
        """
        event_type = type(event)
        for handler in self._listeners.get(event_type, []):
            handler(event)
