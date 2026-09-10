"""Frame composition for Neural Dive.

Owns the order a frame is drawn in and nothing else. The actual drawing lives in
focused modules:

- ``map_renderer`` -- tiles, entities, and erasing what moved
- ``ui_renderer`` -- the status panel along the bottom
- ``overlay_renderer`` -- modal panels and the victory screen
- ``render_helpers`` -- shared colour and wrapped-text primitives

``draw_victory_screen``, ``draw_game_over_screen`` and ``OverlayRenderer`` are
re-exported here because
callers and tests have always reached for them through this module.

This module also owns the terminal-size policy: :func:`required_terminal_size`
says how big a window the content needs, and :func:`draw_too_small_screen` is
what the player sees below that.
"""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

from neural_dive.config import (
    DEFAULT_MAP_HEIGHT,
    MIN_TERMINAL_WIDTH,
    UI_BOTTOM_OFFSET,
)
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
    draw_game_over_screen,
    draw_help_overlay,
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
    "ResizeWatcher",
    "create_overlay",
    "draw_completion_overlay",
    "draw_conversation_overlay",
    "draw_game",
    "draw_help_overlay",
    "draw_inventory_overlay",
    "draw_snippet_overlay",
    "draw_terminal_overlay",
    "draw_game_over_screen",
    "draw_too_small_screen",
    "draw_victory_screen",
    "required_terminal_size",
    "terminal_is_too_small",
]


def required_terminal_size(game: Game) -> tuple[int, int]:
    """The smallest window that can show this game without clipping.

    Measured, not guessed: the maps are authored in
    ``data/content/algorithms/levels.py`` and the game does not scroll, so the
    window has to be as wide as the widest floor and as tall as the tallest
    floor plus the ``UI_BOTTOM_OFFSET`` rows the status panel owns. For the
    shipped content that is 50x34 -- floor 3 is 30 rows on its own, which is
    why a stock 80x24 window could never show the last layer.

    Floors that are generated rather than authored fall back to the configured
    default map size.

    Args:
        game: Game instance, read for its level layouts

    Returns:
        Tuple of (columns, rows)
    """
    width = MIN_TERMINAL_WIDTH
    map_height = DEFAULT_MAP_HEIGHT

    level_data = getattr(game, "level_data", None) or {}
    for floor in level_data.values():
        tiles = floor.get("tiles") if isinstance(floor, dict) else None
        if not tiles:
            continue
        map_height = max(map_height, len(tiles))
        width = max(width, max((len(row) for row in tiles), default=0))

    return width, map_height + UI_BOTTOM_OFFSET


class ResizeWatcher:
    """Notices that the window changed size between frames.

    Blessed does not deliver a KEY_RESIZE through ``inkey``, so the size is
    polled once per frame instead. A resize has to force a full redraw:
    ``draw_game`` only clears the screen when ``redraw_all`` is set, so without
    this the old status panel stays painted at the old row until the next floor
    change.

    Attributes:
        size: The window size as of the last poll
    """

    def __init__(self, backend: RenderBackend) -> None:
        """Start watching, taking the current size as the baseline.

        Args:
            backend: Render backend instance to read the size from
        """
        self._backend = backend
        self.size = (backend.width, backend.height)

    def poll(self) -> bool:
        """Sample the size.

        Returns:
            True when the window changed since the previous poll
        """
        current = (self._backend.width, self._backend.height)
        if current == self.size:
            return False
        self.size = current
        return True


def terminal_is_too_small(backend: RenderBackend, required: tuple[int, int]) -> bool:
    """Whether the window is below the size the content needs.

    Args:
        backend: Render backend instance, for its current size
        required: (columns, rows) from :func:`required_terminal_size`

    Returns:
        True when the game should show the resize prompt instead of the map
    """
    return backend.width < required[0] or backend.height < required[1]


def draw_too_small_screen(backend: RenderBackend, required: tuple[int, int]) -> None:
    """Ask the player to make the window bigger, and say by how much.

    Deliberately plain: no box, no colour, one short line per row, every row
    clipped to the window, and drawn through ``backend.draw_text`` so it is
    recordable. It has to render correctly in exactly the situation where
    nothing else does.

    Args:
        backend: Render backend instance
        required: (columns, rows) from :func:`required_terminal_size`
    """
    backend.clear_screen()

    lines = [
        "Neural Dive needs a bigger window.",
        f"Needs: {required[0]} x {required[1]}",
        f"Has:   {backend.width} x {backend.height}",
        "",
        "Resize the terminal to continue, or press Q to quit.",
    ]
    for row, line in enumerate(lines):
        if row >= backend.height:
            break
        backend.draw_text(0, row, line[: backend.width])

    sys.stdout.flush()


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

    # The help overlay is drawn whenever the conversation engine says it is
    # open. `?` (or ESC) in normal mode sets the flag; the overlay handler
    # clears it.
    if game.conversation_engine.active_help:
        draw_help_overlay(backend, chars, colors)

    sys.stdout.flush()
