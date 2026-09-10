"""Modal panel drawing.

Everything drawn as a centred box on top of the map: the conversation and
completion panels, the terminal, inventory and snippet readers, and the victory
screen. They all share the same background/border chrome, which lives here as
``OverlayRenderer``.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import sys
from typing import TYPE_CHECKING

from neural_dive.config import (
    COMPLETION_OVERLAY_MAX_HEIGHT,
    END_SCREEN_CHROME_ROWS,
    END_SCREEN_MIN_HEIGHT,
    HELP_OVERLAY_MAX_HEIGHT,
    INVENTORY_OVERLAY_MAX_HEIGHT,
    ITEM_CHAR_CODE_SNIPPET,
    ITEM_CHAR_HINT_TOKEN,
    OVERLAY_CONTENT_MARGIN,
    OVERLAY_FOOTER_MARGIN,
    OVERLAY_MAX_HEIGHT,
    OVERLAY_MAX_WIDTH,
    OVERLAY_PADDING_X,
    OVERLAY_SCREEN_MARGIN,
    TERMINAL_OVERLAY_MAX_HEIGHT,
    VICTORY_SCREEN_MAX_WIDTH,
)
from neural_dive.question_renderers import get_question_renderer
from neural_dive.render_helpers import draw_text_block, get_color_func

if TYPE_CHECKING:
    from collections.abc import Callable

    from neural_dive.backends import RenderBackend
    from neural_dive.game import Game
    from neural_dive.models import Conversation
    from neural_dive.themes import CharacterSet, ColorScheme


def _draw_overlay_footer(
    backend: RenderBackend,
    colors: ColorScheme,
    start_x: int,
    start_y: int,
    height: int,
    text: str,
    current_y: int | None = None,
) -> None:
    """Draw a footer prompt (e.g. "[Press any key to continue]") at an overlay's bottom.

    When ``current_y`` is given, the prompt is drawn there only if it still fits above
    the footer margin -- used by scrolling text overlays that append the prompt after
    their content. When ``current_y`` is None, the prompt is drawn unconditionally on
    the fixed footer row.

    Args:
        backend: Render backend instance
        colors: Color scheme (footer uses ``ui_error``)
        start_x: X coordinate of the overlay's left edge
        start_y: Y coordinate of the overlay's top edge
        height: Overlay height in lines
        text: Prompt text to display
        current_y: Optional running Y position; None draws on the fixed footer row
    """
    footer_y = start_y + height - OVERLAY_FOOTER_MARGIN
    if current_y is None:
        y = footer_y
    elif current_y < footer_y:
        y = current_y
    else:
        return
    error_color = get_color_func(backend, f"bold_{colors.ui_error}", "bold_red")
    print(backend.move_xy(start_x + OVERLAY_PADDING_X, y) + error_color(text), end="")


def _draw_overlay_border(
    backend: RenderBackend, start_x: int, start_y: int, width: int, height: int, color_name: str
) -> None:
    """
    Draw a box border around an overlay using Unicode box-drawing characters.

    Args:
        backend: Render backend instance for output
        start_x: X coordinate of overlay top-left corner
        start_y: Y coordinate of overlay top-left corner
        width: Width of overlay in characters
        height: Height of overlay in lines
        color_name: Name of color for border (from color scheme)
    """
    color_func = get_color_func(backend, f"bold_{color_name}", "bold_blue")

    # Top border
    print(
        backend.move_xy(start_x, start_y) + color_func("┏" + "━" * (width - 2) + "┓"),
        end="",
    )

    # Side borders
    for y in range(start_y + 1, start_y + height - 1):
        print(backend.move_xy(start_x, y) + color_func("┃"), end="")
        print(backend.move_xy(start_x + width - 1, y) + color_func("┃"), end="")

    # Bottom border
    print(
        backend.move_xy(start_x, start_y + height - 1) + color_func("┗" + "━" * (width - 2) + "┛"),
        end="",
    )


class OverlayRenderer:
    """Base class for rendering centered overlay panels."""

    def __init__(
        self,
        backend: RenderBackend,
        max_width: int,
        max_height: int,
        border_color: str,
    ):
        """Initialize overlay renderer.

        Args:
            backend: Render backend instance
            max_width: Maximum overlay width
            max_height: Maximum overlay height
            border_color: Color name for border
        """
        self.backend = backend
        self.max_width = max_width
        self.max_height = max_height
        self.border_color = border_color

        # Calculate centered dimensions
        self.width = min(max_width, backend.width - OVERLAY_SCREEN_MARGIN)
        self.height = min(max_height, backend.height - OVERLAY_SCREEN_MARGIN)
        self.start_x = (backend.width - self.width) // 2
        self.start_y = (backend.height - self.height) // 2

    def draw_background(self):
        """Draw white background box for overlay."""
        for y in range(self.start_y, self.start_y + self.height):
            self.backend.draw_with_bg(self.start_x, y, " " * self.width, "black", "white")

    def draw_border(self):
        """Draw colored border around overlay."""
        _draw_overlay_border(
            self.backend,
            self.start_x,
            self.start_y,
            self.width,
            self.height,
            self.border_color,
        )

    def setup(self):
        """Draw background and border (common setup for all overlays)."""
        self.draw_background()
        self.draw_border()


def create_overlay(
    backend: RenderBackend,
    max_height: int,
    border_color: str,
) -> OverlayRenderer:
    """Factory function for creating and setting up overlays.

    Args:
        backend: Render backend instance
        max_height: Maximum overlay height
        border_color: Color name for border

    Returns:
        Configured OverlayRenderer with background and border already drawn
    """
    overlay = OverlayRenderer(
        backend=backend,
        max_width=OVERLAY_MAX_WIDTH,
        max_height=max_height,
        border_color=border_color,
    )
    overlay.setup()
    return overlay


def _draw_overlay_header(
    backend: RenderBackend,
    overlay: OverlayRenderer,
    text: str,
    color_func: Callable[[str], str],
) -> None:
    """Draw a title on an overlay's top border.

    Args:
        backend: Render backend instance
        overlay: The overlay being titled
        text: Title text, normally padded with spaces so the border shows through
        color_func: Colour to draw the title in
    """
    print(
        backend.move_xy(overlay.start_x + OVERLAY_PADDING_X, overlay.start_y) + color_func(text),
        end="",
    )


def draw_conversation_overlay(backend: RenderBackend, game: Game, colors: ColorScheme):
    """Draw conversation overlay panel"""
    conv = game.conversation_engine.active_conversation

    # If no active conversation, check if we have a completion response to show
    if not conv:
        if game.conversation_engine.last_answer_response:
            draw_completion_overlay(backend, game, colors)
        return

    # Setup overlay with OverlayRenderer
    overlay = create_overlay(backend, OVERLAY_MAX_HEIGHT, colors.ui_secondary)

    # NPC name header
    header_color = get_color_func(backend, f"bold_{colors.ui_accent}", "bold_magenta")
    _draw_overlay_header(backend, overlay, f" {conv.npc_name} ", header_color)

    current_y = overlay.start_y + 2

    # If showing greeting
    if game.conversation_engine.show_greeting:
        current_y = draw_text_block(
            backend,
            conv.greeting,
            overlay.start_x + OVERLAY_PADDING_X,
            current_y,
            overlay.start_y + overlay.height - OVERLAY_FOOTER_MARGIN,
            overlay.width - OVERLAY_CONTENT_MARGIN,
        )
        current_y += 1

        _draw_overlay_footer(
            backend,
            colors,
            overlay.start_x,
            overlay.start_y,
            overlay.height,
            "[Press any key to continue]",
            current_y,
        )
        return

    # Check if we have a pending response to show
    if game.conversation_engine.last_answer_response:
        _draw_response(
            backend,
            game,
            overlay.start_x,
            overlay.start_y,
            current_y,
            overlay.width,
            overlay.height,
            colors,
        )
        return

    # Show current question
    if conv.current_question_idx < len(conv.questions):
        _draw_question(
            backend,
            conv,
            overlay.start_x,
            overlay.start_y,
            current_y,
            overlay.width,
            overlay.height,
            colors,
            game,
        )


def _draw_response(
    backend: RenderBackend,
    game: Game,
    start_x: int,
    start_y: int,
    current_y: int,
    overlay_width: int,
    overlay_height: int,
    colors: ColorScheme,
) -> None:
    """
    Draw response to player's answer.

    Args:
        backend: Render backend instance for output
        game: Game instance containing response data
        start_x: X coordinate of overlay start
        start_y: Y coordinate of overlay start
        current_y: Current Y position for drawing
        overlay_width: Width of the overlay
        overlay_height: Height of the overlay
        colors: Color scheme for response colors
    """
    response_text = game.conversation_engine.last_answer_response

    # Handle None response text
    if response_text is None:
        return

    # Check if this is a completion response
    is_completion = "CONVERSATION COMPLETE" in response_text

    if not is_completion:
        # Normal response - draw separator line
        separator = "─" * (overlay_width - OVERLAY_CONTENT_MARGIN)
        sep_color = get_color_func(backend, f"bold_{colors.ui_secondary}", "bold_blue")
        print(
            backend.move_xy(start_x + OVERLAY_PADDING_X, current_y) + sep_color(separator),
            end="",
        )
        current_y += 1

        # Show "RESPONSE:" header
        success_color = get_color_func(backend, f"bold_{colors.ui_success}", "bold_green")
        print(
            backend.move_xy(start_x + OVERLAY_PADDING_X, current_y) + success_color("RESPONSE:"),
            end="",
        )
        current_y += 2

    # Show response text
    current_y = draw_text_block(
        backend,
        response_text,
        start_x + OVERLAY_PADDING_X,
        current_y,
        start_y + overlay_height - 3,
        overlay_width - OVERLAY_CONTENT_MARGIN,
    )
    current_y += 1

    _draw_overlay_footer(
        backend,
        colors,
        start_x,
        start_y,
        overlay_height,
        "[Press any key to continue]",
        current_y,
    )


def _draw_question(
    backend: RenderBackend,
    conv: Conversation,
    start_x: int,
    start_y: int,
    current_y: int,
    overlay_width: int,
    overlay_height: int,
    colors: ColorScheme,
    game: Game,
) -> None:
    """Draw current question using appropriate renderer strategy.

    Uses the Strategy pattern to delegate rendering to question-type-specific renderers.

    Args:
        backend: Render backend instance for output
        conv: Active conversation containing the question
        start_x: X coordinate of overlay start
        start_y: Y coordinate of overlay start
        current_y: Current Y position for drawing
        overlay_width: Width of the overlay
        overlay_height: Height of the overlay
        colors: Color scheme for question colors
        game: Game instance for accessing input buffer
    """
    question = conv.questions[conv.current_question_idx]

    # Get appropriate renderer for this question type
    renderer = get_question_renderer(question.question_type)

    # Delegate rendering to the strategy
    renderer.render(
        term=backend,
        question=question,
        question_number=conv.current_question_idx + 1,
        total_questions=len(conv.questions),
        start_x=start_x,
        start_y=start_y,
        current_y=current_y,
        overlay_width=overlay_width,
        overlay_height=overlay_height,
        colors=colors,
        game=game,
    )


def draw_completion_overlay(backend: RenderBackend, game: Game, colors: ColorScheme):
    """Draw completion message overlay when conversation is complete."""
    response_text = game.conversation_engine.last_answer_response

    # Setup overlay with OverlayRenderer
    overlay = create_overlay(backend, COMPLETION_OVERLAY_MAX_HEIGHT, colors.ui_success)

    current_y = overlay.start_y + 2

    # Show response text directly (no "CONVERSATION COMPLETE" banner)
    current_y = draw_text_block(
        backend,
        response_text,
        overlay.start_x + OVERLAY_PADDING_X,
        current_y,
        overlay.start_y + overlay.height - 3,
        overlay.width - OVERLAY_CONTENT_MARGIN,
    )
    current_y += 1

    # Instructions at bottom
    _draw_overlay_footer(
        backend,
        colors,
        overlay.start_x,
        overlay.start_y,
        overlay.height,
        "[Press any key to continue]",
        current_y,
    )


def draw_terminal_overlay(backend: RenderBackend, game: Game, colors: ColorScheme):
    """Draw terminal info overlay"""
    terminal = game.conversation_engine.active_terminal
    if not terminal:
        return

    # Setup overlay with OverlayRenderer
    overlay = create_overlay(backend, TERMINAL_OVERLAY_MAX_HEIGHT, colors.terminal)

    # Terminal title header
    success_color = get_color_func(backend, f"bold_{colors.ui_success}", "bold_green")
    _draw_overlay_header(backend, overlay, f" {terminal.title} ", success_color)

    current_y = overlay.start_y + 2

    # Show content
    for line in terminal.content:
        current_y = draw_text_block(
            backend,
            line,
            overlay.start_x + OVERLAY_PADDING_X,
            current_y,
            overlay.start_y + overlay.height - OVERLAY_FOOTER_MARGIN,
            overlay.width - OVERLAY_CONTENT_MARGIN,
        )

    # Instructions at bottom
    _draw_overlay_footer(
        backend,
        colors,
        overlay.start_x,
        overlay.start_y,
        overlay.height,
        "[Press ESC or any key to close]",
    )


def _draw_item_lines(
    backend: RenderBackend,
    overlay: OverlayRenderer,
    current_y: int,
    labels: list[str],
    limit: int = 3,
) -> int:
    """List item labels under a heading, saying how many were left out.

    The list used to stop silently after three, so a player carrying six hint
    tokens saw three and no sign of the rest.

    Args:
        backend: Render backend instance
        overlay: Overlay being drawn into
        current_y: Row to start on
        labels: One label per item, in inventory order
        limit: How many labels to show before summarising the rest

    Returns:
        The row after the last line drawn
    """
    bottom = overlay.start_y + overlay.height - 3
    shown = 0
    for label in labels[:limit]:
        if current_y >= bottom:
            break
        print(
            backend.move_xy(overlay.start_x + 4, current_y) + backend.black(f"• {label}"),
            end="",
        )
        current_y += 1
        shown += 1

    remaining = len(labels) - shown
    if remaining > 0 and current_y < bottom:
        print(
            backend.move_xy(overlay.start_x + 4, current_y)
            + backend.black(f"• ... +{remaining} more"),
            end="",
        )
        current_y += 1
    return current_y


def draw_inventory_overlay(backend: RenderBackend, game: Game, colors: ColorScheme):
    """Draw inventory overlay showing player's items."""
    from neural_dive.items import ItemType

    # Setup overlay with OverlayRenderer
    overlay = create_overlay(backend, INVENTORY_OVERLAY_MAX_HEIGHT, colors.ui_primary)

    # Inventory title header
    success_color = get_color_func(backend, f"bold_{colors.ui_success}", "bold_green")
    _draw_overlay_header(backend, overlay, " INVENTORY ", success_color)

    current_y = overlay.start_y + 2

    # Show inventory count
    inventory_count = game.player_manager.get_inventory_count()
    max_size = game.player_manager.max_inventory_size
    count_text = f"Items: {inventory_count}/{max_size}"
    print(
        backend.move_xy(overlay.start_x + OVERLAY_PADDING_X, current_y) + backend.black(count_text),
        end="",
    )
    current_y += 2

    # Show items
    if inventory_count == 0:
        print(
            backend.move_xy(overlay.start_x + OVERLAY_PADDING_X, current_y)
            + backend.black("(Empty)"),
            end="",
        )
    else:
        # Group items by type
        hint_tokens = game.player_manager.get_items_by_type(ItemType.HINT_TOKEN)
        code_snippets = game.player_manager.get_items_by_type(ItemType.CODE_SNIPPET)

        if hint_tokens:
            print(
                backend.move_xy(overlay.start_x + OVERLAY_PADDING_X, current_y)
                + backend.black(f"Hint Tokens: {len(hint_tokens)}"),
                end="",
            )
            current_y += 1
            current_y = _draw_item_lines(
                backend, overlay, current_y, [token.description for token in hint_tokens]
            )
            current_y += 1

        if code_snippets:
            print(
                backend.move_xy(overlay.start_x + OVERLAY_PADDING_X, current_y)
                + backend.black(f"Code Snippets: {len(code_snippets)}"),
                end="",
            )
            current_y += 1
            current_y = _draw_item_lines(
                backend, overlay, current_y, [snippet.name for snippet in code_snippets]
            )

    # Instructions at bottom
    _draw_overlay_footer(
        backend,
        colors,
        overlay.start_x,
        overlay.start_y,
        overlay.height,
        "[Press ESC or V to close]",
    )


