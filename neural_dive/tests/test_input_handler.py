"""Tests for input handling system."""

from __future__ import annotations

import unittest
from unittest.mock import Mock, patch

from blessed.keyboard import Keystroke

from neural_dive.input_handler import (
    CANCELLED_MESSAGE,
    LOAD_PROMPT,
    QUIT_PROMPT,
    ConversationHandler,
    EndGameHandler,
    InputResult,
    NormalModeHandler,
    OverlayHandler,
    overlay_is_open,
)
from neural_dive.managers.conversation_engine import ConversationEngine
from neural_dive.question_types import QuestionType


def make_key(char: str = "", name: str | None = None) -> Keystroke:
    """Build the same object blessed hands the handlers.

    A real ``Keystroke`` rather than a Mock, because the handlers read three
    different things off a key -- ``name``, ``lower()`` and the string value
    itself -- and a Mock silently answers all three with a truthy Mock.

    Args:
        char: The character or escape sequence the key carries
        name: The blessed key name, for special keys such as ``KEY_ESCAPE``

    Returns:
        A Keystroke; sequences (those with a name) report ``is_sequence``
    """
    if name is None:
        return Keystroke(char)
    return Keystroke(ucs=char or name, code=1, name=name)


class TestInputResult(unittest.TestCase):
    """Tests for InputResult dataclass."""

    def test_default_values(self):
        """Test InputResult default values."""
        result = InputResult()
        self.assertFalse(result.handled)
        self.assertFalse(result.should_quit)
        self.assertFalse(result.needs_redraw)
        self.assertIsNone(result.message)
        self.assertIsNone(result.new_game)

    def test_custom_values(self):
        """Test InputResult with custom values."""
        result = InputResult(
            handled=True, should_quit=True, needs_redraw=True, message="Test message"
        )
        self.assertTrue(result.handled)
        self.assertTrue(result.should_quit)
        self.assertTrue(result.needs_redraw)
        self.assertEqual(result.message, "Test message")


class TestEndGameHandler(unittest.TestCase):
    """Tests for EndGameHandler."""

    def setUp(self):
        """Set up test fixtures."""
        self.handler = EndGameHandler()
        self.game = Mock()
        self.game.conversation_engine = ConversationEngine()
        self.term = Mock()

    def test_quit_on_q_key(self):
        """Test that pressing 'q' sets should_quit flag."""
        result = self.handler.handle(make_key("q"), self.game, self.term)

        self.assertTrue(result.handled)
        self.assertTrue(result.should_quit)

    def test_quit_on_uppercase_q_key(self):
        """Test that pressing 'Q' sets should_quit flag."""
        result = self.handler.handle(make_key("Q"), self.game, self.term)

        self.assertTrue(result.handled)
        self.assertTrue(result.should_quit)

    def test_other_key_does_not_quit(self):
        """Test that pressing other keys doesn't quit."""
        result = self.handler.handle(make_key("x"), self.game, self.term)

        self.assertTrue(result.handled)
        self.assertFalse(result.should_quit)


class TestOverlayHandler(unittest.TestCase):
    """Tests for OverlayHandler."""

    def setUp(self):
        """Set up test fixtures."""
        self.handler = OverlayHandler()
        self.game = Mock()
        self.game.conversation_engine = ConversationEngine()
        self.term = Mock()

    def test_close_inventory_with_v_key(self):
        """Test closing inventory with 'v' key."""
        self.game.conversation_engine.active_inventory = True

        result = self.handler.handle(make_key("v"), self.game, self.term)

        self.assertTrue(result.handled)
        self.assertTrue(result.needs_redraw)
        self.assertFalse(self.game.conversation_engine.active_inventory)

    def test_close_inventory_with_escape(self):
        """Test closing inventory with ESC key."""
        self.game.conversation_engine.active_inventory = True

        result = self.handler.handle(make_key(name="KEY_ESCAPE"), self.game, self.term)

        self.assertTrue(result.handled)
        self.assertTrue(result.needs_redraw)
        self.assertFalse(self.game.conversation_engine.active_inventory)

    def test_close_snippet_with_s_key(self):
        """Test closing snippet with 's' key."""
        self.game.conversation_engine.active_snippet = {"title": "test"}

        result = self.handler.handle(make_key("s"), self.game, self.term)

        self.assertTrue(result.handled)
        self.assertTrue(result.needs_redraw)
        self.assertIsNone(self.game.conversation_engine.active_snippet)

    def test_no_overlay_active_returns_not_handled(self):
        """Test that handler returns not handled when no overlay active."""
        result = self.handler.handle(make_key("z"), self.game, self.term)

        self.assertFalse(result.handled)


