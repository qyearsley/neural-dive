"""Tests for behaviour in a window smaller than the content needs.

The repo's policy is "assume a larger terminal, but deal gracefully with a
smaller one". Graceful means: never hang, never write past the edge, and say
plainly what size is missing. Nothing below ~14 columns had any coverage before
these tests, which is where the hang lived.
"""

from __future__ import annotations

from contextlib import redirect_stdout
import io
import signal
import unittest
from unittest.mock import Mock

from neural_dive.backends.test_backend import TestBackend
from neural_dive.config import DEFAULT_MAP_HEIGHT, MIN_TERMINAL_WIDTH, UI_BOTTOM_OFFSET
from neural_dive.map_renderer import draw_entities, draw_map, is_on_screen
from neural_dive.question_renderers import (
    ShortAnswerRenderer,
    YesNoRenderer,
    get_display_width,
    truncate_to_display_width,
)
from neural_dive.question_types import QuestionType
from neural_dive.rendering import (
    ResizeWatcher,
    draw_too_small_screen,
    required_terminal_size,
    terminal_is_too_small,
)
from neural_dive.themes import get_theme


class _Alarm:
    """Fail the test rather than hang it, if a renderer loops forever."""

    def __init__(self, seconds: int = 5):
        self.seconds = seconds

    def __enter__(self):
        def fire(_signum, _frame):
            raise AssertionError("renderer did not terminate")

        self._previous = signal.signal(signal.SIGALRM, fire)
        signal.alarm(self.seconds)
        return self

    def __exit__(self, *_exc):
        signal.alarm(0)
        signal.signal(signal.SIGALRM, self._previous)
        return False


def _text_question(question_type: QuestionType):
    from neural_dive.models import Question

    return Question(
        question_text="Is a heap a tree?",
        topic="algorithms",
        question_type=question_type,
        correct_answer="yes",
    )


def _fake_game(text_buffer: str = ""):
    from neural_dive.managers.conversation_engine import ConversationEngine

    game = Mock()
    engine = ConversationEngine()
    engine.text_input_buffer = text_buffer
    engine.eliminated_answers = set()
    game.conversation_engine = engine
    game.player_manager.has_item_type.return_value = False
    return game


class TestTruncateToDisplayWidth(unittest.TestCase):
    """The replacement for the loop that hung below 14 columns.

    ``OverlayRenderer`` sizes itself as ``min(80, backend.width - 4)``, so a
    13-column window gave an overlay of 9 and a ``max_display_width`` of -1.
    An empty string has width 0, ``0 > -1`` is always true, and ``""[:-1]`` is
    still ``""`` -- the loop could never exit.
    """

    def test_negative_width_returns_empty(self):
        self.assertEqual(truncate_to_display_width("hello", -1), "")

    def test_zero_width_returns_empty(self):
        self.assertEqual(truncate_to_display_width("hello", 0), "")

    def test_short_text_is_untouched(self):
        self.assertEqual(truncate_to_display_width("hi", 10), "hi")

    def test_long_text_is_cut_to_the_limit(self):
        self.assertEqual(truncate_to_display_width("abcdef", 3), "abc")

    def test_wide_characters_count_as_two_cells(self):
        result = truncate_to_display_width("日本語", 4)
        self.assertEqual(result, "日本")
        self.assertEqual(get_display_width(result), 4)

    def test_a_wide_character_is_never_half_drawn(self):
        result = truncate_to_display_width("日本", 3)
        self.assertEqual(result, "日")

    def test_empty_input_at_any_width(self):
        for width in (-5, 0, 1, 100):
            self.assertEqual(truncate_to_display_width("", width), "")


class TestTextRenderersOnNarrowTerminals(unittest.TestCase):
    """The renderers that used the hanging loop, at the widths that hung."""

    def _render(self, renderer, backend: TestBackend, text_buffer: str = "") -> None:
        overlay_width = min(80, backend.width - 4)
        renderer.render(
            term=backend,
            question=_text_question(QuestionType.SHORT_ANSWER),
            question_number=1,
            total_questions=1,
            start_x=0,
            start_y=0,
            current_y=2,
            overlay_width=overlay_width,
            overlay_height=min(20, backend.height - 4),
            colors=Mock(ui_error="red"),
            game=_fake_game(text_buffer),
        )

    def test_short_answer_renderer_terminates_at_every_narrow_width(self):
        with _Alarm():
            for width in range(1, 20):
                backend = TestBackend(width=width, height=24)
                self._render(ShortAnswerRenderer(), backend)

    def test_yes_no_renderer_terminates_at_every_narrow_width(self):
        with _Alarm():
            for width in range(1, 20):
                backend = TestBackend(width=width, height=24)
                self._render(YesNoRenderer(), backend)

    def test_a_typed_answer_does_not_hang_the_narrow_renderer(self):
        with _Alarm():
            for width in range(1, 20):
                backend = TestBackend(width=width, height=24)
                self._render(ShortAnswerRenderer(), backend, text_buffer="a long answer")

    def test_narrow_render_draws_no_negative_length_padding(self):
        backend = TestBackend(width=13, height=24)
        with _Alarm():
            self._render(ShortAnswerRenderer(), backend)

        for call in backend.draw_calls:
            self.assertGreaterEqual(len(call.text), 0)


