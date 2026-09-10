"""Status panel drawing.

The fixed panel along the bottom of the screen: floor, floor progress,
coherence, knowledge, score, the current message, and the control hints.

The panel is built from segments rather than one formatted string. A segment
that would run past the right edge is dropped whole, so a narrow window loses
the last hint instead of a half-written word.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from neural_dive.config import (
    COHERENCE_BAR_EMPTY_CHAR,
    COHERENCE_BAR_FILLED_CHAR,
    COHERENCE_BAR_WIDTH,
    COHERENCE_CRITICAL_FRACTION,
    COHERENCE_WARNING_FRACTION,
    UI_BOTTOM_OFFSET,
)
from neural_dive.render_helpers import get_color_func

if TYPE_CHECKING:
    from collections.abc import Callable

    from neural_dive.backends import RenderBackend
    from neural_dive.game import Game
    from neural_dive.themes import ColorScheme

STATUS_SEPARATOR = " | "
STATUS_START_X = 2

# Order matters: segments are dropped from the end when the window is narrow,
# so the keys a stuck player needs most come first.
CONTROL_HINTS = (
    "Arrows Move",
    "Space Interact",
    ">/< Stairs",
    "? Help",
    "Q Quit",
    "V Inventory",
    "S Save",
    "L Load",
)
CONVERSATION_HINTS = (
    "1-4 Answer",
    "H Hint",
    "S Snippet",
    "Y/N for yes-no",
    "ESC/X Leave",
)


def coherence_bar(coherence: int, max_coherence: int) -> str:
    """A fixed-width meter for the coherence value.

    Args:
        coherence: Current coherence
        max_coherence: Coherence ceiling

    Returns:
        A bracketed bar such as "[████████░░]"
    """
    fraction = _coherence_fraction(coherence, max_coherence)
    filled = round(fraction * COHERENCE_BAR_WIDTH)
    filled = max(0, min(COHERENCE_BAR_WIDTH, filled))
    return (
        "["
        + COHERENCE_BAR_FILLED_CHAR * filled
        + COHERENCE_BAR_EMPTY_CHAR * (COHERENCE_BAR_WIDTH - filled)
        + "]"
    )


def coherence_color_name(coherence: int, max_coherence: int, colors: ColorScheme) -> str:
    """Pick the colour band for the coherence readout.

    Green above half, amber down to a quarter, red below that. Coherence is the
    game's only failure condition, and it used to be drawn in the terminal's
    default attribute -- indistinguishable at 5/100 and 80/100.

    Args:
        coherence: Current coherence
        max_coherence: Coherence ceiling
        colors: Colour scheme to take the band colours from

    Returns:
        A colour name from the scheme
    """
    fraction = _coherence_fraction(coherence, max_coherence)
    if fraction <= COHERENCE_CRITICAL_FRACTION:
        return colors.ui_error
    if fraction <= COHERENCE_WARNING_FRACTION:
        return colors.ui_warning
    return colors.ui_success


def _coherence_fraction(coherence: int, max_coherence: int) -> float:
    """Coherence as a 0.0-1.0 fraction, tolerating a zero or negative ceiling."""
    if max_coherence <= 0:
        return 0.0
    return max(0.0, min(1.0, coherence / max_coherence))


def floor_progress(game: Game) -> tuple[int, int]:
    """How many of this floor's required NPCs are done.

    Reads the requirement set the floor manager already computes; nothing new
    is stored. Floors with no required NPCs report (0, 0).

    Args:
        game: Game instance

    Returns:
        Tuple of (completed, required)
    """
    required = game.floor_manager.floor_requirements.get(game.floor_manager.current_floor, set())
    completed = len(required & game.npcs_completed)
    return completed, len(required)


def _plain_style(backend: RenderBackend) -> Callable[[str], str]:
    """A style function that resets to the terminal's default attribute."""
    reset = str(backend.normal)

    def plain(text: str) -> str:
        return reset + text

    return plain


def _segments_width(start_x: int, segments: list[tuple[str, Callable[[str], str]]]) -> int:
    """The column the last segment would end at."""
    if not segments:
        return start_x
    text_width = sum(len(text) for text, _style in segments)
    return start_x + text_width + len(STATUS_SEPARATOR) * (len(segments) - 1)


