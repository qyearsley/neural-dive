"""Entity classes for Neural Dive game."""

from __future__ import annotations


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
        self.char = "<" if direction == "up" else ">"
        self.color = "yellow"

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