class TestOneDismissalContract(unittest.TestCase):
    """Every overlay closes on the same keys, and only on those.

    The three overlays used to disagree: inventory and snippets ignored Enter,
    Space and ``q`` while claiming to be handled, and the info terminal closed
    on literally any key -- including one aimed at the map.
    """

    def setUp(self):
        """Set up test fixtures."""
        self.handler = OverlayHandler()
        self.game = Mock()
        self.game.conversation_engine = ConversationEngine()
        self.term = Mock()

    def _dismiss_keys(self):
        return [
            make_key(name="KEY_ESCAPE"),
            make_key(name="KEY_ENTER"),
            make_key("\n"),
            make_key("\r"),
            make_key(" "),
            make_key("q"),
        ]

    def test_shared_keys_close_the_help_overlay(self):
        for key in [*self._dismiss_keys(), make_key("?")]:
            with self.subTest(key=key.lower(), name=key.name):
                self.game.conversation_engine.active_help = True

                result = self.handler.handle(key, self.game, self.term)

                self.assertTrue(result.needs_redraw)
                self.assertFalse(self.game.conversation_engine.active_help)

    def test_shared_keys_close_the_inventory(self):
        for key in [*self._dismiss_keys(), make_key("v")]:
            with self.subTest(key=key.lower(), name=key.name):
                self.game.conversation_engine.active_inventory = True

                result = self.handler.handle(key, self.game, self.term)

                self.assertTrue(result.needs_redraw)
                self.assertFalse(self.game.conversation_engine.active_inventory)

    def test_shared_keys_close_the_snippet_overlay(self):
        for key in [*self._dismiss_keys(), make_key("s")]:
            with self.subTest(key=key.lower(), name=key.name):
                self.game.conversation_engine.active_snippet = {"title": "test"}

                result = self.handler.handle(key, self.game, self.term)

                self.assertTrue(result.needs_redraw)
                self.assertIsNone(self.game.conversation_engine.active_snippet)

    def test_shared_keys_close_the_terminal_overlay(self):
        for key in self._dismiss_keys():
            with self.subTest(key=key.lower(), name=key.name):
                self.game.conversation_engine.active_terminal = Mock()

                result = self.handler.handle(key, self.game, self.term)

                self.assertTrue(result.needs_redraw)
                self.assertIsNone(self.game.conversation_engine.active_terminal)

    def test_an_unrelated_key_does_not_close_the_terminal_overlay(self):
        """The regression: a stray keystroke used to throw the panel away."""
        terminal = Mock()
        self.game.conversation_engine.active_terminal = terminal

        result = self.handler.handle(make_key("z"), self.game, self.term)

        self.assertTrue(result.handled)
        self.assertFalse(result.needs_redraw)
        self.assertIs(self.game.conversation_engine.active_terminal, terminal)

    def test_an_unrelated_key_does_not_close_the_help_overlay(self):
        self.game.conversation_engine.active_help = True

        result = self.handler.handle(make_key("z"), self.game, self.term)

        self.assertTrue(result.handled)
        self.assertTrue(self.game.conversation_engine.active_help)

    def test_an_unrelated_key_is_swallowed_not_passed_on(self):
        """Overlays are modal: a key they ignore must not reach the map."""
        self.game.conversation_engine.active_inventory = True

        result = self.handler.handle(make_key("z"), self.game, self.term)

        self.assertTrue(result.handled)
        self.assertTrue(self.game.conversation_engine.active_inventory)


