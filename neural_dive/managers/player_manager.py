"""
Player state management for Neural Dive.

This module provides the PlayerManager class which handles all player-related
state including coherence (health), knowledge modules, and related mechanics.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from neural_dive.config import MAX_COHERENCE, STARTING_COHERENCE


@dataclass
class PlayerManager:
    """
    Manages player state including coherence (health) and knowledge modules.

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
    """

    coherence: int = STARTING_COHERENCE
    max_coherence: int = MAX_COHERENCE
    knowledge_modules: set[str] = field(default_factory=set)

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
        """
        Get the total number of knowledge modules acquired.

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

    def to_dict(self) -> dict:
        """
        Serialize player state to a dictionary.

        Returns:
            Dictionary containing all player state for serialization

        Example:
            >>> pm = PlayerManager(coherence=85)
            >>> pm.add_knowledge("algorithms")
            True
            >>> state = pm.to_dict()
            >>> state["coherence"]
            85
            >>> "algorithms" in state["knowledge_modules"]
            True
        """
        return {
            "coherence": self.coherence,
            "max_coherence": self.max_coherence,
            "knowledge_modules": list(self.knowledge_modules),
        }

    @classmethod
    def from_dict(cls, data: dict) -> PlayerManager:
        """
        Create PlayerManager instance from serialized dictionary.

        Args:
            data: Dictionary containing serialized player state

        Returns:
            New PlayerManager instance with restored state

        Example:
            >>> data = {
            ...     "coherence": 85,
            ...     "max_coherence": 100,
            ...     "knowledge_modules": ["algorithms", "data_structures"]
            ... }
            >>> pm = PlayerManager.from_dict(data)
            >>> pm.coherence
            85
            >>> pm.get_knowledge_count()
            2
        """
        return cls(
            coherence=data.get("coherence", STARTING_COHERENCE),
            max_coherence=data.get("max_coherence", MAX_COHERENCE),
            knowledge_modules=set(data.get("knowledge_modules", [])),
        )
