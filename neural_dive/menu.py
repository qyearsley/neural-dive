"""
Menu system for Neural Dive difficulty selection.

Provides an interactive terminal UI for selecting difficulty before game starts.
"""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

from neural_dive.difficulty import DifficultyLevel, get_all_difficulties

if TYPE_CHECKING:
    from blessed import Terminal


def show_difficulty_menu(term: Terminal) -> DifficultyLevel:
    """
    Show interactive difficulty selection menu.

    Args:
        term: Blessed Terminal instance

    Returns:
        Selected DifficultyLevel

    Controls:
        - Arrow Up/Down: Navigate options
        - Enter/Space: Select difficulty
        - 1-4: Quick select by number
    """
    difficulties = get_all_difficulties()
    selected_index = 1  # Default to Normal

    with term.cbreak(), term.hidden_cursor():
        while True:
            # Clear screen
            print(term.home + term.clear, end="")

            # Title - simple and centered
            title_y = term.height // 3
            print(term.move_xy(0, title_y) + term.center(term.bold_cyan("NEURAL DIVE")).rstrip())
            print(term.move_xy(0, title_y + 1) + term.center("Select Difficulty").rstrip())

            # Difficulty options - compact list
            start_y = title_y + 4
            for i, (_level, settings) in enumerate(difficulties):
                y_pos = start_y + i
                is_selected = i == selected_index

                # Simple selector and formatting
                if is_selected:
                    selector = "►"
                    line = term.bold_green(f"{selector} {i + 1}. {settings.name}")
                else:
                    selector = " "
                    line = f"{selector} {i + 1}. {settings.name}"

                print(term.move_xy(term.width // 2 - 15, y_pos) + line)

            # Simple instructions at bottom
            print(
                term.move_xy(0, term.height - 2)
                + term.center("↑↓ or 1-4 to choose  •  Enter to start  •  Q to quit").rstrip()
            )

            sys.stdout.flush()

            # Get input
            key = term.inkey()

            if key.name == "KEY_UP":
                selected_index = (selected_index - 1) % len(difficulties)
            elif key.name == "KEY_DOWN":
                selected_index = (selected_index + 1) % len(difficulties)
            elif key.name == "KEY_ENTER" or key == " ":
                return difficulties[selected_index][0]
            elif key in ["1", "2", "3", "4"]:
                idx = int(key) - 1
                if 0 <= idx < len(difficulties):
                    return difficulties[idx][0]
            elif key.lower() == "q":
                # Allow quitting
                sys.exit(0)