class TestHelpKey(unittest.TestCase):
    """`?` opens the legend, and it round-trips."""

    def setUp(self):
        """Set up test fixtures."""
        self.normal = NormalModeHandler()
        self.overlay = OverlayHandler()
        self.game = Mock()
        self.game.conversation_engine = ConversationEngine()
        self.term = Mock()

    def test_question_mark_opens_help(self):
        result = self.normal.handle(make_key("?"), self.game, self.term)

        self.assertTrue(result.handled)
        self.assertTrue(result.needs_redraw)
        self.assertTrue(self.game.conversation_engine.active_help)

    def test_escape_opens_help(self):
        """ESC in normal mode used to be a no-op that fell through unhandled."""
        result = self.normal.handle(make_key(name="KEY_ESCAPE"), self.game, self.term)

        self.assertTrue(result.handled)
        self.assertTrue(self.game.conversation_engine.active_help)

    def test_question_mark_closes_help_again(self):
        self.normal.handle(make_key("?"), self.game, self.term)

        self.overlay.handle(make_key("?"), self.game, self.term)

        self.assertFalse(self.game.conversation_engine.active_help)

    def test_the_main_loop_routes_keys_to_the_help_overlay(self):
        """Opening help must also take the keyboard, or ESC would move instead."""
        self.normal.handle(make_key("?"), self.game, self.term)

        self.assertTrue(overlay_is_open(self.game))

    def test_help_is_off_by_default(self):
        self.assertFalse(ConversationEngine().active_help)

    def test_help_is_not_reachable_from_a_conversation(self):
        """`?` is a character a short answer may need, so it must not open help."""
        question = Mock()
        question.question_type = QuestionType.SHORT_ANSWER
        conversation = Mock()
        conversation.get_current_question.return_value = question
        self.game.conversation_engine.active_conversation = conversation
        self.game.conversation_engine.show_greeting = False
        self.game.conversation_engine.last_answer_response = None

        ConversationHandler().handle(make_key("?"), self.game, self.term)

        self.assertFalse(self.game.conversation_engine.active_help)
        self.assertEqual(self.game.conversation_engine.text_input_buffer, "?")


