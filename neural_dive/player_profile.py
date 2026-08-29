"""Cross-run question history.

A run's :class:`~neural_dive.managers.stats_tracker.StatsTracker` forgets
everything when the run ends. This module is the part that does not: it
accumulates per-question outcomes across runs so question selection can
resurface what the player keeps getting wrong.

Design
------

**Question identity.** ``questions.json`` is a dict keyed by an authored
``snake_case`` id (``mutex_purpose``, ``cap_theorem``). Those ids are already
stable, already unique, and already referenced from ``npcs.json``, so they are
the profile's key. Until this module existed the id was dropped during loading;
:func:`neural_dive.data_loader.load_questions` now copies it onto
``Question.question_id``. Hashing the question text would have worked without
that change, but any wording fix -- a typo, a clarification -- would silently
orphan the history for that question, so the authored id is preferred. A
``Question`` with an empty ``question_id`` (hand-built in a test, say) is simply
not recorded.

**Storage.** ``~/.neural_dive/profile.json``, next to the run save file that
:class:`~neural_dive.game_serializer.GameSerializer` writes, but a separate
file: it outlives any individual run and must survive deleting a save. The
top level is keyed by content set, because question ids are only unique within
one. Sets other than the one in play are preserved verbatim on write so playing
one content set cannot erase another's history::

    {
      "schema_version": 1,
      "content_sets": {
        "algorithms": {
          "questions": {
            "cap_theorem": {"seen": 5, "correct": 1, "wrong": 4, "last_seen": 1756...}
          }
        }
      }
    }

**Selection weighting.** One formula, applied per question::

    weight = 1 + 2 * (wrong / seen)

A question never seen weighs 1.0; one missed every time weighs 3.0; one missed
half the time weighs 2.0. A question answered correctly at least
``QUESTION_MASTERY_CORRECT_COUNT`` times with no misses drops to 0.5. Weights
feed a weighted sample without replacement inside
:func:`neural_dive.conversation.create_randomized_conversation`, so the level
and topic structure is untouched -- the bias only reorders preference *within*
the pool an NPC already owns. The formula is self-correcting: answering a
missed question right pulls its weight back down.

**Failure modes.** Every one of them degrades to today's behaviour:

- No profile file: an empty profile. An empty profile is never handed to the
  question selector at all, so a first-time player gets byte-identical
  behaviour, including for a fixed ``--seed``.
- Unreadable or malformed file: logged, renamed to ``profile.json.corrupt`` so
  the next write does not silently eat it, and treated as empty.
- ``schema_version`` newer than this code understands: treated as empty *and*
  marked read-only, so a newer build's profile is never overwritten by an
  older one.
- Individual malformed records: skipped; the rest of the file still loads.
- Question ids no longer in the content set: inert. Weighting only ever looks
  up ids for questions that exist, and the summary view labels the strays
  rather than dropping them, in case the question comes back.
- Unwritable save directory: warned about once, then ignored. The run
  continues; only the history is lost.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import json
import logging
import os
from pathlib import Path
import time
from typing import TYPE_CHECKING, Any

from neural_dive.config import (
    QUESTION_MASTERY_CORRECT_COUNT,
    QUESTION_WEIGHT_BASE,
    QUESTION_WEIGHT_MASTERED,
    QUESTION_WEIGHT_MISS_BONUS,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from neural_dive.models import Question

logger = logging.getLogger(__name__)

SCHEMA_VERSION = 1
DEFAULT_PROFILE_DIR = Path.home() / ".neural_dive"
DEFAULT_PROFILE_FILE = "profile.json"


def get_default_profile_path() -> Path:
    """Get the default profile file path.

    Returns:
        Path to ``~/.neural_dive/profile.json``
    """
    return DEFAULT_PROFILE_DIR / DEFAULT_PROFILE_FILE


@dataclass
class QuestionRecord:
    """What the player has done with one question, across all runs.

    Attributes:
        seen: Times the question has been answered
        correct: Times it was answered correctly
        wrong: Times it was answered incorrectly
        last_seen: Unix timestamp of the most recent answer (0.0 if never)
    """

    seen: int = 0
    correct: int = 0
    wrong: int = 0
    last_seen: float = 0.0

    @property
    def miss_rate(self) -> float:
        """Fraction of attempts that were wrong, clamped to 0.0-1.0.

        Returns:
            0.0 if the question has never been answered
        """
        if self.seen <= 0:
            return 0.0
        return min(1.0, max(0.0, self.wrong / self.seen))

    def to_dict(self) -> dict:
        """Serialize the record for storage.

        Returns:
            Dictionary form of the record
        """
        return {
            "seen": self.seen,
            "correct": self.correct,
            "wrong": self.wrong,
            "last_seen": self.last_seen,
        }

    @classmethod
    def from_dict(cls, data: Any) -> QuestionRecord | None:
        """Deserialize one record, tolerating garbage.

        Args:
            data: The value stored under a question id, which may be anything

        Returns:
            The record, or None if the value could not be read as one
        """
        if not isinstance(data, dict):
            return None
        try:
            return cls(
                seen=max(0, int(data.get("seen", 0))),
                correct=max(0, int(data.get("correct", 0))),
                wrong=max(0, int(data.get("wrong", 0))),
                last_seen=max(0.0, float(data.get("last_seen", 0.0))),
            )
        except (TypeError, ValueError):
            return None


@dataclass
class PlayerProfile:
    """Per-question outcomes accumulated across runs, for one content set.

    Construct with :meth:`load` to read the player's file; construct directly
    (with no ``path``) for an in-memory profile that never touches the disk,
    which is what tests and the ``--no-history`` flag use.

    Attributes:
        content_set: Content set these records belong to
        questions: Question id -> record
        path: File this profile is written back to (None means in-memory only)
        read_only: Set when the file on disk is from a newer schema, so this
            profile must not overwrite it
    """

    content_set: str = "algorithms"
    questions: dict[str, QuestionRecord] = field(default_factory=dict)
    path: Path | None = None
    read_only: bool = False

    # Records for content sets other than ``content_set``, kept verbatim so
    # writing this profile back cannot erase another set's history.
    other_content_sets: dict[str, Any] = field(default_factory=dict)

    # Set after the first failed write, so an unwritable directory produces one
    # warning rather than one per answer.
    _write_failed: bool = False

    @property
    def is_empty(self) -> bool:
        """Whether this profile holds no history for its content set.

        Returns:
            True if nothing has been recorded yet
        """
        return not self.questions

    def get(self, question_id: str) -> QuestionRecord | None:
        """Look up one question's record.

        Args:
            question_id: Authored question id

        Returns:
            The record, or None if the question has never been answered
        """
        return self.questions.get(question_id)

    def record_answer(self, question_id: str, correct: bool, now: float | None = None) -> None:
        """Record one answer and persist the profile.

        Args:
            question_id: Authored question id; empty ids are ignored
            correct: Whether the player answered correctly
            now: Timestamp to store (None for the current wall-clock time)
        """
        if not question_id:
            return

        record = self.questions.setdefault(question_id, QuestionRecord())
        record.seen += 1
        if correct:
            record.correct += 1
        else:
            record.wrong += 1
        record.last_seen = time.time() if now is None else now

        self.save()

    def weight_for(self, question_id: str) -> float:
        """Selection weight for one question.

        ``1 + 2 * miss_rate``, so a question the player always misses is three
        times as likely to be picked as a fresh one. A question answered right
        ``QUESTION_MASTERY_CORRECT_COUNT`` times with no misses is demoted to
        half weight instead.

        Args:
            question_id: Authored question id

        Returns:
            A weight in the range 0.5 to 3.0
        """
        record = self.questions.get(question_id)
        if record is None or record.seen <= 0:
            return QUESTION_WEIGHT_BASE
        if record.wrong == 0 and record.correct >= QUESTION_MASTERY_CORRECT_COUNT:
            return QUESTION_WEIGHT_MASTERED
        return QUESTION_WEIGHT_BASE + QUESTION_WEIGHT_MISS_BONUS * record.miss_rate

    def question_weighter(self) -> Callable[[Question], float]:
        """Build the callable that ``create_randomized_conversation`` takes.

        Returns:
            A function mapping a Question to its selection weight
        """

        def weight(question: Question) -> float:
            return self.weight_for(question.question_id)

        return weight

    def most_missed(self, limit: int = 10) -> list[tuple[str, QuestionRecord]]:
        """The questions the player has got wrong most often.

        Sorted by wrong count, then by miss rate, so a question missed four
        times out of five outranks one missed four times out of twenty.

        Args:
            limit: Maximum number of entries to return

        Returns:
            List of (question id, record) pairs, longest-suffering first
        """
        missed = [(qid, rec) for qid, rec in self.questions.items() if rec.wrong > 0]
        missed.sort(key=lambda item: (item[1].wrong, item[1].miss_rate), reverse=True)
        return missed[:limit]

    def totals(self) -> tuple[int, int, int]:
        """Aggregate counts across every recorded question.

        Returns:
            Tuple of (answers recorded, correct, wrong)
        """
        seen = sum(rec.seen for rec in self.questions.values())
        correct = sum(rec.correct for rec in self.questions.values())
        wrong = sum(rec.wrong for rec in self.questions.values())
        return seen, correct, wrong

    def to_dict(self) -> dict:
        """Serialize the whole profile file, other content sets included.

        Returns:
            Dictionary ready to be written as JSON
        """
        content_sets: dict[str, Any] = dict(self.other_content_sets)
        content_sets[self.content_set] = {
            "questions": {qid: rec.to_dict() for qid, rec in self.questions.items()},
        }
        return {"schema_version": SCHEMA_VERSION, "content_sets": content_sets}

    @classmethod
    def from_dict(
        cls,
        data: Any,
        content_set: str = "algorithms",
        path: Path | None = None,
    ) -> PlayerProfile:
        """Build a profile from parsed JSON, tolerating anything.

        Args:
            data: Parsed contents of a profile file, of unknown shape
            content_set: Content set to read records for
            path: File the profile came from, stored for later writes

        Returns:
            A profile. An unreadable ``data`` yields an empty one; a
            ``schema_version`` from the future yields an empty read-only one.
        """
        if not isinstance(data, dict):
            logger.warning("Player profile is not a JSON object; ignoring it.")
            return cls(content_set=content_set, path=path)

        version = data.get("schema_version", SCHEMA_VERSION)
        if not isinstance(version, int) or version > SCHEMA_VERSION:
            logger.warning(
                "Player profile uses schema version %s, newer than this build understands (%d). "
                "Ignoring it and leaving the file alone.",
                version,
                SCHEMA_VERSION,
            )
            return cls(content_set=content_set, path=path, read_only=True)

        all_sets = data.get("content_sets")
        if not isinstance(all_sets, dict):
            logger.warning("Player profile has no readable content sets; ignoring it.")
            return cls(content_set=content_set, path=path)

        other = {name: blob for name, blob in all_sets.items() if name != content_set}

        questions: dict[str, QuestionRecord] = {}
        this_set = all_sets.get(content_set)
        raw_questions = this_set.get("questions") if isinstance(this_set, dict) else None
        if isinstance(raw_questions, dict):
            for question_id, raw in raw_questions.items():
                record = QuestionRecord.from_dict(raw)
                if record is None:
                    logger.warning("Skipping malformed profile record for %r.", question_id)
                    continue
                questions[str(question_id)] = record

        return cls(
            content_set=content_set,
            questions=questions,
            path=path,
            other_content_sets=other,
        )

    @classmethod
    def load(
        cls,
        content_set: str = "algorithms",
        path: str | Path | None = None,
    ) -> PlayerProfile:
        """Read the player's profile from disk.

        Never raises. A missing, unreadable, or malformed file produces an empty
        profile, which makes question selection behave exactly as it did before
        profiles existed.

        Args:
            content_set: Content set to read records for
            path: Profile file (None for the default location)

        Returns:
            The loaded profile, or an empty one
        """
        resolved = get_default_profile_path() if path is None else Path(path)

        if not resolved.exists():
            return cls(content_set=content_set, path=resolved)

        try:
            with open(resolved, encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, json.JSONDecodeError, UnicodeDecodeError) as e:
            logger.warning("Could not read player profile %s: %s", resolved, e)
            _quarantine(resolved)
            return cls(content_set=content_set, path=resolved)

        return cls.from_dict(data, content_set=content_set, path=resolved)

    def save(self) -> bool:
        """Write the profile back to its file, if it has one.

        Writes to a temporary file and renames it into place, so an interrupted
        write cannot leave a half-written profile behind. Failures are logged
        once and swallowed -- losing history must never end a run.

        Returns:
            True if the profile was written
        """
        if self.path is None or self.read_only:
            return False

        tmp_path = self.path.with_name(self.path.name + ".tmp")
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(self.to_dict(), f, indent=2)
            os.replace(tmp_path, self.path)
        except (OSError, TypeError) as e:
            if not self._write_failed:
                self._write_failed = True
                logger.warning("Could not write player profile %s: %s", self.path, e)
            return False

        self._write_failed = False
        return True


def _quarantine(path: Path) -> None:
    """Move an unreadable profile aside so the next write does not destroy it.

    Best effort: if the rename fails there is nothing useful to do about it.

    Args:
        path: The profile file that could not be parsed
    """
    backup = path.with_name(path.name + ".corrupt")
    try:
        os.replace(path, backup)
    except OSError as e:
        logger.warning("Could not set aside unreadable profile %s: %s", path, e)
    else:
        logger.warning("Moved unreadable profile to %s.", backup)


def weakest_topics(
    profile: PlayerProfile,
    questions: dict[str, Question],
    limit: int = 3,
) -> list[tuple[str, int, int]]:
    """Topics the player misses most, by joining the profile to the content set.

    Args:
        profile: The player's profile
        questions: Question id -> Question, as loaded by ``data_loader``
        limit: Maximum number of topics to return

    Returns:
        List of (topic, wrong count, times seen), worst first. Topics with no
        misses are omitted, as are records whose question is no longer in the
        content set.
    """
    totals: dict[str, list[int]] = {}
    for question_id, record in profile.questions.items():
        question = questions.get(question_id)
        if question is None:
            continue
        bucket = totals.setdefault(question.topic, [0, 0])
        bucket[0] += record.wrong
        bucket[1] += record.seen

    ranked = [(topic, wrong, seen) for topic, (wrong, seen) in totals.items() if wrong > 0]
    ranked.sort(key=lambda item: (item[1], item[1] / item[2] if item[2] else 0.0), reverse=True)
    return ranked[:limit]


def format_profile_summary(
    profile: PlayerProfile,
    questions: dict[str, Question],
    most_missed_limit: int = 10,
) -> list[str]:
    """Render the profile as lines for the ``--stats`` view.

    Args:
        profile: The player's profile
        questions: Question id -> Question, used to show question text and
            topics; ids missing from it are labelled rather than dropped
        most_missed_limit: How many missed questions to list

    Returns:
        Lines of plain text, no trailing newlines
    """
    lines = [f"Neural Dive -- question history ({profile.content_set})"]
    if profile.path is not None:
        lines.append(f"Profile: {profile.path}")
    lines.append("")

    if profile.is_empty:
        lines.append("No history yet. Answer some questions and come back.")
        return lines

    answers, correct, wrong = profile.totals()
    accuracy = (correct / answers * 100) if answers else 0.0
    lines.append(f"Questions seen: {len(profile.questions)} of {len(questions)}")
    lines.append(f"Answers: {answers} ({correct} correct, {wrong} wrong, {accuracy:.1f}% accuracy)")

    missed = profile.most_missed(most_missed_limit)
    if missed:
        lines.append("")
        lines.append("Most-missed questions:")
        for question_id, record in missed:
            question = questions.get(question_id)
            text = (
                question.question_text
                if question is not None
                else "(no longer in this content set)"
            )
            lines.append(f"  {record.wrong}/{record.seen}  {question_id} -- {text}")

    topics = weakest_topics(profile, questions, limit=5)
    if topics:
        lines.append("")
        lines.append("Weakest topics:")
        for topic, topic_wrong, topic_seen in topics:
            lines.append(f"  {topic}: {topic_wrong} missed of {topic_seen}")

    return lines