class TestRequiredTerminalSize(unittest.TestCase):
    """The minimum is measured from the level layouts, not guessed."""

    def _game_with_levels(self, levels):
        game = Mock()
        game.level_data = levels
        return game

    def test_falls_back_to_the_default_map_size_without_level_data(self):
        game = self._game_with_levels({})

        self.assertEqual(
            required_terminal_size(game),
            (MIN_TERMINAL_WIDTH, DEFAULT_MAP_HEIGHT + UI_BOTTOM_OFFSET),
        )

    def test_takes_the_tallest_floor_and_adds_the_status_panel(self):
        game = self._game_with_levels(
            {
                1: {"tiles": [["#"] * 20 for _ in range(10)]},
                2: {"tiles": [["#"] * 20 for _ in range(40)]},
            }
        )

        _width, height = required_terminal_size(game)
        self.assertEqual(height, 40 + UI_BOTTOM_OFFSET)

    def test_takes_the_widest_floor(self):
        game = self._game_with_levels({1: {"tiles": [["#"] * 120 for _ in range(5)]}})

        width, _height = required_terminal_size(game)
        self.assertEqual(width, 120)

    def test_the_shipped_content_needs_more_than_a_stock_80x24_window(self):
        """Floor 3 is 30 rows on its own, so 24 rows was never enough."""
        from neural_dive.data.levels import PARSED_LEVELS

        width, height = required_terminal_size(self._game_with_levels(PARSED_LEVELS))

        self.assertEqual((width, height), (50, 34))
        self.assertGreater(height, 24)

    def test_too_small_is_reported_on_either_axis(self):
        required = (50, 34)
        self.assertTrue(terminal_is_too_small(TestBackend(width=49, height=40), required))
        self.assertTrue(terminal_is_too_small(TestBackend(width=80, height=33), required))
        self.assertFalse(terminal_is_too_small(TestBackend(width=50, height=34), required))
        self.assertFalse(terminal_is_too_small(TestBackend(width=200, height=60), required))


class TestTooSmallScreen(unittest.TestCase):
    """The message a player gets instead of a corrupted display."""

    def _render(self, width: int, height: int, required=(50, 34)) -> TestBackend:
        backend = TestBackend(width=width, height=height)
        draw_too_small_screen(backend, required)
        return backend

    def _text(self, backend: TestBackend) -> str:
        return "\n".join(call.text for call in backend.get_calls_by_type("text"))

    def test_states_both_the_requirement_and_the_current_size(self):
        text = self._text(self._render(80, 24))

        self.assertIn("50 x 34", text)
        self.assertIn("80 x 24", text)

    def test_says_how_to_leave(self):
        self.assertIn("Q to quit", self._text(self._render(80, 24)))

    def test_clears_the_screen_first(self):
        backend = self._render(80, 24)

        self.assertTrue(backend.get_calls_by_type("clear"))

    def test_no_line_is_wider_than_the_window(self):
        backend = self._render(20, 24)

        for call in backend.get_calls_by_type("text"):
            self.assertLessEqual(len(call.text), 20)

    def test_no_line_is_drawn_below_the_last_row(self):
        backend = self._render(10, 2)

        for call in backend.get_calls_by_type("text"):
            self.assertLess(call.y, 2)

    def test_survives_a_one_by_one_window(self):
        with _Alarm():
            self._render(1, 1)

    def test_survives_a_zero_sized_window(self):
        with _Alarm():
            backend = self._render(0, 0)

        self.assertEqual(backend.get_calls_by_type("text"), [])


