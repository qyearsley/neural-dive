"""
Floor management for Neural Dive.

This module provides the FloorManager class which handles floor generation,
progression, and completion checking.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from neural_dive.config import (
    DEFAULT_MAP_HEIGHT,
    DEFAULT_MAP_WIDTH,
    MAX_FLOORS,
    PLAYER_START_X,
    PLAYER_START_Y,
)
from neural_dive.map_generation import create_map

if TYPE_CHECKING:
    from neural_dive.entities import Entity


class FloorManager:
    """
    Manages floor state and progression.

    The FloorManager encapsulates all floor-related logic including:
    - Floor generation (map creation)
    - Floor transitions (using stairs)
    - Floor completion tracking
    - Player positioning on floor entry

    Attributes:
        current_floor: Current floor number (1-indexed)
        max_floors: Maximum number of floors
        game_map: 2D map array for current floor
        map_width: Current map width
        map_height: Current map height
        seed: Random seed for map generation
    """

    def __init__(
        self,
        max_floors: int = MAX_FLOORS,
        map_width: int = DEFAULT_MAP_WIDTH,
        map_height: int = DEFAULT_MAP_HEIGHT,
        seed: int | None = None,
        level_data: dict | None = None,
        floor_requirements: dict[int, set[str]] | None = None,
    ):
        """
        Initialize FloorManager.

        Args:
            max_floors: Maximum number of floors
            map_width: Default map width
            map_height: Default map height
            seed: Random seed for reproducibility
            level_data: Dictionary of parsed level data (PARSED_LEVELS)
            floor_requirements: Dictionary mapping floor numbers to required NPC names
        """
        self.current_floor = 1
        self.max_floors = max_floors
        self.map_width = map_width
        self.map_height = map_height
        self.seed = seed
        self.level_data = level_data if level_data is not None else {}
        self.floor_requirements = floor_requirements if floor_requirements is not None else {}

        # Initialize map for first floor
        self.game_map = self._create_map_for_floor(1)

    def _create_map_for_floor(self, floor: int) -> list[list[str]]:
        """
        Create map for a specific floor.

        Args:
            floor: Floor number

        Returns:
            2D map array
        """
        level_data = self.level_data.get(floor)

        if level_data and "tiles" in level_data:
            # Use predefined map from level data
            game_map: list[list[str]] = level_data["tiles"]
            self.map_height = len(game_map)
            self.map_width = len(game_map[0]) if game_map else 0
            return game_map
        else:
            # Generate procedural map
            return create_map(self.map_width, self.map_height, floor, seed=self.seed)

    def generate_floor(self, floor: int, player: Entity) -> tuple[int, int]:
        """
        Generate a new floor and return player start position.

        Args:
            floor: Floor number to generate
            player: Player entity (to update position)

        Returns:
            Tuple of (player_x, player_y) start position
        """
        self.current_floor = floor
        self.game_map = self._create_map_for_floor(floor)

        # Get player start position from level data
        level_data = self.level_data.get(floor)
        if level_data and "player_start" in level_data:
            player_start = level_data["player_start"]
            if player_start:
                player.x, player.y = player_start
                return player.x, player.y

        # Default start position
        player.x, player.y = PLAYER_START_X, PLAYER_START_Y
        return player.x, player.y

    def can_use_stairs_down(self) -> bool:
        """
        Check if player can use stairs to go down.

        Returns:
            True if not on bottom floor
        """
        return self.current_floor < self.max_floors

    def can_use_stairs_up(self) -> bool:
        """
        Check if player can use stairs to go up.

        Returns:
            True if not on top floor
        """
        return self.current_floor > 1

    def move_to_next_floor(self, player: Entity) -> tuple[int, int]:
        """
        Move to the next floor down.

        Args:
            player: Player entity

        Returns:
            New player position (x, y)
        """
        if not self.can_use_stairs_down():
            return player.x, player.y

        return self.generate_floor(self.current_floor + 1, player)

    def move_to_previous_floor(self, player: Entity) -> tuple[int, int]:
        """
        Move to the previous floor up.

        Args:
            player: Player entity

        Returns:
            New player position (x, y)
        """
        if not self.can_use_stairs_up():
            return player.x, player.y

        return self.generate_floor(self.current_floor - 1, player)

    def is_floor_complete(self, npcs_completed: set[str], npc_data: dict) -> bool:
        """
        Check if the current floor is complete.

        A floor is complete when all required NPCs have been defeated/completed.

        Args:
            npcs_completed: Set of completed NPC names
            npc_data: Dictionary of all NPC data

        Returns:
            True if floor completion requirements are met
        """
        # Get required NPCs for this floor from dynamic requirements
        required_npcs = self.floor_requirements.get(self.current_floor, set())

        # Check if all required NPCs have been completed
        return all(npc_name in npcs_completed for npc_name in required_npcs)

    def is_final_floor(self) -> bool:
        """
        Check if on the final floor.

        Returns:
            True if on bottom floor
        """
        return self.current_floor == self.max_floors

    def to_dict(self) -> dict:
        """
        Serialize floor manager state to dictionary.

        Returns:
            Dictionary containing floor state
        """
        return {
            "current_floor": self.current_floor,
            "max_floors": self.max_floors,
            "map_width": self.map_width,
            "map_height": self.map_height,
        }

    @classmethod
    def from_dict(
        cls, data: dict, seed: int | None = None, level_data: dict | None = None
    ) -> FloorManager:
        """
        Create FloorManager from serialized dictionary.

        Args:
            data: Serialized floor manager state
            seed: Random seed
            level_data: Dictionary of parsed level data

        Returns:
            Restored FloorManager instance
        """
        manager = cls(
            max_floors=data.get("max_floors", MAX_FLOORS),
            map_width=data.get("map_width", DEFAULT_MAP_WIDTH),
            map_height=data.get("map_height", DEFAULT_MAP_HEIGHT),
            seed=seed,
            level_data=level_data,
        )

        # Restore current floor (will regenerate map)
        current_floor = data.get("current_floor", 1)
        if current_floor != 1:
            # Create dummy player for position (will be overridden)
            from neural_dive.entities import Entity

            dummy_player = Entity(PLAYER_START_X, PLAYER_START_Y, "@", "cyan", "Player")
            manager.generate_floor(current_floor, dummy_player)

        return manager
