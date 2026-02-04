"""Entity rendering strategies for Neural Dive.

This module implements the Strategy pattern for rendering different entity types.
Each renderer is responsible for drawing a specific entity type on the game map.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    from neural_dive.backends import RenderBackend
    from neural_dive.themes import CharacterSet, ColorScheme


class Renderable(Protocol):
    """Protocol for objects that can be rendered on the map.

    Any object with x, y, and char attributes can be rendered.
    """

    x: int
    y: int
    char: str


class EntityRenderer(Protocol):
    """Protocol for entity rendering strategies.

    Each renderer handles drawing a specific entity type on the map.
    """

    def render(
        self,
        term: RenderBackend,
        entity: Any,  # Accept any object with the required attributes
        chars: CharacterSet,
        colors: ColorScheme,
        **kwargs: Any,
    ) -> None:
        """Render the entity on the map.

        Args:
            term: Render backend instance for output
            entity: Entity to render (must have x, y attributes)
            chars: Character set for rendering
            colors: Color scheme for rendering
            **kwargs: Additional renderer-specific arguments
        """
        ...


class NPCRenderer:
    """Renderer for NPC entities."""

    def render(
        self,
        term: RenderBackend,
        entity: Any,
        chars: CharacterSet,
        colors: ColorScheme,
        **kwargs: Any,
    ) -> None:
        """Render an NPC with type-based coloring and required NPC highlighting.

        Args:
            term: Render backend instance for output
            entity: NPC entity to render
            chars: Character set (unused for NPCs)
            colors: Color scheme for NPC colors
            **kwargs: Must include 'is_required' bool for required NPC highlighting
        """
        is_required = kwargs.get("is_required", False)

        # Get color based on NPC type
        npc_type = entity.npc_type or "specialist"
        if npc_type == "specialist":
            color_name = colors.npc_specialist
        elif npc_type == "helper":
            color_name = colors.npc_helper
        elif npc_type == "enemy":
            color_name = colors.npc_enemy
        elif npc_type == "quest":
            color_name = colors.npc_quest
        else:
            color_name = colors.npc_specialist

        # Use bold for required NPCs, bright_ prefix if available
        if is_required:
            # Try bright variant first for required NPCs
            bright_color = (
                f"bright_{color_name}" if not color_name.startswith("bright_") else color_name
            )
            npc_color = getattr(
                term, f"bold_{bright_color}", getattr(term, f"bold_{color_name}", term.bold_magenta)
            )
        else:
            # Regular bold for optional NPCs
            npc_color = getattr(term, f"bold_{color_name}", term.bold_magenta)

        print(term.move_xy(entity.x, entity.y) + npc_color(entity.char), end="")


class TerminalRenderer:
    """Renderer for info terminal entities."""

    def render(
        self,
        term: RenderBackend,
        entity: Any,
        chars: CharacterSet,
        colors: ColorScheme,
        **kwargs: Any,
    ) -> None:
        """Render an info terminal.

        Args:
            term: Render backend instance for output
            entity: Terminal entity to render
            chars: Character set for terminal character
            colors: Color scheme for terminal color
            **kwargs: Additional arguments (unused)
        """
        terminal_color = getattr(term, f"bold_{colors.terminal}", term.bold_cyan)
        print(term.move_xy(entity.x, entity.y) + terminal_color(chars.terminal), end="")


class StairsRenderer:
    """Renderer for stair entities."""

    def render(
        self,
        term: RenderBackend,
        entity: Any,
        chars: CharacterSet,
        colors: ColorScheme,
        **kwargs: Any,
    ) -> None:
        """Render stairs (up or down).

        Args:
            term: Render backend instance for output
            entity: Stairs entity to render
            chars: Character set for stairs characters
            colors: Color scheme for stairs color
            **kwargs: Additional arguments (unused)
        """
        # entity.direction should be "up" or "down" for Stairs
        stair_char = chars.stairs_up if entity.direction == "up" else chars.stairs_down
        stair_color = getattr(term, f"bold_{colors.stairs}", term.bold_yellow)
        print(term.move_xy(entity.x, entity.y) + stair_color(stair_char), end="")


class ItemPickupRenderer:
    """Renderer for item pickup entities."""

    def render(
        self,
        term: RenderBackend,
        entity: Any,
        chars: CharacterSet,
        colors: ColorScheme,
        **kwargs: Any,
    ) -> None:
        """Render an item pickup.

        Args:
            term: Render backend instance for output
            entity: Item pickup entity to render
            chars: Character set (unused for items)
            colors: Color scheme (unused, item has its own color)
            **kwargs: Additional arguments (unused)
        """
        pickup_color = getattr(term, f"bold_{entity.color}", term.bold_yellow)
        print(term.move_xy(entity.x, entity.y) + pickup_color(entity.char), end="")


class PlayerRenderer:
    """Renderer for the player entity."""

    def render(
        self,
        term: RenderBackend,
        entity: Any,
        chars: CharacterSet,
        colors: ColorScheme,
        **kwargs: Any,
    ) -> None:
        """Render the player.

        Args:
            term: Render backend instance for output
            entity: Player entity to render
            chars: Character set for player character
            colors: Color scheme for player color
            **kwargs: Additional arguments (unused)
        """
        player_color = getattr(term, f"bold_{colors.player}", term.bold_green)
        print(term.move_xy(entity.x, entity.y) + player_color(chars.player), end="")


# Entity type enum for registry
class EntityType:
    """Entity type constants for renderer registry."""

    NPC = "npc"
    TERMINAL = "terminal"
    STAIRS = "stairs"
    ITEM_PICKUP = "item_pickup"
    PLAYER = "player"


# Entity renderer registry
_ENTITY_RENDERERS: dict[str, EntityRenderer] = {
    EntityType.NPC: NPCRenderer(),
    EntityType.TERMINAL: TerminalRenderer(),
    EntityType.STAIRS: StairsRenderer(),
    EntityType.ITEM_PICKUP: ItemPickupRenderer(),
    EntityType.PLAYER: PlayerRenderer(),
}


def get_entity_renderer(entity_type: str) -> EntityRenderer:
    """Get the appropriate renderer for an entity type.

    Args:
        entity_type: Type of entity to render

    Returns:
        EntityRenderer instance for the entity type

    Raises:
        ValueError: If entity type is not supported
    """
    if entity_type not in _ENTITY_RENDERERS:
        raise ValueError(f"Unsupported entity type: {entity_type}")
    return _ENTITY_RENDERERS[entity_type]
