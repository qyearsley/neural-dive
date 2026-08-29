"""
Unit tests for conversation utilities.
"""

import random
import unittest

from neural_dive.conversation import (
    _weighted_sample,
    create_randomized_conversation,
    randomize_answers,
    wrap_text,
)
from neural_dive.enums import NPCType
from neural_dive.models import Answer, Conversation, Question


def _pool(size: int) -> list[Question]:
    """Build a pool of distinguishable questions with stable ids."""
    return [
        Question(
            question_text=f"Question {i}?",
            answers=[Answer("Yes", True, "Correct!")],
            topic="test",
            question_id=f"q{i}",
        )
        for i in range(size)
    ]


def _conversation(size: int) -> Conversation:
    """Build a conversation whose NPC owns ``size`` questions."""
    return Conversation(
        npc_name="TEST_NPC",
        greeting="Hello!",
        questions=_pool(size),
        npc_type=NPCType.SPECIALIST,
    )


class TestRandomization(unittest.TestCase):
    """Test answer and question randomization"""

    def test_randomize_answers(self):
        """Test that answers are randomized"""
        answers = [
            Answer("A", False, "No."),
            Answer("B", False, "No."),
            Answer("C", True, "Yes!"),
            Answer("D", False, "No."),
        ]
        question = Question(question_text="Test?", answers=answers, topic="test")

        # Randomize with seed for reproducibility
        randomized = randomize_answers(question, seed=42)

        # Should have same answers but potentially different order
        self.assertEqual(len(randomized.answers), len(question.answers))
        self.assertEqual(
            {a.text for a in randomized.answers},
            {a.text for a in question.answers},
        )

        # At least verify they're the same question
        self.assertEqual(randomized.question_text, question.question_text)
        self.assertEqual(randomized.topic, question.topic)


class TestWeightedQuestionSelection(unittest.TestCase):
    """Test biasing question selection toward previously missed questions."""

    def test_unweighted_selection_is_unchanged(self):
        """Without weights the subset is the plain uniform sample it always was."""
        conv = _conversation(6)

        selected = create_randomized_conversation(
            conv,
            randomize_question_order=False,
            randomize_answer_order=False,
            seed=42,
            num_questions=2,
        )

        random.seed(42)
        expected = random.sample(conv.questions, 2)

        self.assertEqual(
            [q.question_id for q in selected.questions],
            [q.question_id for q in expected],
        )

    def test_weighted_selection_favours_the_heavy_question(self):
        conv = _conversation(6)

        def weight(question):
            return 3.0 if question.question_id == "q3" else 1.0

        picks = 0
        for seed in range(200):
            selected = create_randomized_conversation(
                conv,
                randomize_question_order=False,
                randomize_answer_order=False,
                seed=seed,
                num_questions=1,
                question_weight=weight,
            )
            if selected.questions[0].question_id == "q3":
                picks += 1

        # Uniform selection would pick it about 33 times in 200.
        self.assertGreater(picks, 60)

    def test_weighted_selection_still_reaches_every_question(self):
        conv = _conversation(4)

        def weight(question):
            return 3.0 if question.question_id == "q0" else 0.5

        seen = set()
        for seed in range(200):
            selected = create_randomized_conversation(
                conv,
                randomize_question_order=False,
                randomize_answer_order=False,
                seed=seed,
                num_questions=1,
                question_weight=weight,
            )
            seen.add(selected.questions[0].question_id)

        self.assertEqual(seen, {"q0", "q1", "q2", "q3"})

    def test_weights_do_not_change_how_many_questions_are_asked(self):
        conv = _conversation(8)

        selected = create_randomized_conversation(
            conv,
            seed=7,
            num_questions=3,
            question_weight=lambda q: 5.0 if q.question_id == "q1" else 1.0,
        )

        self.assertEqual(len(selected.questions), 3)

    def test_a_small_pool_is_used_whole_regardless_of_weights(self):
        conv = _conversation(2)

        selected = create_randomized_conversation(
            conv,
            randomize_question_order=False,
            randomize_answer_order=False,
            seed=7,
            num_questions=5,
            question_weight=lambda q: 0.5,
        )

        self.assertEqual({q.question_id for q in selected.questions}, {"q0", "q1"})

    def test_weighted_sample_never_repeats_a_question(self):
        questions = _pool(5)
        random.seed(1)

        chosen = _weighted_sample(questions, lambda q: 1.0, 5)

        self.assertEqual(len({q.question_id for q in chosen}), 5)

    def test_weighted_sample_tolerates_zero_weights(self):
        questions = _pool(3)
        random.seed(1)

        chosen = _weighted_sample(questions, lambda q: 0.0, 2)

        self.assertEqual(len(chosen), 2)


class TestWrapText(unittest.TestCase):
    """Test text wrapping functionality"""

    def test_wrap_short_text(self):
        """Test wrapping text that fits in one line"""
        text = "Hello world"
        lines = wrap_text(text, width=50)

        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0], "Hello world")

    def test_wrap_long_text(self):
        """Test wrapping text that needs multiple lines"""
        text = "This is a very long piece of text that definitely needs to be wrapped"
        lines = wrap_text(text, width=20)

        self.assertGreater(len(lines), 1)
        for line in lines:
            self.assertLessEqual(len(line), 20)

    def test_wrap_respects_words(self):
        """Test that wrapping doesn't break words"""
        text = "The quick brown fox jumps over the lazy dog"
        lines = wrap_text(text, width=15)

        for line in lines:
            # No partial words (except potentially at line boundaries)
            words = line.split()
            for word in words:
                self.assertIn(word, text.split())

    def test_wrap_empty_text(self):
        """Test wrapping empty text"""
        text = ""
        lines = wrap_text(text, width=50)

        self.assertEqual(len(lines), 0)

    def test_wrap_single_word(self):
        """Test wrapping a single word"""
        text = "Supercalifragilisticexpialidocious"
        lines = wrap_text(text, width=50)

        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0], text)


if __name__ == "__main__":
    unittest.main()
