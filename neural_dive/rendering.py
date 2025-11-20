"""
Terminal rendering for Neural Dive.
Uses blessed library for terminal control.
"""

from __future__ import annotations

from collections.abc import Callable
import sys
from typing import TYPE_CHECKING, cast

from neural_dive.config import (
    COMPLETION_OVERLAY_MAX_HEIGHT,
    INVENTORY_OVERLAY_MAX_HEIGHT,
    OVERLAY_MAX_HEIGHT,
    OVERLAY_MAX_WIDTH,
    TERMINAL_OVERLAY_MAX_HEIGHT,
    UI_BOTTOM_OFFSET,
)
from neural_dive.conversation import wrap_text
from neural_dive.question_renderers import get_question_renderer
from neural_dive.themes import CharacterSet, ColorScheme

if TYPE_CHECKING:
    from blessed import Terminal

    from neural_dive.game import Game
    from neural_dive.models import Conversation


class OverlayRenderer:
    """Base class for rendering centered overlay panels."""

    def __init__(
        self,
        term: Terminal,
        max_width: int,
        max_height: int,
        border_color: str,
    ):
        """
        Initialize overlay renderer.

        Args:
            term: Blessed Terminal instance
            max_width: Maximum overlay width
            max_height: Maximum overlay height
            border_color: Color name for border
        """
        self.term = term
        self.max_width = max_width
        self.max_height = max_height
        self.border_color = border_color

        # Calculate centered dimensions
        self.width = min(max_width, term.width - 4)
        self.height = min(max_height, term.height - 4)
        self.start_x = (term.width - self.width) // 2
        self.start_y = (term.height - self.height) // 2

    def draw_background(self):
        """Draw white background box for overlay."""
        for y in range(self.start_y, self.start_y + self.height):
            print(
                self.term.move_xy(self.start_x, y) + self.term.black_on_white(" " * self.width),
                end="",
            )

    def draw_border(self):
        """Draw colored border around overlay."""
        _draw_overlay_border(
            self.term,
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
    term: Terminal,
    max_height: int,
    border_color: str,
) -> OverlayRenderer:
    """Factory function for creating and setting up overlays.

    Args:
        term: Blessed Terminal instance
        max_height: Maximum overlay height
        border_color: Color name for border

    Returns:
        Configured OverlayRenderer with background and border already drawn
    """
    overlay = OverlayRenderer(
        term=term,
        max_width=OVERLAY_MAX_WIDTH,
        max_height=max_height,
        border_color=border_color,
    )
    overlay.setup()
    return overlay


def draw_game(
    term: Terminal,
    game: Game,
    chars: CharacterSet,
    colors: ColorScheme,
    redraw_all: bool = False,
):
    """
    Draw the entire game state.

    Args:
        term: Blessed Terminal instance
        game: Game instance
        chars: Character set for rendering
        colors: Color scheme for rendering
        redraw_all: Whether to redraw everything (first draw or after floor change)
    """
    if redraw_all:
        # Clear screen on first draw or floor change
        # Use home + clear to completely clear the display buffer
        print(term.home + term.clear, end="")
        sys.stdout.flush()  # Ensure screen is cleared before drawing

        # Draw map
        _draw_map(term, game, chars, colors)
    else:
        # Clear old player position
        _clear_old_player_position(term, game, chars, colors)

        # Clear old NPC positions
        _clear_old_npc_positions(term, game, chars, colors)

    # Draw all entities
    _draw_entities(term, game, chars, colors)

    # Draw UI at bottom
    _draw_ui(term, game, colors)

    # Draw overlays if active
    if game.active_conversation or (
        hasattr(game, "last_answer_response") and game.last_answer_response
    ):
        draw_conversation_overlay(term, game, colors)

    if game.active_terminal:
        draw_terminal_overlay(term, game, colors)

    if game.active_inventory:
        draw_inventory_overlay(term, game, colors)

    if game.active_snippet:
        draw_snippet_overlay(term, game, colors)

    sys.stdout.flush()


