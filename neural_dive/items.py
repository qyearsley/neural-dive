"""Item system for Neural Dive.

This module provides item classes for the inventory system including
hint tokens, code snippets, and item pickups.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ItemType(Enum):
    """Types of items in the game."""

    HINT_TOKEN = "hint_token"
    CODE_SNIPPET = "code_snippet"


@dataclass
class Item:
    """Base class for inventory items.

    Attributes:
        name: Display name of the item
        description: Short description shown in inventory
        item_type: Type of item (HINT_TOKEN, CODE_SNIPPET)
    """

    name: str
    description: str
    item_type: ItemType

    def use(self) -> bool:
        """Use the item. Override in subclasses.

        Returns:
            True if item was successfully used
        """
        return False


class HintToken(Item):
    """A hint token that eliminates wrong answers.

    When used during a multiple choice question, removes one or more
    incorrect answers to make the question easier.

    Attributes:
        answers_to_eliminate: Number of wrong answers to remove (default 1)
    """

    def __init__(self, answers_to_eliminate: int = 1):
        super().__init__(
            name="Hint Token",
            description=f"Eliminates {answers_to_eliminate} wrong answer(s)",
            item_type=ItemType.HINT_TOKEN,
        )
        self.answers_to_eliminate = answers_to_eliminate


class CodeSnippet(Item):
    """A code snippet containing reference information.

    Contains educational content that can be viewed during questions
    to help answer them correctly.

    Attributes:
        topic: Topic this snippet covers (e.g., "algorithms", "python")
        content: List of content lines to display
    """

    def __init__(self, name: str, topic: str, content: list[str]):
        super().__init__(
            name=name,
            description=f"Reference for {topic}",
            item_type=ItemType.CODE_SNIPPET,
        )
        self.topic = topic
        self.content = content


class ItemPickup:
    """An item pickup that appears on the game map.

    Players can walk over these to collect the item into their inventory.

    Attributes:
        x: X position on map
        y: Y position on map
        item: The item to be picked up
        char: Character to display on map
        color: Color of the pickup
    """

    def __init__(self, x: int, y: int, item: Item):
        self.x = x
        self.y = y
        self.item = item
        self.char = self._get_char_for_item(item)
        self.color = self._get_color_for_item(item)

    def _get_char_for_item(self, item: Item) -> str:
        """Get the map character for an item type."""
        if item.item_type == ItemType.HINT_TOKEN:
            return "?"
        # item.item_type == ItemType.CODE_SNIPPET
        return "S"

    def _get_color_for_item(self, item: Item) -> str:
        """Get the color for an item type."""
        if item.item_type == ItemType.HINT_TOKEN:
            return "yellow"
        # item.item_type == ItemType.CODE_SNIPPET
        return "cyan"

    def __repr__(self) -> str:
        return f"ItemPickup(item={self.item.name}, pos=({self.x}, {self.y}))"
