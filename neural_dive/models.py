"""Data models for Neural Dive game."""

from __future__ import annotations

from dataclasses import dataclass, field

from neural_dive.config import ENEMY_WRONG_ANSWER_PENALTY
from neural_dive.enums import NPCType
from neural_dive.question_types import QuestionType


@dataclass
class Answer:
    """A possible answer to a conversation question."""

    text: str
    correct: bool
    response: str  # NPC's response to this answer
    reward_knowledge: str | None = None  # Knowledge module gained if correct
    enemy_penalty: int = ENEMY_WRONG_ANSWER_PENALTY  # Extra penalty for enemies


@dataclass
class Question:
    """A question in a conversation.

    Supports multiple question types:
    - MULTIPLE_CHOICE: Traditional 4-option questions (answers list)
    - SHORT_ANSWER: Type-in answer (correct_answer field, match_type)
    - YES_NO: True/False questions (correct_answer is "yes" or "no")
    """

    question_text: str
    topic: str  # e.g., "vocabulary", "geography", "algorithms"
    question_type: QuestionType = QuestionType.MULTIPLE_CHOICE

    # For MULTIPLE_CHOICE questions.
    answers: list[Answer] = field(default_factory=list)

    # For SHORT_ANSWER and YES_NO questions.
    correct_answer: str | None = None  # e.g., "O(n)|linear", "yes", "DFS|Depth-First Search"
    correct_response: str | None = None  # Response when correct
    incorrect_response: str | None = None  # Response when incorrect
    reward_knowledge: str | None = None  # Knowledge module for correct answer
    match_type: str = "exact"  # "exact", "complexity", "numeric"
    case_sensitive: bool = False  # For exact matching


@dataclass
class Conversation:
    """A conversation with an NPC."""

    npc_name: str
    greeting: str
    questions: list[Question]
    npc_type: NPCType = NPCType.SPECIALIST
    current_question_idx: int = 0
    completed: bool = False

    def get_current_question(self) -> Question | None:
        """Get the current question, or None if conversation is complete"""
        if self.current_question_idx < len(self.questions):
            return self.questions[self.current_question_idx]
        return None

    def advance_question(self) -> None:
        """Move to the next question"""
        self.current_question_idx += 1
        if self.current_question_idx >= len(self.questions):
            self.completed = True

    def is_complete(self) -> bool:
        """Check if all questions have been answered"""
        return self.current_question_idx >= len(self.questions)