def draw_snippet_overlay(backend: RenderBackend, game: Game, colors: ColorScheme):
    """Draw code snippet overlay showing reference material."""
    snippet = game.conversation_engine.active_snippet
    if not snippet:
        return

    # Setup overlay with OverlayRenderer
    overlay = create_overlay(backend, OVERLAY_MAX_HEIGHT, colors.ui_accent)

    # Snippet title header
    success_color = get_color_func(backend, f"bold_{colors.ui_success}", "bold_green")
    _draw_overlay_header(backend, overlay, f" {snippet['name']} ", success_color)

    current_y = overlay.start_y + 2

    # Show content
    for line in snippet["content"]:
        if current_y < overlay.start_y + overlay.height - OVERLAY_FOOTER_MARGIN:
            # No text wrapping for code snippets - preserve formatting
            max_len = overlay.width - OVERLAY_CONTENT_MARGIN
            display_line = line[:max_len] if len(line) > max_len else line
            print(
                backend.move_xy(overlay.start_x + OVERLAY_PADDING_X, current_y)
                + backend.black(display_line),
                end="",
            )
            current_y += 1

    # Instructions at bottom
    _draw_overlay_footer(
        backend,
        colors,
        overlay.start_x,
        overlay.start_y,
        overlay.height,
        "[Press ESC or S to close]",
    )