class TestConversationHandler(unittest.TestCase):
    """Tests for ConversationHandler."""

    def setUp(self):
        """Set up test fixtures."""
        self.handler = ConversationHandler()
        self.game = Mock()
        self.game.conversation_engine = ConversationEngine()
        self.term = Mock()

    def _multiple_choice(self, answer_count: int = 4):
        """Put a multiple choice question on screen."""
        question = Mock()
        question.question_type = QuestionType.MULTIPLE_CHOICE
        question.answers = [Mock() for _ in range(answer_count)]

        conversation = Mock()
        conversation.get_current_question.return_value = question

        self.game.conversation_engine.active_conversation = conversation
        self.game.conversation_engine.show_greeting = False
        self.game.conversation_engine.last_answer_response = None
        return question

    def _text_question(self, question_type):
        """Put a text-based question on screen."""
        question = Mock()
        question.question_type = question_type

        conversation = Mock()
        conversation.get_current_question.return_value = question

        self.game.conversation_engine.active_conversation = conversation
        self.game.conversation_engine.show_greeting = False
        self.game.conversation_engine.last_answer_response = None
        return question

    def test_no_conversation_returns_not_handled(self):
        """Test handler returns not handled when no conversation active."""
        result = self.handler.handle(make_key("z"), self.game, self.term)

        self.assertFalse(result.handled)

    def test_cleans_up_lingering_response_state(self):
        """Test that handler cleans up lingering response without active conversation."""
        self.game.conversation_engine.last_answer_response = "Old response"

        result = self.handler.handle(make_key("z"), self.game, self.term)

        self.assertTrue(result.handled)
        self.assertTrue(result.needs_redraw)
        self.assertIsNone(self.game.conversation_engine.last_answer_response)

    def test_greeting_dismissal_any_key(self):
        """Test that any key dismisses greeting."""
        self.game.conversation_engine.active_conversation = Mock()
        self.game.conversation_engine.show_greeting = True

        result = self.handler.handle(make_key("z"), self.game, self.term)

        self.assertTrue(result.handled)
        self.assertFalse(self.game.conversation_engine.show_greeting)
        self.assertEqual(self.game.conversation_engine.text_input_buffer, "")

    def test_response_dismissal_any_key(self):
        """Test that any key dismisses response."""
        self.game.conversation_engine.active_conversation = Mock()
        self.game.conversation_engine.last_answer_response = "Test response"

        result = self.handler.handle(make_key("z"), self.game, self.term)

        self.assertTrue(result.handled)
        self.assertIsNone(self.game.conversation_engine.last_answer_response)
        self.assertEqual(self.game.conversation_engine.text_input_buffer, "")

    def test_yes_no_question_y_answer(self):
        """Test answering yes/no question with 'y'."""
        self._text_question(QuestionType.YES_NO)
        self.game.answer_text_question.return_value = (True, "Correct!")

        result = self.handler.handle(make_key("y"), self.game, self.term)

        self.assertTrue(result.handled)
        self.assertTrue(result.needs_redraw)
        self.game.answer_text_question.assert_called_once_with("yes")
        self.assertEqual(self.game.conversation_engine.last_answer_response, "Correct!")

    def test_yes_no_question_n_answer(self):
        """Test answering yes/no question with 'n'."""
        self._text_question(QuestionType.YES_NO)
        self.game.answer_text_question.return_value = (False, "Incorrect!")

        result = self.handler.handle(make_key("n"), self.game, self.term)

        self.assertTrue(result.handled)
        self.assertTrue(result.needs_redraw)
        self.game.answer_text_question.assert_called_once_with("no")
        self.assertEqual(self.game.conversation_engine.last_answer_response, "Incorrect!")

    def test_multiple_choice_answer_selection(self):
        """Test answering multiple choice question with number key."""
        self._multiple_choice()
        self.game.answer_question.return_value = (True, "Correct!")

        result = self.handler.handle(make_key("1"), self.game, self.term)

        self.assertTrue(result.handled)
        self.assertTrue(result.needs_redraw)
        self.game.answer_question.assert_called_once_with(0)
        self.assertEqual(self.game.conversation_engine.last_answer_response, "Correct!")

    def test_multiple_choice_hint_usage(self):
        """Test using hint in multiple choice question."""
        self._multiple_choice()
        self.game.use_hint.return_value = (True, "Hint: Look for Big O notation")

        result = self.handler.handle(make_key("h"), self.game, self.term)

        self.assertTrue(result.handled)
        self.assertTrue(result.needs_redraw)
        self.game.use_hint.assert_called_once()
        self.assertEqual(self.game.message, "Hint: Look for Big O notation")

    def test_exit_conversation_with_escape(self):
        """Test exiting conversation with ESC key."""
        self._multiple_choice()

        result = self.handler.handle(make_key(name="KEY_ESCAPE"), self.game, self.term)

        self.assertTrue(result.handled)
        self.assertTrue(result.needs_redraw)
        self.game.exit_conversation.assert_called_once()


