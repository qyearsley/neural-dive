"""Unit tests for StatsTracker.

This test module covers statistics tracking including:
- Recording correct and wrong answers
- Accuracy calculation
- Score calculation
- Time tracking
- Final stats aggregation
- Serialization/deserialization
"""

from __future__ import annotations

import time
import unittest

from neural_dive.managers.stats_tracker import StatsTracker


class TestStatsTrackerInitialization(unittest.TestCase):
    """Test StatsTracker initialization."""

    def test_default_initialization(self):
        """Test StatsTracker initializes with default values."""
        tracker = StatsTracker()

        self.assertEqual(tracker.questions_answered, 0)
        self.assertEqual(tracker.questions_correct, 0)
        self.assertEqual(tracker.questions_wrong, 0)
        self.assertIsInstance(tracker.start_time, float)
        self.assertGreater(tracker.start_time, 0)

    def test_custom_initialization(self):
        """Test StatsTracker can be initialized with custom values."""
        start_time = time.time() - 100
        tracker = StatsTracker(
            questions_answered=10,
            questions_correct=7,
            questions_wrong=3,
            start_time=start_time,
        )

        self.assertEqual(tracker.questions_answered, 10)
        self.assertEqual(tracker.questions_correct, 7)
        self.assertEqual(tracker.questions_wrong, 3)
        self.assertEqual(tracker.start_time, start_time)


class TestAnswerRecording(unittest.TestCase):
    """Test recording answer statistics."""

    def test_record_correct_answer(self):
        """Test recording a correct answer increments both counters."""
        tracker = StatsTracker()

        tracker.record_correct_answer()

        self.assertEqual(tracker.questions_answered, 1)
        self.assertEqual(tracker.questions_correct, 1)
        self.assertEqual(tracker.questions_wrong, 0)

    def test_record_wrong_answer(self):
        """Test recording a wrong answer increments both counters."""
        tracker = StatsTracker()

        tracker.record_wrong_answer()

        self.assertEqual(tracker.questions_answered, 1)
        self.assertEqual(tracker.questions_correct, 0)
        self.assertEqual(tracker.questions_wrong, 1)

    def test_record_multiple_answers(self):
        """Test recording multiple answers updates counts correctly."""
        tracker = StatsTracker()

        tracker.record_correct_answer()
        tracker.record_correct_answer()
        tracker.record_wrong_answer()
        tracker.record_correct_answer()
        tracker.record_wrong_answer()

        self.assertEqual(tracker.questions_answered, 5)
        self.assertEqual(tracker.questions_correct, 3)
        self.assertEqual(tracker.questions_wrong, 2)

    def test_record_only_correct_answers(self):
        """Test recording only correct answers."""
        tracker = StatsTracker()

        for _ in range(10):
            tracker.record_correct_answer()

        self.assertEqual(tracker.questions_answered, 10)
        self.assertEqual(tracker.questions_correct, 10)
        self.assertEqual(tracker.questions_wrong, 0)

    def test_record_only_wrong_answers(self):
        """Test recording only wrong answers."""
        tracker = StatsTracker()

        for _ in range(5):
            tracker.record_wrong_answer()

        self.assertEqual(tracker.questions_answered, 5)
        self.assertEqual(tracker.questions_correct, 0)
        self.assertEqual(tracker.questions_wrong, 5)


class TestAccuracyCalculation(unittest.TestCase):
    """Test accuracy calculation."""

    def test_accuracy_with_no_answers(self):
        """Test accuracy is 0.0 when no questions answered."""
        tracker = StatsTracker()

        accuracy = tracker.get_accuracy()

        self.assertEqual(accuracy, 0.0)

    def test_accuracy_with_all_correct(self):
        """Test accuracy is 100.0 when all answers correct."""
        tracker = StatsTracker()

        for _ in range(10):
            tracker.record_correct_answer()

        accuracy = tracker.get_accuracy()

        self.assertEqual(accuracy, 100.0)

    def test_accuracy_with_all_wrong(self):
        """Test accuracy is 0.0 when all answers wrong."""
        tracker = StatsTracker()

        for _ in range(5):
            tracker.record_wrong_answer()

        accuracy = tracker.get_accuracy()

        self.assertEqual(accuracy, 0.0)

    def test_accuracy_with_mixed_answers(self):
        """Test accuracy calculation with mixed correct/wrong."""
        tracker = StatsTracker()

        # 3 correct, 2 wrong = 60% accuracy
        tracker.record_correct_answer()
        tracker.record_correct_answer()
        tracker.record_wrong_answer()
        tracker.record_correct_answer()
        tracker.record_wrong_answer()

        accuracy = tracker.get_accuracy()

        self.assertAlmostEqual(accuracy, 60.0, places=2)

    def test_accuracy_with_7_out_of_10(self):
        """Test accuracy with 70% correct."""
        tracker = StatsTracker()

        for _ in range(7):
            tracker.record_correct_answer()
        for _ in range(3):
            tracker.record_wrong_answer()

        accuracy = tracker.get_accuracy()

        self.assertAlmostEqual(accuracy, 70.0, places=2)


