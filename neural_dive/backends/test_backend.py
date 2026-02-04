"""Test backend for Neural Dive rendering tests.

This module provides a TestBackend implementation that records all drawing
operations, allowing tests to verify rendering behavior without requiring
an actual terminal.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class DrawCall:
    """Record of a drawing operation.

    Attributes:
        call_type: Type of operation ("text", "text_bg", "clear", "move", etc.)
        x: X coordinate (for positional calls)
        y: Y coordinate (for positional calls)
        text: Text content (for text calls)
        color: Color name (for text calls)
        fg: Foreground color (for bg calls)
        bg: Background color (for bg calls)
        bold: Bold flag (for text calls)
    """

    call_type: str
    x: int = 0
    y: int = 0
    text: str = ""
    color: str | None = None
    fg: str | None = None
    bg: str | None = None
    bold: bool = False


class TestBackend:
    """Mock rendering backend for unit testing.

    This backend records all drawing operations instead of actually rendering,
    allowing tests to verify rendering behavior.
    """

    def __init__(self, width: int = 80, height: int = 24):
        """Initialize test backend.

        Args:
            width: Terminal width in characters
            height: Terminal height in characters
        """
        self._width = width
        self._height = height
        self.draw_calls: list[DrawCall] = []

    @property
    def width(self) -> int:
        """Get terminal width in characters."""
        return self._width

    @property
    def height(self) -> int:
        """Get terminal height in characters."""
        return self._height

    def clear_screen(self) -> None:
        """Clear the entire screen."""
        self.draw_calls.append(DrawCall(call_type="clear"))

    def move_cursor(self, x: int, y: int) -> None:
        """Move cursor to position (x, y)."""
        self.draw_calls.append(DrawCall(call_type="move", x=x, y=y))

    def draw_text(
        self, x: int, y: int, text: str, color: str | None = None, bold: bool = False
    ) -> None:
        """Draw text at position (x, y) with optional color and bold.

        Args:
            x: X coordinate
            y: Y coordinate
            text: Text to draw
            color: Color name
            bold: Whether to draw in bold
        """
        self.draw_calls.append(
            DrawCall(call_type="text", x=x, y=y, text=text, color=color, bold=bold)
        )

    def draw_with_bg(self, x: int, y: int, text: str, fg: str, bg: str) -> None:
        """Draw text with foreground and background colors.

        Args:
            x: X coordinate
            y: Y coordinate
            text: Text to draw
            fg: Foreground color name
            bg: Background color name
        """
        self.draw_calls.append(DrawCall(call_type="text_bg", x=x, y=y, text=text, fg=fg, bg=bg))

    def flush(self) -> None:
        """Flush output buffer to screen (no-op for test backend)."""
        # No-op for test backend - don't record calls
        pass

    def hide_cursor(self) -> None:
        """Hide the cursor."""
        self.draw_calls.append(DrawCall(call_type="hide_cursor"))

    def show_cursor(self) -> None:
        """Show the cursor."""
        self.draw_calls.append(DrawCall(call_type="show_cursor"))

    def get_color_func(self, color: str, bold: bool = False):
        """Get a color function for the given color and style.

        Args:
            color: Color name
            bold: Whether to use bold style

        Returns:
            Callable that applies the color/style to text (identity function for test)
        """
        # Return identity function for testing
        return lambda text: text

    def get_draw_at(self, x: int, y: int) -> DrawCall | None:
        """Get the most recent draw call at position (x, y).

        Useful for tests to verify what was drawn at a specific location.

        Args:
            x: X coordinate
            y: Y coordinate

        Returns:
            Most recent DrawCall at that position, or None if nothing drawn there
        """
        for call in reversed(self.draw_calls):
            if call.call_type in ("text", "text_bg") and call.x == x and call.y == y:
                return call
        return None

    def clear_calls(self) -> None:
        """Clear all recorded draw calls.

        Useful for tests that want to check drawing for specific operations
        without noise from previous operations.
        """
        self.draw_calls.clear()

    def get_calls_by_type(self, call_type: str) -> list[DrawCall]:
        """Get all draw calls of a specific type.

        Args:
            call_type: Type of calls to retrieve

        Returns:
            List of DrawCall objects matching the type
        """
        return [call for call in self.draw_calls if call.call_type == call_type]

    def __getattr__(self, name: str):
        """Provide default attributes for backwards compatibility.

        This allows code to call getattr(backend, "bold_cyan", backend.normal)
        without errors. Returns identity function for all color attributes.
        Also provides move_xy and Terminal string properties for backwards compatibility.

        Args:
            name: Attribute name

        Returns:
            Identity function for color attributes, empty string function for positioning,
            empty string for Terminal formatting strings
        """
        # Return empty string for positioning attributes
        if name == "move_xy":
            return lambda x, y: ""

        # Return empty string for Terminal string properties (formatting codes)
        if name in ("normal", "clear", "home", "hide_cursor", "normal_cursor"):
            return ""

        # Return identity function for color/style attributes
        if any(
            name.startswith(prefix)
            for prefix in [
                "bold_",
                "bright_",
                "on_",
                "black",
                "red",
                "green",
                "yellow",
                "blue",
                "magenta",
                "cyan",
                "white",
            ]
        ):
            return lambda text: text
        raise AttributeError(f"'TestBackend' object has no attribute '{name}'")
