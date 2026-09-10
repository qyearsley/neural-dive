"""Conversation utilities for Neural Dive."""

from __future__ import annotations

import copy
import random
from typing import TYPE_CHECKING

from neural_dive.models import Conversation, Question

if TYPE_CHECKING:
    from collections.abc import Callable

# Floating-point weights can only get so small before a question would never be
# drawn; the profile's lowest weight is 0.5, so this is only a guard.
_MIN_WEIGHT = 1e-6

# Used when a caller asks for randomization but supplies neither a generator nor
# a seed. It is a private instance rather than the ``random`` module so that
# nothing in here can disturb, or be disturbed by, the process-wide generator.
_DEFAULT_RNG = random.Random()


def _resolve_rng(rng: random.Random | None, seed: int | None) -> random.Random:
    """Pick the generator to draw from.

    An explicit generator wins. A seed builds a private generator for this call
    -- it never reseeds the process-wide ``random`` module, which used to make
    one seeded conversation change every other random draw in the program.

    Args:
        rng: The generator to use, if the caller has one
        seed: A seed to build a private generator from

    Returns:
        The generator to draw from
    """
    if rng is not None:
        return rng
    if seed is not None:
        return random.Random(seed)
    return _DEFAULT_RNG


def _weighted_sample(
    questions: list[Question],
    weight_of: Callable[[Question], float],
    count: int,
    rng: random.Random,
) -> list[Question]:
    """Pick ``count`` questions without replacement, biased by weight.

    Each round picks one question with probability proportional to its weight
    among those still in the pool. Weights are clamped to a small positive
    minimum so a question can never become unpickable.

    Args:
        questions: Questions to choose from
        weight_of: Selection weight for a question; higher is likelier
        count: How many to pick (capped at the pool size)
        rng: Generator to draw from

    Returns:
        The chosen questions, in the order they were drawn
    """
    pool = [(question, max(_MIN_WEIGHT, weight_of(question))) for question in questions]
    chosen: list[Question] = []

    for _ in range(min(count, len(pool))):
        total = sum(weight for _, weight in pool)
        target = rng.random() * total
        running = 0.0
        index = len(pool) - 1
        for i, (_, weight) in enumerate(pool):
            running += weight
            if target < running:
                index = i
                break
        chosen.append(pool.pop(index)[0])

    return chosen


def randomize_answers(
    question: Question,
    seed: int | None = None,
    rng: random.Random | None = None,
) -> Question:
    """Create a copy of a question with randomized answer order.

    Args:
        question: The question to randomize
        seed: Optional random seed for reproducibility
        rng: Generator to draw from. Takes precedence over ``seed``.

    Returns:
        New Question object with shuffled answers
    """
    generator = _resolve_rng(rng, seed)

    # Deep copy the question
    new_question = copy.deepcopy(question)

    # Shuffle answers
    generator.shuffle(new_question.answers)

    return new_question


def apply_answer_order(question: Question, answer_texts: list[str]) -> Question:
    """Copy a question with its answers put back in a recorded order.

    This is how a save restores the answer order a conversation was drawn with,
    instead of shuffling again and moving the correct answer out from under the
    index the player was looking at.

    Answers whose text is not in ``answer_texts`` keep their authored order and
    go on the end, so a reworded or added answer degrades to "shown last"
    rather than disappearing.

    Args:
        question: The authored question, in its authored answer order
        answer_texts: Answer texts in the order they should appear

    Returns:
        New Question object with the answers reordered
    """
    new_question = copy.deepcopy(question)

    remaining = list(new_question.answers)
    ordered = []
    for text in answer_texts:
        match = next((answer for answer in remaining if answer.text == text), None)
        if match is not None:
            remaining.remove(match)
            ordered.append(match)

    new_question.answers = ordered + remaining
    return new_question


def create_randomized_conversation(
    conversation: Conversation,
    randomize_question_order: bool = True,
    randomize_answer_order: bool = True,
    seed: int | None = None,
    num_questions: int = 3,
    question_weight: Callable[[Question], float] | None = None,
    rng: random.Random | None = None,
) -> Conversation:
    """
    Create a copy of a conversation with randomized questions and answers.

    Args:
        conversation: The conversation to randomize
        randomize_question_order: Whether to shuffle questions
        randomize_answer_order: Whether to shuffle answers within questions
        seed: Optional random seed for reproducibility. Builds a private
            generator for this call; it does not reseed ``random``.
        num_questions: Number of questions to select from available pool (default: 3)
        question_weight: Optional selection weight per question, used to bias
            the subset toward questions the player has missed before (see
            :mod:`neural_dive.player_profile`). None keeps the plain uniform
            sample, which is what a player with no history gets.
        rng: Generator to draw from. Takes precedence over ``seed``. This is
            what the game passes, so ``--seed`` makes question selection
            reproducible along with everything else.

    Returns:
        New Conversation object with randomized content
    """
    generator = _resolve_rng(rng, seed)

    new_conv = copy.deepcopy(conversation)

    # Select a subset of questions if we have more than num_questions
    if len(new_conv.questions) > num_questions:
        if question_weight is None:
            new_conv.questions = generator.sample(new_conv.questions, num_questions)
        else:
            new_conv.questions = _weighted_sample(
                new_conv.questions, question_weight, num_questions, generator
            )

    # Randomize question order if requested
    if randomize_question_order and len(new_conv.questions) > 1:
        generator.shuffle(new_conv.questions)

    # Randomize answer order for each question if requested
    if randomize_answer_order:
        for i, question in enumerate(new_conv.questions):
            new_conv.questions[i] = randomize_answers(question, rng=generator)

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
