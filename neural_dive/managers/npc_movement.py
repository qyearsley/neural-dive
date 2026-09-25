"""NPC wandering AI.

NPCs alternate between standing still and drifting around their home tile.
Enemies the player has not beaten break off to chase the player when close. This
module owns that behaviour and the record of where NPCs were on the previous
frame, which the renderer needs in order to erase them.
"""

from __future__ import annotations

from collections import deque
from typing import TYPE_CHECKING

from neural_dive.config import (
    ENEMY_CHASE_RADIUS,
    ENEMY_CHASE_SPEED,
    ENEMY_GIVE_UP_RADIUS,
    NPC_IDLE_TICKS_MAX,
    NPC_IDLE_TICKS_MIN,
    NPC_MOVEMENT_SPEEDS,
    NPC_WANDER_ENABLED,
    NPC_WANDER_RADIUS,
    NPC_WANDER_TICKS_MAX,
    NPC_WANDER_TICKS_MIN,
)

if TYPE_CHECKING:
    from collections.abc import Collection
    import random

    from neural_dive.entities import Entity

# Orthogonal moves first, so a path prefers straight lines over zigzags
_STEPS = ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1))


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
        beaten: Collection[str] = (),
    ) -> None:
        """
        Advance the wandering state of every NPC on the floor.

        NPCs alternate between idle and wander states. During wander state,
        they move slowly in random directions. Different NPC types have different
        movement speeds and behaviors. An enemy that is chasing (see
        :meth:`is_chasing`) steps toward the player instead.

        Args:
            npcs: NPCs on the current floor
            game_map: 2D map array for collision detection
            player_pos: (x, y) position of player
            is_conversation_active: Whether a conversation is active (freezes NPCs)
            beaten: Names of NPCs whose conversation is completed; they never chase
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
            if npc.stun_ticks > 0:
                npc.stun_ticks -= 1

            npc.chasing = self.is_chasing(npc, player_pos, beaten)
            if npc.chasing:
                if npc.move_cooldown <= 0:
                    self._chase(npc, npcs, game_map, player_x, player_y)
                continue

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

    @staticmethod
    def is_chasing(npc: Entity, player_pos: tuple[int, int], beaten: Collection[str]) -> bool:
        """Whether an NPC is currently pursuing the player.

        Only an unbeaten, unstunned enemy chases. It starts within
        ENEMY_CHASE_RADIUS tiles and, once started, keeps going out to
        ENEMY_GIVE_UP_RADIUS. Distance is Chebyshev, the measure interaction
        uses.
        """
        if npc.npc_type != "enemy" or npc.name in beaten or npc.stun_ticks > 0:
            return False
        distance = max(abs(npc.x - player_pos[0]), abs(npc.y - player_pos[1]))
        return distance <= (ENEMY_GIVE_UP_RADIUS if npc.chasing else ENEMY_CHASE_RADIUS)

    def _chase(
        self,
        npc: Entity,
        npcs: list[Entity],
        game_map: list[list[str]],
        player_x: int,
        player_y: int,
    ) -> None:
        """Step an enemy one tile along the shortest path to the player.

        A breadth-first search rather than a straight line: layouts have rooms,
        and an enemy heading straight at the player gets stuck on the wall of a
        room whose door is on the far side. An enemy already next to the player
        stays put: contact is the ambush.
        """
        npc.move_cooldown = ENEMY_CHASE_SPEED
        step = self._first_step_toward(npc, npcs, game_map, player_x, player_y)
        if step is not None:
            self.old_positions[npc.name] = (npc.x, npc.y)
            npc.x, npc.y = step

    def _first_step_toward(
        self,
        npc: Entity,
        npcs: list[Entity],
        game_map: list[list[str]],
        player_x: int,
        player_y: int,
    ) -> tuple[int, int] | None:
        """The first tile of a shortest path to any tile next to the player.

        Returns None if the NPC is already next to the player or no path exists.
        """
        start = (npc.x, npc.y)

        def next_to_player(tile: tuple[int, int]) -> bool:
            return max(abs(tile[0] - player_x), abs(tile[1] - player_y)) <= 1

        if next_to_player(start):
            return None

        # Each reached tile maps to the first step taken to get there
        first_step: dict[tuple[int, int], tuple[int, int]] = {}
        queue: deque[tuple[int, int]] = deque([start])
        while queue:
            x, y = queue.popleft()
            for dx, dy in _STEPS:
                tile = (x + dx, y + dy)
                if tile == start or tile in first_step:
                    continue
                if not self._is_valid_position(*tile, npcs, game_map, player_x, player_y, npc):
                    continue
                first_step[tile] = first_step.get((x, y), tile)
                if next_to_player(tile):
                    return first_step[tile]
                queue.append(tile)
        return None

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
