"""NPC spawning.

Turns NPC definitions into placed entities for a floor, either at the positions
the level layout specifies or at random walkable tiles when there is no layout.
Also keeps the record of every NPC created so far, which is what the save file
persists.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from neural_dive.config import NPC_MIN_DISTANCE_FROM_PLAYER, NPC_PLACEMENT_ATTEMPTS
from neural_dive.entities import Entity

if TYPE_CHECKING:
    import random


class NPCSpawner:
    """Creates the NPC entities for a floor.

    Attributes:
        all_npcs: Every NPC created so far, across all floors. The save file
            persists this, so an NPC keeps its position and wander state after
            the player leaves and returns to a floor.
    """

    def __init__(self, npc_data: dict, rng: random.Random, level_data: dict | None = None):
        """
        Initialize the spawner.

        Args:
            npc_data: Dictionary of NPC definitions
            rng: Random number generator instance
            level_data: Dictionary of parsed level data (PARSED_LEVELS)
        """
        self.npc_data = npc_data
        self.rng = rng
        self.level_data = level_data if level_data is not None else {}
        self.all_npcs: list[Entity] = []

    def generate_for_floor(
        self,
        floor: int,
        game_map: list[list[str]],
        player_pos: tuple[int, int],
        random_placement: bool,
        map_width: int,
        map_height: int,
    ) -> list[Entity]:
        """
        Create the NPCs that belong on a floor.

        Args:
            floor: Floor number to generate NPCs for
            game_map: 2D map array for collision detection
            player_pos: (x, y) position of player
            random_placement: Whether to use random placement (fallback mode)
            map_width: Map width for random placement
            map_height: Map height for random placement

        Returns:
            The NPCs placed on this floor. Empty if the floor has neither a
            layout nor random placement enabled.
        """
        floor_npcs = [
            (npc_name, npc_info)
            for npc_name, npc_info in self.npc_data.items()
            if npc_info["floor"] == floor
        ]

        level_data = self.level_data.get(floor)
        if level_data and "npc_positions" in level_data:
            return self._from_level_data(floor_npcs, level_data)
        if random_placement:
            return self._randomly_placed(floor_npcs, game_map, player_pos, map_width, map_height)
        return []

    def _from_level_data(
        self, floor_npcs: list[tuple[str, dict]], level_data: dict
    ) -> list[Entity]:
        """Place NPCs at the positions the level layout gives for their character."""
        # Copy each char's position list. The loop below pops from these to give
        # two NPCs sharing a char different spots, and level_data is long-lived
        # and shared -- popping from it directly would drain the floor's
        # positions permanently, so generating the same floor a second time
        # (which is what loading a save does) would place no NPCs at all.
        positions_by_char = {
            char: list(positions) for char, positions in level_data["npc_positions"].items()
        }

        placed: list[Entity] = []
        for npc_name, npc_info in floor_npcs:
            positions = positions_by_char.get(npc_info["char"], [])
            if positions:
                x, y = positions.pop(0)
                placed.append(self._build(npc_name, npc_info, x, y))
        return placed

    def _randomly_placed(
        self,
        floor_npcs: list[tuple[str, dict]],
        game_map: list[list[str]],
        player_pos: tuple[int, int],
        map_width: int,
        map_height: int,
    ) -> list[Entity]:
        """Place NPCs on random walkable tiles, keeping clear of the player."""
        from neural_dive.placement import EntityPlacementStrategy

        strategy = EntityPlacementStrategy(
            game_map=game_map,
            random_mode=True,
            rng=self.rng,
            map_width=map_width,
            map_height=map_height,
        )

        placed: list[Entity] = []
        for npc_name, npc_info in floor_npcs:
            positions = strategy.place_entities(
                level_positions=None,
                default_positions=None,
                num_attempts=NPC_PLACEMENT_ATTEMPTS,
                min_distance_from=player_pos,
                min_distance=NPC_MIN_DISTANCE_FROM_PLAYER,
                x_range=(10, map_width - 2),
                y_range=(5, map_height - 2),
                count=1,
            )
            if positions:
                x, y = positions[0]
                placed.append(self._build(npc_name, npc_info, x, y))
        return placed

    def _build(self, npc_name: str, npc_info: dict, x: int, y: int) -> Entity:
        """Create an NPC entity and record it in ``all_npcs`` if it is new."""
        npc = Entity(
            x,
            y,
            npc_info["char"],
            npc_info["color"],
            npc_name,
            npc_type=npc_info.get("npc_type", "specialist"),
        )
        if not any(known.name == npc_name for known in self.all_npcs):
            self.all_npcs.append(npc)
        return npc
