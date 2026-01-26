"""Game entities for Neural Dive.

This module defines the entity classes that populate the game world,
including players, NPCs, stairs, gates, and information terminals.

Classes:
    Entity: Base class for all positioned game objects (player, NPCs)
    Stairs: Represents stairs connecting floors (up/down)
    InfoTerminal: Interactive terminals displaying game information
    Gate: Floor exit gates that unlock when conditions are met

Entity attributes include position (x, y), visual representation (char, color),
and optional NPC-specific properties (type, wandering behavior).

Example usage:
    from neural_dive.entities import Entity, Stairs, InfoTerminal

    # Create player entity
    player = Entity(10, 10, "@", "cyan", "Data Runner")

    # Create NPC
    npc = Entity(15, 15, "A", "green", "ALGO_SPIRIT", npc_type="specialist")

    # Create stairs to next floor
    stairs = Stairs(30, 10, "down")
"""

from __future__ import annotations

from neural_dive.config import STAIRS_COLOR, STAIRS_DOWN_CHAR, STAIRS_UP_CHAR


class Entity:
    """A generic entity in the game (player, NPC, etc.)."""

    def __init__(
        self,
        x: int,
        y: int,
        char: str,
        color: str,
        name: str,
        npc_type: str | None = None,
    ):
        self.x = x
        self.y = y
        self.char = char
        self.color = color
        self.name = name
        self.npc_type = npc_type  # "specialist", "helper", "enemy", "quest", or None for player

        # Wandering state (for NPCs)
        self.home_x = x  # Original spawn position
        self.home_y = y
        self.wander_state = "idle"  # "idle" or "wander"
        self.wander_ticks_remaining = 0  # Ticks until state change
        self.move_cooldown = 0  # Ticks until next move allowed

    def __repr__(self) -> str:
        return f"Entity(name={self.name}, pos=({self.x}, {self.y}))"

    def should_return_home(self, max_radius: int) -> bool:
        """Check if NPC should return to home position."""
        distance = float(((self.x - self.home_x) ** 2 + (self.y - self.home_y) ** 2) ** 0.5)
        return distance > max_radius


class Stairs:
    """Stairs to go up or down floors."""

    def __init__(self, x: int, y: int, direction: str):
        self.x = x
        self.y = y
        self.direction = direction  # "up" or "down"
        self.char = STAIRS_UP_CHAR if direction == "up" else STAIRS_DOWN_CHAR
        self.color = STAIRS_COLOR

    def __repr__(self) -> str:
        return f"Stairs(direction={self.direction}, pos=({self.x}, {self.y}))"


class InfoTerminal:
    """Info terminal that displays hints or lore."""

    def __init__(self, x: int, y: int, title: str, content: list[str]):
        self.x = x
        self.y = y
        self.char = "T"
        self.color = "cyan"
        self.title = title
        self.content = content  # List of strings (paragraphs)

    def __repr__(self) -> str:
        return f"InfoTerminal(title={self.title}, pos=({self.x}, {self.y}))"