def _draw_map(term: Terminal, game: Game, chars: CharacterSet, colors: ColorScheme) -> None:
    """
    Draw the game map tiles to the terminal.

    Args:
        term: Blessed Terminal instance for output
        game: Game instance containing map data
        chars: Character set for rendering tiles
        colors: Color scheme for tile colors
    """
    for y in range(len(game.game_map)):
        for x in range(len(game.game_map[0])):
            char = game.game_map[y][x]
            if char == "#":
                color_func = getattr(term, f"bold_{colors.wall}", term.bold_blue)
                print(term.move_xy(x, y) + color_func(chars.wall), end="")
            elif char == ".":
                color_func = getattr(term, colors.floor, term.cyan)
                print(term.move_xy(x, y) + color_func(chars.floor), end="")


def _clear_old_player_position(
    term: Terminal, game: Game, chars: CharacterSet, colors: ColorScheme
) -> None:
    """
    Clear the old player position by redrawing the floor tile.

    Args:
        term: Blessed Terminal instance for output
        game: Game instance with player position data
        chars: Character set for rendering tiles
        colors: Color scheme for tile colors
    """
    if game.old_player_pos:
        old_x, old_y = game.old_player_pos
        char = game.game_map[old_y][old_x]
        if char == ".":
            color_func = getattr(term, colors.floor, term.cyan)
            print(term.move_xy(old_x, old_y) + color_func(chars.floor), end="")


def _clear_old_npc_positions(
    term: Terminal, game: Game, chars: CharacterSet, colors: ColorScheme
) -> None:
    """
    Clear old NPC positions by redrawing floor tiles where NPCs have moved from.

    Args:
        term: Blessed Terminal instance for output
        game: Game instance with NPC position data
        chars: Character set for rendering tiles
        colors: Color scheme for tile colors
    """
    for _npc_name, (old_x, old_y) in game.old_npc_positions.items():
        # Check if position is still occupied by any entity
        occupied = False

        # Check if player is there
        if game.player.x == old_x and game.player.y == old_y:
            occupied = True

        # Check if any NPC is there
        if not occupied:
            for npc in game.npcs:
                if npc.x == old_x and npc.y == old_y:
                    occupied = True
                    break

        # Check if any terminal is there
        if not occupied:
            for terminal in game.terminals:
                if terminal.x == old_x and terminal.y == old_y:
                    occupied = True
                    break

        # Check if any stairs are there
        if not occupied:
            for stair in game.stairs:
                if stair.x == old_x and stair.y == old_y:
                    occupied = True
                    break

        # If not occupied, redraw the floor tile
        if not occupied:
            char = game.game_map[old_y][old_x]
            if char == ".":
                color_func = getattr(term, colors.floor, term.cyan)
                print(term.move_xy(old_x, old_y) + color_func(chars.floor), end="")
            elif char == "#":
                color_func = getattr(term, f"bold_{colors.wall}", term.bold_blue)
                print(term.move_xy(old_x, old_y) + color_func(chars.wall), end="")

    # Clear the tracking dictionary after processing
    game.old_npc_positions.clear()


