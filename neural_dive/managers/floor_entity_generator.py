"""Floor entity generator for Neural Dive.

This module provides the FloorEntityGenerator class which handles generation
of all non-NPC entities (terminals, stairs, item pickups) for a given floor.
"""

from __future__ import annotations

import random
from typing import TYPE_CHECKING

from neural_dive.config import (
    NPC_PLACEMENT_ATTEMPTS,
    STAIRS_DOWN_DEFAULT_X,
    STAIRS_DOWN_DEFAULT_Y,
    STAIRS_UP_DEFAULT_X,
    STAIRS_UP_DEFAULT_Y,
)
from neural_dive.data.levels import ZONE_TERMINALS
from neural_dive.entities import InfoTerminal, Stairs
from neural_dive.placement import EntityPlacementStrategy

if TYPE_CHECKING:
    from neural_dive.items import ItemPickup


class FloorEntityGenerator:
    """Generates non-NPC entities for floor transitions.

    This class handles generation of terminals, stairs, and item pickups
    for a given floor. It uses level data when available and falls back
    to procedural placement strategies.

    Attributes:
        level_data: Dictionary mapping floor numbers to level layout data
        snippets: Dictionary of code snippets available for pickup
        rand: Random number generator for deterministic placement
    """

    def __init__(self, level_data: dict, snippets: dict, rand: random.Random):
        """Initialize FloorEntityGenerator.

        Args:
            level_data: Level layouts and entity positions per floor
            snippets: Available code snippets for item generation
            rand: Random number generator for placement
        """
        self.level_data = level_data
        self.snippets = snippets
        self.rand = rand

    def generate_all_entities(
        self,
        floor: int,
        max_floors: int,
        game_map: list[list[str]],
        map_width: int,
        map_height: int,
        player_pos: tuple[int, int],
        random_placement: bool,
    ) -> tuple[list[Stairs], list[InfoTerminal], list[ItemPickup]]:
        """Generate all entities for a floor.

        Args:
            floor: Current floor number
            max_floors: Maximum number of floors in game
            game_map: Current floor's map grid
            map_width: Width of the map
            map_height: Height of the map
            player_pos: Player's (x, y) position
            random_placement: Whether to use random placement

        Returns:
            Tuple of (stairs, terminals, item_pickups)
        """
        # Generate each entity type
        terminals = self._generate_terminals(floor)
        stairs = self._generate_stairs(
            floor, max_floors, game_map, map_width, map_height, player_pos, random_placement
        )
        item_pickups = self._generate_items(
            floor, game_map, map_width, map_height, player_pos, random_placement
        )

        return stairs, terminals, item_pickups

    def _generate_terminals(self, floor: int) -> list[InfoTerminal]:
        """Generate and place info terminals for the current floor.

        Args:
            floor: Current floor number

        Returns:
            List of InfoTerminal entities
        """
        terminals: list[InfoTerminal] = []
        level_data = self.level_data.get(floor)

        if not level_data or "terminal_positions" not in level_data:
            # No terminals defined for this floor
            return terminals

        terminal_positions = list(level_data["terminal_positions"])  # Copy to avoid mutation
        zone_terminals = ZONE_TERMINALS.get(floor, {})

        # Create zone terminals based on labels in the level
        for _zone_name, zone_data in zone_terminals.items():
            if terminal_positions:
                # Use next available terminal position
                x, y = terminal_positions.pop(0)
                title = zone_data["title"]
                content = zone_data["content"]
                # Type assertions for mypy
                assert isinstance(title, str)
                assert isinstance(content, list)
                terminal = InfoTerminal(x, y, title, content)
                terminals.append(terminal)

        return terminals

    def _generate_stairs(
        self,
        floor: int,
        max_floors: int,
        game_map: list[list[str]],
        map_width: int,
        map_height: int,
        player_pos: tuple[int, int],
        random_placement: bool,
    ) -> list[Stairs]:
        """Generate stairs up and/or down based on current floor.

        Args:
            floor: Current floor number
            max_floors: Maximum number of floors
            game_map: Current floor's map grid
            map_width: Width of the map
            map_height: Height of the map
            player_pos: Player's (x, y) position
            random_placement: Whether to use random placement

        Returns:
            List of Stairs entities
        """
        stairs: list[Stairs] = []
        level_data = self.level_data.get(floor)

        if level_data:
            # Use stairs from level layout
            stairs_down_position = level_data.get("stairs_down")
            stairs_up_position = level_data.get("stairs_up")

            # Add stairs down
            if floor < max_floors and stairs_down_position:
                stairs.extend(self._add_stairs_from_positions(stairs_down_position, "down"))

            # Add stairs up
            if floor > 1 and stairs_up_position:
                stairs.extend(self._add_stairs_from_positions(stairs_up_position, "up"))
        else:
            # Fallback to placement strategy
            strategy = EntityPlacementStrategy(
                game_map=game_map,
                random_mode=random_placement,
                rng=self.rand,
                map_width=map_width,
                map_height=map_height,
            )

            player_x, player_y = player_pos

            # Stairs down (if not on bottom floor)
            if floor < max_floors:
                down_positions = strategy.place_entities(
                    level_positions=None,
                    default_positions=[(STAIRS_DOWN_DEFAULT_X, STAIRS_DOWN_DEFAULT_Y)],
                    num_attempts=NPC_PLACEMENT_ATTEMPTS,
                    x_range=(map_width // 2, map_width - 2),
                    y_range=(map_height // 2, map_height - 2),
                    count=1,
                    validation_fn=lambda x, y: abs(x - player_x) > 10,
                )
                if down_positions:
                    x, y = down_positions[0]
                    stairs.append(Stairs(x, y, "down"))

            # Stairs up (if not on top floor)
            if floor > 1:
                up_positions = strategy.place_entities(
                    level_positions=None,
                    default_positions=[(STAIRS_UP_DEFAULT_X, STAIRS_UP_DEFAULT_Y)],
                    num_attempts=NPC_PLACEMENT_ATTEMPTS,
                    x_range=(2, map_width // 3),
                    y_range=(2, map_height // 3),
                    count=1,
                )
                if up_positions:
                    x, y = up_positions[0]
                    stairs.append(Stairs(x, y, "up"))

        return stairs

    def _add_stairs_from_positions(
        self, position_data: tuple[int, int] | list[tuple[int, int]], direction: str
    ) -> list[Stairs]:
        """Add stairs from position data.

        Args:
            position_data: Either a single (x, y) tuple or list of (x, y) tuples
            direction: "up" or "down"

        Returns:
            List of Stairs entities
        """
        stairs: list[Stairs] = []

        if isinstance(position_data, tuple):
            # Single position
            x, y = position_data
            stairs.append(Stairs(x, y, direction))
        else:
            # List of positions
            for x, y in position_data:
                stairs.append(Stairs(x, y, direction))

        return stairs

    def _generate_items(
        self,
        floor: int,
        game_map: list[list[str]],
        map_width: int,
        map_height: int,
        player_pos: tuple[int, int],
        random_placement: bool,
    ) -> list[ItemPickup]:
        """Generate and place item pickups for the current floor.

        Args:
            floor: Current floor number
            game_map: Current floor's map grid
            map_width: Width of the map
            map_height: Height of the map
            player_pos: Player's (x, y) position
            random_placement: Whether to use random placement

        Returns:
            List of ItemPickup entities
        """
        from neural_dive.items import CodeSnippet, HintToken, ItemPickup

        item_pickups: list[ItemPickup] = []

        strategy = EntityPlacementStrategy(
            game_map=game_map,
            random_mode=random_placement,
            rng=self.rand,
            map_width=map_width,
            map_height=map_height,
        )

        player_x, player_y = player_pos

        # Number of items per floor (increases with floor difficulty)
        num_hint_tokens = 1 + (floor // 2)  # 1 on floor 1, 2 on floors 2-3
        num_snippets = 1 if floor >= 2 else 0  # 1 snippet starting on floor 2

        # Place hint tokens
        hint_positions = strategy.place_entities(
            level_positions=None,
            default_positions=[],
            num_attempts=50,
            x_range=(3, map_width - 3),
            y_range=(3, map_height - 3),
            count=num_hint_tokens,
            validation_fn=lambda x, y: abs(x - player_x) + abs(y - player_y) > 8,
        )

        for x, y in hint_positions:
            hint_item = HintToken()
            pickup = ItemPickup(x, y, hint_item)
            item_pickups.append(pickup)

        # Place code snippets
        if num_snippets > 0 and self.snippets:
            snippet_positions = strategy.place_entities(
                level_positions=None,
                default_positions=[],
                num_attempts=50,
                x_range=(3, map_width - 3),
                y_range=(3, map_height - 3),
                count=num_snippets,
                validation_fn=lambda x, y: abs(x - player_x) + abs(y - player_y) > 8,
            )

            # Pick random snippets from available ones
            available_snippet_ids = list(self.snippets.keys())
            for x, y in snippet_positions:
                if available_snippet_ids:
                    snippet_id = self.rand.choice(available_snippet_ids)
                    snippet_data = self.snippets[snippet_id]
                    snippet_item = CodeSnippet(
                        name=snippet_data["name"],
                        topic=snippet_data["topic"],
                        content=snippet_data["content"],
                    )
                    pickup = ItemPickup(x, y, snippet_item)
                    item_pickups.append(pickup)

        return item_pickups