def help_overlay_lines(chars: CharacterSet) -> list[str]:
    """The text of the help overlay, one screen row per entry.

    A row that starts in column 0 is a heading; the rest are indented. An empty
    string is a blank row.

    The legend has to disambiguate two glyphs that the map reuses. "?" and "S"
    are item pickups, but "S" is also the char of the layer-2 NPC SYSTEM_CORE,
    and both items and NPCs are drawn as a single bold letter. What separates
    them is reverse video, which only NPCs use.

    Args:
        chars: Character set the map is drawn with, so the legend shows the
            glyphs the player is actually looking at

    Returns:
        The rows to draw, in order
    """
    return [
        "MAP LEGEND",
        f"  {chars.player}  You          {chars.terminal}  Info terminal"
        f"     {chars.wall}  Wall     {chars.floor}  Floor",
        f"  {chars.stairs_up}  Stairs up    {chars.stairs_down}  Stairs down",
        "  A-Z  Someone to talk to. Reverse video = required on this layer,",
        "       underlined = boss, plain = optional.",
        f"  {ITEM_CHAR_HINT_TOKEN}  Hint token (item)"
        f"     {ITEM_CHAR_CODE_SNIPPET}  Code snippet (item)",
        f"     '{ITEM_CHAR_CODE_SNIPPET}' is also the NPC SYSTEM_CORE on layer 2. Items are never",
        "     drawn in reverse video; NPCs you still owe always are.",
        "",
        "KEYS",
        "  Arrows  Move             Space/Enter  Talk, read, or pick up",
        "  > or <  Take the stairs  V Inventory  S Save   L Load   Q Quit",
        "  ? or ESC  This help",
        "  In a conversation: 1-4 choose an answer, Y/N answer a yes-no",
        "  question, H spend a hint token, S read a snippet, ENTER submit,",
        "  ESC or X walk away.",
        "",
        "COHERENCE",
        "  Your health. Wrong answers cost it, right ones restore some, and",
        "  enemies cost far more. At zero the run ends. The status bar meter",
        "  turns amber at half and red at a quarter.",
        "",
        "GETTING DEEPER",
        "  The stairs down only open once every required NPC on this layer is",
        "  done -- the status bar counts them ('NPCs 2/5'). On the last layer,",
        "  beat a boss to win.",
    ]


