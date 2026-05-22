"""Tests for question_renderers.

Verifies that each strategy renders the expected text content (question stem,
answer choices, prompt labels) and that the registry returns the right
implementation per ``QuestionType``.
"""

from __future__ import annotations

from contextlib import redirect_stdout
import io
import unittest
from unittest.mock import Mock

from neural_dive.backends.test_backend import TestBackend
from neural_dive.models import Answer, Question
from neural_dive.question_renderers import (
    MultipleChoiceRenderer,
    ShortAnswerRenderer,
    YesNoRenderer,
    get_display_width,
    get_question_renderer,
)
from neural_dive.question_types import QuestionType


def _make_mc_question() -> Question:
    return Question(
        question_text="What is 2+2?",
        topic="math",
        question_type=QuestionType.MULTIPLE_CHOICE,
        answers=[
            Answer(text="3", correct=False, response=""),
            Answer(text="4", correct=True, response=""),
            Answer(text="5", correct=False, response=""),
            Answer(text="22", correct=False, response=""),
        ],
    )


def _fake_game(eliminated: set[int] | None = None) -> Mock:
    """Build a minimal game stub with the attributes the renderers read."""
    game = Mock()
    game.eliminated_answers = eliminated or set()
    game.text_input_buffer = ""
    game.player_manager.has_item_type.return_value = False
    return game


def _fake_colors() -> Mock:
    colors = Mock()
    colors.ui_error = "red"
    return colors


def _render_and_capture(render_call) -> str:
    """Run a renderer and return everything it wrote to stdout."""
    buf = io.StringIO()
    with redirect_stdout(buf):
        render_call()
    return buf.getvalue()


class TestMultipleChoiceRenderer(unittest.TestCase):
    def setUp(self) -> None:
        self.renderer = MultipleChoiceRenderer()
        self.backend = TestBackend()

    def test_renders_question_text(self):
        question = _make_mc_question()

        output = _render_and_capture(
            lambda: self.renderer.render(
                term=self.backend,
                question=question,
                question_number=1,
                total_questions=3,
                start_x=0,
                start_y=0,
                current_y=2,
                overlay_width=80,
                overlay_height=20,
                colors=_fake_colors(),
                game=_fake_game(),
            )
        )

        self.assertIn("What is 2+2?", output)
        self.assertIn("Q1/3", output)

    def test_renders_all_answer_choices(self):
        question = _make_mc_question()

        output = _render_and_capture(
            lambda: self.renderer.render(
                term=self.backend,
                question=question,
                question_number=1,
                total_questions=1,
                start_x=0,
                start_y=0,
                current_y=2,
                overlay_width=80,
                overlay_height=20,
                colors=_fake_colors(),
                game=_fake_game(),
            )
        )

        for i, ans in enumerate(question.answers, start=1):
            self.assertIn(f"{i}. {ans.text}", output)

    def test_skips_eliminated_answers(self):
        question = _make_mc_question()

        output = _render_and_capture(
            lambda: self.renderer.render(
                term=self.backend,
                question=question,
                question_number=1,
                total_questions=1,
                start_x=0,
                start_y=0,
                current_y=2,
                overlay_width=80,
                overlay_height=20,
                colors=_fake_colors(),
                game=_fake_game(eliminated={0, 2}),
            )
        )

        self.assertNotIn("1. 3", output)
        self.assertNotIn("3. 5", output)
        self.assertIn("2. 4", output)
        self.assertIn("4. 22", output)

    def test_renders_instructions_footer(self):
        output = _render_and_capture(
            lambda: self.renderer.render(
                term=self.backend,
                question=_make_mc_question(),
                question_number=1,
                total_questions=1,
                start_x=0,
                start_y=0,
                current_y=2,
                overlay_width=80,
                overlay_height=20,
                colors=_fake_colors(),
                game=_fake_game(),
            )
        )

        self.assertIn("Press 1-4 to answer", output)
        self.assertIn("ESC/Q to exit", output)


class TestShortAnswerRenderer(unittest.TestCase):
    def test_renders_question_and_input_prompt(self):
        question = Question(
            question_text="Big-O of binary search?",
            topic="algorithms",
            question_type=QuestionType.SHORT_ANSWER,
            correct_answer="log n",
        )
        backend = TestBackend()
        game = _fake_game()
        game.text_input_buffer = "log"

        output = _render_and_capture(
            lambda: ShortAnswerRenderer().render(
                term=backend,
                question=question,
                question_number=1,
                total_questions=1,
                start_x=0,
                start_y=0,
                current_y=2,
                overlay_width=80,
                overlay_height=20,
                colors=_fake_colors(),
                game=game,
            )
        )

        self.assertIn("Big-O of binary search?", output)
        self.assertIn("Your answer:", output)
        self.assertIn("log", output)
        self.assertIn("Type your answer", output)


class TestYesNoRenderer(unittest.TestCase):
    def test_renders_yes_no_prompt(self):
        question = Question(
            question_text="Is the heap balanced?",
            topic="algorithms",
            question_type=QuestionType.YES_NO,
            correct_answer="yes",
        )

        output = _render_and_capture(
            lambda: YesNoRenderer().render(
                term=TestBackend(),
                question=question,
                question_number=2,
                total_questions=2,
                start_x=0,
                start_y=0,
                current_y=2,
                overlay_width=80,
                overlay_height=20,
                colors=_fake_colors(),
                game=_fake_game(),
            )
        )

        self.assertIn("Is the heap balanced?", output)
        self.assertIn("Answer (yes/no):", output)
        self.assertIn("Press Y/N", output)


class TestRendererRegistry(unittest.TestCase):
    def test_returns_multiple_choice_renderer(self):
        renderer = get_question_renderer(QuestionType.MULTIPLE_CHOICE)
        self.assertIsInstance(renderer, MultipleChoiceRenderer)

    def test_returns_short_answer_renderer(self):
        renderer = get_question_renderer(QuestionType.SHORT_ANSWER)
        self.assertIsInstance(renderer, ShortAnswerRenderer)

    def test_returns_yes_no_renderer(self):
        renderer = get_question_renderer(QuestionType.YES_NO)
        self.assertIsInstance(renderer, YesNoRenderer)


class TestDisplayWidth(unittest.TestCase):
    def test_ascii_width_equals_length(self):
        self.assertEqual(get_display_width("hello"), 5)

    def test_wide_chars_count_double(self):
        # CJK characters take 2 terminal cells each
        self.assertEqual(get_display_width("你好"), 4)

    def test_mixed_width(self):
        self.assertEqual(get_display_width("a你b"), 4)

    def test_empty_string(self):
        self.assertEqual(get_display_width(""), 0)


if __name__ == "__main__":
    unittest.main()
