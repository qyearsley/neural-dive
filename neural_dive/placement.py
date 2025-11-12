"""
Entity placement strategies for Neural Dive.

This module provides unified entity placement logic to eliminate code duplication
across NPC, terminal, and stairs generation.
"""

from __future__ import annotations

from collections.abc import Callable
import random


class EntityPlacementStrategy:
    """
    Universal entity placement strategy.

    Handles three placement modes:
    1. Level-based: Use positions from level layout data
    2. Random: Generate random valid positions
    3. Default: Use predefined fallback positions

    This eliminates ~150 lines of duplicate placement code.
    """

    def __init__(
        self,
        game_map: list[list[str]],
        random_mode: bool,
        rng: random.Random,
        map_width: int,
        map_height: int,
    ):
        """
        Initialize placement strategy.

        Args:
            game_map: 2D map array for collision detection
            random_mode: Whether to use random placement
            rng: Random number generator for reproducibility
            map_width: Map width for random placement
            map_height: Map height for random placement
        """
        self.game_map = game_map
        self.random_mode = random_mode
        self.rng = rng
        self.map_width = map_width
        self.map_height = map_height

    def place_entities(
        self,
        level_positions: list[tuple[int, int]] | None,
        default_positions: list[tuple[int, int]] | None = None,
        num_attempts: int = 50,
        min_distance_from: tuple[int, int] | None = None,
        min_distance: int = 0,
        x_range: tuple[int, int] | None = None,
        y_range: tuple[int, int] | None = None,
        count: int | None = None,
        validation_fn: Callable[[int, int], bool] | None = None,
    ) -> list[tuple[int, int]]:
        """
        Place entities using priority-based strategy.

        Priority order:
        1. Level layout positions (if provided)
        2. Random placement (if random_mode enabled)
        3. Default positions (if provided)

        Args:
            level_positions: Positions from level layout data
            default_positions: Fallback positions if no level data
            num_attempts: Max attempts for random placement
            min_distance_from: Position to maintain distance from (e.g., player)
            min_distance: Minimum distance to maintain
            x_range: (min, max) X coordinate range for random placement
            y_range: (min, max) Y coordinate range for random placement
            count: Number of entities to place (for random mode)
            validation_fn: Custom validation function for positions

        Returns:
            List of (x, y) positions for entities
        """
        # Priority 1: Use level layout positions
        if level_positions:
            return level_positions

        # Priority 2: Random placement
        if self.random_mode:
            if count is None:
                count = len(default_positions) if default_positions else 1

            return self._place_random(
                count=count,
                num_attempts=num_attempts,
                min_distance_from=min_distance_from,
                min_distance=min_distance,
                x_range=x_range,
                y_range=y_range,
                validation_fn=validation_fn,
            )

        # Priority 3: Use default positions
        if default_positions:
            return default_positions

        # No positions available
        return []

    def _place_random(
        self,
        count: int,
        num_attempts: int,
        min_distance_from: tuple[int, int] | None,
        min_distance: int,
        x_range: tuple[int, int] | None,
        y_range: tuple[int, int] | None,
        validation_fn: Callable[[int, int], bool] | None,
    ) -> list[tuple[int, int]]:
        """
        Generate random valid positions.

        Args:
            count: Number of positions to generate
            num_attempts: Max attempts per position
            min_distance_from: Position to maintain distance from
            min_distance: Minimum distance to maintain
            x_range: (min, max) X coordinate range
            y_range: (min, max) Y coordinate range
            validation_fn: Custom validation function

        Returns:
            List of valid (x, y) positions
        """
        positions = []

        # Default ranges if not specified
        if x_range is None:
            x_range = (2, self.map_width - 2)
        if y_range is None:
            y_range = (2, self.map_height - 2)

        for _ in range(count):
            for _ in range(num_attempts):
                x = self.rng.randint(x_range[0], x_range[1])
                y = self.rng.randint(y_range[0], y_range[1])

                if self._is_valid_position(x, y, min_distance_from, min_distance, validation_fn):
                    positions.append((x, y))
                    break

        return positions

    def _is_valid_position(
        self,
        x: int,
        y: int,
        min_distance_from: tuple[int, int] | None,
        min_distance: int,
        validation_fn: Callable[[int, int], bool] | None,
    ) -> bool:
        """
        Check if a position is valid for entity placement.

        Args:
            x: X coordinate
            y: Y coordinate
            min_distance_from: Position to maintain distance from
            min_distance: Minimum distance to maintain
            validation_fn: Custom validation function

        Returns:
            True if position is valid
        """
        # Check bounds
        if y < 0 or y >= len(self.game_map):
            return False
        if x < 0 or x >= len(self.game_map[0]):
            return False

        # Check walkable (not a wall)
        if self.game_map[y][x] == "#":
            return False

        # Check minimum distance
        if min_distance_from and min_distance > 0:
            dx = abs(x - min_distance_from[0])
            dy = abs(y - min_distance_from[1])
            if dx <= min_distance and dy <= min_distance:
                return False

        # Custom validation
        if validation_fn:
            return validation_fn(x, y)

        return True
