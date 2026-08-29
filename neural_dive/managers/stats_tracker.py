"""Game statistics tracking for Neural Dive.

This module provides the StatsTracker class which tracks game statistics
including questions answered, score calculation, and final stats aggregation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import time


def _now() -> float:
    """Read the monotonic clock.

    Wrapped in a function rather than passed as ``default_factory=time.monotonic``
    so the lookup happens at call time -- a direct reference is bound when the
    dataclass is defined, which tests cannot patch.
    """
    return time.monotonic()


@dataclass
class StatsTracker:
    """Tracks game statistics and scoring.

    The StatsTracker encapsulates all game statistics tracking and provides
    clean interfaces for recording answers and calculating scores. This makes it easier to:
    - Test scoring logic in isolation
    - Track player performance metrics
    - Generate final statistics for end screens
    - Add new scoring mechanics (combos, bonuses, achievements)

    Time played is accumulated rather than derived from a wall-clock start
    timestamp. ``accumulated_seconds`` banks the play time of earlier sessions
    and ``_session_start`` marks when the current one began, so a run that is
    saved, quit, and resumed the next day does not count the intervening night.
    Intervals are measured with :func:`time.monotonic`, which cannot jump when
    the system clock is stepped by NTP, a DST change, or a sleep/wake cycle.

    Attributes:
        questions_answered: Total number of questions answered
        questions_correct: Number of correct answers
        questions_wrong: Number of wrong answers
        accumulated_seconds: Play time banked by earlier sessions of this run
    """

    questions_answered: int = 0
    questions_correct: int = 0
    questions_wrong: int = 0
    accumulated_seconds: float = 0.0

    # Monotonic reading taken when this session started. Not part of the save
    # format, not comparable across processes, so it stays out of __init__,
    # __repr__, and __eq__.
    _session_start: float = field(
        default_factory=_now,
        init=False,
        repr=False,
        compare=False,
    )

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
            Play time banked by earlier sessions plus the elapsed time of the
            current one. Time spent with the game closed is not counted.
        """
        return self.accumulated_seconds + (_now() - self._session_start)

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

        Stores the running play-time total rather than an absolute timestamp,
        so the clock resumes where it stopped when the save is loaded.

        Returns:
            Dictionary containing all stats state
        """
        return {
            "questions_answered": self.questions_answered,
            "questions_correct": self.questions_correct,
            "questions_wrong": self.questions_wrong,
            "accumulated_seconds": self.get_time_played(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> StatsTracker:
        """Deserialize stats from dictionary.

        Saves written before play time was accumulated carry only a
        ``start_time`` wall-clock timestamp. That timestamp records when the
        run began in real-world terms, not how long it was played, so there is
        nothing to recover from it -- such a save resumes with its play-time
        total at zero rather than importing hours the player spent away from
        the game. The pre-fix portion of that run's time is lost; everything
        after the load is measured correctly.

        Args:
            data: Dictionary containing stats state from to_dict()

        Returns:
            New StatsTracker instance with loaded state
        """
        # A missing, non-numeric, or negative total degrades to zero. `load`
        # only catches ValueError, so a `null` here would otherwise crash.
        raw = data.get("accumulated_seconds", 0.0)
        accumulated = float(raw) if isinstance(raw, (int, float)) else 0.0

        return cls(
            questions_answered=data.get("questions_answered", 0),
            questions_correct=data.get("questions_correct", 0),
            questions_wrong=data.get("questions_wrong", 0),
            accumulated_seconds=max(0.0, accumulated),
        )
