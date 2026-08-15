"""NPC opinion tracking.

How each NPC feels about the player. Answering an NPC's question correctly
raises its opinion, getting one wrong lowers it.
"""

from __future__ import annotations


class NPCRelationships:
    """Tracks each NPC's opinion of the player.

    Attributes:
        opinions: Opinion score per NPC name. An NPC with no entry is neutral.
    """

    def __init__(self) -> None:
        """Initialize with no opinions recorded."""
        self.opinions: dict[str, int] = {}

    def get_opinion(self, npc_name: str) -> int:
        """
        Get NPC's opinion of the player.

        Args:
            npc_name: Name of the NPC

        Returns:
            Opinion value (0 if not tracked)
        """
        return self.opinions.get(npc_name, 0)

    def update_opinion(self, npc_name: str, delta: int) -> None:
        """
        Update NPC's opinion of the player.

        An NPC that has no opinion yet starts from neutral, so callers don't
        need to seed the entry first.

        Args:
            npc_name: Name of the NPC
            delta: Change in opinion (positive or negative)
        """
        self.opinions[npc_name] = self.opinions.get(npc_name, 0) + delta
