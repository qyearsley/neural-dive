"""Input handling system for Neural Dive.

This module provides a protocol-based input handling system with
standardized interfaces and return types. Replaces scattered handler
functions with cohesive, testable handler classes.

Key components:
- InputResult: Standardized return type for all handlers
- InputHandler: Protocol defining handler interface
- Mode-specific handlers: Normal, Conversation, Overlay, EndGame
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from blessed import Terminal
    from blessed.keyboard import Keystroke

    from neural_dive.game import Game


@dataclass
class InputResult:
    """Result of handling an input event.

    Attributes:
        handled: Whether the input was handled by this handler
        should_quit: Whether the game should quit
        needs_redraw: Whether a full screen redraw is needed
        message: Optional message to display to user
        new_game: Optional new Game instance (for load operations)
    """

    handled: bool = False
    should_quit: bool = False
    needs_redraw: bool = False
    message: str | None = None
    new_game: Game | None = None


class InputHandler(Protocol):
    """Protocol for input handlers.

    All input handlers must implement the handle method with this signature.
    """

    def handle(self, key: Keystroke, game: Game, term: Terminal) -> InputResult:
        """Handle an input key.

        Args:
            key: Input keystroke from terminal
            game: Current game instance
            term: Terminal instance for rendering

        Returns:
            InputResult indicating how the input was handled
        """
        ...


class EndGameHandler:
    """Handles input for end game states (victory and game over).

    This handler processes input when the game has ended, either through
    victory (collecting all knowledge) or failure (coherence <= 0).
    """

    def handle(self, key: Keystroke, game: Game, term: Terminal) -> InputResult:
        """Handle end game input (only 'q' to quit).

        Args:
            key: Input keystroke
            game: Game instance
            term: Terminal instance

        Returns:
            InputResult with should_quit=True if user pressed 'q'
        """
        if key and key.lower() == "q":
            return InputResult(handled=True, should_quit=True)
        return InputResult(handled=True)


class OverlayHandler:
    """Handles input for overlay modes (inventory, snippets, terminals).

    Overlays are temporary full-screen displays that can be dismissed
    with ESC or their corresponding toggle key.
    """

    def handle(self, key: Keystroke, game: Game, term: Terminal) -> InputResult:
        """Handle overlay input.

        Args:
            key: Input keystroke
            game: Game instance
            term: Terminal instance

        Returns:
            InputResult with needs_redraw=True if overlay was closed
        """
        # Inventory mode
        if game.active_inventory:
            if key.name == "KEY_ESCAPE" or key.lower() == "v":
                game.active_inventory = False
                return InputResult(handled=True, needs_redraw=True)
            return InputResult(handled=True)

        # Snippet viewing mode
        if game.active_snippet:
            if key.name == "KEY_ESCAPE" or key.lower() == "s":
                game.active_snippet = None
                return InputResult(handled=True, needs_redraw=True)
            return InputResult(handled=True)

        # Terminal reading mode
        if game.active_terminal:
            # Any key closes terminal
            game.active_terminal = None
            return InputResult(handled=True, needs_redraw=True)

        return InputResult(handled=False)


class ConversationHandler:
    """Handles input during NPC conversations.

    Conversations have multiple stages:
    1. Greeting display (any key continues)
    2. Question presentation with answer input
    3. Response display (any key continues)

    Supports multiple question types: multiple choice, yes/no, short answer.
    """

    def handle(self, key: Keystroke, game: Game, term: Terminal) -> InputResult:
        """Handle conversation input.

        Args:
            key: Input keystroke
            game: Game instance
            term: Terminal instance

        Returns:
            InputResult indicating conversation state changes
        """
        if not game.active_conversation:
            # Clean up any lingering response state
            if hasattr(game, "last_answer_response") and game.last_answer_response:
                game.last_answer_response = None
                return InputResult(handled=True, needs_redraw=True)
            return InputResult(handled=False)

        # Stage 1: Greeting dismissal
        if hasattr(game, "show_greeting") and game.show_greeting:
            game.show_greeting = False
            game.text_input_buffer = ""
            return InputResult(handled=True)

        # Stage 2: Response dismissal
        if hasattr(game, "last_answer_response") and game.last_answer_response:
            game.last_answer_response = None
            game.text_input_buffer = ""
            return InputResult(handled=True)

        # Stage 3: Question answering
        from neural_dive.question_types import QuestionType

        current_question = game.active_conversation.get_current_question()
        if not current_question:
            return InputResult(handled=False)

        # Handle text-based questions (short answer, yes/no)
        if current_question.question_type in [
            QuestionType.SHORT_ANSWER,
            QuestionType.YES_NO,
        ]:
            return self._handle_text_question(key, game, current_question)

        # Handle multiple choice questions
        elif current_question.question_type == QuestionType.MULTIPLE_CHOICE:
            return self._handle_multiple_choice_question(key, game)

        return InputResult(handled=False)

    def _handle_text_question(self, key: Keystroke, game: Game, question) -> InputResult:
        """Handle text-based question input (short answer, yes/no).

        Args:
            key: Input keystroke
            game: Game instance
            question: Current question object

        Returns:
            InputResult with response if answer was given
        """
        from neural_dive.question_types import QuestionType

        # Quick Y/N answer for yes/no questions
        if question.question_type == QuestionType.YES_NO:
            if key.lower() == "y":
                correct, response = game.answer_text_question("yes")
                game.text_input_buffer = ""
                game.last_answer_response = response
                return InputResult(handled=True, needs_redraw=True)
            elif key.lower() == "n":
                correct, response = game.answer_text_question("no")
                game.text_input_buffer = ""
                game.last_answer_response = response
                return InputResult(handled=True, needs_redraw=True)

        # Enter submits answer
        if key.name == "KEY_ENTER" or key == "\n" or key == "\r":
            if game.text_input_buffer.strip():
                correct, response = game.answer_text_question(game.text_input_buffer.strip())
                game.text_input_buffer = ""
                game.last_answer_response = response
                return InputResult(handled=True, needs_redraw=True)
            return InputResult(handled=True)

        # ESC/X exits conversation (only when buffer empty)
        if key.name == "KEY_ESCAPE" or (key.lower() == "x" and not game.text_input_buffer):
            self._exit_conversation(game)
            return InputResult(handled=True, needs_redraw=True)

        # Handle text input (backspace, regular chars)
        if self._process_text_input(key, game):
            return InputResult(handled=True)

        return InputResult(handled=False)

    def _handle_multiple_choice_question(self, key: Keystroke, game: Game) -> InputResult:
        """Handle multiple choice question input.

        Args:
            key: Input keystroke
            game: Game instance

        Returns:
            InputResult with response if answer was given
        """
        # Hint usage (H key)
        if key.lower() == "h":
            success, message = game.use_hint()
            game.message = message
            return InputResult(handled=True, needs_redraw=success)

        # Snippet viewing (S key)
        if key.lower() == "s":
            success, message = game.view_snippet()
            if not success:
                game.message = message
            return InputResult(handled=True, needs_redraw=success)

        # Answer selection (1-4)
        if key in ["1", "2", "3", "4"]:
            answer_idx = int(key) - 1
            correct, response = game.answer_question(answer_idx)
            game.text_input_buffer = ""
            game.last_answer_response = response
            return InputResult(handled=True, needs_redraw=True)

        # ESC/Q/X exits conversation
        if key.name == "KEY_ESCAPE" or key.lower() in ["x", "q"]:
            self._exit_conversation(game)
            return InputResult(handled=True, needs_redraw=True)

        return InputResult(handled=False)

    def _process_text_input(self, key: Keystroke, game: Game) -> bool:
        """Process text input for text-based questions.

        Args:
            key: Input keystroke
            game: Game instance

        Returns:
            True if input was processed, False otherwise
        """
        # Backspace
        if key.name == "KEY_BACKSPACE" or key == "\x7f":
            if game.text_input_buffer:
                game.text_input_buffer = game.text_input_buffer[:-1]
            return True

        # Regular character input
        if key.is_sequence:
            return True  # Ignore special sequences
        if len(key) == 1 and key.isprintable():
            game.text_input_buffer += key
            return True

        return False

    def _exit_conversation(self, game: Game) -> None:
        """Exit conversation and clean up state.

        Args:
            game: Game instance
        """
        game.exit_conversation()
        if hasattr(game, "last_answer_response"):
            del game.last_answer_response
        if hasattr(game, "show_greeting"):
            del game.show_greeting
        game.text_input_buffer = ""


class NormalModeHandler:
    """Handles input during normal gameplay (movement, interactions).

    This is the default input mode when not in a conversation or overlay.
    Handles movement, NPC interactions, stairs, save/load, and game exit.
    """

    def handle(self, key: Keystroke, game: Game, term: Terminal) -> InputResult:
        """Handle normal mode input.

        Args:
            key: Input keystroke
            game: Game instance
            term: Terminal instance

        Returns:
            InputResult indicating state changes and actions taken
        """
        # Quit game (Q key)
        if key.lower() == "q":
            return InputResult(handled=True, should_quit=True)

        # Save game (S key)
        if key.lower() == "s":
            success, save_path = game.save_game()
            if success and save_path:
                message = f"Game saved to {save_path}"
            else:
                message = "Failed to save game."
            return InputResult(handled=True, needs_redraw=True, message=message)

        # Load game (L key)
        if key.lower() == "l":
            from neural_dive.game import Game as GameClass
            from neural_dive.game_serializer import GameSerializer

            save_path = GameSerializer.get_default_save_path()
            loaded_game = GameClass.load_game()
            if loaded_game:
                message = f"Game loaded from {save_path}"
                return InputResult(
                    handled=True, needs_redraw=True, message=message, new_game=loaded_game
                )
            else:
                message = f"No save file found at {save_path}"
                return InputResult(handled=True, needs_redraw=True, message=message)

        # Toggle inventory (V key)
        if key.lower() == "v":
            game.active_inventory = not game.active_inventory
            return InputResult(handled=True, needs_redraw=True)

        # Movement and interactions
        return self._handle_movement(key, game)

    def _handle_movement(self, key: Keystroke, game: Game) -> InputResult:
        """Handle movement and interaction input.

        Args:
            key: Input keystroke
            game: Game instance

        Returns:
            InputResult with needs_redraw=True if floor changed
        """
        # Arrow key movement
        if key.name == "KEY_UP":
            game.move_player(0, -1)
            return InputResult(handled=True)
        elif key.name == "KEY_DOWN":
            game.move_player(0, 1)
            return InputResult(handled=True)
        elif key.name == "KEY_LEFT":
            game.move_player(-1, 0)
            return InputResult(handled=True)
        elif key.name == "KEY_RIGHT":
            game.move_player(1, 0)
            return InputResult(handled=True)

        # Stairs navigation: > or . (down), < or , (up)
        elif key in [">", "."] or key in ["<", ","]:
            if game.use_stairs():
                return InputResult(handled=True, needs_redraw=True)
            else:
                # Try interact if no stairs present
                game.interact()
                return InputResult(handled=True)

        # Interaction: Space, Enter, or 'i'
        elif key.lower() == "i" or key == " " or key.name == "KEY_ENTER":
            result = game.interact()
            if result and game.active_conversation:
                # Starting conversation - initialize state
                game.show_greeting = True
                game.last_answer_response = None
                return InputResult(handled=True)
            elif not result:
                # No NPC nearby, try stairs
                if game.use_stairs():
                    return InputResult(handled=True, needs_redraw=True)
            return InputResult(handled=True)

        return InputResult(handled=False)
