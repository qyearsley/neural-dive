"""Quest management for Neural Dive.

This module provides the QuestManager class which handles quest progression
and objective tracking.
"""

from __future__ import annotations

from neural_dive.config import QUEST_COMPLETION_COHERENCE_BONUS, QUEST_TARGET_NPCS


class QuestManager:
    """Manages quest progression and objectives.

    The QuestManager encapsulates quest-related state and logic, making it easier to:
    - Test quest mechanics in isolation
    - Track quest progress independently
    - Add new quest types
    - Modify quest completion criteria

    Attributes:
        quest_active: Whether the main quest has been activated
        completed_npcs: Set of NPC names that have been completed for quest objectives
    """

    def __init__(self) -> None:
        """Initialize QuestManager with default state."""
        self.quest_active = False
        self.completed_npcs: set[str] = set()

    def activate_quest(self) -> tuple[bool, str]:
        """Activate the main quest.

        Returns:
            Tuple of (success, message) where success is True if quest was activated,
            and message describes the activation
        """
        if self.quest_active:
            return False, "Quest already active"

        self.quest_active = True
        return True, "Quest activated! Seek out the target NPCs."

    def complete_npc_objective(self, npc_name: str) -> tuple[bool, str]:
        """Mark an NPC as completed for quest objectives.

        Args:
            npc_name: Name of the NPC that was defeated/completed

        Returns:
            Tuple of (success, message) describing the result
        """
        if npc_name in self.completed_npcs:
            return False, f"{npc_name} already completed"

        self.completed_npcs.add(npc_name)

        if self.is_quest_complete():
            return True, f"{npc_name} completed! Quest objectives complete!"
        else:
            remaining = len(QUEST_TARGET_NPCS - self.completed_npcs)
            return True, f"{npc_name} completed! {remaining} objectives remaining."

    def is_quest_complete(self) -> bool:
        """Check if all quest objectives are complete.

        Returns:
            True if all target NPCs have been defeated
        """
        return QUEST_TARGET_NPCS.issubset(self.completed_npcs)

    def get_remaining_objectives(self) -> set[str]:
        """Get the set of remaining quest objective NPCs.

        Returns:
            Set of NPC names that haven't been completed yet
        """
        return QUEST_TARGET_NPCS - self.completed_npcs

    def get_completion_bonus(self) -> int:
        """Get the coherence bonus for completing the quest.

        Returns:
            Coherence bonus amount (0 if quest not complete)
        """
        if self.is_quest_complete():
            return QUEST_COMPLETION_COHERENCE_BONUS
        return 0

    def reset(self) -> None:
        """Reset quest state (for new game or floor transition if needed).

        Note: Currently quests persist across floors, so this is mainly
        for future extensibility or testing.
        """
        self.quest_active = False
        self.completed_npcs.clear()

    def to_dict(self) -> dict:
        """Serialize quest state to dictionary for save/load.

        Returns:
            Dictionary containing quest state
        """
        return {
            "quest_active": self.quest_active,
            "completed_npcs": list(self.completed_npcs),
        }

    @classmethod
    def from_dict(cls, data: dict) -> QuestManager:
        """Deserialize quest state from dictionary.

        Args:
            data: Dictionary containing quest state from to_dict()

        Returns:
            New QuestManager instance with loaded state
        """
        manager = cls()
        manager.quest_active = data.get("quest_active", False)
        manager.completed_npcs = set(data.get("completed_npcs", []))
        return manager