def draw_help_overlay(backend: RenderBackend, chars: CharacterSet, colors: ColorScheme) -> None:
    """Draw the glyph legend and key list.

    There was no in-game legend at all, only an author-facing docstring in the
    level data, so a new player got a grid of letters with no key.

    Args:
        backend: Render backend instance
        chars: Character set the map is drawn with
        colors: Colour scheme for the border and headings
    """
    overlay = create_overlay(backend, HELP_OVERLAY_MAX_HEIGHT, colors.ui_accent)

    header_color = get_color_func(backend, f"bold_{colors.ui_success}", "bold_green")
    _draw_overlay_header(backend, overlay, " HELP ", header_color)

    current_y = overlay.start_y + 2
    bottom = overlay.start_y + overlay.height - OVERLAY_FOOTER_MARGIN
    max_len = max(0, overlay.width - OVERLAY_CONTENT_MARGIN)

    for line in help_overlay_lines(chars):
        if current_y >= bottom:
            break
        if line:
            # Headings are the unindented rows; draw them bold so the sections
            # are findable at a glance.
            style = backend.bold_black if not line.startswith(" ") else backend.black
            print(
                backend.move_xy(overlay.start_x + OVERLAY_PADDING_X, current_y)
                + style(line[:max_len]),
                end="",
            )
        current_y += 1

    _draw_overlay_footer(
        backend,
        colors,
        overlay.start_x,
        overlay.start_y,
        overlay.height,
        "[Press ESC or ? to close]",
    )


