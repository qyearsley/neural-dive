"""Conversation utilities for Neural Dive."""

from __future__ import annotations

import copy
import random

from neural_dive.models import Conversation, Question


def randomize_answers(question: Question, seed: int | None = None) -> Question:
    """Create a copy of a question with randomized answer order.

    Args:
        question: The question to randomize
        seed: Optional random seed for reproducibility

    Returns:
        New Question object with shuffled answers
    """
    if seed is not None:
        random.seed(seed)

    # Deep copy the question
    new_question = copy.deepcopy(question)

    # Shuffle answers
    random.shuffle(new_question.answers)

    return new_question


def create_randomized_conversation(
    conversation: Conversation,
    randomize_question_order: bool = True,
    randomize_answer_order: bool = True,
    seed: int | None = None,
    num_questions: int = 3,
) -> Conversation:
    """
    Create a copy of a conversation with randomized questions and answers.

    Args:
        conversation: The conversation to randomize
        randomize_question_order: Whether to shuffle questions
        randomize_answer_order: Whether to shuffle answers within questions
        seed: Optional random seed for reproducibility
        num_questions: Number of questions to select from available pool (default: 3)

    Returns:
        New Conversation object with randomized content
    """
    if seed is not None:
        random.seed(seed)

    new_conv = copy.deepcopy(conversation)

    # Select a random subset of questions if we have more than num_questions
    if len(new_conv.questions) > num_questions:
        new_conv.questions = random.sample(new_conv.questions, num_questions)

    # Randomize question order if requested
    if randomize_question_order and len(new_conv.questions) > 1:
        random.shuffle(new_conv.questions)

    # Randomize answer order for each question if requested
    if randomize_answer_order:
        for i, question in enumerate(new_conv.questions):
            # Use different seed for each question
            q_seed = seed + i if seed is not None else None
            new_conv.questions[i] = randomize_answers(question, q_seed)

    return new_conv


def wrap_text(text: str, width: int) -> list[str]:
    """
    Wrap text to fit within width.

    Args:
        text: Text to wrap
        width: Maximum line width

    Returns:
        List of wrapped lines
    """
    words = text.split()
    lines = []
    current_line: list[str] = []

    for word in words:
        # Calculate what the line length would be if we add this word
        test_line = current_line + [word]
        # n words need n-1 spaces between them
        test_length = sum(len(w) for w in test_line) + len(test_line) - 1

        if test_length > width and current_line:
            # Line would be too long, save current line and start new one
            lines.append(" ".join(current_line))
            current_line = [word]
        else:
            # Word fits, add it
            current_line.append(word)

    if current_line:
        lines.append(" ".join(current_line))

    return lines
