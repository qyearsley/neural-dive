"""Input handling system for Neural Dive.

This module provides a protocol-based input handling system with
standardized interfaces and return types. Replaces scattered handler
functions with cohesive, testable handler classes.

Key components:
- InputResult: Standardized return type for all handlers
- InputHandler: Protocol defining handler interface
- Mode-specific handlers: Normal, Conversation, Overlay, EndGame

Two rules hold across every mode:

- **One dismissal contract for modal overlays.** ESC, Enter, Space, ``q`` and
  the key that opened the overlay all close it; every other key is swallowed.
  See :func:`closes_overlay`.
- **Nothing ends a run on one keystroke.** ``Q`` and ``L`` in normal mode both
  ask for confirmation first, because both used to discard an unsaved run from
  a key that sits next to the movement keys.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from blessed import Terminal
    from blessed.keyboard import Keystroke

    from neural_dive.game import Game
    from neural_dive.models import Question


# Keys that close any modal overlay, on top of ESC, Enter and the overlay's own
# toggle key. `q` is here because it reads as "quit this panel" everywhere else
# in the game.
OVERLAY_DISMISS_CHARS = frozenset({"\n", "\r", " ", "q"})

# Number keys that can select an answer. Answers past the ninth would need a
# second keystroke, so they are simply not selectable; the shipped content tops
# out at four.
MAX_NUMBERED_ANSWERS = 9
NUMBER_KEYS = frozenset("123456789")

# Confirmation prompts. Both fit the 46 columns the message line has at the
# minimum supported window width, so neither is truncated where it matters.
CONFIRM_QUIT = "quit"
CONFIRM_LOAD = "load"
QUIT_PROMPT = "Quit? Unsaved progress is lost. Y=quit N=stay"
LOAD_PROMPT = "Load save? Current run is lost. Y=load N=stay"
CANCELLED_MESSAGE = "Cancelled."


def closes_overlay(key: Keystroke, toggle_key: str | None = None) -> bool:
    """Whether this key should dismiss a modal overlay.

    Every overlay used to have its own contract: inventory took ESC or ``V``,
    snippets took ESC or ``S``, and the info terminal closed on *any* key -- so
    Enter did nothing in two of them and a stray keystroke threw the third away
    mid-sentence. They all take the same set now.

    Args:
        key: Input keystroke
        toggle_key: The lowercase character that opens this overlay, if it has
            one. Info terminals are opened by walking into them, so they pass
            None.

    Returns:
        True if the overlay should close
    """
    if key.name in ("KEY_ESCAPE", "KEY_ENTER"):
        return True
    char = key.lower()
    if char in OVERLAY_DISMISS_CHARS:
        return True
    return toggle_key is not None and char == toggle_key


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
    victory (a boss on the final layer defeated) or failure (coherence <= 0).
    """

    def handle(self, key: Keystroke, game: Game, term: Terminal) -> InputResult:
        """Handle end game input (only 'q' to quit).

        No confirmation here, unlike normal mode: the run is already over, so
        there is nothing left for a stray keystroke to destroy.

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


def overlay_is_open(game: Game) -> bool:
    """Whether a modal overlay currently owns the keyboard.

    The main loop routes to :class:`OverlayHandler` when this is true. It lives
    here, next to the handler, so the list of overlays is written once: the
    dispatch used to name them separately, and a new overlay was one edit away
    from being drawn but never reachable.

    Args:
        game: Game instance

    Returns:
        True if the keystroke belongs to an overlay
    """
    engine = game.conversation_engine
    return bool(
        engine.active_help
        or engine.active_inventory
        or engine.active_snippet
        or engine.active_terminal
    )


class OverlayHandler:
    """Handles input for overlay modes (help, inventory, snippets, terminals).

    Overlays are temporary full-screen displays. They all share one dismissal
    contract -- see :func:`closes_overlay` -- and swallow everything else, so a
    keystroke aimed at a panel never leaks through to the map underneath.
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
        engine = game.conversation_engine

        # Help legend
        if engine.active_help:
            if closes_overlay(key, "?"):
                engine.active_help = False
                return InputResult(handled=True, needs_redraw=True)
            return InputResult(handled=True)

        # Inventory
        if engine.active_inventory:
            if closes_overlay(key, "v"):
                engine.active_inventory = False
                return InputResult(handled=True, needs_redraw=True)
            return InputResult(handled=True)

        # Snippet viewing mode
        if engine.active_snippet:
            if closes_overlay(key, "s"):
                engine.active_snippet = None
                return InputResult(handled=True, needs_redraw=True)
            return InputResult(handled=True)

        # Terminal reading mode. No toggle key: you open one by walking into it.
        if engine.active_terminal:
            if closes_overlay(key):
                engine.active_terminal = None
                return InputResult(handled=True, needs_redraw=True)
            return InputResult(handled=True)

        return InputResult(handled=False)