def _weak_areas_line(game: Game) -> str | None:
    """Summarize the player's weakest topics from their cross-run history.

    Args:
        game: Game instance, which may or may not carry a profile

    Returns:
        A single line for the victory screen, or None when there is no history
        to report -- in which case the screen looks exactly as it always did.
    """
    from neural_dive.player_profile import weakest_topics

    profile = game.profile
    if profile is None or profile.is_empty:
        return None

    topics = weakest_topics(profile, game.questions, limit=3)
    if not topics:
        return None

    return "Weak areas: " + ", ".join(f"{topic} ({wrong} missed)" for topic, wrong, _ in topics)


def format_time(seconds: float) -> str:
    """Seconds as "3m 07s", for the end screens."""
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{minutes}m {secs}s"


@dataclass(frozen=True)
class _SummaryLine:
    """One row of the end-screen summary, with how much it is worth keeping.

    ``priority`` orders what survives a short window: the lowest goes first.
    Blank spacers score 0, the weak-areas line scores highest, because the
    whole point of showing a summary after a loss is telling the player what to
    study next.
    """

    text: str
    priority: int


def _end_screen_entries(game: Game) -> list[_SummaryLine]:
    """The run summary both end screens show, each line ranked for dropping."""
    stats = game.get_final_stats()
    entries = [
        _SummaryLine(f"Final Score: {stats['score']}", 90),
        _SummaryLine("", 0),
        _SummaryLine(f"Questions Answered: {stats['questions_answered']}", 50),
        _SummaryLine(
            f"Correct: {stats['questions_correct']} | Wrong: {stats['questions_wrong']}", 60
        ),
        _SummaryLine(f"Accuracy: {stats['accuracy']:.1f}%", 80),
        _SummaryLine("", 0),
        _SummaryLine(f"NPCs Defeated: {stats['npcs_completed']}", 30),
        _SummaryLine(f"Knowledge Modules: {stats['knowledge_modules']}", 40),
        _SummaryLine(
            f"Final Coherence: {stats['final_coherence']}/{game.player_manager.max_coherence}", 70
        ),
        _SummaryLine("", 0),
        _SummaryLine(f"Time Played: {format_time(stats['time_played'])}", 10),
        _SummaryLine(
            f"Deepest Layer: {stats['current_floor']}/{game.floor_manager.max_floors}", 20
        ),
    ]
    weak_areas = _weak_areas_line(game)
    if weak_areas:
        entries.extend([_SummaryLine("", 0), _SummaryLine(weak_areas, 100)])
    return entries


