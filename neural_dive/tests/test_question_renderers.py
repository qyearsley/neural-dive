"""Tests for question_renderers.

Verifies that each strategy draws the expected text content (question stem,
answer choices, prompt labels), that it draws through the backend rather than
printing, and that the registry returns the right implementation per
``QuestionType``.

The renderers go through ``backend.draw_text``, so ``TestBackend`` records every
line as a ``DrawCall``. That lets these tests assert on position and colour too,
not just on the text.
"""

from __future__ import annotations

import unittest
from unittest.mock import Mock

from neural_dive.backends.test_backend import DrawCall, TestBackend
from neural_dive.managers.conversation_engine import ConversationEngine
from neural_dive.models import Answer, Question
from neural_dive.question_renderers import (
    MultipleChoiceRenderer,
    ShortAnswerRenderer,
    YesNoRenderer,
    get_display_width,
    get_question_renderer,
)
from neural_dive.question_types import QuestionType

OVERLAY_WIDTH = 80
OVERLAY_HEIGHT = 20


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


def _fake_game(eliminated: set[int] | None = None, text_buffer: str = "") -> Mock:
    """Build a minimal game stub with the state the renderers read.

    ``ConversationEngine`` is cheap, so use the real one rather than a Mock --
    the renderers read the typed answer and eliminated-answer set from it.
    """
    game = Mock()
    engine = ConversationEngine()
    engine.eliminated_answers = eliminated or set()
    engine.text_input_buffer = text_buffer
    game.conversation_engine = engine
    game.player_manager.has_item_type.return_value = False
    return game


def _fake_colors() -> Mock:
    colors = Mock()
    colors.ui_error = "red"
    return colors


def _render(
    renderer,
    backend: TestBackend,
    question: Question,
    *,
    game: Mock | None = None,
    question_number: int = 1,
    total_questions: int = 1,
) -> None:
    """Render a question with the fixed overlay geometry these tests assume."""
    renderer.render(
        term=backend,
        question=question,
        question_number=question_number,
        total_questions=total_questions,
        start_x=0,
        start_y=0,
        current_y=2,
        overlay_width=OVERLAY_WIDTH,
        overlay_height=OVERLAY_HEIGHT,
        colors=_fake_colors(),
        game=game if game is not None else _fake_game(),
    )


def _text_calls(backend: TestBackend) -> list[DrawCall]:
    """Every text-drawing call the renderer made, in order."""
    return [call for call in backend.draw_calls if call.call_type == "text"]


def _drawn_text(backend: TestBackend) -> str:
    """All drawn text joined by newlines, for substring assertions."""
    return "\n".join(call.text for call in _text_calls(backend))


class TestMultipleChoiceRenderer(unittest.TestCase):
    def setUp(self) -> None:
        self.renderer = MultipleChoiceRenderer()
        self.backend = TestBackend()

    def test_renders_question_text(self):
        _render(self.renderer, self.backend, _make_mc_question(), total_questions=3)

        drawn = _drawn_text(self.backend)
        self.assertIn("What is 2+2?", drawn)
        self.assertIn("Q1/3", drawn)

    def test_draws_through_the_backend_rather_than_printing(self):
        _render(self.renderer, self.backend, _make_mc_question())

        # If the renderer went back to print(), there would be no recorded calls.
        self.assertTrue(_text_calls(self.backend))

    def test_renders_all_answer_choices(self):
        question = _make_mc_question()

        _render(self.renderer, self.backend, question)

        drawn = _drawn_text(self.backend)
        for i, ans in enumerate(question.answers, start=1):
            self.assertIn(f"{i}. {ans.text}", drawn)

    def test_skips_eliminated_answers(self):
        _render(
            self.renderer,
            self.backend,
            _make_mc_question(),
            game=_fake_game(eliminated={0, 2}),
        )

        drawn = _drawn_text(self.backend)
        self.assertNotIn("1. 3", drawn)
        self.assertNotIn("3. 5", drawn)
        self.assertIn("2. 4", drawn)
        self.assertIn("4. 22", drawn)

    def test_renders_instructions_footer(self):
        _render(self.renderer, self.backend, _make_mc_question())

        footer = next(call for call in _text_calls(self.backend) if "ESC/Q to exit" in call.text)
        self.assertIn("Press 1-4 to answer", footer.text)
        # Pinned to the overlay's second-to-last row, in the error colour
        self.assertEqual(footer.y, OVERLAY_HEIGHT - 2)
        self.assertEqual(footer.color, "red")
        self.assertTrue(footer.bold)

    def test_question_stem_is_bold_and_answers_are_not(self):
        _render(self.renderer, self.backend, _make_mc_question())

        stem = next(call for call in _text_calls(self.backend) if "What is 2+2?" in call.text)
        choice = next(call for call in _text_calls(self.backend) if call.text == "1. 3")
        self.assertTrue(stem.bold)
        self.assertEqual(stem.color, "black")
        self.assertFalse(choice.bold)
        self.assertEqual(choice.color, "blue")

    def test_stops_drawing_answers_at_the_overlay_bottom(self):
        # Long answers wrap to many lines; nothing may be drawn below the footer row.
        question = Question(
            question_text="Pick one",
            topic="math",
            question_type=QuestionType.MULTIPLE_CHOICE,
            answers=[
                Answer(text=f"choice {i} " + "padding " * 20, correct=False, response="")
                for i in range(4)
            ],
        )

        _render(self.renderer, self.backend, question)

        answer_rows = [call.y for call in _text_calls(self.backend) if call.color == "blue"]
        self.assertTrue(answer_rows)
        self.assertLessEqual(max(answer_rows), OVERLAY_HEIGHT - 2)


