"""Unit tests for the cross-run player profile.

Covers the store round-trip, the selection weighting formula, the summary
views, and every documented failure mode: a missing file, an unreadable one, a
non-object one, a profile written by a newer schema, individual malformed
records, question ids that have left the content set, and an unwritable
directory.
"""

from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from neural_dive.models import Question
from neural_dive.player_profile import (
    SCHEMA_VERSION,
    PlayerProfile,
    QuestionRecord,
    format_profile_summary,
    get_default_profile_path,
    weakest_topics,
)
from neural_dive.question_types import QuestionType


def _question(question_id: str, topic: str = "algorithms") -> Question:
    """Build a minimal question carrying an id and a topic."""
    return Question(
        question_text=f"Question {question_id}?",
        topic=topic,
        question_type=QuestionType.YES_NO,
        question_id=question_id,
        correct_answer="yes",
        correct_response="Yes.",
        incorrect_response="No.",
    )


class ProfileFileTestCase(unittest.TestCase):
    """Base fixture giving each test its own throwaway profile directory."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.tmp_path = Path(self._tmp.name)
        self.profile_path = self.tmp_path / "profile.json"

    def write_profile(self, text: str) -> None:
        """Write raw text to the profile path."""
        self.profile_path.write_text(text, encoding="utf-8")


class TestQuestionRecord(unittest.TestCase):
    """Test the per-question record."""

    def test_miss_rate_of_unseen_question_is_zero(self):
        self.assertEqual(QuestionRecord().miss_rate, 0.0)

    def test_miss_rate(self):
        record = QuestionRecord(seen=4, correct=1, wrong=3)
        self.assertAlmostEqual(record.miss_rate, 0.75)

    def test_miss_rate_is_clamped(self):
        # Inconsistent counts (wrong > seen) must not produce a rate above 1.
        record = QuestionRecord(seen=1, correct=0, wrong=9)
        self.assertEqual(record.miss_rate, 1.0)

    def test_from_dict_rejects_non_mapping(self):
        self.assertIsNone(QuestionRecord.from_dict("nonsense"))
        self.assertIsNone(QuestionRecord.from_dict(None))
        self.assertIsNone(QuestionRecord.from_dict([1, 2, 3]))

    def test_from_dict_rejects_unparseable_numbers(self):
        self.assertIsNone(QuestionRecord.from_dict({"seen": "many"}))

    def test_from_dict_clamps_negatives(self):
        record = QuestionRecord.from_dict({"seen": -5, "correct": -1, "wrong": -2, "last_seen": -9})
        assert record is not None
        self.assertEqual((record.seen, record.correct, record.wrong), (0, 0, 0))
        self.assertEqual(record.last_seen, 0.0)


class TestRecordingAnswers(unittest.TestCase):
    """Test accumulating outcomes in memory."""

    def test_records_accumulate(self):
        profile = PlayerProfile()
        profile.record_answer("cap_theorem", correct=False, now=100.0)
        profile.record_answer("cap_theorem", correct=False, now=200.0)
        profile.record_answer("cap_theorem", correct=True, now=300.0)

        record = profile.get("cap_theorem")
        assert record is not None
        self.assertEqual(record.seen, 3)
        self.assertEqual(record.correct, 1)
        self.assertEqual(record.wrong, 2)
        self.assertEqual(record.last_seen, 300.0)

    def test_empty_question_id_is_ignored(self):
        profile = PlayerProfile()
        profile.record_answer("", correct=False)

        self.assertTrue(profile.is_empty)

    def test_is_empty(self):
        profile = PlayerProfile()
        self.assertTrue(profile.is_empty)
        profile.record_answer("q", correct=True)
        self.assertFalse(profile.is_empty)

    def test_totals(self):
        profile = PlayerProfile()
        profile.record_answer("a", correct=True)
        profile.record_answer("a", correct=False)
        profile.record_answer("b", correct=True)

        self.assertEqual(profile.totals(), (3, 2, 1))

    def test_most_missed_orders_by_wrong_count_then_rate(self):
        profile = PlayerProfile(
            questions={
                "often": QuestionRecord(seen=20, correct=16, wrong=4),
                "always": QuestionRecord(seen=4, correct=0, wrong=4),
                "once": QuestionRecord(seen=3, correct=2, wrong=1),
                "never": QuestionRecord(seen=3, correct=3, wrong=0),
            }
        )

        ranked = [qid for qid, _ in profile.most_missed()]

        # Same wrong count, so the higher miss rate wins the tie.
        self.assertEqual(ranked, ["always", "often", "once"])

    def test_most_missed_respects_limit(self):
        profile = PlayerProfile(
            questions={f"q{i}": QuestionRecord(seen=1, wrong=1) for i in range(10)}
        )

        self.assertEqual(len(profile.most_missed(limit=3)), 3)


class TestSelectionWeight(unittest.TestCase):
    """Test the weight = 1 + 2 * miss_rate formula and its mastery demotion."""

    def test_unseen_question_has_base_weight(self):
        self.assertEqual(PlayerProfile().weight_for("unseen"), 1.0)

    def test_always_wrong_question_has_max_weight(self):
        profile = PlayerProfile(questions={"q": QuestionRecord(seen=3, correct=0, wrong=3)})
        self.assertAlmostEqual(profile.weight_for("q"), 3.0)

    def test_half_wrong_question_sits_in_the_middle(self):
        profile = PlayerProfile(questions={"q": QuestionRecord(seen=4, correct=2, wrong=2)})
        self.assertAlmostEqual(profile.weight_for("q"), 2.0)

    def test_answering_correctly_pulls_the_weight_back_down(self):
        profile = PlayerProfile()
        profile.record_answer("q", correct=False)
        missed_weight = profile.weight_for("q")
        profile.record_answer("q", correct=True)
        profile.record_answer("q", correct=True)

        self.assertAlmostEqual(missed_weight, 3.0)
        self.assertLess(profile.weight_for("q"), missed_weight)

    def test_mastered_question_is_demoted(self):
        profile = PlayerProfile(questions={"q": QuestionRecord(seen=2, correct=2, wrong=0)})
        self.assertEqual(profile.weight_for("q"), 0.5)

    def test_one_correct_answer_is_not_yet_mastery(self):
        profile = PlayerProfile(questions={"q": QuestionRecord(seen=1, correct=1, wrong=0)})
        self.assertEqual(profile.weight_for("q"), 1.0)

    def test_a_single_miss_prevents_mastery(self):
        profile = PlayerProfile(questions={"q": QuestionRecord(seen=5, correct=4, wrong=1)})
        self.assertGreater(profile.weight_for("q"), 1.0)

    def test_question_weighter_reads_the_question_id(self):
        profile = PlayerProfile(questions={"missed": QuestionRecord(seen=1, wrong=1)})
        weight = profile.question_weighter()

        self.assertAlmostEqual(weight(_question("missed")), 3.0)
        self.assertAlmostEqual(weight(_question("fresh")), 1.0)


class TestRoundTrip(ProfileFileTestCase):
    """Test writing a profile and reading it back."""

    def test_save_then_load(self):
        profile = PlayerProfile(content_set="algorithms", path=self.profile_path)
        profile.record_answer("cap_theorem", correct=False, now=1000.0)
        profile.record_answer("mutex_purpose", correct=True, now=2000.0)

        reloaded = PlayerProfile.load("algorithms", self.profile_path)

        self.assertEqual(len(reloaded.questions), 2)
        cap = reloaded.get("cap_theorem")
        assert cap is not None
        self.assertEqual((cap.seen, cap.correct, cap.wrong, cap.last_seen), (1, 0, 1, 1000.0))

    def test_record_answer_persists_immediately(self):
        profile = PlayerProfile(path=self.profile_path)
        profile.record_answer("q", correct=True)

        # No explicit save() call -- a run that is killed must not lose history.
        self.assertTrue(self.profile_path.exists())

    def test_written_file_has_the_documented_shape(self):
        profile = PlayerProfile(content_set="algorithms", path=self.profile_path)
        profile.record_answer("q", correct=True, now=5.0)

        data = json.loads(self.profile_path.read_text(encoding="utf-8"))

        self.assertEqual(data["schema_version"], SCHEMA_VERSION)
        self.assertEqual(
            data["content_sets"]["algorithms"]["questions"]["q"],
            {"seen": 1, "correct": 1, "wrong": 0, "last_seen": 5.0},
        )

    def test_save_leaves_no_temporary_file_behind(self):
        profile = PlayerProfile(path=self.profile_path)
        profile.record_answer("q", correct=True)

        self.assertEqual([p.name for p in self.tmp_path.iterdir()], ["profile.json"])

    def test_save_creates_the_directory(self):
        nested = self.tmp_path / "does" / "not" / "exist" / "profile.json"
        profile = PlayerProfile(path=nested)

        self.assertTrue(profile.save())
        self.assertTrue(nested.exists())

    def test_in_memory_profile_never_touches_disk(self):
        profile = PlayerProfile()
        profile.record_answer("q", correct=True)

        self.assertFalse(profile.save())
        self.assertEqual(list(self.tmp_path.iterdir()), [])

    def test_other_content_sets_are_preserved(self):
        self.write_profile(
            json.dumps(
                {
                    "schema_version": SCHEMA_VERSION,
                    "content_sets": {
                        "algorithms": {"questions": {"a": {"seen": 1, "correct": 1, "wrong": 0}}},
                        "spanish": {"questions": {"hola": {"seen": 9, "correct": 2, "wrong": 7}}},
                    },
                }
            )
        )

        profile = PlayerProfile.load("algorithms", self.profile_path)
        profile.record_answer("b", correct=False)

        data = json.loads(self.profile_path.read_text(encoding="utf-8"))
        self.assertEqual(
            data["content_sets"]["spanish"]["questions"]["hola"],
            {"seen": 9, "correct": 2, "wrong": 7},
        )
        self.assertEqual(set(data["content_sets"]["algorithms"]["questions"]), {"a", "b"})

    def test_default_path_is_beside_the_save_file(self):
        from neural_dive.game_serializer import GameSerializer

        self.assertEqual(
            get_default_profile_path().parent,
            GameSerializer.get_default_save_path().parent,
        )
        self.assertNotEqual(get_default_profile_path(), GameSerializer.get_default_save_path())


class TestLoadFailureModes(ProfileFileTestCase):
    """Every one of these must degrade to an empty profile, never raise."""

    def test_missing_file_gives_an_empty_profile(self):
        profile = PlayerProfile.load("algorithms", self.profile_path)

        self.assertTrue(profile.is_empty)
        self.assertFalse(profile.read_only)
        self.assertEqual(profile.path, self.profile_path)

    def test_unparseable_json_gives_an_empty_profile(self):
        self.write_profile("{ this is not json")

        with self.assertLogs("neural_dive.player_profile", level="WARNING"):
            profile = PlayerProfile.load("algorithms", self.profile_path)

        self.assertTrue(profile.is_empty)

    def test_unparseable_json_is_moved_aside_rather_than_overwritten(self):
        self.write_profile("{ this is not json")

        with self.assertLogs("neural_dive.player_profile", level="WARNING"):
            profile = PlayerProfile.load("algorithms", self.profile_path)
        profile.record_answer("q", correct=True)

        backup = self.tmp_path / "profile.json.corrupt"
        self.assertTrue(backup.exists())
        self.assertEqual(backup.read_text(encoding="utf-8"), "{ this is not json")
        self.assertTrue(self.profile_path.exists())

    def test_json_that_is_not_an_object_gives_an_empty_profile(self):
        self.write_profile("[1, 2, 3]")

        with self.assertLogs("neural_dive.player_profile", level="WARNING"):
            profile = PlayerProfile.load("algorithms", self.profile_path)

        self.assertTrue(profile.is_empty)

    def test_missing_content_sets_key_gives_an_empty_profile(self):
        self.write_profile(json.dumps({"schema_version": SCHEMA_VERSION}))

        with self.assertLogs("neural_dive.player_profile", level="WARNING"):
            profile = PlayerProfile.load("algorithms", self.profile_path)

        self.assertTrue(profile.is_empty)

    def test_unknown_content_set_gives_an_empty_profile(self):
        self.write_profile(
            json.dumps(
                {
                    "schema_version": SCHEMA_VERSION,
                    "content_sets": {"spanish": {"questions": {"hola": {"seen": 1}}}},
                }
            )
        )

        profile = PlayerProfile.load("algorithms", self.profile_path)

        self.assertTrue(profile.is_empty)
        self.assertFalse(profile.read_only)

    def test_newer_schema_is_ignored_and_left_alone(self):
        original = json.dumps(
            {
                "schema_version": SCHEMA_VERSION + 1,
                "content_sets": {"algorithms": {"questions": {"q": {"seen": 4, "wrong": 4}}}},
            }
        )
        self.write_profile(original)

        with self.assertLogs("neural_dive.player_profile", level="WARNING"):
            profile = PlayerProfile.load("algorithms", self.profile_path)

        self.assertTrue(profile.is_empty)
        self.assertTrue(profile.read_only)

        # A read-only profile still accepts answers in memory but refuses to
        # write, so an older build cannot clobber a newer one's file.
        profile.record_answer("q", correct=False)
        self.assertFalse(profile.save())
        self.assertEqual(self.profile_path.read_text(encoding="utf-8"), original)

    def test_non_integer_schema_version_is_treated_as_newer(self):
        self.write_profile(json.dumps({"schema_version": "one", "content_sets": {}}))

        with self.assertLogs("neural_dive.player_profile", level="WARNING"):
            profile = PlayerProfile.load("algorithms", self.profile_path)

        self.assertTrue(profile.read_only)

    def test_missing_schema_version_is_assumed_current(self):
        self.write_profile(
            json.dumps({"content_sets": {"algorithms": {"questions": {"q": {"seen": 1}}}}})
        )

        profile = PlayerProfile.load("algorithms", self.profile_path)

        self.assertFalse(profile.is_empty)
        self.assertFalse(profile.read_only)

    def test_malformed_records_are_skipped_and_the_rest_survive(self):
        self.write_profile(
            json.dumps(
                {
                    "schema_version": SCHEMA_VERSION,
                    "content_sets": {
                        "algorithms": {
                            "questions": {
                                "good": {"seen": 2, "correct": 1, "wrong": 1},
                                "bad": "not a record",
                                "worse": {"seen": "many"},
                            }
                        }
                    },
                }
            )
        )

        with self.assertLogs("neural_dive.player_profile", level="WARNING"):
            profile = PlayerProfile.load("algorithms", self.profile_path)

        self.assertEqual(set(profile.questions), {"good"})

    def test_questions_key_of_the_wrong_type_gives_an_empty_profile(self):
        self.write_profile(
            json.dumps(
                {
                    "schema_version": SCHEMA_VERSION,
                    "content_sets": {"algorithms": {"questions": ["a", "b"]}},
                }
            )
        )

        profile = PlayerProfile.load("algorithms", self.profile_path)

        self.assertTrue(profile.is_empty)

    def test_unwritable_location_warns_once_and_keeps_going(self):
        # A directory where the profile file should be: every write fails.
        blocked = self.tmp_path / "profile.json"
        blocked.mkdir()
        profile = PlayerProfile(path=blocked)

        with self.assertLogs("neural_dive.player_profile", level="WARNING") as logs:
            profile.record_answer("q", correct=True)
            profile.record_answer("q", correct=False)

        self.assertEqual(len(logs.output), 1)
        # The answers were still recorded in memory; only persistence was lost.
        record = profile.get("q")
        assert record is not None
        self.assertEqual(record.seen, 2)

    def test_load_of_an_unreadable_path_gives_an_empty_profile(self):
        # A directory is not a readable JSON file.
        blocked = self.tmp_path / "profile.json"
        blocked.mkdir()

        with self.assertLogs("neural_dive.player_profile", level="WARNING"):
            profile = PlayerProfile.load("algorithms", blocked)

        self.assertTrue(profile.is_empty)


class TestWeakestTopics(unittest.TestCase):
    """Test joining the profile back onto the content set."""

    def setUp(self) -> None:
        self.questions = {
            "a": _question("a", topic="databases"),
            "b": _question("b", topic="databases"),
            "c": _question("c", topic="security"),
            "d": _question("d", topic="algorithms"),
        }

    def test_topics_are_ranked_by_misses(self):
        profile = PlayerProfile(
            questions={
                "a": QuestionRecord(seen=3, correct=1, wrong=2),
                "b": QuestionRecord(seen=2, correct=1, wrong=1),
                "c": QuestionRecord(seen=2, correct=1, wrong=1),
                "d": QuestionRecord(seen=2, correct=2, wrong=0),
            }
        )

        ranked = weakest_topics(profile, self.questions)

        self.assertEqual(ranked[0], ("databases", 3, 5))
        self.assertEqual(ranked[1], ("security", 1, 2))
        # A topic with no misses is not a weak area.
        self.assertNotIn("algorithms", [topic for topic, _, _ in ranked])

    def test_questions_no_longer_in_the_content_set_are_ignored(self):
        profile = PlayerProfile(
            questions={
                "deleted_question": QuestionRecord(seen=9, correct=0, wrong=9),
                "c": QuestionRecord(seen=1, correct=0, wrong=1),
            }
        )

        ranked = weakest_topics(profile, self.questions)

        self.assertEqual(ranked, [("security", 1, 1)])

    def test_empty_profile_has_no_weak_topics(self):
        self.assertEqual(weakest_topics(PlayerProfile(), self.questions), [])


class TestProfileSummary(unittest.TestCase):
    """Test the text rendered by ``ndive --stats``."""

    def setUp(self) -> None:
        self.questions = {
            "cap_theorem": _question("cap_theorem", topic="distributed_systems"),
            "mutex_purpose": _question("mutex_purpose", topic="systems"),
        }

    def test_empty_profile_says_so(self):
        lines = format_profile_summary(PlayerProfile(), self.questions)

        self.assertIn("No history yet. Answer some questions and come back.", lines)

    def test_summary_reports_totals_and_misses(self):
        profile = PlayerProfile(
            questions={
                "cap_theorem": QuestionRecord(seen=4, correct=1, wrong=3),
                "mutex_purpose": QuestionRecord(seen=2, correct=2, wrong=0),
            }
        )

        text = "\n".join(format_profile_summary(profile, self.questions))

        self.assertIn("Questions seen: 2 of 2", text)
        self.assertIn("Answers: 6 (3 correct, 3 wrong, 50.0% accuracy)", text)
        self.assertIn("3/4  cap_theorem -- Question cap_theorem?", text)
        self.assertIn("distributed_systems: 3 missed of 4", text)

    def test_summary_labels_questions_that_left_the_content_set(self):
        profile = PlayerProfile(questions={"gone": QuestionRecord(seen=2, correct=0, wrong=2)})

        text = "\n".join(format_profile_summary(profile, self.questions))

        self.assertIn("gone -- (no longer in this content set)", text)

    def test_summary_includes_the_path_when_there_is_one(self):
        profile = PlayerProfile(path=Path("/tmp/profile.json"))

        text = "\n".join(format_profile_summary(profile, self.questions))

        self.assertIn("Profile: /tmp/profile.json", text)


if __name__ == "__main__":
    unittest.main()
