"""
Difficulty system for Neural Dive.

Provides different difficulty levels to accommodate students at various skill levels,
from beginners learning CS fundamentals to advanced students preparing for technical interviews.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class DifficultyLevel(Enum):
    """Available difficulty levels."""

    NORMAL = "normal"


@dataclass
class DifficultySettings:
    """
    Configuration for a specific difficulty level.

    Attributes:
        name: Display name for the difficulty
        description: Short description of what this difficulty entails
        starting_coherence: Initial coherence value
        max_coherence: Maximum coherence capacity
        correct_answer_gain: Coherence gained for correct answers
        wrong_answer_penalty: Coherence lost for wrong answers (non-enemy)
        enemy_wrong_answer_penalty: Coherence lost for wrong answers to enemy NPCs
        helper_restore_amount: Coherence restored by helper NPCs
        questions_per_npc: Number of questions each NPC asks (min, max)
        boss_questions: Number of questions boss NPCs ask
        time_pressure: Whether answers have time limits
        answer_time_limit: Seconds to answer (if time_pressure enabled)
    """

    name: str
    description: str
    starting_coherence: int
    max_coherence: int
    correct_answer_gain: int
    wrong_answer_penalty: int
    enemy_wrong_answer_penalty: int
    helper_restore_amount: int
    questions_per_npc: tuple[int, int]
    boss_questions: int
    time_pressure: bool = False
    answer_time_limit: int = 30


# Predefined difficulty configurations
DIFFICULTY_CONFIGS: dict[DifficultyLevel, DifficultySettings] = {
    DifficultyLevel.NORMAL: DifficultySettings(
        name="Normal",
        description="Balanced experience - standard settings for most players",
        starting_coherence=80,
        max_coherence=100,
        correct_answer_gain=10,
        wrong_answer_penalty=25,
        enemy_wrong_answer_penalty=40,
        helper_restore_amount=20,
        questions_per_npc=(2, 3),
        boss_questions=4,
        time_pressure=False,
        answer_time_limit=60,
    ),
}


def get_difficulty_settings(level: DifficultyLevel) -> DifficultySettings:
    """
    Get the settings for a specific difficulty level.

    Args:
        level: The difficulty level to get settings for

    Returns:
        DifficultySettings for the specified level

    Example:
        >>> settings = get_difficulty_settings(DifficultyLevel.NORMAL)
        >>> print(settings.starting_coherence)
        80
    """
    return DIFFICULTY_CONFIGS[level]


def get_difficulty_from_string(difficulty_str: str) -> DifficultyLevel:
    """
    Convert a string to a DifficultyLevel enum.

    Args:
        difficulty_str: String representation of difficulty (case-insensitive)

    Returns:
        Corresponding DifficultyLevel

    Raises:
        ValueError: If difficulty_str doesn't match any difficulty level

    Example:
        >>> level = get_difficulty_from_string("normal")
        >>> print(level)
        DifficultyLevel.NORMAL
    """
    difficulty_str = difficulty_str.lower()
    for level in DifficultyLevel:
        if level.value == difficulty_str:
            return level
    raise ValueError(
        f"Unknown difficulty: {difficulty_str}. "
        f"Valid options: {', '.join(level.value for level in DifficultyLevel)}"
    )


def get_all_difficulties() -> list[tuple[DifficultyLevel, DifficultySettings]]:
    """Get all available difficulties (only NORMAL).

    Returns:
        List with single entry: [(DifficultyLevel.NORMAL, settings)]
    """
    return [(DifficultyLevel.NORMAL, DIFFICULTY_CONFIGS[DifficultyLevel.NORMAL])]
