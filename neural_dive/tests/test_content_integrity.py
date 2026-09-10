"""Integrity checks for the shipped algorithms content set.

These are content tests, not code tests: they read
``neural_dive/data/content/algorithms/`` and assert the properties that make a
question set playable and fair. Two of them exist because the set had already
drifted -- 31 questions no NPC referenced, and a literal ``\\!`` escape that
rendered as a backslash in game.
"""

from __future__ import annotations

import json
import unittest

from neural_dive.data_loader import get_content_dir
from neural_dive.question_types import QuestionType

CONTENT_SET = "algorithms"


def _load(name: str) -> dict:
    with open(get_content_dir(CONTENT_SET) / name) as handle:
        loaded: dict = json.load(handle)
    return loaded


def _strings(node):
    if isinstance(node, str):
        yield node
    elif isinstance(node, dict):
        for value in node.values():
            yield from _strings(value)
    elif isinstance(node, list):
        for value in node:
            yield from _strings(value)


class TestQuestionNPCLinkage(unittest.TestCase):
    """Every question must be reachable, and every reference must resolve."""

    def setUp(self):
        self.questions = _load("questions.json")
        self.npcs = _load("npcs.json")
        self.referenced = {
            question_id for npc in self.npcs.values() for question_id in npc.get("questions", [])
        }

    def test_no_npc_references_a_missing_question(self):
        dangling = sorted(self.referenced - set(self.questions))
        self.assertEqual([], dangling)

    def test_no_question_is_orphaned(self):
        """An unreferenced question can never appear in a run."""
        orphans = sorted(set(self.questions) - self.referenced)
        self.assertEqual([], orphans)

    def test_no_npc_lists_the_same_question_twice(self):
        for name, npc in self.npcs.items():
            ids = npc.get("questions", [])
            self.assertEqual(len(ids), len(set(ids)), f"{name} repeats a question")


class TestQuestionSchema(unittest.TestCase):
    """Shape rules the loader and the renderers both assume."""

    def setUp(self):
        self.questions = _load("questions.json")

    def test_every_question_type_is_known(self):
        for question_id, data in self.questions.items():
            with self.subTest(question_id):
                QuestionType(data.get("type", "multiple_choice"))

    def test_multiple_choice_has_four_answers_and_one_correct(self):
        for question_id, data in self.questions.items():
            if data.get("type", "multiple_choice") != "multiple_choice":
                continue
            with self.subTest(question_id):
                answers = data["answers"]
                self.assertEqual(4, len(answers), "in-game keys are only 1-4")
                self.assertEqual(1, sum(1 for a in answers if a["correct"]))
                for answer in answers:
                    self.assertTrue(answer["text"].strip())
                    self.assertTrue(answer["response"].strip())

    def test_typed_questions_carry_their_answer_fields(self):
        for question_id, data in self.questions.items():
            question_type = data.get("type", "multiple_choice")
            if question_type == "multiple_choice":
                continue
            with self.subTest(question_id):
                self.assertTrue(data["correct_answer"].strip())
                self.assertTrue(data["correct_response"].strip())
                self.assertTrue(data["incorrect_response"].strip())

    def test_no_stray_backslash_escapes(self):
        """``\\!`` in the JSON decodes to a backslash and renders as one."""
        offenders = sorted(
            question_id
            for question_id, data in self.questions.items()
            if any("\\" in text for text in _strings(data))
        )
        self.assertEqual([], offenders)


class TestAnswerFairness(unittest.TestCase):
    """Two strategies that used to beat the game without knowing anything."""

    def setUp(self):
        self.questions = _load("questions.json")

    def test_the_longest_option_is_rarely_the_correct_one(self):
        """Answer order is shuffled at runtime, but answer length is not."""
        multiple_choice = [
            data
            for data in self.questions.values()
            if data.get("type", "multiple_choice") == "multiple_choice"
        ]
        strictly_longest = 0
        for data in multiple_choice:
            lengths = [(len(a["text"]), a["correct"]) for a in data["answers"]]
            longest = max(length for length, _ in lengths)
            correct = next(length for length, is_correct in lengths if is_correct)
            if correct == longest and sum(1 for x, _ in lengths if x == longest) == 1:
                strictly_longest += 1

        rate = strictly_longest / len(multiple_choice)
        self.assertLess(rate, 0.40, f"'pick the longest' wins {rate:.0%} of the time")

    def test_yes_no_questions_are_not_all_yes(self):
        yes_no = [data for data in self.questions.values() if data.get("type") == "yes_no"]
        self.assertGreater(len(yes_no), 0)
        yes = sum(
            1
            for data in yes_no
            if data["correct_answer"].split("|")[0].lower() in ("yes", "true", "y")
        )
        self.assertGreaterEqual(yes, len(yes_no) // 3)
        self.assertLessEqual(yes, len(yes_no) - len(yes_no) // 3)


class TestNPCPlacement(unittest.TestCase):
    """An NPC that is not on the map can never be talked to."""

    def test_every_npc_char_appears_in_its_floor_layout(self):
        from neural_dive.data.content.algorithms.levels import (
            PARSED_LEVELS,
            validate_npc_layout_consistency,
        )

        warnings = validate_npc_layout_consistency(_load("npcs.json"), PARSED_LEVELS)
        self.assertEqual([], warnings)


if __name__ == "__main__":
    unittest.main()
