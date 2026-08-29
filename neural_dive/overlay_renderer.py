"""Modal panel drawing.

Everything drawn as a centred box on top of the map: the conversation and
completion panels, the terminal, inventory and snippet readers, and the victory
screen. They all share the same background/border chrome, which lives here as
``OverlayRenderer``.
"""

from __future__ import annotations

from collections.abc import Callable
import sys
from typing import TYPE_CHECKING

from neural_dive.config import (
    COMPLETION_OVERLAY_MAX_HEIGHT,
    INVENTORY_OVERLAY_MAX_HEIGHT,
    OVERLAY_CONTENT_MARGIN,
    OVERLAY_FOOTER_MARGIN,
    OVERLAY_MAX_HEIGHT,
    OVERLAY_MAX_WIDTH,
    OVERLAY_PADDING_X,
    OVERLAY_SCREEN_MARGIN,
    TERMINAL_OVERLAY_MAX_HEIGHT,
    VICTORY_SCREEN_MAX_HEIGHT,
    VICTORY_SCREEN_MAX_WIDTH,
)
from neural_dive.question_renderers import get_question_renderer
from neural_dive.render_helpers import draw_text_block, get_color_func

if TYPE_CHECKING:
    from collections.abc import Callable

    from neural_dive.backends import RenderBackend
    from neural_dive.game import Game
    from neural_dive.models import Conversation
    from neural_dive.themes import ColorScheme


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
            for token in hint_tokens[:3]:  # Show first 3
                if current_y < overlay.start_y + overlay.height - 3:
                    print(
                        backend.move_xy(overlay.start_x + 4, current_y)
                        + backend.black(f"• {token.description}"),
                        end="",
                    )
                    current_y += 1
            current_y += 1

        if code_snippets:
            print(
                backend.move_xy(overlay.start_x + OVERLAY_PADDING_X, current_y)
                + backend.black(f"Code Snippets: {len(code_snippets)}"),
                end="",
            )
            current_y += 1
            for snippet in code_snippets[:3]:  # Show first 3
                if current_y < overlay.start_y + overlay.height - 3:
                    print(
                        backend.move_xy(overlay.start_x + 4, current_y)
                        + backend.black(f"• {snippet.name}"),
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


def draw_victory_screen(backend: RenderBackend, game: Game, colors: ColorScheme):
    """Draw victory screen with final statistics"""
    stats = game.get_final_stats()

    # Clear screen
    print(backend.home + backend.clear, end="")

    # Calculate centered position
    width = min(VICTORY_SCREEN_MAX_WIDTH, backend.width - OVERLAY_SCREEN_MARGIN)
    height = min(VICTORY_SCREEN_MAX_HEIGHT, backend.height - OVERLAY_SCREEN_MARGIN)
    start_x = (backend.width - width) // 2
    start_y = (backend.height - height) // 2

    # Draw background
    for y in range(start_y, start_y + height):
        print(backend.move_xy(start_x, y) + backend.black_on_white(" " * width), end="")

    # Draw border
    success_color = get_color_func(backend, f"bold_{colors.ui_success}", "bold_green")
    _draw_overlay_border(backend, start_x, start_y, width, height, colors.ui_success)

    current_y = start_y + 1

    # Title
    title = "★ VICTORY ★"
    print(
        backend.move_xy(start_x + (width - len(title)) // 2, current_y) + success_color(title),
        end="",
    )
    current_y += 1

    subtitle = "Neural Dive Complete"
    print(
        backend.move_xy(start_x + (width - len(subtitle)) // 2, current_y)
        + backend.bold_black(subtitle),
        end="",
    )
    current_y += 2

    # Stats
    def format_time(seconds):
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes}m {secs}s"

    stats_lines = [
        f"Final Score: {stats['score']}",
        "",
        f"Questions Answered: {stats['questions_answered']}",
        f"Correct: {stats['questions_correct']} | Wrong: {stats['questions_wrong']}",
        f"Accuracy: {stats['accuracy']:.1f}%",
        "",
        f"NPCs Defeated: {stats['npcs_completed']}",
        f"Knowledge Modules: {stats['knowledge_modules']}",
        f"Final Coherence: {stats['final_coherence']}/{game.player_manager.max_coherence}",
        "",
        f"Time Played: {format_time(stats['time_played'])}",
        f"Deepest Layer: {stats['current_floor']}/{game.floor_manager.max_floors}",
    ]

    weak_areas = _weak_areas_line(game)
    if weak_areas:
        stats_lines.extend(["", weak_areas])

    for line in stats_lines:
        if current_y < start_y + height - 2:
            if line == "":
                current_y += 1
                continue
            # Center align stats
            print(backend.move_xy(start_x + 2, current_y) + backend.bold_black(line), end="")
            current_y += 1

    # Footer
    print(
        backend.move_xy(start_x + 2, start_y + height - 2)
        + get_color_func(backend, f"bold_{colors.ui_primary}", "bold")("[Press Q to quit]"),
        end="",
    )

    sys.stdout.flush()
