"""Tests for short-answer matching.

Focused on the complexity matcher, which is the one with real logic in it:
a word, a notation and a Big-O expression all have to compare equal when they
name the same complexity.
"""

from __future__ import annotations

import doctest
import unittest

from neural_dive import answer_matching
from neural_dive.answer_matching import (
    COMPLEXITY_SYNONYMS,
    match_answer,
    matches_complexity,
    matches_exact,
    matches_numeric,
    normalize_answer,
)


class TestModuleDoctests(unittest.TestCase):
    """Run the module's doctests, which nothing else did.

    Every matcher documents itself with examples and none of them were
    executed, so the examples were free to drift from the code.
    """

    def test_doctests_pass(self):
        results = doctest.testmod(answer_matching, verbose=False)

        self.assertEqual(results.failed, 0)
        self.assertGreater(results.attempted, 0)


class TestCanonicalWordMatchesItsOwnNotation(unittest.TestCase):
    """The regression guard for the synonym groups.

    ``COMPLEXITY_SYNONYMS`` maps "constant" to ["1", "o(1)", "constanttime"],
    and the key was not a member of its own list. The lookup asks whether both
    answers are in the same group, so the canonical word never matched the
    notation it is a synonym for: `matches_complexity("linear", "O(n)")` was
    False. "constant time" worked, because that spelling *is* in the list.

    No shipped question was broken -- all four ``match_type: complexity``
    questions spell out both forms in ``correct_answer`` -- so this was a trap
    for the next question author rather than a live bug.
    """

    def test_word_matches_notation(self):
        for word, notation in (
            ("constant", "O(1)"),
            ("linear", "O(n)"),
            ("logarithmic", "O(log n)"),
            ("quadratic", "O(n^2)"),
        ):
            with self.subTest(word=word):
                self.assertTrue(matches_complexity(word, notation))

    def test_notation_matches_word(self):
        for word, notation in (
            ("constant", "O(1)"),
            ("linear", "O(n)"),
            ("logarithmic", "O(log n)"),
            ("quadratic", "O(n^2)"),
        ):
            with self.subTest(word=word):
                self.assertTrue(matches_complexity(notation, word))

    def test_every_key_matches_every_synonym_of_its_group(self):
        """The property the groups exist for, checked over the whole table."""
        for key, synonyms in COMPLEXITY_SYNONYMS.items():
            for synonym in synonyms:
                with self.subTest(key=key, synonym=synonym):
                    self.assertTrue(matches_complexity(key, synonym))
                    self.assertTrue(matches_complexity(synonym, key))

    def test_different_complexities_still_do_not_match(self):
        for user, correct in (
            ("linear", "O(n^2)"),
            ("constant", "linear"),
            ("O(n)", "O(log n)"),
            ("exponential", "cubic"),
        ):
            with self.subTest(user=user, correct=correct):
                self.assertFalse(matches_complexity(user, correct))


class TestComplexityMatchingBasics(unittest.TestCase):
    def test_alternatives_separated_by_pipe(self):
        self.assertTrue(matches_complexity("linear", "O(n)|linear"))
        self.assertTrue(matches_complexity("O(n)", "O(n)|linear"))

    def test_whitespace_and_case_are_ignored(self):
        self.assertTrue(matches_complexity("  o( N )  ", "O(n)"))

    def test_spelled_out_time_suffix(self):
        self.assertTrue(matches_complexity("constant time", "O(1)"))
        self.assertTrue(matches_complexity("linearithmic", "O(n log n)"))

    def test_unrelated_text_does_not_match(self):
        self.assertFalse(matches_complexity("no idea", "O(n)"))
        self.assertFalse(matches_complexity("", "O(n)"))


class TestNormalizeAnswer(unittest.TestCase):
    def test_strips_all_whitespace_and_lowercases(self):
        self.assertEqual(normalize_answer("  O( N )  "), "o(n)")


class TestExactAndNumericMatching(unittest.TestCase):
    def test_exact_is_case_insensitive_by_default(self):
        self.assertTrue(matches_exact("dfs", "DFS|Depth-First Search"))

    def test_exact_honours_case_sensitivity(self):
        self.assertFalse(matches_exact("bfs", "BFS", case_sensitive=True))

    def test_numeric_within_tolerance(self):
        self.assertTrue(matches_numeric("3.14", "3.14159"))
        self.assertFalse(matches_numeric("50", "100"))

    def test_numeric_rejects_non_numbers(self):
        self.assertFalse(matches_numeric("about ten", "10"))


class TestMatchAnswerDispatch(unittest.TestCase):
    def test_dispatches_to_complexity(self):
        self.assertTrue(match_answer("linear", "O(n)", match_type="complexity"))

    def test_unknown_match_type_falls_back_to_exact(self):
        self.assertTrue(match_answer("DFS", "dfs", match_type="not_a_type"))
        self.assertFalse(match_answer("linear", "O(n)", match_type="not_a_type"))


if __name__ == "__main__":
    unittest.main()
