"""Tests for the bottom status panel.

The panel prints escape sequences directly rather than going through
``backend.draw_text``, so these tests capture stdout. ``TestBackend`` emits no
escapes, which makes the captured text readable.
"""

from __future__ import annotations

from contextlib import redirect_stdout
import io
import unittest
from unittest.mock import Mock

from neural_dive.backends.test_backend import TestBackend
from neural_dive.config import COHERENCE_BAR_EMPTY_CHAR, COHERENCE_BAR_FILLED_CHAR
from neural_dive.themes import get_theme
from neural_dive.ui_renderer import (
    CONTROL_HINTS,
    CONVERSATION_HINTS,
    coherence_bar,
    coherence_color_name,
    draw_ui,
    floor_progress,
)


def _game(
    *,
    coherence: int = 80,
    max_coherence: int = 100,
    floor: int = 1,
    required: set[str] | None = None,
    completed: set[str] | None = None,
    in_conversation: bool = False,
) -> Mock:
    game = Mock()
    game.player_manager.coherence = coherence
    game.player_manager.max_coherence = max_coherence
    game.player_manager.knowledge_modules = []
    game.floor_manager.current_floor = floor
    game.floor_manager.max_floors = 3
    game.floor_manager.floor_requirements = {floor: required if required else set()}
    game.npcs_completed = completed if completed else set()
    game.get_current_score.return_value = 0
    game.message = ""
    game.conversation_engine.active_conversation = Mock() if in_conversation else None
    return game


def _render(backend: TestBackend, game: Mock) -> str:
    _chars, colors = get_theme()
    buffer = io.StringIO()
    with redirect_stdout(buffer):
        draw_ui(backend, game, colors)
    return buffer.getvalue()


class TestCoherenceMeter(unittest.TestCase):
    """Coherence used to print in the default attribute at every value.

    5/100 and 80/100 rendered identically, which hid the game's only failure
    condition.
    """

    def test_full_bar_at_full_coherence(self):
        bar = coherence_bar(100, 100)

        self.assertNotIn(COHERENCE_BAR_EMPTY_CHAR, bar)
        self.assertIn(COHERENCE_BAR_FILLED_CHAR, bar)

    def test_empty_bar_at_zero(self):
        self.assertNotIn(COHERENCE_BAR_FILLED_CHAR, coherence_bar(0, 100))

    def test_bar_is_a_fixed_width_whatever_the_value(self):
        widths = {len(coherence_bar(value, 100)) for value in (0, 1, 37, 50, 99, 100)}

        self.assertEqual(len(widths), 1)

    def test_bar_survives_a_zero_ceiling(self):
        self.assertNotIn(COHERENCE_BAR_FILLED_CHAR, coherence_bar(0, 0))

    def test_bar_clamps_above_the_ceiling(self):
        self.assertNotIn(COHERENCE_BAR_EMPTY_CHAR, coherence_bar(500, 100))

    def test_colour_bands_are_three_distinct_colours(self):
        _chars, colors = get_theme()
        healthy = coherence_color_name(80, 100, colors)
        warning = coherence_color_name(40, 100, colors)
        critical = coherence_color_name(10, 100, colors)

        self.assertEqual(len({healthy, warning, critical}), 3)

    def test_healthy_is_the_success_colour_and_critical_is_the_error_colour(self):
        _chars, colors = get_theme()

        self.assertEqual(coherence_color_name(100, 100, colors), colors.ui_success)
        self.assertEqual(coherence_color_name(0, 100, colors), colors.ui_error)

    def test_the_boundaries_land_on_the_more_cautious_band(self):
        _chars, colors = get_theme()

        self.assertEqual(coherence_color_name(50, 100, colors), colors.ui_warning)
        self.assertEqual(coherence_color_name(25, 100, colors), colors.ui_error)


class TestFloorProgress(unittest.TestCase):
    """There was no indication of how much of a layer was left."""

    def test_counts_completed_required_npcs(self):
        game = _game(required={"A", "B", "C"}, completed={"A", "C"})

        self.assertEqual(floor_progress(game), (2, 3))

    def test_completed_npcs_from_other_floors_do_not_count(self):
        game = _game(required={"A"}, completed={"A", "Z"})

        self.assertEqual(floor_progress(game), (1, 1))

    def test_a_floor_with_no_requirements_reports_zero_of_zero(self):
        self.assertEqual(floor_progress(_game()), (0, 0))

    def test_progress_appears_in_the_status_line(self):
        output = _render(TestBackend(width=100, height=40), _game(required={"A", "B"}))

        self.assertIn("NPCs 0/2", output)


class TestStatusLine(unittest.TestCase):
    def test_shows_layer_coherence_knowledge_and_score(self):
        output = _render(TestBackend(width=100, height=40), _game())

        self.assertIn("Layer 1/3", output)
        self.assertIn("Coherence 80/100", output)
        self.assertIn("Knowledge: 0", output)
        self.assertIn("Score: 0", output)

    def test_a_narrow_window_drops_whole_segments(self):
        """Not half a word: the panel must stay readable when it does not fit."""
        output = _render(TestBackend(width=30, height=40), _game())

        self.assertIn("Layer 1/3", output)
        self.assertNotIn("Score", output)

    def test_the_panel_renders_at_the_minimum_supported_width(self):
        output = _render(TestBackend(width=50, height=34), _game())

        self.assertIn("Layer 1/3", output)

    def test_coherence_survives_at_the_minimum_supported_width(self):
        """Coherence is drawn second precisely so a narrow window keeps it."""
        output = _render(TestBackend(width=50, height=34), _game())

        self.assertIn("Coherence 80/100", output)

    def test_the_meter_is_the_first_thing_dropped_when_the_line_is_tight(self):
        output = _render(TestBackend(width=50, height=34), _game())

        self.assertNotIn(COHERENCE_BAR_FILLED_CHAR, output)
        self.assertIn("NPCs 0/0", output)

    def test_a_wide_window_keeps_the_meter(self):
        output = _render(TestBackend(width=100, height=40), _game())

        self.assertIn(COHERENCE_BAR_FILLED_CHAR, output)

    def test_no_output_when_there_is_no_room_for_the_panel(self):
        output = _render(TestBackend(width=40, height=2), _game())

        self.assertEqual(output, "")


class TestHintLine(unittest.TestCase):
    """The hint line listed six keys and omitted five real ones."""

    def test_lists_the_keys_a_player_needs(self):
        output = _render(TestBackend(width=120, height=40), _game())

        for key in ("Arrows Move", "V Inventory", "? Help", "S Save", "L Load", "Q Quit"):
            self.assertIn(key, output)

    def test_conversation_mode_lists_the_conversation_keys(self):
        output = _render(TestBackend(width=120, height=40), _game(in_conversation=True))

        for key in ("1-4 Answer", "H Hint", "S Snippet", "ESC/X Leave"):
            self.assertIn(key, output)

    def test_help_survives_a_narrow_window(self):
        """ "? Help" is ordered early precisely so it is not the first casualty."""
        output = _render(TestBackend(width=60, height=40), _game())

        self.assertIn("? Help", output)

    def test_the_two_hint_sets_do_not_overlap_in_meaning(self):
        self.assertNotEqual(CONTROL_HINTS, CONVERSATION_HINTS)


if __name__ == "__main__":
    unittest.main()