def _print_segments(
    backend: RenderBackend,
    start_x: int,
    y: int,
    segments: list[tuple[str, Callable[[str], str]]],
) -> None:
    """Print separator-joined segments, dropping any that would overflow.

    Args:
        backend: Render backend instance
        start_x: Column the first segment starts at
        y: Row to print on
        segments: (text, colour function) pairs in priority order
    """
    x = start_x
    first = True
    for text, color_func in segments:
        prefix = "" if first else STATUS_SEPARATOR
        if x + len(prefix) + len(text) > backend.width:
            return
        if prefix:
            print(backend.move_xy(x, y) + str(backend.normal) + prefix, end="")
            x += len(prefix)
        print(backend.move_xy(x, y) + color_func(text), end="")
        x += len(text)
        first = False


def _hint_segments(
    backend: RenderBackend, hints: tuple[str, ...]
) -> list[tuple[str, Callable[[str], str]]]:
    """Wrap plain hint strings as unstyled segments."""
    plain = _plain_style(backend)
    return [(hint, plain) for hint in hints]


def draw_ui(backend: RenderBackend, game: Game, colors: ColorScheme) -> None:
    """
    Draw the UI panel at the bottom of the screen.

    Displays the layer, this floor's required-NPC progress, a coloured
    coherence meter, knowledge count, score, the current message, and the
    control hints.

    Args:
        backend: Render backend instance for output
        game: Game instance containing UI state data
        colors: Color scheme for UI colors
    """
    ui_y = backend.height - UI_BOTTOM_OFFSET
    if ui_y < 0:
        return

    # Separator line - use non-bold for light backgrounds to ensure visibility
    ui_color = get_color_func(backend, colors.ui_primary, "normal")
    print(backend.move_xy(0, ui_y) + ui_color("─" * min(backend.width, 80)), end="")

    _draw_status_line(backend, game, colors, ui_y + 1)
    _draw_message_line(backend, game, colors, ui_y + 2)
    _draw_hint_line(backend, game, backend.height - 1)


def _status_segments(
    backend: RenderBackend, game: Game, colors: ColorScheme, with_bar: bool
) -> list[tuple[str, Callable[[str], str]]]:
    """Build the status segments, in the order they are drawn and dropped.

    Coherence sits second on purpose. Segments are dropped from the right, and
    coherence is the one number the player cannot afford to lose sight of.

    Args:
        backend: Render backend instance
        game: Game instance
        colors: Colour scheme
        with_bar: Whether to append the meter to the coherence readout

    Returns:
        (text, style) pairs
    """
    plain = _plain_style(backend)
    player = game.player_manager
    coherence_color = get_color_func(
        backend,
        f"bold_{coherence_color_name(player.coherence, player.max_coherence, colors)}",
        "normal",
    )
    completed, required = floor_progress(game)

    coherence_text = f"Coherence {player.coherence}/{player.max_coherence}"
    if with_bar:
        coherence_text += " " + coherence_bar(player.coherence, player.max_coherence)

    return [
        (f"Layer {game.floor_manager.current_floor}/{game.floor_manager.max_floors}", plain),
        (coherence_text, coherence_color),
        (f"NPCs {completed}/{required}", plain),
        (f"Knowledge: {len(player.knowledge_modules)}", plain),
        (f"Score: {game.get_current_score()}", plain),
    ]


def _draw_status_line(backend: RenderBackend, game: Game, colors: ColorScheme, y: int) -> None:
    """Draw the layer / coherence / progress / knowledge / score line.

    The meter is the first thing to go when the line does not fit: dropping it
    keeps all five readings visible at the minimum supported width, where
    keeping it would cost the last two segments instead.
    """
    segments = _status_segments(backend, game, colors, with_bar=True)
    if _segments_width(STATUS_START_X, segments) > backend.width:
        segments = _status_segments(backend, game, colors, with_bar=False)
    _print_segments(backend, STATUS_START_X, y, segments)


def _draw_message_line(backend: RenderBackend, game: Game, colors: ColorScheme, y: int) -> None:
    """Draw (and first blank) the transient message row."""
    room = max(0, backend.width - 4)
    print(backend.move_xy(2, y) + " " * room, end="")
    msg_color = get_color_func(backend, f"bold_{colors.ui_warning}", "bold_yellow")
    print(backend.move_xy(2, y) + msg_color(game.message[:room]), end="")


def _draw_hint_line(backend: RenderBackend, game: Game, y: int) -> None:
    """Draw the control hints for whichever mode the player is in."""
    if y < 0:
        return
    hints = CONVERSATION_HINTS if game.conversation_engine.active_conversation else CONTROL_HINTS
    _print_segments(backend, 0, y, _hint_segments(backend, hints))