class TestTimeTracking(unittest.TestCase):
    """Test time tracking."""

    def test_time_played_initial(self):
        """Test time played is near 0 initially."""
        tracker = StatsTracker()

        time_played = tracker.get_time_played()

        # Should be very small (< 1 second)
        self.assertLess(time_played, 1.0)
        self.assertGreaterEqual(time_played, 0.0)

    def test_time_played_with_delay(self):
        """Test time played increases over time."""
        start_time = time.time() - 5.0  # 5 seconds ago
        tracker = StatsTracker(start_time=start_time)

        time_played = tracker.get_time_played()

        # Should be approximately 5 seconds (allow small variance)
        self.assertGreater(time_played, 4.9)
        self.assertLess(time_played, 5.2)

    def test_time_played_after_100_seconds(self):
        """Test time played with longer duration."""
        start_time = time.time() - 100.0
        tracker = StatsTracker(start_time=start_time)

        time_played = tracker.get_time_played()

        self.assertGreater(time_played, 99.9)
        self.assertLess(time_played, 100.2)


class TestScoreCalculation(unittest.TestCase):
    """Test score calculation logic."""

    def test_score_with_no_progress(self):
        """Test score is 0 with no progress."""
        tracker = StatsTracker()

        score = tracker.get_current_score(
            knowledge_count=0,
            npcs_completed_count=0,
            coherence=0,
        )

        self.assertEqual(score, 0)

    def test_score_with_correct_answers_only(self):
        """Test score calculation with only correct answers."""
        tracker = StatsTracker()
        tracker.record_correct_answer()
        tracker.record_correct_answer()
        tracker.record_correct_answer()

        # 3 correct * 100 = 300
        score = tracker.get_current_score(
            knowledge_count=0,
            npcs_completed_count=0,
            coherence=0,
        )

        self.assertEqual(score, 300)

    def test_score_with_knowledge_modules(self):
        """Test score calculation with knowledge modules."""
        tracker = StatsTracker()

        # 5 knowledge modules * 50 = 250
        score = tracker.get_current_score(
            knowledge_count=5,
            npcs_completed_count=0,
            coherence=0,
        )

        self.assertEqual(score, 250)

    def test_score_with_npcs_completed(self):
        """Test score calculation with NPCs completed."""
        tracker = StatsTracker()

        # 3 NPCs * 200 = 600
        score = tracker.get_current_score(
            knowledge_count=0,
            npcs_completed_count=3,
            coherence=0,
        )

        self.assertEqual(score, 600)

    def test_score_with_coherence_bonus(self):
        """Test score calculation with coherence bonus."""
        tracker = StatsTracker()

        # 80 coherence * 10 = 800
        score = tracker.get_current_score(
            knowledge_count=0,
            npcs_completed_count=0,
            coherence=80,
        )

        self.assertEqual(score, 800)

    def test_score_with_all_components(self):
        """Test score calculation with all components."""
        tracker = StatsTracker()
        tracker.record_correct_answer()
        tracker.record_correct_answer()
        tracker.record_correct_answer()

        # 3 correct * 100 = 300
        # 5 knowledge * 50 = 250
        # 2 NPCs * 200 = 400
        # 75 coherence * 10 = 750
        # Total = 1700
        score = tracker.get_current_score(
            knowledge_count=5,
            npcs_completed_count=2,
            coherence=75,
        )

        self.assertEqual(score, 1700)

    def test_score_ignores_wrong_answers(self):
        """Test score calculation ignores wrong answers."""
        tracker = StatsTracker()
        tracker.record_correct_answer()
        tracker.record_wrong_answer()
        tracker.record_wrong_answer()
        tracker.record_correct_answer()

        # Only 2 correct answers count
        score = tracker.get_current_score(
            knowledge_count=0,
            npcs_completed_count=0,
            coherence=0,
        )

        self.assertEqual(score, 200)


