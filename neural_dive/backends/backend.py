"""Rendering backend protocol for Neural Dive.

This module defines the RenderBackend protocol that abstracts terminal operations,
allowing different rendering implementations (blessed, curses, web, test) to be
used interchangeably.
"""

from __future__ import annotations

from typing import Any, Protocol


class RenderBackend(Protocol):
    """Protocol for rendering backends.

    This protocol defines the interface that all rendering backends must implement.
    Backends handle low-level terminal operations like drawing text, colors, and
    cursor positioning.

    Backends also forward arbitrary attribute access to the underlying terminal
    library (e.g. ``backend.move_xy(x, y)``, ``backend.bold_black(text)``,
    ``backend.normal``). The ``__getattr__`` hook below documents that contract
    so static analysis accepts these blessed-style accessors.
    """

    @property
    def width(self) -> int:
        """Get terminal width in characters."""
        ...

    @property
    def height(self) -> int:
        """Get terminal height in characters."""
        ...

    def clear_screen(self) -> None:
        """Clear the entire screen."""
        ...

    def move_cursor(self, x: int, y: int) -> None:
        """Move cursor to position (x, y)."""
        ...

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
        ...

    def draw_with_bg(self, x: int, y: int, text: str, fg: str, bg: str) -> None:
        """Draw text with foreground and background colors.

        Args:
            x: X coordinate
            y: Y coordinate
            text: Text to draw
            fg: Foreground color name
            bg: Background color name
        """
        ...

    def flush(self) -> None:
        """Flush output buffer to screen."""
        ...

    def hide_cursor(self) -> None:
        """Hide the cursor."""
        ...

    def show_cursor(self) -> None:
        """Show the cursor."""
        ...

    def get_color_func(self, color: str, bold: bool = False) -> Any:
        """Get a color function for the given color and style.

        Args:
            color: Color name
            bold: Whether to use bold style

        Returns:
            Callable that applies the color/style to text
        """
        ...

    def __getattr__(self, name: str) -> Any:
        """Forward arbitrary attribute access to the underlying terminal.

        Used for blessed-style accessors like ``move_xy``, ``home``, ``clear``,
        ``normal``, and color functions (``red``, ``bold_black``,
        ``black_on_white``, etc.). Returns either an escape-sequence string or a
        callable depending on what the wrapped terminal exposes.
        """
        ...
