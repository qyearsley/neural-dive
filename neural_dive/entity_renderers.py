"""Entity rendering strategies for Neural Dive.

This module implements the Strategy pattern for rendering different entity types.
Each renderer is responsible for drawing a specific entity type on the game map.

Every renderer draws through ``backend.draw_text``, so what it drew is
recordable: ``TestBackend`` keeps a ``DrawCall`` per entity, and a test can
assert on the glyph and the style rather than on captured stdout.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    from neural_dive.backends import RenderBackend
    from neural_dive.themes import CharacterSet, ColorScheme


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


def split_bold(style_name: str) -> tuple[str, bool]:
    """Split a whole style name into the ``(color, bold)`` ``draw_text`` takes.

    ``npc_style_name`` names a style the way blessed does, as one composed
    attribute ("bold_reverse_bright_magenta"). ``draw_text`` takes bold as a
    flag and composes the "bold_" prefix itself, so the two have to be pulled
    apart before the call.

    Args:
        style_name: A blessed style attribute name

    Returns:
        Tuple of (style name without the "bold_" prefix, whether it had one)
    """
    if style_name.startswith("bold_"):
        return style_name[len("bold_") :], True
    return style_name, False


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

        style, bold = split_bold(npc_style_name(npc_type, colors, is_required))
        term.draw_text(entity.x, entity.y, entity.char, style, bold=bold)


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
        term.draw_text(entity.x, entity.y, chars.terminal, colors.terminal, bold=True)


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
        term.draw_text(entity.x, entity.y, stair_char, colors.stairs, bold=True)


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
        term.draw_text(entity.x, entity.y, entity.char, entity.color, bold=True)


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
        term.draw_text(entity.x, entity.y, chars.player, colors.player, bold=True)


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
