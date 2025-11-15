"""
Unit tests for conversation utilities.
"""

import unittest

from neural_dive.conversation import randomize_answers, wrap_text
from neural_dive.models import Answer, Question


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