class ConversationHandler:
    """Handles input during NPC conversations.

    Conversations have multiple stages:
    1. Greeting display (any key continues)
    2. Question presentation with answer input
    3. Response display (any key continues)

    Supports multiple question types: multiple choice, yes/no, short answer.

    ``q`` leaves the conversation in every stage except while a short answer is
    being typed, where it is a letter the player needs ("queue", "quicksort").
    That is the one place the footer's "ESC/X to exit" is the whole story.
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
        if not game.conversation_engine.active_conversation:
            # Clean up any lingering response state
            if game.conversation_engine.last_answer_response:
                game.conversation_engine.last_answer_response = None
                return InputResult(handled=True, needs_redraw=True)
            return InputResult(handled=False)

        # Stage 1: Greeting dismissal
        if game.conversation_engine.show_greeting:
            game.conversation_engine.show_greeting = False
            game.conversation_engine.text_input_buffer = ""
            return InputResult(handled=True)

        # Stage 2: Response dismissal
        if game.conversation_engine.last_answer_response:
            game.conversation_engine.last_answer_response = None
            game.conversation_engine.text_input_buffer = ""
            return InputResult(handled=True)

        # Stage 3: Question answering
        from neural_dive.question_types import QuestionType

        current_question = game.conversation_engine.active_conversation.get_current_question()
        if not current_question:
            return InputResult(handled=False)

        if current_question.question_type == QuestionType.YES_NO:
            return self._handle_yes_no_question(key, game)

        if current_question.question_type == QuestionType.SHORT_ANSWER:
            return self._handle_short_answer_question(key, game)

        # Multiple choice is the only QuestionType left. Adding a variant to the
        # enum makes mypy report a missing return here until it is dispatched.
        return self._handle_multiple_choice_question(key, game, current_question)

    def _handle_yes_no_question(self, key: Keystroke, game: Game) -> InputResult:
        """Handle a yes/no question.

        One keystroke answers it, which is what the footer promises ("Press Y
        for yes or N for no"). Nothing is typed into the text buffer here: it
        used to be, which meant pressing any other letter first quietly made
        ``X`` stop exiting.

        Args:
            key: Input keystroke
            game: Game instance

        Returns:
            InputResult with response if answer was given
        """
        if key.lower() == "y":
            self._submit_text_answer(game, "yes")
            return InputResult(handled=True, needs_redraw=True)
        if key.lower() == "n":
            self._submit_text_answer(game, "no")
            return InputResult(handled=True, needs_redraw=True)

        if key.name == "KEY_ESCAPE" or key.lower() in ("x", "q"):
            game.exit_conversation()
            return InputResult(handled=True, needs_redraw=True)

        # Nothing else means anything on a yes/no question; swallow it rather
        # than letting it fall through to normal mode.
        return InputResult(handled=True)

    def _handle_short_answer_question(self, key: Keystroke, game: Game) -> InputResult:
        """Handle a typed short-answer question.

        Args:
            key: Input keystroke
            game: Game instance

        Returns:
            InputResult with response if answer was submitted
        """
        # Enter submits answer
        if key.name == "KEY_ENTER" or key == "\n" or key == "\r":
            answer = game.conversation_engine.text_input_buffer.strip()
            if answer:
                self._submit_text_answer(game, answer)
                return InputResult(handled=True, needs_redraw=True)
            return InputResult(handled=True)

        # ESC/X exits conversation (X only when the buffer is empty, so it stays
        # typeable). This is what the footer says: "ESC/X to exit".
        if key.name == "KEY_ESCAPE" or (
            key.lower() == "x" and not game.conversation_engine.text_input_buffer
        ):
            game.exit_conversation()
            return InputResult(handled=True, needs_redraw=True)

        # Handle text input (editing keys, regular chars)
        if self._process_text_input(key, game):
            return InputResult(handled=True)

        return InputResult(handled=False)

    def _handle_multiple_choice_question(
        self, key: Keystroke, game: Game, question: Question
    ) -> InputResult:
        """Handle multiple choice question input.

        The accepted number keys are derived from the answers actually on
        screen. A hardcoded "1"-"4" accepted an option a hint token had removed
        from the display, and would have made a five-option question
        unanswerable.

        Args:
            key: Input keystroke
            game: Game instance
            question: The question being displayed

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

        # Answer selection, restricted to the options the renderer drew
        eliminated = game.conversation_engine.eliminated_answers
        selectable = {
            str(index + 1)
            for index in range(min(len(question.answers), MAX_NUMBERED_ANSWERS))
            if index not in eliminated
        }
        if key in selectable:
            _correct, response = game.answer_question(int(key) - 1)
            game.conversation_engine.text_input_buffer = ""
            game.conversation_engine.last_answer_response = response
            return InputResult(handled=True, needs_redraw=True)

        # A number key for an option that is not on screen: eaten, not acted on
        if key in NUMBER_KEYS:
            return InputResult(handled=True)

        # ESC/Q/X exits conversation
        if key.name == "KEY_ESCAPE" or key.lower() in ("x", "q"):
            game.exit_conversation()
            return InputResult(handled=True, needs_redraw=True)

        return InputResult(handled=False)

    @staticmethod
    def _submit_text_answer(game: Game, answer: str) -> None:
        """Send a typed or Y/N answer and show the response.

        Args:
            game: Game instance
            answer: The answer text to submit
        """
        _correct, response = game.answer_text_question(answer)
        game.conversation_engine.text_input_buffer = ""
        game.conversation_engine.last_answer_response = response

    def _process_text_input(self, key: Keystroke, game: Game) -> bool:
        """Process text input for short-answer questions.

        There is no cursor: editing is always at the end of the line. Backspace,
        Ctrl+U and Ctrl+W cover what a one-line answer needs, and arrow keys are
        swallowed rather than inserted.

        Args:
            key: Input keystroke
            game: Game instance

        Returns:
            True if input was processed, False otherwise
        """
        engine = game.conversation_engine

        # Backspace
        if key.name == "KEY_BACKSPACE" or key == "\x7f":
            if engine.text_input_buffer:
                engine.text_input_buffer = engine.text_input_buffer[:-1]
            return True

        # Ctrl+U: clear the whole line
        if key == "\x15":
            engine.text_input_buffer = ""
            return True

        # Ctrl+W: delete the word before the cursor, keeping the space that
        # separated it -- the same thing readline does.
        if key == "\x17":
            head, _sep, _word = engine.text_input_buffer.rstrip().rpartition(" ")
            engine.text_input_buffer = f"{head} " if head else ""
            return True

        # Regular character input
        if key.is_sequence:
            return True  # Ignore special sequences
        if len(key) == 1 and key.isprintable():
            engine.text_input_buffer += key
            return True

        return False


class NormalModeHandler:
    """Handles input during normal gameplay (movement, interactions).

    This is the default input mode when not in a conversation or overlay.
    Handles movement, NPC interactions, stairs, save/load, help, and game exit.

    ``Q`` and ``L`` both discard an unsaved run, and both sit a finger away from
    the keys a player uses constantly. Each now arms a confirmation instead of
    acting: the *next* keystroke either confirms with ``Y`` or cancels. Any key
    resolves the prompt, so it cannot strand the player.

    Attributes:
        pending_confirm: Which destructive action is waiting for a Y, if any
    """

    def __init__(self) -> None:
        """Start with no confirmation pending."""
        self.pending_confirm: str | None = None

    def handle(self, key: Keystroke, game: Game, term: Terminal) -> InputResult:
        """Handle normal mode input.

        Args:
            key: Input keystroke
            game: Game instance
            term: Terminal instance

        Returns:
            InputResult indicating state changes and actions taken
        """
        if self.pending_confirm is not None:
            return self._resolve_confirmation(key, game)

        # Quit game (Q key) -- asks first
        if key.lower() == "q":
            self.pending_confirm = CONFIRM_QUIT
            return InputResult(handled=True, message=QUIT_PROMPT)

        # Save game (S key)
        if key.lower() == "s":
            return self._save_game(game)

        # Load game (L key) -- asks first, because it throws this run away
        if key.lower() == "l":
            self.pending_confirm = CONFIRM_LOAD
            return InputResult(handled=True, message=LOAD_PROMPT)

        # Help legend (? key, or ESC, which would otherwise do nothing at all)
        if key == "?" or key.name == "KEY_ESCAPE":
            game.conversation_engine.active_help = True
            return InputResult(handled=True, needs_redraw=True)

        # Toggle inventory (V key)
        if key.lower() == "v":
            game.conversation_engine.active_inventory = (
                not game.conversation_engine.active_inventory
            )
            return InputResult(handled=True, needs_redraw=True)

        # Movement and interactions
        return self._handle_movement(key, game)

    def _resolve_confirmation(self, key: Keystroke, game: Game) -> InputResult:
        """Answer the pending Y/N prompt.

        Args:
            key: Input keystroke
            game: Game instance

        Returns:
            InputResult carrying out the action, or cancelling it
        """
        pending, self.pending_confirm = self.pending_confirm, None

        if key.lower() != "y":
            return InputResult(handled=True, message=CANCELLED_MESSAGE)

        if pending == CONFIRM_QUIT:
            return InputResult(handled=True, should_quit=True)

        return self._load_game(game)

    def _save_game(self, game: Game) -> InputResult:
        """Write the save file and report where it went.

        Args:
            game: Game instance

        Returns:
            InputResult carrying the outcome message
        """
        success, save_path = game.save_game()
        message = f"Game saved to {save_path}" if success and save_path else "Failed to save game."
        return InputResult(handled=True, needs_redraw=True, message=message)

    def _load_game(self, game: Game) -> InputResult:
        """Replace the running game with the saved one.

        Args:
            game: Game instance being discarded

        Returns:
            InputResult carrying the loaded game, or a message if there is none
        """
        from neural_dive.game import Game as GameClass
        from neural_dive.game_serializer import GameSerializer

        save_path = GameSerializer.get_default_save_path()
        # Carry the current run's profile across, so history keeps
        # accumulating after a mid-run load.
        loaded_game = GameClass.load_game(profile=game.profile)
        if loaded_game:
            message = f"Game loaded from {save_path}"
            return InputResult(
                handled=True, needs_redraw=True, message=message, new_game=loaded_game
            )
        message = f"No save file found at {save_path}"
        return InputResult(handled=True, needs_redraw=True, message=message)

    def _handle_movement(self, key: Keystroke, game: Game) -> InputResult:
        """Handle movement and interaction input.

        Arrow keys only. Neither hjkl nor WASD can be added without a clash:
        ``l`` is Load and ``s`` is Save, both documented in the README, the
        ``--help`` epilog and the in-game legend, and both also mean something
        in a conversation (``h`` hint, ``s`` snippet). A half scheme -- h, j, k
        but not l -- would be worse than none.

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

        # Interaction: Space, Enter, or 'i'. `Game.interact` starts the
        # conversation through the engine, which sets the greeting and clears
        # the last response itself -- nothing to initialize here.
        elif key.lower() == "i" or key == " " or key.name == "KEY_ENTER":
            # No NPC or terminal nearby: fall back to the stairs, so one key
            # covers everything you can be standing next to.
            if not game.interact() and game.use_stairs():
                return InputResult(handled=True, needs_redraw=True)
            return InputResult(handled=True)

        return InputResult(handled=False)
