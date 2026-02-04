"""Movement and collision detection for Neural Dive.

This module provides the MovementController class which handles player
movement logic and collision detection.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from neural_dive.entities import Entity, Stairs
    from neural_dive.items import ItemPickup
    from neural_dive.managers.player_manager import PlayerManager


@dataclass
class MoveResult:
    """Result of a movement attempt.

    Attributes:
        success: Whether the movement was successful
        message: Message to display to the player
        old_position: Player's previous position (only set if movement succeeded)
    """

    success: bool
    message: str
    old_position: tuple[int, int] | None = None


class MovementController:
    """Handles player movement and collision detection.

    This class is responsible for:
    - Checking if positions are walkable
    - Moving the player
    - Handling automatic item pickup
    - Showing stairs hints

    The controller is stateless and works with the entities and managers
    passed to it.
    """

    @staticmethod
    def is_walkable(x: int, y: int, game_map: list[list[str]]) -> bool:
        """Check if a position is walkable.

        Args:
            x: X coordinate to check
            y: Y coordinate to check
            game_map: The game map grid

        Returns:
            True if the position can be walked on, False otherwise
        """
        # Check bounds
        if y < 0 or y >= len(game_map):
            return False
        if x < 0 or x >= len(game_map[0]):
            return False

        # Check for walls
        return bool(game_map[y][x] != "#")

    def move_player(
        self,
        player: Entity,
        dx: int,
        dy: int,
        game_map: list[list[str]],
        item_pickups: list[ItemPickup],
        stairs: list[Stairs],
        player_manager: PlayerManager,
        is_in_conversation: bool,
    ) -> MoveResult:
        """Attempt to move the player by a delta.

        Args:
            player: The player entity
            dx: Change in x position
            dy: Change in y position
            game_map: The game map grid
            item_pickups: List of item pickups (modified in place if items collected)
            stairs: List of stairs on current floor
            player_manager: PlayerManager for inventory operations
            is_in_conversation: Whether player is currently in a conversation

        Returns:
            MoveResult with success status, message, and old position if moved
        """
        # Can't move during conversation
        if is_in_conversation:
            return MoveResult(
                success=False,
                message="You're in a conversation. Answer or press ESC to exit.",
                old_position=None,
            )

        new_x = player.x + dx
        new_y = player.y + dy

        # Try to move
        if not self.is_walkable(new_x, new_y, game_map):
            return MoveResult(
                success=False,
                message="Blocked by firewall!",
                old_position=None,
            )

        # Movement is valid - update position
        old_pos = (player.x, player.y)
        player.x = new_x
        player.y = new_y

        # Check for item pickups
        for pickup in item_pickups[:]:  # Use slice to allow removal during iteration
            if player.x == pickup.x and player.y == pickup.y:
                # Try to add to inventory
                if player_manager.add_item(pickup.item):
                    item_pickups.remove(pickup)
                    return MoveResult(
                        success=True,
                        message=f"Picked up {pickup.item.name}!",
                        old_position=old_pos,
                    )
                else:
                    return MoveResult(
                        success=True,
                        message="Inventory full!",
                        old_position=old_pos,
                    )

        # Check if standing on stairs and show hint
        for stair in stairs:
            if player.x == stair.x and player.y == stair.y:
                direction = "up" if stair.direction == "up" else "down"
                return MoveResult(
                    success=True,
                    message=f"Standing on stairs {direction}. Press Space or >/< to use.",
                    old_position=old_pos,
                )

        # Normal movement
        return MoveResult(
            success=True,
            message="",
            old_position=old_pos,
        )