class TestAnswersMustBeOnScreen(unittest.TestCase):
    """Number keys only select options the renderer actually drew.

    "1"-"4" was hardcoded, while the renderer skips indices a hint token
    eliminated -- so the player could pick an option that was not displayed,
    and a five-option question would have been unanswerable.
    """

    def setUp(self):
        """Set up test fixtures."""
        self.handler = ConversationHandler()
        self.game = Mock()
        self.game.conversation_engine = ConversationEngine()
        self.game.answer_question.return_value = (True, "Correct!")
        self.term = Mock()

    def _show(self, answer_count: int, eliminated: set[int] | None = None):
        question = Mock()
        question.question_type = QuestionType.MULTIPLE_CHOICE
        question.answers = [Mock() for _ in range(answer_count)]

        conversation = Mock()
        conversation.get_current_question.return_value = question

        self.game.conversation_engine.active_conversation = conversation
        self.game.conversation_engine.show_greeting = False
        self.game.conversation_engine.last_answer_response = None
        self.game.conversation_engine.eliminated_answers = eliminated or set()

    def test_an_eliminated_answer_cannot_be_selected(self):
        self._show(4, eliminated={1})

        result = self.handler.handle(make_key("2"), self.game, self.term)

        self.assertTrue(result.handled)
        self.game.answer_question.assert_not_called()

    def test_the_answers_still_on_screen_keep_their_numbers(self):
        """Eliminating index 1 must not renumber 3 into 2."""
        self._show(4, eliminated={1})

        self.handler.handle(make_key("3"), self.game, self.term)

        self.game.answer_question.assert_called_once_with(2)

    def test_a_number_past_the_last_answer_is_ignored(self):
        self._show(3)

        result = self.handler.handle(make_key("4"), self.game, self.term)

        self.assertTrue(result.handled)
        self.game.answer_question.assert_not_called()

    def test_a_fifth_option_is_selectable(self):
        self._show(5)

        self.handler.handle(make_key("5"), self.game, self.term)

        self.game.answer_question.assert_called_once_with(4)


class TestExitKeysMatchTheFooter(unittest.TestCase):
    """The keys the renderers promise are the keys the handler takes."""

    def setUp(self):
        """Set up test fixtures."""
        self.handler = ConversationHandler()
        self.game = Mock()
        self.game.conversation_engine = ConversationEngine()
        self.term = Mock()

    def _show(self, question_type):
        question = Mock()
        question.question_type = question_type
        question.answers = [Mock() for _ in range(4)]

        conversation = Mock()
        conversation.get_current_question.return_value = question

        self.game.conversation_engine.active_conversation = conversation
        self.game.conversation_engine.show_greeting = False
        self.game.conversation_engine.last_answer_response = None

    def test_short_answer_exits_on_lowercase_x(self):
        self._show(QuestionType.SHORT_ANSWER)

        self.handler.handle(make_key("x"), self.game, self.term)

        self.game.exit_conversation.assert_called_once()

    def test_short_answer_exits_on_uppercase_x(self):
        """`key.lower()` is what the handler compares, so case cannot diverge."""
        self._show(QuestionType.SHORT_ANSWER)

        self.handler.handle(make_key("X"), self.game, self.term)

        self.game.exit_conversation.assert_called_once()

    def test_short_answer_keeps_x_typeable_once_typing_has_started(self):
        self._show(QuestionType.SHORT_ANSWER)
        self.game.conversation_engine.text_input_buffer = "quic"

        self.handler.handle(make_key("x"), self.game, self.term)

        self.game.exit_conversation.assert_not_called()
        self.assertEqual(self.game.conversation_engine.text_input_buffer, "quicx")

    def test_short_answer_keeps_q_typeable(self):
        """ "quicksort" starts with the key that leaves every other question."""
        self._show(QuestionType.SHORT_ANSWER)

        self.handler.handle(make_key("q"), self.game, self.term)

        self.game.exit_conversation.assert_not_called()
        self.assertEqual(self.game.conversation_engine.text_input_buffer, "q")

    def test_yes_no_exits_on_x(self):
        self._show(QuestionType.YES_NO)

        self.handler.handle(make_key("x"), self.game, self.term)

        self.game.exit_conversation.assert_called_once()

    def test_yes_no_exits_on_q(self):
        self._show(QuestionType.YES_NO)

        self.handler.handle(make_key("q"), self.game, self.term)

        self.game.exit_conversation.assert_called_once()

    def test_yes_no_does_not_collect_typed_text(self):
        """Typing a letter used to fill the buffer and disarm the X exit."""
        self._show(QuestionType.YES_NO)

        self.handler.handle(make_key("m"), self.game, self.term)

        self.assertEqual(self.game.conversation_engine.text_input_buffer, "")
        self.game.answer_text_question.assert_not_called()

    def test_yes_no_still_exits_on_x_after_a_stray_letter(self):
        self._show(QuestionType.YES_NO)

        self.handler.handle(make_key("m"), self.game, self.term)
        self.handler.handle(make_key("x"), self.game, self.term)

        self.game.exit_conversation.assert_called_once()

    def test_multiple_choice_exits_on_q(self):
        self._show(QuestionType.MULTIPLE_CHOICE)

        self.handler.handle(make_key("q"), self.game, self.term)

        self.game.exit_conversation.assert_called_once()


