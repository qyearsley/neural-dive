"""
Menu system for Neural Dive difficulty and content selection.

Provides interactive terminal UI for selecting difficulty and content sets before game starts.
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


def show_content_menu(term: Terminal) -> str:
    """
    Show interactive content set selection menu.

    Args:
        term: Blessed Terminal instance

    Returns:
        Selected content set ID

    Controls:
        - Arrow Up/Down: Navigate options
        - Enter/Space: Select content set
        - 1-9: Quick select by number
    """
    from neural_dive.data_loader import list_content_sets, load_content_metadata

    content_sets = list_content_sets()
    if not content_sets:
        return "algorithms"  # Fallback

    # Load metadata for all content sets
    content_metadata = []
    for cs in content_sets:
        try:
            metadata = load_content_metadata(cs["id"])
            content_metadata.append((cs["id"], metadata, cs.get("default", False)))
        except Exception:
            # Skip invalid content sets
            continue

    if not content_metadata:
        return "algorithms"  # Fallback

    # Find default index
    selected_index = 0
    for i, (_, _, is_default) in enumerate(content_metadata):
        if is_default:
            selected_index = i
            break

    with term.cbreak(), term.hidden_cursor():
        while True:
            # Clear screen
            print(term.home + term.clear, end="")

            # Title
            title_y = max(2, term.height // 4)
            print(term.move_xy(0, title_y) + term.center(term.bold_cyan("NEURAL DIVE")).rstrip())
            print(term.move_xy(0, title_y + 1) + term.center("Select Learning Content").rstrip())

            # Content options
            start_y = title_y + 4
            for i, (_content_id, metadata, _is_default) in enumerate(content_metadata):
                y_pos = start_y + (i * 3)  # 3 lines per option for description
                if y_pos >= term.height - 4:
                    break  # Don't overflow screen

                is_selected = i == selected_index

                # Selector and name
                if is_selected:
                    selector = "►"
                    name_line = term.bold_green(f"{selector} {i + 1}. {metadata['name']}")
                else:
                    selector = " "
                    name_line = f"{selector} {i + 1}. {metadata['name']}"

                # Description
                desc = metadata.get("description", "")
                if len(desc) > 60:
                    desc = desc[:57] + "..."

                x_offset = term.width // 2 - 30
                print(term.move_xy(x_offset, y_pos) + name_line)

                # Use dim if available, otherwise use normal formatting
                desc_text = f"    {desc}"
                try:
                    desc_line = term.dim(desc_text)
                except (TypeError, AttributeError):
                    # Fallback if terminal doesn't support dim
                    desc_line = term.normal + desc_text
                print(term.move_xy(x_offset, y_pos + 1) + desc_line)

            # Instructions
            print(
                term.move_xy(0, term.height - 2)
                + term.center("↑↓ or 1-9 to choose  •  Enter to continue  •  Q to quit").rstrip()
            )

            sys.stdout.flush()

            # Get input
            key = term.inkey()

            if key.name == "KEY_UP":
                selected_index = (selected_index - 1) % len(content_metadata)
            elif key.name == "KEY_DOWN":
                selected_index = (selected_index + 1) % len(content_metadata)
            elif key.name == "KEY_ENTER" or key == " ":
                return content_metadata[selected_index][0]
            elif key.isdigit():
                idx = int(key) - 1
                if 0 <= idx < len(content_metadata):
                    return content_metadata[idx][0]
            elif key.lower() == "q":
                sys.exit(0)