class TestShortAnswerRenderer(unittest.TestCase):
    def test_renders_question_and_input_prompt(self):
        question = Question(
            question_text="Big-O of binary search?",
            topic="algorithms",
            question_type=QuestionType.SHORT_ANSWER,
            correct_answer="log n",
        )
        backend = TestBackend()

        _render(
            ShortAnswerRenderer(),
            backend,
            question,
            game=_fake_game(text_buffer="log"),
        )

        drawn = _drawn_text(backend)
        self.assertIn("Big-O of binary search?", drawn)
        self.assertIn("Your answer:", drawn)
        self.assertIn("log", drawn)
        self.assertIn("Type your answer", drawn)

    def test_draws_the_input_box_and_the_typed_text(self):
        question = Question(
            question_text="Big-O of binary search?",
            topic="algorithms",
            question_type=QuestionType.SHORT_ANSWER,
            correct_answer="log n",
        )
        backend = TestBackend()

        _render(ShortAnswerRenderer(), backend, question, game=_fake_game(text_buffer="log"))

        calls = _text_calls(backend)
        # The box is drawn in three segments on the text row: left border, the
        # typed text, then padding and the right border.
        typed = next(call for call in calls if call.text == "log")
        left_border = next(call for call in calls if call.text == "│ " and call.y == typed.y)
        self.assertEqual(left_border.x, 2)
        self.assertEqual(typed.x, 4)
        self.assertEqual(typed.color, "black")
        self.assertEqual(left_border.color, "blue")
        # Top and bottom rules
        self.assertTrue(any(call.text.startswith("┌") for call in calls))
        self.assertTrue(any(call.text.startswith("└") for call in calls))

    def test_truncates_typed_text_that_overflows_the_box(self):
        question = Question(
            question_text="Long?",
            topic="algorithms",
            question_type=QuestionType.SHORT_ANSWER,
            correct_answer="x",
        )
        backend = TestBackend()
        long_answer = "x" * 200

        _render(ShortAnswerRenderer(), backend, question, game=_fake_game(text_buffer=long_answer))

        typed = next(call for call in _text_calls(backend) if call.text.startswith("xxx"))
        self.assertLessEqual(get_display_width(typed.text), OVERLAY_WIDTH - 10)


class TestYesNoRenderer(unittest.TestCase):
    def test_renders_yes_no_prompt(self):
        question = Question(
            question_text="Is the heap balanced?",
            topic="algorithms",
            question_type=QuestionType.YES_NO,
            correct_answer="yes",
        )
        backend = TestBackend()

        _render(YesNoRenderer(), backend, question, question_number=2, total_questions=2)

        drawn = _drawn_text(backend)
        self.assertIn("Is the heap balanced?", drawn)
        self.assertIn("Answer (yes/no):", drawn)
        self.assertIn("Press Y/N", drawn)


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
