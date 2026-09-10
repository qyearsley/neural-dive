"""Question rendering strategies for Neural Dive.

This module implements the Strategy pattern for rendering different question types.
Each renderer is responsible for drawing a specific question type in the conversation overlay.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol
import unicodedata

from neural_dive.question_types import QuestionType
from neural_dive.render_helpers import draw_wrapped_text

if TYPE_CHECKING:
    from neural_dive.backends import RenderBackend
    from neural_dive.game import Game
    from neural_dive.models import Question
    from neural_dive.themes import ColorScheme


def get_display_width(text: str) -> int:
    """Calculate the display width of text accounting for wide characters.

    Wide characters (like Chinese, Japanese, Korean) take 2 terminal cells
    but count as 1 character. This function returns the actual terminal width.

    Args:
        text: Text to measure

    Returns:
        Display width in terminal cells
    """
    width = 0
    for char in text:
        # East Asian Width property
        ea_width = unicodedata.east_asian_width(char)
        if ea_width in ("F", "W") or ea_width == "A":  # Fullwidth or Wide
            width += 2
        else:
            width += 1
    return width


def truncate_to_display_width(text: str, max_width: int) -> str:
    """Cut ``text`` down to at most ``max_width`` terminal cells.

    Wide characters count as two cells, so the result can be shorter than
    ``max_width`` when the next character would straddle the edge.

    This replaced a ``while get_display_width(t) > max_width: t = t[:-1]`` loop.
    On a terminal narrower than 14 columns the overlay is small enough that
    ``max_width`` goes negative, and an empty string is never narrower than a
    negative width, so the loop spun forever on ``""[:-1]``.

    Args:
        text: Text to truncate
        max_width: Maximum display width in cells; zero or less returns ""

    Returns:
        The longest prefix of ``text`` that fits in ``max_width`` cells
    """
    if max_width <= 0:
        return ""
    width = 0
    for index, char in enumerate(text):
        char_width = get_display_width(char)
        if width + char_width > max_width:
            return text[:index]
        width += char_width
    return text


def answer_key_hint(question: Question, eliminated: set[int]) -> str:
    """Describe the number keys that actually answer this question.

    The footer used to be a hardcoded "Press 1-4", which stayed wrong in two
    ways: questions can have fewer than four answers, and using a hint token
    removes an option without renumbering the rest.

    Args:
        question: Question being displayed
        eliminated: Indices of answers a hint has removed

    Returns:
        A fragment such as "Press 1-3" or "Press 1/3/4", or "" when nothing is
        selectable
    """
    live = [i + 1 for i in range(len(question.answers)) if i not in eliminated]
    if not live:
        return ""
    if len(live) == 1:
        return f"Press {live[0]}"
    if live == list(range(live[0], live[-1] + 1)):
        return f"Press {live[0]}-{live[-1]}"
    return "Press " + "/".join(str(number) for number in live)


class QuestionRenderer(Protocol):
    """Protocol for question rendering strategies.

    Each renderer handles drawing a specific question type in the conversation overlay.
    """

    def render(
        self,
        term: RenderBackend,
        question: Question,
        question_number: int,
        total_questions: int,
        start_x: int,
        start_y: int,
        current_y: int,
        overlay_width: int,
        overlay_height: int,
        colors: ColorScheme,
        game: Game,
    ) -> None:
        """Render the question in the overlay.

        Args:
            term: Render backend instance for output
            question: Question to render
            question_number: Current question number (1-indexed)
            total_questions: Total number of questions in conversation
            start_x: X coordinate of overlay start
            start_y: Y coordinate of overlay start
            current_y: Current Y position for drawing
            overlay_width: Width of the overlay
            overlay_height: Height of the overlay
            colors: Color scheme for rendering
            game: Game instance for accessing state like text_input_buffer
        """
        ...


class MultipleChoiceRenderer:
    """Renderer for multiple choice questions."""

    def render(
        self,
        term: RenderBackend,
        question: Question,
        question_number: int,
        total_questions: int,
        start_x: int,
        start_y: int,
        current_y: int,
        overlay_width: int,
        overlay_height: int,
        colors: ColorScheme,
        game: Game,
    ) -> None:
        """Render multiple choice question with numbered answers."""
        # Question text
        q_text = f"Q{question_number}/{total_questions}: {question.question_text}"
        current_y = draw_wrapped_text(
            term,
            q_text,
            start_x + 2,
            current_y,
            start_y + overlay_height - 4,
            overlay_width - 4,
            color="black",
            bold=True,
        )

        current_y += 1

        # Show numbered answers (skip eliminated ones)
        eliminated = game.conversation_engine.eliminated_answers
        answers_max_y = start_y + overlay_height - 2
        for i, answer in enumerate(question.answers):
            # Skip eliminated answers
            if i in eliminated:
                continue

            current_y = draw_wrapped_text(
                term,
                f"{i + 1}. {answer.text}",
                start_x + 2,
                current_y,
                answers_max_y,
                overlay_width - 4,
                color="blue",
            )

        # Instructions at bottom - show hint option if available
        from neural_dive.items import ItemType

        has_hints = game.player_manager.has_item_type(ItemType.HINT_TOKEN)
        has_snippets = game.player_manager.has_item_type(ItemType.CODE_SNIPPET)

        hint_text = " | H: Use Hint" if has_hints else ""
        snippet_text = " | S: View Snippet" if has_snippets else ""
        key_hint = answer_key_hint(question, eliminated)
        answer_text = f"{key_hint} to answer" if key_hint else "No answers left"
        term.draw_text(
            start_x + 2,
            start_y + overlay_height - 2,
            f"{answer_text}{hint_text}{snippet_text} | ESC/Q to exit",
            colors.ui_error,
            bold=True,
        )


class TextInputRenderer:
    """Base renderer for text input questions (short answer, yes/no)."""

    def _render_question_text(
        self,
        term: RenderBackend,
        question: Question,
        question_number: int,
        total_questions: int,
        start_x: int,
        start_y: int,
        current_y: int,
        overlay_width: int,
        overlay_height: int,
    ) -> int:
        """Render question text and return new current_y position."""
        q_text = f"Q{question_number}/{total_questions}: {question.question_text}"
        current_y = draw_wrapped_text(
            term,
            q_text,
            start_x + 2,
            current_y,
            start_y + overlay_height - 4,
            overlay_width - 4,
            color="black",
            bold=True,
        )
        return current_y + 2  # Add spacing

    def _render_text_input_box(
        self,
        term: RenderBackend,
        prompt_text: str,
        text_buffer: str,
        start_x: int,
        current_y: int,
        overlay_width: int,
    ) -> int:
        """Render text input box and return new current_y position."""
        # Input prompt
        term.draw_text(start_x + 2, current_y, prompt_text, "black", bold=True)
        current_y += 1

        # Input box top
        border_width = max(0, overlay_width - 6)
        term.draw_text(start_x + 2, current_y, "┌" + "─" * border_width + "┓", "blue")
        current_y += 1

        # Input area with user's typed text. The row is three segments -- the left
        # border, the text, then padding and the right border -- so each is drawn
        # at its own x rather than concatenated into one coloured string.
        max_display_width = overlay_width - 10

        # Truncate text to fit display width (accounting for wide chars)
        display_text = truncate_to_display_width(text_buffer, max_display_width)

        text_display_width = get_display_width(display_text)
        padding_width = max(0, overlay_width - 8 - text_display_width)

        term.draw_text(start_x + 2, current_y, "│ ", "blue")
        term.draw_text(start_x + 4, current_y, display_text, "black")
        term.draw_text(
            start_x + 4 + text_display_width, current_y, " " * padding_width + " │", "blue"
        )
        current_y += 1

        # Input box bottom
        term.draw_text(start_x + 2, current_y, "└" + "─" * border_width + "┘", "blue")
        current_y += 1

        return current_y


class ShortAnswerRenderer(TextInputRenderer):
    """Renderer for short answer questions."""

    def render(
        self,
        term: RenderBackend,
        question: Question,
        question_number: int,
        total_questions: int,
        start_x: int,
        start_y: int,
        current_y: int,
        overlay_width: int,
        overlay_height: int,
        colors: ColorScheme,
        game: Game,
    ) -> None:
        """Render short answer question with text input."""
        # Render question text
        current_y = self._render_question_text(
            term,
            question,
            question_number,
            total_questions,
            start_x,
            start_y,
            current_y,
            overlay_width,
            overlay_height,
        )

        # Render text input box
        text_buffer = game.conversation_engine.text_input_buffer
        current_y = self._render_text_input_box(
            term, "Your answer:", text_buffer, start_x, current_y, overlay_width
        )

        # Instructions at bottom. ConversationHandler exits on ESC, or on "x"
        # while the input box is empty -- "Q" types a letter here, it does not
        # leave.
        term.draw_text(
            start_x + 2,
            start_y + overlay_height - 2,
            "Type your answer and press ENTER | ESC/X to exit",
            colors.ui_error,
            bold=True,
        )


class YesNoRenderer(TextInputRenderer):
    """Renderer for yes/no questions."""

    def render(
        self,
        term: RenderBackend,
        question: Question,
        question_number: int,
        total_questions: int,
        start_x: int,
        start_y: int,
        current_y: int,
        overlay_width: int,
        overlay_height: int,
        colors: ColorScheme,
        game: Game,
    ) -> None:
        """Render yes/no question with text input."""
        # Render question text
        current_y = self._render_question_text(
            term,
            question,
            question_number,
            total_questions,
            start_x,
            start_y,
            current_y,
            overlay_width,
            overlay_height,
        )

        # Render text input box
        text_buffer = game.conversation_engine.text_input_buffer
        current_y = self._render_text_input_box(
            term, "Answer (Y/N):", text_buffer, start_x, current_y, overlay_width
        )

        # Instructions at bottom. ConversationHandler submits on the first "y"
        # or "n", so the word "yes" can never reach the input box -- the old
        # "or type answer and press ENTER" was an instruction that could not be
        # followed.
        term.draw_text(
            start_x + 2,
            start_y + overlay_height - 2,
            "Press Y for yes or N for no | ESC/X to exit",
            colors.ui_error,
            bold=True,
        )


# Question renderer registry
_QUESTION_RENDERERS: dict[QuestionType, QuestionRenderer] = {
    QuestionType.MULTIPLE_CHOICE: MultipleChoiceRenderer(),
    QuestionType.SHORT_ANSWER: ShortAnswerRenderer(),
    QuestionType.YES_NO: YesNoRenderer(),
}


def get_question_renderer(question_type: QuestionType) -> QuestionRenderer:
    """Get the appropriate renderer for a question type.

    Args:
        question_type: Type of question to render

    Returns:
        QuestionRenderer instance for the question type

    Raises:
        ValueError: If question type is not supported
    """
    if question_type not in _QUESTION_RENDERERS:
        raise ValueError(f"Unsupported question type: {question_type}")
    return _QUESTION_RENDERERS[question_type]
