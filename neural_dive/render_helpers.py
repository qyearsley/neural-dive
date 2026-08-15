"""Shared low-level drawing primitives.

Colour lookup and wrapped-text drawing, used by the map, UI, overlay, and
question renderers. These are the pieces that would otherwise be copied into
each renderer.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, cast

from neural_dive.conversation import wrap_text

if TYPE_CHECKING:
    from neural_dive.backends import RenderBackend


def get_color_func(backend: RenderBackend, color_expr: str, fallback: str) -> Callable[[str], str]:
    """Resolve a color/style function on the backend by attribute name.

    Args:
        backend: Render backend instance
        color_expr: Attribute name to look up (e.g. "bold_green")
        fallback: Fallback attribute name if color_expr doesn't exist

    Returns:
        Callable that applies the color/style to text
    """
    return cast(
        Callable[[str], str],
        getattr(backend, color_expr, getattr(backend, fallback)),
    )


def draw_wrapped_lines(
    backend: RenderBackend,
    lines: list[str],
    start_x: int,
    current_y: int,
    max_y: int,
    color_func: Callable[[str], str] | None = None,
) -> int:
    """Draw pre-wrapped text lines within a vertical bound.

    Args:
        backend: Render backend instance
        lines: Pre-wrapped text lines to draw
        start_x: X coordinate for each line
        current_y: Starting Y coordinate
        max_y: Stop drawing before this Y coordinate
        color_func: Color function to apply (defaults to backend.black)

    Returns:
        The Y coordinate after the last drawn line
    """
    draw = color_func if color_func is not None else backend.black
    for line in lines:
        if current_y < max_y:
            print(backend.move_xy(start_x, current_y) + draw(line), end="")
            current_y += 1
    return current_y


def draw_text_block(
    backend: RenderBackend,
    text: str | None,
    start_x: int,
    current_y: int,
    max_y: int,
    wrap_width: int,
    color_func: Callable[[str], str] | None = None,
) -> int:
    """Wrap a string to ``wrap_width`` and draw it within a vertical bound.

    Convenience wrapper combining ``wrap_text`` + ``draw_wrapped_lines`` so callers
    don't repeat the same wrap-then-draw boilerplate. Empty / None ``text`` is a no-op.

    Returns:
        The Y coordinate after the last drawn line (``current_y`` if nothing drawn).
    """
    if not text:
        return current_y
    lines = wrap_text(text, wrap_width)
    return draw_wrapped_lines(backend, lines, start_x, current_y, max_y, color_func)


def draw_wrapped_text(
    backend: RenderBackend,
    text: str | None,
    start_x: int,
    current_y: int,
    max_y: int,
    wrap_width: int,
    color: str | None = None,
    bold: bool = False,
) -> int:
    """Wrap a string and draw it through ``backend.draw_text``.

    The same job as :func:`draw_text_block`, but going through the backend's
    ``draw_text`` with a colour *name* instead of printing with a colour
    *function*. That keeps the drawing observable: ``TestBackend`` records each
    line as a ``DrawCall``, so tests can assert on what was drawn rather than
    capturing stdout.

    Args:
        backend: Render backend instance
        text: Text to wrap and draw. Empty or None is a no-op.
        start_x: X coordinate for each line
        current_y: Starting Y coordinate
        max_y: Stop drawing before this Y coordinate
        wrap_width: Width to wrap the text to
        color: Colour name (e.g. "black", "blue")
        bold: Whether to draw bold

    Returns:
        The Y coordinate after the last drawn line
    """
    if not text:
        return current_y
    for line in wrap_text(text, wrap_width):
        if current_y >= max_y:
            break
        backend.draw_text(start_x, current_y, line, color, bold=bold)
        current_y += 1
    return current_y
