"""Status panel drawing.

The fixed panel along the bottom of the screen: floor, coherence, knowledge,
score, the current message, and the control hints.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from neural_dive.config import UI_BOTTOM_OFFSET
from neural_dive.render_helpers import get_color_func

if TYPE_CHECKING:
    from neural_dive.backends import RenderBackend
    from neural_dive.game import Game
    from neural_dive.themes import ColorScheme


def draw_ui(backend: RenderBackend, game: Game, colors: ColorScheme) -> None:
    """
    Draw the UI panel at the bottom of the screen.

    Displays floor number, coherence percentage, knowledge count, messages, and controls.

    Args:
        backend: Render backend instance for output
        game: Game instance containing UI state data
        colors: Color scheme for UI colors
    """
    ui_y = backend.height - UI_BOTTOM_OFFSET

    # Separator line - use non-bold for light backgrounds to ensure visibility
    ui_color = get_color_func(backend, colors.ui_primary, "normal")
    print(backend.move_xy(0, ui_y) + ui_color("─" * min(backend.width, 80)), end="")

    # Status line
    score = game.get_current_score()
    knowledge_count = len(game.player_manager.knowledge_modules)

    status_line = (
        f"Layer {game.floor_manager.current_floor}/{game.floor_manager.max_floors} | "
        f"Coherence: {game.player_manager.coherence}/{game.player_manager.max_coherence} | "
        f"Knowledge: {knowledge_count} | "
        f"Score: {score}"
    )
    # Use backend.normal like the instruction line for consistent visibility
    print(backend.move_xy(2, ui_y + 1) + backend.normal + status_line, end="")

    # Message line
    print(backend.move_xy(2, ui_y + 2) + " " * (backend.width - 4), end="")
    msg_color = get_color_func(backend, f"bold_{colors.ui_warning}", "bold_yellow")
    print(
        backend.move_xy(2, ui_y + 2) + msg_color(game.message[: backend.width - 4]),
        end="",
    )

    # Instructions
    if game.conversation_engine.active_conversation:
        print(
            backend.move_xy(0, backend.height - 1)
            + backend.normal
            + "In conversation - see overlay above",
            end="",
        )
    else:
        print(
            backend.move_xy(0, backend.height - 1)
            + backend.normal
            + "Move: Arrows | Interact: Space/Enter | Stairs: >/< | S: Save | L: Load | Q: Quit",
            end="",
        )