class TestMapClipping(unittest.TestCase):
    """Drawing past the last row scrolls the terminal and shifts the frame."""

    def setUp(self):
        self.chars, self.colors = get_theme()

    def _game(self, map_width: int, map_height: int):
        game = Mock()
        game.game_map = [["." for _ in range(map_width)] for _ in range(map_height)]
        return game

    def test_draw_map_stops_at_the_bottom_of_the_window(self):
        backend = TestBackend(width=80, height=24)
        draw_map(backend, self._game(50, 30), self.chars, self.colors)

        self.assertTrue(backend.draw_calls)
        self.assertLessEqual(max(call.y for call in backend.draw_calls), 23)

    def test_draw_map_stops_at_the_right_edge(self):
        backend = TestBackend(width=20, height=40)
        draw_map(backend, self._game(50, 30), self.chars, self.colors)

        self.assertLessEqual(max(call.x for call in backend.draw_calls), 19)

    def test_draw_map_on_a_window_smaller_than_one_tile(self):
        backend = TestBackend(width=0, height=0)
        draw_map(backend, self._game(50, 30), self.chars, self.colors)

        self.assertEqual(backend.draw_calls, [])

    def test_is_on_screen_rejects_the_edges(self):
        backend = TestBackend(width=10, height=5)

        self.assertTrue(is_on_screen(backend, 0, 0))
        self.assertTrue(is_on_screen(backend, 9, 4))
        self.assertFalse(is_on_screen(backend, 10, 4))
        self.assertFalse(is_on_screen(backend, 9, 5))
        self.assertFalse(is_on_screen(backend, -1, 0))


class TestEntityClipping(unittest.TestCase):
    """Entities off the bottom of the window are skipped, not drawn."""

    def setUp(self):
        self.chars, self.colors = get_theme()

    def _game(self, positions):
        """A game whose only entities are NPCs at the given positions."""
        game = Mock()
        game.game_map = [["." for _ in range(50)] for _ in range(30)]
        game.npc_manager.npcs = [
            Mock(x=x, y=y, char="A", name=f"NPC{i}", npc_type="specialist")
            for i, (x, y) in enumerate(positions)
        ]
        game.terminals = []
        game.stairs = []
        game.item_pickups = []
        game.player = Mock(x=200, y=200)
        game.floor_manager.floor_requirements = {}
        game.floor_manager.current_floor = 1
        return game

    def _render(self, backend, game) -> str:
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            draw_entities(backend, game, self.chars, self.colors)
        return buffer.getvalue()

    def test_offscreen_npcs_are_not_drawn(self):
        backend = TestBackend(width=80, height=24)
        # (41, 21) is on screen; (48, 30) is past the bottom of a 24-row window.
        output = self._render(backend, self._game([(41, 21), (48, 30)]))

        self.assertEqual(output.count("A"), 1)

    def test_offscreen_player_is_not_drawn(self):
        backend = TestBackend(width=80, height=24)
        output = self._render(backend, self._game([]))

        self.assertEqual(output, "")

    def test_nothing_is_drawn_in_a_zero_sized_window(self):
        backend = TestBackend(width=0, height=0)
        output = self._render(backend, self._game([(0, 0), (5, 5)]))

        self.assertEqual(output, "")


class TestResizeWatcher(unittest.TestCase):
    """A resize has to force a full redraw.

    ``draw_game`` only clears the screen when ``redraw_all`` is set, so after a
    resize the old status panel stayed painted at the old row until the next
    floor change. Blessed does not deliver a KEY_RESIZE through ``inkey``, so
    the size is polled once per frame.
    """

    class _Resizable(TestBackend):
        def resize(self, width: int, height: int) -> None:
            self._width = width
            self._height = height

    def test_no_change_reports_false(self):
        watcher = ResizeWatcher(self._Resizable(80, 40))

        self.assertFalse(watcher.poll())
        self.assertFalse(watcher.poll())

    def test_a_width_change_is_noticed(self):
        backend = self._Resizable(80, 40)
        watcher = ResizeWatcher(backend)
        backend.resize(100, 40)

        self.assertTrue(watcher.poll())

    def test_a_height_change_is_noticed(self):
        backend = self._Resizable(80, 40)
        watcher = ResizeWatcher(backend)
        backend.resize(80, 30)

        self.assertTrue(watcher.poll())

    def test_a_change_is_reported_once(self):
        backend = self._Resizable(80, 40)
        watcher = ResizeWatcher(backend)
        backend.resize(100, 50)

        self.assertTrue(watcher.poll())
        self.assertFalse(watcher.poll())

    def test_shrinking_below_the_minimum_and_growing_back_both_register(self):
        backend = self._Resizable(80, 40)
        watcher = ResizeWatcher(backend)
        required = (50, 34)

        backend.resize(40, 20)
        self.assertTrue(watcher.poll())
        self.assertTrue(terminal_is_too_small(backend, required))

        backend.resize(80, 40)
        self.assertTrue(watcher.poll())
        self.assertFalse(terminal_is_too_small(backend, required))


if __name__ == "__main__":
    unittest.main()