class TestTextEditing(unittest.TestCase):
    """Backspace was the only edit available; Ctrl+U and Ctrl+W now work too."""

    def setUp(self):
        """Set up test fixtures."""
        self.handler = ConversationHandler()
        self.game = Mock()
        self.game.conversation_engine = ConversationEngine()
        self.term = Mock()

        question = Mock()
        question.question_type = QuestionType.SHORT_ANSWER
        conversation = Mock()
        conversation.get_current_question.return_value = question
        self.game.conversation_engine.active_conversation = conversation
        self.game.conversation_engine.show_greeting = False
        self.game.conversation_engine.last_answer_response = None

    def _type(self, text: str) -> None:
        self.game.conversation_engine.text_input_buffer = text

    def test_ctrl_u_clears_the_line(self):
        self._type("binary search tree")

        self.handler.handle(make_key("\x15"), self.game, self.term)

        self.assertEqual(self.game.conversation_engine.text_input_buffer, "")

    def test_ctrl_u_on_an_empty_line_is_harmless(self):
        self.handler.handle(make_key("\x15"), self.game, self.term)

        self.assertEqual(self.game.conversation_engine.text_input_buffer, "")

    def test_ctrl_w_deletes_the_last_word(self):
        self._type("binary search tree")

        self.handler.handle(make_key("\x17"), self.game, self.term)

        self.assertEqual(self.game.conversation_engine.text_input_buffer, "binary search ")

    def test_ctrl_w_reaches_past_a_trailing_space(self):
        self._type("binary search ")

        self.handler.handle(make_key("\x17"), self.game, self.term)

        self.assertEqual(self.game.conversation_engine.text_input_buffer, "binary ")

    def test_ctrl_w_on_a_single_word_empties_the_line(self):
        self._type("quicksort")

        self.handler.handle(make_key("\x17"), self.game, self.term)

        self.assertEqual(self.game.conversation_engine.text_input_buffer, "")

    def test_backspace_still_works(self):
        self._type("heap")

        self.handler.handle(make_key("\x7f"), self.game, self.term)

        self.assertEqual(self.game.conversation_engine.text_input_buffer, "hea")

    def test_a_control_key_is_not_typed_as_a_character(self):
        self._type("heap")

        self.handler.handle(make_key("\x15"), self.game, self.term)

        self.assertNotIn("\x15", self.game.conversation_engine.text_input_buffer)


