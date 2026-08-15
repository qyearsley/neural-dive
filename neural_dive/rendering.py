"""Frame composition for Neural Dive.

Owns the order a frame is drawn in and nothing else. The actual drawing lives in
focused modules:

- ``map_renderer`` -- tiles, entities, and erasing what moved
- ``ui_renderer`` -- the status panel along the bottom
- ``overlay_renderer`` -- modal panels and the victory screen
- ``render_helpers`` -- shared colour and wrapped-text primitives

``draw_victory_screen`` and ``OverlayRenderer`` are re-exported here because
callers and tests have always reached for them through this module.
"""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

from neural_dive.map_renderer import (
    clear_old_npc_positions,
    clear_old_player_position,
    draw_entities,
    draw_map,
)
from neural_dive.overlay_renderer import (
    OverlayRenderer,
    create_overlay,
    draw_completion_overlay,
    draw_conversation_overlay,
    draw_inventory_overlay,
    draw_snippet_overlay,
    draw_terminal_overlay,
    draw_victory_screen,
)
from neural_dive.ui_renderer import draw_ui

if TYPE_CHECKING:
    from neural_dive.backends import RenderBackend
    from neural_dive.game import Game
    from neural_dive.themes import CharacterSet, ColorScheme

__all__ = [
    "OverlayRenderer",
    "create_overlay",
    "draw_completion_overlay",
    "draw_conversation_overlay",
    "draw_game",
    "draw_inventory_overlay",
    "draw_snippet_overlay",
    "draw_terminal_overlay",
    "draw_victory_screen",
]


def draw_game(
    backend: RenderBackend,
    game: Game,
    chars: CharacterSet,
    colors: ColorScheme,
    redraw_all: bool = False,
):
    """Draw the entire game state.

    Args:
        backend: Render backend instance
        game: Game instance
        chars: Character set for rendering
        colors: Color scheme for rendering
        redraw_all: Whether to redraw everything (first draw or after floor change)
    """
    if redraw_all:
        # Clear screen on first draw or floor change
        backend.clear_screen()
        sys.stdout.flush()  # Ensure screen is cleared before drawing

        draw_map(backend, game, chars, colors)
    else:
        # Repaint the tiles the player and NPCs vacated since the last frame
        clear_old_player_position(backend, game, chars, colors)
        clear_old_npc_positions(backend, game, chars, colors)

    draw_entities(backend, game, chars, colors)
    draw_ui(backend, game, colors)

    # Draw overlays if active
    if (
        game.conversation_engine.active_conversation
        or game.conversation_engine.last_answer_response
    ):
        draw_conversation_overlay(backend, game, colors)

    if game.conversation_engine.active_terminal:
        draw_terminal_overlay(backend, game, colors)

    if game.conversation_engine.active_inventory:
        draw_inventory_overlay(backend, game, colors)

    if game.conversation_engine.active_snippet:
        draw_snippet_overlay(backend, game, colors)

    sys.stdout.flush()
