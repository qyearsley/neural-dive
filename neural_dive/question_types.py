"""Question type enumerations for Neural Dive."""

from __future__ import annotations

from enum import Enum


class QuestionType(Enum):
    """Types of questions that can be asked."""

    MULTIPLE_CHOICE = "multiple_choice"  # Traditional 4-option questions
    SHORT_ANSWER = "short_answer"  # Type-in answer (e.g., "O(n)", "DFS")
    YES_NO = "yes_no"  # True/False questions
