"""NPC wandering AI.

NPCs alternate between standing still and drifting around their home tile. This
module owns that behaviour and the record of where NPCs were on the previous
frame, which the renderer needs in order to erase them.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from neural_dive.config import (
    NPC_IDLE_TICKS_MAX,
    NPC_IDLE_TICKS_MIN,
    NPC_MOVEMENT_SPEEDS,
    NPC_WANDER_ENABLED,
    NPC_WANDER_RADIUS,
    NPC_WANDER_TICKS_MAX,
    NPC_WANDER_TICKS_MIN,
)

if TYPE_CHECKING:
    import random

    from neural_dive.entities import Entity


class NPCMovement:
    """Moves NPCs around and records where they came from.

    Attributes:
        old_positions: Tiles NPCs vacated since the renderer last cleared them,
            keyed by NPC name. The renderer repaints these and then clears the
            dict; without it NPCs would leave a trail.
    """

    def __init__(self, rng: random.Random):
        """
        Initialize movement.

        Args:
            rng: Random number generator instance
        """
        self.rng = rng
        self.old_positions: dict[str, tuple[int, int]] = {}

    def update(
        self,
        npcs: list[Entity],
        game_map: list[list[str]],
        player_pos: tuple[int, int],
        is_conversation_active: bool,
    ) -> None:
        """
        Advance the wandering state of every NPC on the floor.

        NPCs alternate between idle and wander states. During wander state,
        they move slowly in random directions. Different NPC types have different
        movement speeds and behaviors.

        Args:
            npcs: NPCs on the current floor
            game_map: 2D map array for collision detection
            player_pos: (x, y) position of player
            is_conversation_active: Whether a conversation is active (freezes NPCs)
        """
        if not NPC_WANDER_ENABLED:
            return

        # Freeze NPC movement during conversations
        if is_conversation_active:
            return

        player_x, player_y = player_pos

        for npc in npcs:
            # Decrement move cooldown
            if npc.move_cooldown > 0:
                npc.move_cooldown -= 1

            # Decrement state timer
            npc.wander_ticks_remaining -= 1

            # Check if need to switch states
            if npc.wander_ticks_remaining <= 0:
                if npc.wander_state == "idle":
                    npc.wander_state = "wander"
                    npc.wander_ticks_remaining = self.rng.randint(
                        NPC_WANDER_TICKS_MIN, NPC_WANDER_TICKS_MAX
                    )
                else:
                    npc.wander_state = "idle"
                    npc.wander_ticks_remaining = self.rng.randint(
                        NPC_IDLE_TICKS_MIN, NPC_IDLE_TICKS_MAX
                    )

            # Move if in wander state and cooldown expired
            if npc.wander_state == "wander" and npc.move_cooldown <= 0:
                self._move_npc(npc, npcs, game_map, player_x, player_y)

    def _move_npc(
        self,
        npc: Entity,
        npcs: list[Entity],
        game_map: list[list[str]],
        player_x: int,
        player_y: int,
    ) -> None:
        """
        Move a single NPC one tile, if the destination is free.

        Args:
            npc: The NPC entity to move
            npcs: All NPCs on the floor, for collision checks
            game_map: 2D map array for collision detection
            player_x: Player X position
            player_y: Player Y position
        """
        # Get movement speed for this NPC type
        npc_type = npc.npc_type or "specialist"
        npc.move_cooldown = NPC_MOVEMENT_SPEEDS.get(npc_type, 2)

        # If too far from home, head back; otherwise drift randomly
        if npc.should_return_home(NPC_WANDER_RADIUS):
            dx, dy = self._home_direction(npc)
        else:
            dx = self.rng.choice([-1, 0, 1])
            dy = self.rng.choice([-1, 0, 1])

        new_x = npc.x + dx
        new_y = npc.y + dy

        if self._is_valid_position(new_x, new_y, npcs, game_map, player_x, player_y, npc):
            # Track old position so the renderer can erase the NPC's last tile
            self.old_positions[npc.name] = (npc.x, npc.y)
            npc.x = new_x
            npc.y = new_y

    def _home_direction(self, npc: Entity) -> tuple[int, int]:
        """
        Calculate direction towards NPC's home position.

        Args:
            npc: The NPC entity

        Returns:
            Tuple of (dx, dy) movement direction
        """
        dx = 0
        dy = 0

        if npc.x < npc.home_x:
            dx = 1
        elif npc.x > npc.home_x:
            dx = -1

        if npc.y < npc.home_y:
            dy = 1
        elif npc.y > npc.home_y:
            dy = -1

        # Sometimes move diagonally, sometimes along one axis only
        if self.rng.random() < 0.5 and dx != 0:
            dy = 0
        elif dy != 0:
            dx = 0

        return dx, dy

    def _is_valid_position(
        self,
        x: int,
        y: int,
        npcs: list[Entity],
        game_map: list[list[str]],
        player_x: int,
        player_y: int,
        moving_npc: Entity,
    ) -> bool:
        """
        Check if a position is valid for NPC movement.

        Args:
            x: Target X position
            y: Target Y position
            npcs: All NPCs on the floor
            game_map: 2D map array
            player_x: Player X position
            player_y: Player Y position
            moving_npc: The NPC that is moving

        Returns:
            True if position is valid
        """
        # Check bounds
        if y < 0 or y >= len(game_map) or x < 0 or x >= len(game_map[0]):
            return False

        # Check walkable
        if game_map[y][x] == "#":
            return False

        # Check if position is occupied by player
        if x == player_x and y == player_y:
            return False

        # Check if position is occupied by another NPC
        return not any(other is not moving_npc and other.x == x and other.y == y for other in npcs)