def _end_screen_lines(game: Game) -> list[str]:
    """The run summary both end screens show. An empty string is a blank line."""
    return [entry.text for entry in _end_screen_entries(game)]


def fit_end_screen_lines(entries: list[_SummaryLine], capacity: int) -> list[str]:
    """Choose which summary rows to keep when only ``capacity`` rows are free.

    Lowest priority goes first, and the surviving rows stay in their original
    order. Leading and trailing blanks are dropped once the cut is made, so a
    tight fit does not spend a row on a spacer. Previously the loop simply
    stopped at the bottom of the panel, which threw away the tail -- the
    weak-areas line on a 22-row window, and the last three lines on a 20-row
    one.

    Args:
        entries: Ranked summary rows, in display order
        capacity: How many rows the panel has for summary content

    Returns:
        The text of the rows to draw, in order
    """
    if capacity <= 0:
        return []

    keep = set(range(len(entries)))
    if capacity < len(entries):
        ranked = sorted(range(len(entries)), key=lambda i: (-entries[i].priority, i))
        keep = set(ranked[:capacity])

    lines = [entries[i].text for i in sorted(keep)]
    while lines and lines[0] == "":
        lines.pop(0)
    while lines and lines[-1] == "":
        lines.pop()
    return lines


def _draw_end_screen(
    backend: RenderBackend,
    game: Game,
    colors: ColorScheme,
    title: str,
    subtitle: str,
    accent: str,
) -> None:
    """Draw a full-screen run summary. Both endings go through here.

    They did not always. The victory screen was a function here and the game
    over screen was twenty lines of raw terminal escapes inline in the main
    loop, which is why only one of them ever showed any statistics -- and the
    one that did not is the ending where the weak-areas line would help most.
    Sharing the body also makes both testable against `TestBackend`, which the
    inline version could not be.

    The panel is sized from the summary it is about to draw, not from a fixed
    constant, and drops its least valuable rows when the window is too short.
    """
    print(backend.home + backend.clear, end="")

    entries = _end_screen_entries(game)
    width = min(VICTORY_SCREEN_MAX_WIDTH, backend.width - OVERLAY_SCREEN_MARGIN)
    wanted_height = max(END_SCREEN_MIN_HEIGHT, len(entries) + END_SCREEN_CHROME_ROWS)
    height = min(wanted_height, backend.height - OVERLAY_SCREEN_MARGIN)
    start_x = (backend.width - width) // 2
    start_y = (backend.height - height) // 2

    for y in range(start_y, start_y + height):
        print(backend.move_xy(start_x, y) + backend.black_on_white(" " * width), end="")

    accent_color = get_color_func(backend, f"bold_{accent}", "bold")
    _draw_overlay_border(backend, start_x, start_y, width, height, accent)

    current_y = start_y + 1
    print(
        backend.move_xy(start_x + (width - len(title)) // 2, current_y) + accent_color(title),
        end="",
    )
    current_y += 1

    print(
        backend.move_xy(start_x + (width - len(subtitle)) // 2, current_y)
        + backend.bold_black(subtitle),
        end="",
    )
    current_y += 2

    capacity = (start_y + height - 2) - current_y
    for line in fit_end_screen_lines(entries, capacity):
        if line == "":
            current_y += 1
            continue
        print(backend.move_xy(start_x + 2, current_y) + backend.bold_black(line), end="")
        current_y += 1

    print(
        backend.move_xy(start_x + 2, start_y + height - 2)
        + get_color_func(backend, f"bold_{colors.ui_primary}", "bold")("[Press Q to quit]"),
        end="",
    )

    sys.stdout.flush()


def draw_victory_screen(backend: RenderBackend, game: Game, colors: ColorScheme) -> None:
    """The run was finished: a boss on the final layer went down."""
    _draw_end_screen(
        backend,
        game,
        colors,
        title="\u2605 VICTORY \u2605",
        subtitle="Neural Dive Complete",
        accent=colors.ui_success,
    )


def draw_game_over_screen(backend: RenderBackend, game: Game, colors: ColorScheme) -> None:
    """Coherence ran out.

    The same summary as the victory screen, deliberately. This ending used to
    show two lines of red text over the map and nothing else -- so the score,
    the accuracy, the time and the weak-areas line were all invisible at exactly
    the moment they are worth reading.
    """
    _draw_end_screen(
        backend,
        game,
        colors,
        title="SYSTEM FAILURE",
        subtitle="Coherence lost",
        accent=colors.ui_error,
    )
