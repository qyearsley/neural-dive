"""Shared low-level drawing primitives.

Wrapped-text drawing, used by the overlay and question renderers. This is the
piece that would otherwise be copied into each renderer.

Everything here draws through ``backend.draw_text``. There used to be a second
set of helpers that took a colour *function* and ``print``ed the result --
``get_color_func``, ``draw_wrapped_lines``, ``draw_text_block``. They are gone:
output that bypasses the backend is output no test can record, which is what
kept twelve rendering tests skipped.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from neural_dive.conversation import wrap_text

if TYPE_CHECKING:
    from neural_dive.backends import RenderBackend


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