class TestNormalModeHandler(unittest.TestCase):
    """Tests for NormalModeHandler."""

    def setUp(self):
        """Set up test fixtures."""
        self.handler = NormalModeHandler()
        self.game = Mock()
        self.game.conversation_engine = ConversationEngine()
        self.term = Mock()

    def test_save_game_success(self):
        """Test saving game successfully."""
        self.game.save_game.return_value = (True, "/path/to/save.json")

        result = self.handler.handle(make_key("s"), self.game, self.term)

        self.assertTrue(result.handled)
        self.assertTrue(result.needs_redraw)
        self.assertEqual(result.message, "Game saved to /path/to/save.json")

    def test_save_game_failure(self):
        """Test saving game failure."""
        self.game.save_game.return_value = (False, None)

        result = self.handler.handle(make_key("s"), self.game, self.term)

        self.assertTrue(result.handled)
        self.assertTrue(result.needs_redraw)
        self.assertEqual(result.message, "Failed to save game.")

    def test_toggle_inventory(self):
        """Test toggling inventory."""
        result = self.handler.handle(make_key("v"), self.game, self.term)

        self.assertTrue(result.handled)
        self.assertTrue(result.needs_redraw)
        self.assertTrue(self.game.conversation_engine.active_inventory)

    def test_move_up(self):
        """Test moving player up."""
        result = self.handler.handle(make_key(name="KEY_UP"), self.game, self.term)

        self.assertTrue(result.handled)
        self.game.move_player.assert_called_once_with(0, -1)

    def test_move_down(self):
        """Test moving player down."""
        result = self.handler.handle(make_key(name="KEY_DOWN"), self.game, self.term)

        self.assertTrue(result.handled)
        self.game.move_player.assert_called_once_with(0, 1)

    def test_move_left(self):
        """Test moving player left."""
        result = self.handler.handle(make_key(name="KEY_LEFT"), self.game, self.term)

        self.assertTrue(result.handled)
        self.game.move_player.assert_called_once_with(-1, 0)

    def test_move_right(self):
        """Test moving player right."""
        result = self.handler.handle(make_key(name="KEY_RIGHT"), self.game, self.term)

        self.assertTrue(result.handled)
        self.game.move_player.assert_called_once_with(1, 0)

    def test_use_stairs_with_angle_bracket(self):
        """Test using stairs with '>' character."""
        self.game.use_stairs.return_value = True

        result = self.handler.handle(make_key(">"), self.game, self.term)

        self.assertTrue(result.handled)
        self.assertTrue(result.needs_redraw)
        self.game.use_stairs.assert_called_once()

    def test_interact_starts_conversation(self):
        """Test that interaction starts conversation."""
        self.game.interact.return_value = True

        result = self.handler.handle(make_key("i"), self.game, self.term)

        self.assertTrue(result.handled)
        self.game.interact.assert_called_once()

    def test_interact_with_space_key(self):
        """Test interaction with space key."""
        self.game.interact.return_value = True

        result = self.handler.handle(make_key(" "), self.game, self.term)

        self.assertTrue(result.handled)
        self.game.interact.assert_called_once()

    def test_interact_does_not_second_guess_the_engine(self):
        """`Game.interact` sets the greeting itself; the handler must not redo it."""
        self.game.interact.return_value = True
        self.game.conversation_engine.show_greeting = True
        self.game.conversation_engine.last_answer_response = "left over"

        self.handler.handle(make_key(" "), self.game, self.term)

        self.assertEqual(self.game.conversation_engine.last_answer_response, "left over")


