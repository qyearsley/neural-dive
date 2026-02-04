"""Blessed terminal backend for Neural Dive.

This module provides a BlessedBackend implementation that wraps the blessed.Terminal
library for actual terminal rendering.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from blessed import Terminal


class BlessedBackend:
    """Rendering backend using blessed.Terminal.

    This backend wraps blessed.Terminal to provide the RenderBackend interface,
    allowing the game to render to actual terminal windows.
    """

    def __init__(self, term: Terminal):
        """Initialize blessed backend.

        Args:
            term: Blessed Terminal instance
        """
        self._term = term

    @property
    def width(self) -> int:
        """Get terminal width in characters."""
        return self._term.width

    @property
    def height(self) -> int:
        """Get terminal height in characters."""
        return self._term.height

    def clear_screen(self) -> None:
        """Clear the entire screen."""
        print(self._term.clear, end="", flush=True)

    def move_cursor(self, x: int, y: int) -> None:
        """Move cursor to position (x, y)."""
        print(self._term.move_xy(x, y), end="", flush=False)

    def draw_text(
        self, x: int, y: int, text: str, color: str | None = None, bold: bool = False
    ) -> None:
        """Draw text at position (x, y) with optional color and bold.

        Args:
            x: X coordinate
            y: Y coordinate
            text: Text to draw
            color: Color name (e.g., "red", "blue", "green")
            bold: Whether to draw in bold
        """
        # Move to position
        print(self._term.move_xy(x, y), end="")

        # Apply color/style
        if color:
            attr_name = f"bold_{color}" if bold else color
            color_func = getattr(self._term, attr_name, self._term.normal)
            print(color_func(text), end="")
        elif bold:
            print(self._term.bold(text), end="")
        else:
            print(text, end="")

    def draw_with_bg(self, x: int, y: int, text: str, fg: str, bg: str) -> None:
        """Draw text with foreground and background colors.

        Args:
            x: X coordinate
            y: Y coordinate
            text: Text to draw
            fg: Foreground color name
            bg: Background color name
        """
        # Move to position
        print(self._term.move_xy(x, y), end="")

        # Get color functions
        fg_func = getattr(self._term, fg, self._term.normal)
        bg_func = getattr(self._term, f"on_{bg}", self._term.normal)

        # Apply both foreground and background
        print(fg_func(bg_func(text)), end="")

    def flush(self) -> None:
        """Flush output buffer to screen."""
        import sys

        sys.stdout.flush()

    def hide_cursor(self) -> None:
        """Hide the cursor."""
        print(self._term.hide_cursor, end="", flush=True)

    def show_cursor(self) -> None:
        """Show the cursor."""
        print(self._term.normal_cursor, end="", flush=True)

    def get_color_func(self, color: str, bold: bool = False):
        """Get a color function for the given color and style.

        Args:
            color: Color name
            bold: Whether to use bold style

        Returns:
            Callable that applies the color/style to text
        """
        attr_name = f"bold_{color}" if bold else color
        return getattr(self._term, attr_name, self._term.normal)

    def __getattr__(self, name: str):
        """Delegate unknown attributes to the wrapped Terminal for backwards compatibility.

        This allows rendering code to access Terminal attributes like move_xy, color functions,
        etc. directly through the backend, easing the transition to the backend abstraction.

        Args:
            name: Attribute name

        Returns:
            The attribute from the wrapped Terminal
        """
        return getattr(self._term, name)