class TestFinalStats(unittest.TestCase):
    """Test final stats aggregation."""

    def test_final_stats_structure(self):
        """Test final stats returns correct structure."""
        tracker = StatsTracker()

        stats = tracker.get_final_stats(
            npcs_completed_count=0,
            knowledge_count=0,
            final_coherence=100,
            current_floor=1,
        )

        # Check all expected keys are present
        expected_keys = {
            "time_played",
            "questions_answered",
            "questions_correct",
            "questions_wrong",
            "accuracy",
            "npcs_completed",
            "knowledge_modules",
            "final_coherence",
            "current_floor",
            "score",
        }
        self.assertEqual(set(stats.keys()), expected_keys)

    def test_final_stats_with_game_progress(self):
        """Test final stats with actual game progress."""
        start_time = time.time() - 300  # 5 minutes ago
        tracker = StatsTracker(start_time=start_time)

        # Simulate game progress
        for _ in range(7):
            tracker.record_correct_answer()
        for _ in range(3):
            tracker.record_wrong_answer()

        stats = tracker.get_final_stats(
            npcs_completed_count=2,
            knowledge_count=5,
            final_coherence=75,
            current_floor=3,
        )

        self.assertAlmostEqual(stats["time_played"], 300, delta=1)
        self.assertEqual(stats["questions_answered"], 10)
        self.assertEqual(stats["questions_correct"], 7)
        self.assertEqual(stats["questions_wrong"], 3)
        self.assertAlmostEqual(stats["accuracy"], 70.0, places=1)
        self.assertEqual(stats["npcs_completed"], 2)
        self.assertEqual(stats["knowledge_modules"], 5)
        self.assertEqual(stats["final_coherence"], 75)
        self.assertEqual(stats["current_floor"], 3)
        # Score: 700 + 250 + 400 + 750 = 2100
        self.assertEqual(stats["score"], 2100)

    def test_final_stats_victory_scenario(self):
        """Test final stats in a victory scenario."""
        tracker = StatsTracker()

        # Perfect victory: all correct, high coherence
        for _ in range(20):
            tracker.record_correct_answer()

        stats = tracker.get_final_stats(
            npcs_completed_count=10,
            knowledge_count=15,
            final_coherence=95,
            current_floor=5,
        )

        self.assertEqual(stats["questions_correct"], 20)
        self.assertEqual(stats["questions_wrong"], 0)
        self.assertEqual(stats["accuracy"], 100.0)
        # Score: 2000 + 750 + 2000 + 950 = 5700
        self.assertEqual(stats["score"], 5700)

    def test_final_stats_game_over_scenario(self):
        """Test final stats in a game over scenario."""
        tracker = StatsTracker()

        # Failed quickly: few answers, low coherence
        tracker.record_correct_answer()
        tracker.record_wrong_answer()
        tracker.record_wrong_answer()

        stats = tracker.get_final_stats(
            npcs_completed_count=0,
            knowledge_count=1,
            final_coherence=0,
            current_floor=1,
        )

        self.assertEqual(stats["questions_answered"], 3)
        self.assertEqual(stats["questions_correct"], 1)
        self.assertEqual(stats["questions_wrong"], 2)
        self.assertAlmostEqual(stats["accuracy"], 33.33, places=1)
        # Score: 100 + 50 + 0 + 0 = 150
        self.assertEqual(stats["score"], 150)


class TestSerialization(unittest.TestCase):
    """Test serialization and deserialization."""

    def test_to_dict(self):
        """Test converting StatsTracker to dictionary."""
        tracker = StatsTracker(
            questions_answered=10,
            questions_correct=7,
            questions_wrong=3,
            start_time=1234567890.0,
        )

        data = tracker.to_dict()

        self.assertEqual(data["questions_answered"], 10)
        self.assertEqual(data["questions_correct"], 7)
        self.assertEqual(data["questions_wrong"], 3)
        self.assertEqual(data["start_time"], 1234567890.0)

    def test_from_dict(self):
        """Test creating StatsTracker from dictionary."""
        data = {
            "questions_answered": 10,
            "questions_correct": 7,
            "questions_wrong": 3,
            "start_time": 1234567890.0,
        }

        tracker = StatsTracker.from_dict(data)

        self.assertEqual(tracker.questions_answered, 10)
        self.assertEqual(tracker.questions_correct, 7)
        self.assertEqual(tracker.questions_wrong, 3)
        self.assertEqual(tracker.start_time, 1234567890.0)

    def test_from_dict_with_defaults(self):
        """Test from_dict uses defaults for missing keys."""
        data: dict[str, int | float] = {}

        tracker = StatsTracker.from_dict(data)

        self.assertEqual(tracker.questions_answered, 0)
        self.assertEqual(tracker.questions_correct, 0)
        self.assertEqual(tracker.questions_wrong, 0)
        self.assertGreater(tracker.start_time, 0)  # Uses current time

    def test_round_trip_serialization(self):
        """Test serialization round-trip preserves state."""
        original = StatsTracker(
            questions_answered=15,
            questions_correct=12,
            questions_wrong=3,
            start_time=1234567890.0,
        )

        # Convert to dict and back
        data = original.to_dict()
        restored = StatsTracker.from_dict(data)

        self.assertEqual(restored.questions_answered, original.questions_answered)
        self.assertEqual(restored.questions_correct, original.questions_correct)
        self.assertEqual(restored.questions_wrong, original.questions_wrong)
        self.assertEqual(restored.start_time, original.start_time)


if __name__ == "__main__":
    unittest.main()