def _draw_entities(term: Terminal, game: Game, chars: CharacterSet, colors: ColorScheme) -> None:
    """
    Draw all game entities including NPCs, terminals, stairs, and player.

    Args:
        term: Blessed Terminal instance for output
        game: Game instance containing entity data
        chars: Character set for rendering entities
        colors: Color scheme for entity colors
    """
    from neural_dive.config import FLOOR_REQUIRED_NPCS

    # Get required NPCs for current floor
    required_npcs = FLOOR_REQUIRED_NPCS.get(game.current_floor, set())

    # Draw NPCs
    for npc in game.npcs:
        # Check if this is a required NPC
        is_required = npc.name in required_npcs

        # Get color based on NPC type
        npc_type = npc.npc_type or "specialist"
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

        print(term.move_xy(npc.x, npc.y) + npc_color(npc.char), end="")

    # Draw terminals
    for terminal in game.terminals:
        terminal_color = getattr(term, f"bold_{colors.terminal}", term.bold_cyan)
        print(term.move_xy(terminal.x, terminal.y) + terminal_color(chars.terminal), end="")

    # Draw stairs
    for stair in game.stairs:
        stair_char = chars.stairs_up if stair.direction == "up" else chars.stairs_down
        stair_color = getattr(term, f"bold_{colors.stairs}", term.bold_yellow)
        print(term.move_xy(stair.x, stair.y) + stair_color(stair_char), end="")

    # Draw item pickups
    for pickup in game.item_pickups:
        pickup_color = getattr(term, f"bold_{pickup.color}", term.bold_yellow)
        print(term.move_xy(pickup.x, pickup.y) + pickup_color(pickup.char), end="")

    # Draw player
    player_color = getattr(term, f"bold_{colors.player}", term.bold_green)
    print(
        term.move_xy(game.player.x, game.player.y) + player_color(chars.player),
        end="",
    )


def _draw_ui(term: Terminal, game: Game, colors: ColorScheme) -> None:
    """
    Draw the UI panel at the bottom of the screen.

    Displays floor number, coherence percentage, knowledge count, messages, and controls.

    Args:
        term: Blessed Terminal instance for output
        game: Game instance containing UI state data
        colors: Color scheme for UI colors
    """
    ui_y = term.height - UI_BOTTOM_OFFSET

    # Separator line - use non-bold for light backgrounds to ensure visibility
    ui_color = cast(Callable[[str], str], getattr(term, colors.ui_primary, term.normal))
    print(term.move_xy(0, ui_y) + ui_color("─" * min(term.width, 80)), end="")

    # Status line
    score = game.get_current_score()
    knowledge_count = len(game.knowledge_modules)

    # Use localized term for coherence based on content set
    coherence_label = "分" if game.content_set == "chinese-hsk6" else "Coherence"
    knowledge_label = "知识" if game.content_set == "chinese-hsk6" else "Knowledge"
    score_label = "分数" if game.content_set == "chinese-hsk6" else "Score"
    layer_label = "层" if game.content_set == "chinese-hsk6" else "Layer"

    status_line = (
        f"{layer_label} {game.current_floor}/{game.max_floors} | "
        f"{coherence_label}: {game.coherence}/{game.max_coherence} | "
        f"{knowledge_label}: {knowledge_count} | "
        f"{score_label}: {score}"
    )
    # Use term.normal like the instruction line for consistent visibility
    print(term.move_xy(2, ui_y + 1) + term.normal + status_line, end="")

    # Message line
    print(term.move_xy(2, ui_y + 2) + " " * (term.width - 4), end="")
    msg_color = getattr(term, f"bold_{colors.ui_warning}", term.bold_yellow)
    print(
        term.move_xy(2, ui_y + 2) + msg_color(game.message[: term.width - 4]),
        end="",
    )

    # Instructions
    if game.active_conversation:
        print(
            term.move_xy(0, term.height - 1) + term.normal + "In conversation - see overlay above",
            end="",
        )
    else:
        print(
            term.move_xy(0, term.height - 1)
            + term.normal
            + "Move: Arrows | Interact: Space/Enter | Stairs: >/< | S: Save | L: Load | Q: Quit",
            end="",
        )


