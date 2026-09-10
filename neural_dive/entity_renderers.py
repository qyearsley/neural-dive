"""Entity rendering strategies for Neural Dive.

This module implements the Strategy pattern for rendering different entity types.
Each renderer is responsible for drawing a specific entity type on the game map.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol, cast

if TYPE_CHECKING:
    from collections.abc import Callable

    from neural_dive.backends import RenderBackend
    from neural_dive.themes import CharacterSet, ColorScheme


def _identity(text: str) -> str:
    return text


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


def _resolve_style(term: RenderBackend, *candidates: str) -> Callable[[str], str]:
    """Return the first style attribute the backend actually has.

    Blessed composes attribute names ("bold_reverse_bright_red"), but a backend
    is free not to expose one. Each candidate is tried in order and a plain
    identity function is the last resort, so an unknown style degrades to
    unstyled text rather than raising.

    Args:
        term: Render backend instance
        *candidates: Attribute names to try, most specific first

    Returns:
        A callable that applies the style to a string
    """
    for name in candidates:
        style = getattr(term, name, None)
        if callable(style):
            return cast("Callable[[str], str]", style)
    return _identity


def npc_style_name(npc_type: str, colors: ColorScheme, is_required: bool) -> str:
    """Name the terminal style an NPC is drawn in.

    Three tiers, each visibly different on both light and dark backgrounds:

    - boss: bold + underline + reverse video, in the boss colour.
    - required (specialist, enemy): bold + reverse video, in the type colour.
    - optional (helper, quest): bold, in the type colour.

    Reverse video swaps foreground and background, so a required NPC reads as a
    filled cell rather than a slightly different shade. The previous rule asked
    for "bright_<colour>" when required and "<colour>" otherwise, but every
    theme colour already starts with "bright_", so both branches produced the
    identical escape sequence and no shipped NPC ever looked required.

    Args:
        npc_type: NPC type from the content data
        colors: Colour scheme to take the base colour from
        is_required: Whether this NPC gates floor completion

    Returns:
        A backend style attribute name, e.g. "bold_reverse_bright_magenta"
    """
    if npc_type == "boss":
        return f"bold_underline_reverse_{colors.npc_boss}"

    color_name = _NPC_TYPE_COLORS.get(npc_type, "npc_specialist")
    base = getattr(colors, color_name)
    return f"bold_reverse_{base}" if is_required else f"bold_{base}"


# NPC type -> the ColorScheme field holding its colour.
_NPC_TYPE_COLORS = {
    "specialist": "npc_specialist",
    "helper": "npc_helper",
    "enemy": "npc_enemy",
    "quest": "npc_quest",
}


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
        """Render an NPC, distinguishing bosses and required NPCs.

        Args:
            term: Render backend instance for output
            entity: NPC entity to render
            chars: Character set (unused for NPCs)
            colors: Color scheme for NPC colors
            **kwargs: Must include 'is_required' bool for required NPC highlighting
        """
        is_required = bool(kwargs.get("is_required", False))
        npc_type = entity.npc_type or "specialist"

        style_name = npc_style_name(npc_type, colors, is_required)
        npc_color = _resolve_style(term, style_name, "bold_magenta")

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
