"""
Player state management for Neural Dive.

This module provides the PlayerManager class which handles all player-related
state including coherence (health), knowledge modules, and inventory.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from neural_dive.config import MAX_COHERENCE, STARTING_COHERENCE

if TYPE_CHECKING:
    from neural_dive.items import Item, ItemType


@dataclass
class PlayerManager:
    """Manages player state including coherence (health), knowledge modules, and inventory.

    The PlayerManager encapsulates all player-related state and provides
    a clean interface for modifying player stats. This makes it easier to:
    - Test player mechanics in isolation
    - Add new player features (buffs, debuffs, equipment)
    - Serialize player state for save/load
    - Track player stat changes for achievements

    Attributes:
        coherence: Current coherence (health) value
        max_coherence: Maximum coherence capacity
        knowledge_modules: Set of acquired knowledge module names
        inventory: List of items the player is carrying
        max_inventory_size: Maximum number of items (default 20)
    """

    coherence: int = STARTING_COHERENCE
    max_coherence: int = MAX_COHERENCE
    knowledge_modules: set[str] = field(default_factory=set)
    inventory: list[Item] = field(default_factory=list)
    max_inventory_size: int = 20

    def gain_coherence(self, amount: int) -> int:
        """
        Add coherence points, capped at maximum.

        Args:
            amount: Amount of coherence to add (must be non-negative)

        Returns:
            Actual amount of coherence gained (accounting for cap)

        Raises:
            ValueError: If amount is negative

        Example:
            >>> pm = PlayerManager(coherence=95, max_coherence=100)
            >>> gained = pm.gain_coherence(10)
            >>> print(gained)  # Only gained 5 due to cap
            5
            >>> print(pm.coherence)
            100
        """
        if amount < 0:
            raise ValueError(f"Cannot gain negative coherence: {amount}")

        old_coherence = self.coherence
        self.coherence = min(self.max_coherence, self.coherence + amount)
        actual_gain = self.coherence - old_coherence

        return actual_gain

    def lose_coherence(self, amount: int) -> int:
        """
        Lose coherence points, minimum 0.

        Args:
            amount: Amount of coherence to lose (must be non-negative)

        Returns:
            Actual amount of coherence lost

        Raises:
            ValueError: If amount is negative

        Example:
            >>> pm = PlayerManager(coherence=10)
            >>> lost = pm.lose_coherence(30)
            >>> print(lost)  # Only lost 10 (dropped to 0)
            10
            >>> print(pm.coherence)
            0
        """
        if amount < 0:
            raise ValueError(f"Cannot lose negative coherence: {amount}")

        old_coherence = self.coherence
        self.coherence = max(0, self.coherence - amount)
        actual_loss = old_coherence - self.coherence

        return actual_loss

    def add_knowledge(self, module: str) -> bool:
        """
        Add a knowledge module to the player's collection.

        Args:
            module: Name of the knowledge module to add

        Returns:
            True if the module was newly added, False if already known

        Example:
            >>> pm = PlayerManager()
            >>> pm.add_knowledge("algorithms")
            True
            >>> pm.add_knowledge("algorithms")  # Already have it
            False
            >>> len(pm.knowledge_modules)
            1
        """
        if module in self.knowledge_modules:
            return False

        self.knowledge_modules.add(module)
        return True

    def has_knowledge(self, module: str) -> bool:
        """
        Check if player has acquired a specific knowledge module.

        Args:
            module: Name of the knowledge module to check

        Returns:
            True if player has this knowledge module

        Example:
            >>> pm = PlayerManager()
            >>> pm.add_knowledge("data_structures")
            True
            >>> pm.has_knowledge("data_structures")
            True
            >>> pm.has_knowledge("algorithms")
            False
        """
        return module in self.knowledge_modules

    def is_alive(self) -> bool:
        """
        Check if player is still alive (has coherence remaining).

        Returns:
            True if player has positive coherence

        Example:
            >>> pm = PlayerManager(coherence=50)
            >>> pm.is_alive()
            True
            >>> pm.lose_coherence(50)
            50
            >>> pm.is_alive()
            False
        """
        return self.coherence > 0

    def get_knowledge_count(self) -> int:
        """Get the total number of knowledge modules acquired.

        Returns:
            Number of unique knowledge modules

        Example:
            >>> pm = PlayerManager()
            >>> pm.add_knowledge("algorithms")
            True
            >>> pm.add_knowledge("data_structures")
            True
            >>> pm.get_knowledge_count()
            2
        """
        return len(self.knowledge_modules)

    def add_item(self, item: Item) -> bool:
        """Add an item to the player's inventory.

        Args:
            item: The item to add

        Returns:
            True if item was added, False if inventory is full

        Example:
            >>> from neural_dive.items import HintToken
            >>> pm = PlayerManager()
            >>> pm.add_item(HintToken())
            True
            >>> len(pm.inventory)
            1
        """
        if len(self.inventory) >= self.max_inventory_size:
            return False

        self.inventory.append(item)
        return True

    def remove_item(self, item: Item) -> bool:
        """Remove an item from the player's inventory.

        Args:
            item: The item to remove

        Returns:
            True if item was removed, False if not found

        Example:
            >>> from neural_dive.items import HintToken
            >>> pm = PlayerManager()
            >>> hint = HintToken()
            >>> pm.add_item(hint)
            True
            >>> pm.remove_item(hint)
            True
            >>> len(pm.inventory)
            0
        """
        if item in self.inventory:
            self.inventory.remove(item)
            return True
        return False

    def has_item_type(self, item_type: ItemType) -> bool:
        """Check if player has any items of a specific type.

        Args:
            item_type: The type of item to check for

        Returns:
            True if player has at least one item of this type

        Example:
            >>> from neural_dive.items import HintToken, ItemType
            >>> pm = PlayerManager()
            >>> pm.add_item(HintToken())
            True
            >>> pm.has_item_type(ItemType.HINT_TOKEN)
            True
            >>> pm.has_item_type(ItemType.CODE_SNIPPET)
            False
        """
        return any(item.item_type == item_type for item in self.inventory)

    def get_items_by_type(self, item_type: ItemType) -> list[Item]:
        """Get all items of a specific type from inventory.

        Args:
            item_type: The type of items to retrieve

        Returns:
            List of items matching the type

        Example:
            >>> from neural_dive.items import HintToken, ItemType
            >>> pm = PlayerManager()
            >>> pm.add_item(HintToken())
            True
            >>> pm.add_item(HintToken())
            True
            >>> hints = pm.get_items_by_type(ItemType.HINT_TOKEN)
            >>> len(hints)
            2
        """
        return [item for item in self.inventory if item.item_type == item_type]

    def get_inventory_count(self) -> int:
        """Get the current number of items in inventory.

        Returns:
            Number of items in inventory

        Example:
            >>> from neural_dive.items import HintToken
            >>> pm = PlayerManager()
            >>> pm.get_inventory_count()
            0
            >>> pm.add_item(HintToken())
            True
            >>> pm.get_inventory_count()
            1
        """
        return len(self.inventory)

    def is_inventory_full(self) -> bool:
        """Check if inventory is at maximum capacity.

        Returns:
            True if inventory is full

        Example:
            >>> pm = PlayerManager(max_inventory_size=2)
            >>> pm.is_inventory_full()
            False
            >>> from neural_dive.items import HintToken
            >>> pm.add_item(HintToken())
            True
            >>> pm.add_item(HintToken())
            True
            >>> pm.is_inventory_full()
            True
        """
        return len(self.inventory) >= self.max_inventory_size

    def to_dict(self) -> dict:
        """Serialize player state to a dictionary.

        Returns:
            Dictionary containing all player state for serialization

        Example:
            >>> from neural_dive.items import HintToken
            >>> pm = PlayerManager(coherence=85)
            >>> pm.add_knowledge("algorithms")
            True
            >>> pm.add_item(HintToken())
            True
            >>> state = pm.to_dict()
            >>> state["coherence"]
            85
            >>> "algorithms" in state["knowledge_modules"]
            True
            >>> len(state["inventory"])
            1
        """
        from neural_dive.items import CodeSnippet, HintToken

        inventory_data: list[dict[str, str | int | list[str]]] = []
        for item in self.inventory:
            item_dict: dict[str, str | int | list[str]] = {
                "name": item.name,
                "description": item.description,
                "item_type": item.item_type.value,
            }
            # Add type-specific data
            if isinstance(item, CodeSnippet):
                item_dict["topic"] = item.topic
                item_dict["content"] = item.content
            elif isinstance(item, HintToken):
                item_dict["answers_to_eliminate"] = item.answers_to_eliminate
            inventory_data.append(item_dict)

        return {
            "coherence": self.coherence,
            "max_coherence": self.max_coherence,
            "knowledge_modules": list(self.knowledge_modules),
            "inventory": inventory_data,
            "max_inventory_size": self.max_inventory_size,
        }

    @classmethod
    def from_dict(cls, data: dict) -> PlayerManager:
        """Create PlayerManager instance from serialized dictionary.

        Args:
            data: Dictionary containing serialized player state

        Returns:
            New PlayerManager instance with restored state

        Example:
            >>> data = {
            ...     "coherence": 85,
            ...     "max_coherence": 100,
            ...     "knowledge_modules": ["algorithms", "data_structures"],
            ...     "inventory": [],
            ...     "max_inventory_size": 20,
            ... }
            >>> pm = PlayerManager.from_dict(data)
            >>> pm.coherence
            85
            >>> pm.get_knowledge_count()
            2
        """
        from neural_dive.items import CodeSnippet, HintToken, ItemType

        # Reconstruct inventory items
        inventory: list[Item] = []
        for item_data in data.get("inventory", []):
            item_type = ItemType(item_data["item_type"])
            if item_type == ItemType.HINT_TOKEN:
                answers_to_eliminate = item_data.get("answers_to_eliminate", 1)
                inventory.append(HintToken(answers_to_eliminate=answers_to_eliminate))
            elif item_type == ItemType.CODE_SNIPPET:
                inventory.append(
                    CodeSnippet(
                        name=item_data["name"],
                        topic=item_data["topic"],
                        content=item_data["content"],
                    )
                )

        return cls(
            coherence=data.get("coherence", STARTING_COHERENCE),
            max_coherence=data.get("max_coherence", MAX_COHERENCE),
            knowledge_modules=set(data.get("knowledge_modules", [])),
            inventory=inventory,
            max_inventory_size=data.get("max_inventory_size", 20),
        )