def draw_conversation_overlay(term: Terminal, game: Game, colors: ColorScheme):
    """Draw conversation overlay panel"""
    conv = game.active_conversation

    # If no active conversation, check if we have a completion response to show
    if not conv:
        if hasattr(game, "last_answer_response") and game.last_answer_response:
            draw_completion_overlay(term, game, colors)
        return

    # Setup overlay with OverlayRenderer
    overlay = create_overlay(term, OVERLAY_MAX_HEIGHT, colors.ui_secondary)

    # NPC name header
    header = f" {conv.npc_name} "
    header_color = getattr(term, f"bold_{colors.ui_accent}", term.bold_magenta)
    print(term.move_xy(overlay.start_x + 2, overlay.start_y) + header_color(header), end="")

    current_y = overlay.start_y + 2

    # If showing greeting
    if hasattr(game, "show_greeting") and game.show_greeting:
        lines = wrap_text(conv.greeting, overlay.width - 4)
        for line in lines:
            if current_y < overlay.start_y + overlay.height - 2:
                print(term.move_xy(overlay.start_x + 2, current_y) + term.black(line), end="")
                current_y += 1
        current_y += 1

        if current_y < overlay.start_y + overlay.height - 2:
            error_color = getattr(term, f"bold_{colors.ui_error}", term.bold_red)
            print(
                term.move_xy(overlay.start_x + 2, current_y)
                + error_color("[Press any key to continue]"),
                end="",
            )
        return

    # Check if we have a pending response to show
    if hasattr(game, "last_answer_response") and game.last_answer_response:
        _draw_response(
            term,
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
            term,
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
    term: Terminal,
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
        term: Blessed Terminal instance for output
        game: Game instance containing response data
        start_x: X coordinate of overlay start
        start_y: Y coordinate of overlay start
        current_y: Current Y position for drawing
        overlay_width: Width of the overlay
        overlay_height: Height of the overlay
        colors: Color scheme for response colors
    """
    response_text = game.last_answer_response

    # Handle None response text
    if response_text is None:
        return

    # Check if this is a completion response
    is_completion = "CONVERSATION COMPLETE" in response_text

    if not is_completion:
        # Normal response - draw separator line
        separator = "─" * (overlay_width - 4)
        sep_color = getattr(term, f"bold_{colors.ui_secondary}", term.bold_blue)
        print(term.move_xy(start_x + 2, current_y) + sep_color(separator), end="")
        current_y += 1

        # Show "RESPONSE:" header
        success_color = getattr(term, f"bold_{colors.ui_success}", term.bold_green)
        print(term.move_xy(start_x + 2, current_y) + success_color("RESPONSE:"), end="")
        current_y += 2

    # Show response text
    lines = wrap_text(response_text, overlay_width - 4)
    for line in lines:
        if current_y < start_y + overlay_height - 3:
            print(term.move_xy(start_x + 2, current_y) + term.black(line), end="")
            current_y += 1
    current_y += 1

    if current_y < start_y + overlay_height - 2:
        error_color = getattr(term, f"bold_{colors.ui_error}", term.bold_red)
        print(
            term.move_xy(start_x + 2, current_y) + error_color("[Press any key to continue]"),
            end="",
        )


def _draw_question(
    term: Terminal,
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
        term: Blessed Terminal instance for output
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
        term=term,
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


def draw_completion_overlay(term: Terminal, game: Game, colors: ColorScheme):
    """Draw completion message overlay when conversation is complete."""
    response_text = game.last_answer_response

    # Setup overlay with OverlayRenderer
    overlay = create_overlay(term, COMPLETION_OVERLAY_MAX_HEIGHT, colors.ui_success)

    current_y = overlay.start_y + 2

    # Big completion banner at top - REMOVED per user request
    # (No longer showing "CONVERSATION COMPLETE" banner)

    # Show response text directly
    lines = wrap_text(response_text, overlay.width - 4) if response_text else []
    for line in lines:
        if current_y < overlay.start_y + overlay.height - 3:
            print(term.move_xy(overlay.start_x + 2, current_y) + term.black(line), end="")
            current_y += 1
    current_y += 1

    # Instructions at bottom
    if current_y < overlay.start_y + overlay.height - 2:
        error_color = getattr(term, f"bold_{colors.ui_error}", term.bold_red)
        print(
            term.move_xy(overlay.start_x + 2, current_y)
            + error_color("[Press any key to continue]"),
            end="",
        )


def draw_terminal_overlay(term: Terminal, game: Game, colors: ColorScheme):
    """Draw terminal info overlay"""
    terminal = game.active_terminal
    if not terminal:
        return

    # Setup overlay with OverlayRenderer
    overlay = create_overlay(term, TERMINAL_OVERLAY_MAX_HEIGHT, colors.terminal)

    # Terminal title header
    header = f" {terminal.title} "
    success_color = getattr(term, f"bold_{colors.ui_success}", term.bold_green)
    print(term.move_xy(overlay.start_x + 2, overlay.start_y) + success_color(header), end="")

    current_y = overlay.start_y + 2

    # Show content
    for line in terminal.content:
        wrapped_lines = wrap_text(line, overlay.width - 4)
        for wrapped_line in wrapped_lines:
            if current_y < overlay.start_y + overlay.height - 2:
                print(
                    term.move_xy(overlay.start_x + 2, current_y) + term.black(wrapped_line),
                    end="",
                )
                current_y += 1

    # Instructions at bottom
    error_color = getattr(term, f"bold_{colors.ui_error}", term.bold_red)
    print(
        term.move_xy(overlay.start_x + 2, overlay.start_y + overlay.height - 2)
        + error_color("[Press ESC or any key to close]"),
        end="",
    )


def draw_inventory_overlay(term: Terminal, game: Game, colors: ColorScheme):
    """Draw inventory overlay showing player's items."""
    from neural_dive.items import ItemType

    # Setup overlay with OverlayRenderer
    overlay = create_overlay(term, INVENTORY_OVERLAY_MAX_HEIGHT, colors.ui_primary)

    # Inventory title header
    header = " INVENTORY "
    success_color = getattr(term, f"bold_{colors.ui_success}", term.bold_green)
    print(term.move_xy(overlay.start_x + 2, overlay.start_y) + success_color(header), end="")

    current_y = overlay.start_y + 2

    # Show inventory count
    inventory_count = game.player_manager.get_inventory_count()
    max_size = game.player_manager.max_inventory_size
    count_text = f"Items: {inventory_count}/{max_size}"
    print(
        term.move_xy(overlay.start_x + 2, current_y) + term.black(count_text),
        end="",
    )
    current_y += 2

    # Show items
    if inventory_count == 0:
        print(
            term.move_xy(overlay.start_x + 2, current_y) + term.black("(Empty)"),
            end="",
        )
    else:
        # Group items by type
        hint_tokens = game.player_manager.get_items_by_type(ItemType.HINT_TOKEN)
        code_snippets = game.player_manager.get_items_by_type(ItemType.CODE_SNIPPET)

        if hint_tokens:
            print(
                term.move_xy(overlay.start_x + 2, current_y)
                + term.black(f"Hint Tokens: {len(hint_tokens)}"),
                end="",
            )
            current_y += 1
            for token in hint_tokens[:3]:  # Show first 3
                if current_y < overlay.start_y + overlay.height - 3:
                    print(
                        term.move_xy(overlay.start_x + 4, current_y)
                        + term.black(f"• {token.description}"),
                        end="",
                    )
                    current_y += 1
            current_y += 1

        if code_snippets:
            print(
                term.move_xy(overlay.start_x + 2, current_y)
                + term.black(f"Code Snippets: {len(code_snippets)}"),
                end="",
            )
            current_y += 1
            for snippet in code_snippets[:3]:  # Show first 3
                if current_y < overlay.start_y + overlay.height - 3:
                    print(
                        term.move_xy(overlay.start_x + 4, current_y)
                        + term.black(f"• {snippet.name}"),
                        end="",
                    )
                    current_y += 1

    # Instructions at bottom
    error_color = getattr(term, f"bold_{colors.ui_error}", term.bold_red)
    print(
        term.move_xy(overlay.start_x + 2, overlay.start_y + overlay.height - 2)
        + error_color("[Press ESC or V to close]"),
        end="",
    )


def draw_snippet_overlay(term: Terminal, game: Game, colors: ColorScheme):
    """Draw code snippet overlay showing reference material."""
    snippet = game.active_snippet
    if not snippet:
        return

    # Setup overlay with OverlayRenderer
    overlay = create_overlay(term, OVERLAY_MAX_HEIGHT, colors.ui_accent)

    # Snippet title header
    header = f" {snippet['name']} "
    success_color = getattr(term, f"bold_{colors.ui_success}", term.bold_green)
    print(term.move_xy(overlay.start_x + 2, overlay.start_y) + success_color(header), end="")

    current_y = overlay.start_y + 2

    # Show content
    for line in snippet["content"]:
        if current_y < overlay.start_y + overlay.height - 2:
            # No text wrapping for code snippets - preserve formatting
            display_line = line[: overlay.width - 4] if len(line) > overlay.width - 4 else line
            print(
                term.move_xy(overlay.start_x + 2, current_y) + term.black(display_line),
                end="",
            )
            current_y += 1

    # Instructions at bottom
    error_color = getattr(term, f"bold_{colors.ui_error}", term.bold_red)
    print(
        term.move_xy(overlay.start_x + 2, overlay.start_y + overlay.height - 2)
        + error_color("[Press ESC or S to close]"),
        end="",
    )


def _draw_overlay_border(
    term: Terminal, start_x: int, start_y: int, width: int, height: int, color_name: str
) -> None:
    """
    Draw a box border around an overlay using Unicode box-drawing characters.

    Args:
        term: Blessed Terminal instance for output
        start_x: X coordinate of overlay top-left corner
        start_y: Y coordinate of overlay top-left corner
        width: Width of overlay in characters
        height: Height of overlay in lines
        color_name: Name of color for border (from color scheme)
    """
    color_func = getattr(term, f"bold_{color_name}", term.bold_blue)

    # Top border
    print(
        term.move_xy(start_x, start_y) + color_func("┏" + "━" * (width - 2) + "┓"),
        end="",
    )

    # Side borders
    for y in range(start_y + 1, start_y + height - 1):
        print(term.move_xy(start_x, y) + color_func("┃"), end="")
        print(term.move_xy(start_x + width - 1, y) + color_func("┃"), end="")

    # Bottom border
    print(
        term.move_xy(start_x, start_y + height - 1) + color_func("┗" + "━" * (width - 2) + "┛"),
        end="",
    )


def draw_victory_screen(term: Terminal, game: Game, colors: ColorScheme):
    """Draw victory screen with final statistics"""
    stats = game.get_final_stats()

    # Clear screen
    print(term.home + term.clear, end="")

    # Calculate centered position
    width = min(70, term.width - 4)
    height = min(20, term.height - 4)
    start_x = (term.width - width) // 2
    start_y = (term.height - height) // 2

    # Draw background
    for y in range(start_y, start_y + height):
        print(term.move_xy(start_x, y) + term.black_on_white(" " * width), end="")

    # Draw border
    success_color = getattr(term, f"bold_{colors.ui_success}", term.bold_green)
    _draw_overlay_border(term, start_x, start_y, width, height, colors.ui_success)

    current_y = start_y + 1

    # Title
    title = "★ VICTORY ★"
    print(
        term.move_xy(start_x + (width - len(title)) // 2, current_y) + success_color(title), end=""
    )
    current_y += 1

    subtitle = "Neural Dive Complete"
    print(
        term.move_xy(start_x + (width - len(subtitle)) // 2, current_y) + term.bold_black(subtitle),
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
        f"Final Coherence: {stats['final_coherence']}/{game.max_coherence}",
        "",
        f"Time Played: {format_time(stats['time_played'])}",
        f"Deepest Layer: {stats['current_floor']}/{game.max_floors}",
    ]

    for line in stats_lines:
        if current_y < start_y + height - 2:
            if line == "":
                current_y += 1
                continue
            # Center align stats
            print(term.move_xy(start_x + 2, current_y) + term.bold_black(line), end="")
            current_y += 1

    # Footer
    print(
        term.move_xy(start_x + 2, start_y + height - 2)
        + getattr(term, f"bold_{colors.ui_primary}", term.bold)("[Press Q to quit]"),
        end="",
    )

    sys.stdout.flush()
