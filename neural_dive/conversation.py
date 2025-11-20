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


def _is_cjk_char(char: str) -> bool:
    """Check if a character is CJK (Chinese, Japanese, Korean).

    Args:
        char: Single character to check

    Returns:
        True if character is CJK, False otherwise
    """
    code_point = ord(char)
    # CJK Unified Ideographs ranges
    return (
        0x4E00 <= code_point <= 0x9FFF  # CJK Unified Ideographs
        or 0x3400 <= code_point <= 0x4DBF  # CJK Extension A
        or 0x20000 <= code_point <= 0x2A6DF  # CJK Extension B
        or 0x2A700 <= code_point <= 0x2B73F  # CJK Extension C
        or 0x2B740 <= code_point <= 0x2B81F  # CJK Extension D
        or 0x2B820 <= code_point <= 0x2CEAF  # CJK Extension E
        or 0xF900 <= code_point <= 0xFAFF  # CJK Compatibility Ideographs
        or 0x2F800 <= code_point <= 0x2FA1F  # CJK Compatibility Ideographs Supplement
    )


def _has_significant_cjk(text: str) -> bool:
    """Check if text contains significant CJK content (>20% CJK characters).

    Args:
        text: Text to analyze

    Returns:
        True if text has significant CJK content
    """
    if not text:
        return False
    cjk_count = sum(1 for char in text if _is_cjk_char(char))
    return cjk_count / len(text) > 0.2


def wrap_text(text: str, width: int) -> list[str]:
    """Wrap text to fit within width, with CJK character support.

    For text with significant CJK content, wraps by character count.
    For other text, wraps by word boundaries (space-separated).

    Args:
        text: Text to wrap
        width: Maximum line width

    Returns:
        List of wrapped lines
    """
    if not text:
        return []

    # Check if text has significant CJK content
    if _has_significant_cjk(text):
        # CJK wrapping: break by character, preferably at punctuation
        lines: list[str] = []
        current_line_str = ""

        for char in text:
            # Check if adding this character would exceed width
            if len(current_line_str) + 1 > width:
                # Line is full, save it and start new line
                lines.append(current_line_str)
                current_line_str = char
            else:
                current_line_str += char

        if current_line_str:
            lines.append(current_line_str)

        return lines

    # English/space-separated wrapping (original logic)
    words = text.split()
    result_lines: list[str] = []
    current_line_words: list[str] = []

    for word in words:
        # Calculate what the line length would be if we add this word
        test_line = current_line_words + [word]
        # n words need n-1 spaces between them
        test_length = sum(len(w) for w in test_line) + len(test_line) - 1

        if test_length > width and current_line_words:
            # Line would be too long, save current line and start new one
            result_lines.append(" ".join(current_line_words))
            current_line_words = [word]
        else:
            # Word fits, add it
            current_line_words.append(word)

    if current_line_words:
        result_lines.append(" ".join(current_line_words))

    return result_lines