class TestDestructiveKeysAskFirst(unittest.TestCase):
    """Q and L used to end a run on one keystroke, next to the movement keys."""

    def setUp(self):
        """Set up test fixtures."""
        self.handler = NormalModeHandler()
        self.game = Mock()
        self.game.conversation_engine = ConversationEngine()
        self.term = Mock()

    def test_q_does_not_quit_on_its_own(self):
        result = self.handler.handle(make_key("q"), self.game, self.term)

        self.assertTrue(result.handled)
        self.assertFalse(result.should_quit)
        self.assertEqual(result.message, QUIT_PROMPT)

    def test_q_then_y_quits(self):
        self.handler.handle(make_key("q"), self.game, self.term)

        result = self.handler.handle(make_key("y"), self.game, self.term)

        self.assertTrue(result.should_quit)

    def test_q_then_n_cancels(self):
        self.handler.handle(make_key("q"), self.game, self.term)

        result = self.handler.handle(make_key("n"), self.game, self.term)

        self.assertTrue(result.handled)
        self.assertFalse(result.should_quit)
        self.assertEqual(result.message, CANCELLED_MESSAGE)

    def test_any_other_key_cancels_the_quit_prompt(self):
        self.handler.handle(make_key("q"), self.game, self.term)

        result = self.handler.handle(make_key(name="KEY_UP"), self.game, self.term)

        self.assertFalse(result.should_quit)
        self.game.move_player.assert_not_called()

    def test_cancelling_returns_to_normal_mode(self):
        """A cancelled prompt must not leave the player in a mode with no exit."""
        self.handler.handle(make_key("q"), self.game, self.term)
        self.handler.handle(make_key("n"), self.game, self.term)

        self.assertIsNone(self.handler.pending_confirm)

        result = self.handler.handle(make_key(name="KEY_UP"), self.game, self.term)

        self.assertTrue(result.handled)
        self.game.move_player.assert_called_once_with(0, -1)

    def test_confirming_a_quit_does_not_leave_the_prompt_armed(self):
        self.handler.handle(make_key("q"), self.game, self.term)
        self.handler.handle(make_key("y"), self.game, self.term)

        self.assertIsNone(self.handler.pending_confirm)

    @patch("neural_dive.game_serializer.GameSerializer")
    @patch("neural_dive.game.Game")
    def test_l_does_not_load_on_its_own(self, mock_game_class, mock_serializer):
        mock_serializer.get_default_save_path.return_value = "/path/to/save.json"

        result = self.handler.handle(make_key("l"), self.game, self.term)

        self.assertTrue(result.handled)
        self.assertIsNone(result.new_game)
        self.assertEqual(result.message, LOAD_PROMPT)
        mock_game_class.load_game.assert_not_called()

    @patch("neural_dive.game_serializer.GameSerializer")
    @patch("neural_dive.game.Game")
    def test_l_then_y_loads(self, mock_game_class, mock_serializer):
        mock_serializer.get_default_save_path.return_value = "/path/to/save.json"
        loaded_game = Mock()
        mock_game_class.load_game.return_value = loaded_game

        self.handler.handle(make_key("l"), self.game, self.term)
        result = self.handler.handle(make_key("y"), self.game, self.term)

        self.assertTrue(result.needs_redraw)
        self.assertEqual(result.message, "Game loaded from /path/to/save.json")
        self.assertEqual(result.new_game, loaded_game)

    @patch("neural_dive.game_serializer.GameSerializer")
    @patch("neural_dive.game.Game")
    def test_l_then_n_keeps_the_run(self, mock_game_class, mock_serializer):
        mock_serializer.get_default_save_path.return_value = "/path/to/save.json"

        self.handler.handle(make_key("l"), self.game, self.term)
        result = self.handler.handle(make_key("n"), self.game, self.term)

        self.assertIsNone(result.new_game)
        self.assertEqual(result.message, CANCELLED_MESSAGE)
        mock_game_class.load_game.assert_not_called()

    @patch("neural_dive.game_serializer.GameSerializer")
    @patch("neural_dive.game.Game")
    def test_load_with_no_save_file_reports_it(self, mock_game_class, mock_serializer):
        mock_serializer.get_default_save_path.return_value = "/path/to/save.json"
        mock_game_class.load_game.return_value = None

        self.handler.handle(make_key("l"), self.game, self.term)
        result = self.handler.handle(make_key("y"), self.game, self.term)

        self.assertTrue(result.handled)
        self.assertEqual(result.message, "No save file found at /path/to/save.json")
        self.assertIsNone(result.new_game)

    def test_the_prompt_fits_the_narrowest_supported_message_line(self):
        """`_draw_message_line` clips at width - 4, and the minimum width is 50."""
        from neural_dive.config import MIN_TERMINAL_WIDTH

        for prompt in (QUIT_PROMPT, LOAD_PROMPT, CANCELLED_MESSAGE):
            with self.subTest(prompt=prompt):
                self.assertLessEqual(len(prompt), MIN_TERMINAL_WIDTH - 4)


class TestOverlayDispatch(unittest.TestCase):
    """`overlay_is_open` is what the main loop routes on."""

    def setUp(self):
        """Set up test fixtures."""
        self.game = Mock()
        self.game.conversation_engine = ConversationEngine()

    def test_no_overlay_leaves_the_keyboard_to_normal_mode(self):
        self.assertFalse(overlay_is_open(self.game))

    def test_every_overlay_takes_the_keyboard(self):
        cases = {
            "active_help": True,
            "active_inventory": True,
            "active_snippet": {"title": "test"},
            "active_terminal": Mock(),
        }
        for field, value in cases.items():
            with self.subTest(field=field):
                engine = ConversationEngine()
                setattr(engine, field, value)
                self.game.conversation_engine = engine

                self.assertTrue(overlay_is_open(self.game))


if __name__ == "__main__":
    unittest.main()
