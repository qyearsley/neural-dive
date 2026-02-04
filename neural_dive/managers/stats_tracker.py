"""Game statistics tracking for Neural Dive.

This module provides the StatsTracker class which tracks game statistics
including questions answered, score calculation, and final stats aggregation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import time


@dataclass
class StatsTracker:
    """Tracks game statistics and scoring.

    The StatsTracker encapsulates all game statistics tracking and provides
    clean interfaces for recording answers and calculating scores. This makes it easier to:
    - Test scoring logic in isolation
    - Track player performance metrics
    - Generate final statistics for end screens
    - Add new scoring mechanics (combos, bonuses, achievements)

    Attributes:
        questions_answered: Total number of questions answered
        questions_correct: Number of correct answers
        questions_wrong: Number of wrong answers
        start_time: Timestamp when tracking began
    """

    questions_answered: int = 0
    questions_correct: int = 0
    questions_wrong: int = 0
    start_time: float = field(default_factory=time.time)

    def record_correct_answer(self) -> None:
        """Record a correct answer.

        Increments both total questions answered and correct answer count.
        """
        self.questions_answered += 1
        self.questions_correct += 1

    def record_wrong_answer(self) -> None:
        """Record a wrong answer.

        Increments both total questions answered and wrong answer count.
        """
        self.questions_answered += 1
        self.questions_wrong += 1

    def get_accuracy(self) -> float:
        """Calculate answer accuracy percentage.

        Returns:
            Accuracy as a percentage (0-100), or 0.0 if no questions answered
        """
        if self.questions_answered == 0:
            return 0.0
        return (self.questions_correct / self.questions_answered) * 100

    def get_time_played(self) -> float:
        """Get total time played in seconds.

        Returns:
            Time elapsed since tracking started
        """
        return time.time() - self.start_time

    def get_current_score(
        self,
        knowledge_count: int,
        npcs_completed_count: int,
        coherence: int,
    ) -> int:
        """Calculate the current score based on player progress.

        Scoring formula:
        - 100 points per correct answer
        - 50 points per knowledge module acquired
        - 200 points per NPC completed
        - 10 points per coherence point remaining

        Args:
            knowledge_count: Number of knowledge modules acquired
            npcs_completed_count: Number of NPCs defeated/completed
            coherence: Current coherence (health) value

        Returns:
            Current score value
        """
        return (
            (self.questions_correct * 100)
            + (knowledge_count * 50)
            + (npcs_completed_count * 200)
            + (coherence * 10)
        )

    def get_final_stats(
        self,
        npcs_completed_count: int,
        knowledge_count: int,
        final_coherence: int,
        current_floor: int,
    ) -> dict:
        """Get final game statistics for victory/game over screen.

        Args:
            npcs_completed_count: Number of NPCs completed
            knowledge_count: Number of knowledge modules acquired
            final_coherence: Final coherence value
            current_floor: Floor reached when game ended

        Returns:
            Dictionary containing all game stats including time, accuracy, and score
        """
        time_played = self.get_time_played()
        accuracy = self.get_accuracy()
        score = self.get_current_score(
            knowledge_count,
            npcs_completed_count,
            final_coherence,
        )

        return {
            "time_played": time_played,
            "questions_answered": self.questions_answered,
            "questions_correct": self.questions_correct,
            "questions_wrong": self.questions_wrong,
            "accuracy": accuracy,
            "npcs_completed": npcs_completed_count,
            "knowledge_modules": knowledge_count,
            "final_coherence": final_coherence,
            "current_floor": current_floor,
            "score": int(score),
        }

    def to_dict(self) -> dict:
        """Serialize stats to dictionary for save/load.

        Returns:
            Dictionary containing all stats state
        """
        return {
            "questions_answered": self.questions_answered,
            "questions_correct": self.questions_correct,
            "questions_wrong": self.questions_wrong,
            "start_time": self.start_time,
        }

    @classmethod
    def from_dict(cls, data: dict) -> StatsTracker:
        """Deserialize stats from dictionary.

        Args:
            data: Dictionary containing stats state from to_dict()

        Returns:
            New StatsTracker instance with loaded state
        """
        return cls(
            questions_answered=data.get("questions_answered", 0),
            questions_correct=data.get("questions_correct", 0),
            questions_wrong=data.get("questions_wrong", 0),
            start_time=data.get("start_time", time.time()),
        )
