"""Tests for input handling system."""

from __future__ import annotations

import unittest
from unittest.mock import Mock, patch

from neural_dive.input_handler import (
    ConversationHandler,
    EndGameHandler,
    InputResult,
    NormalModeHandler,
    OverlayHandler,
)
from neural_dive.question_types import QuestionType


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
        self.term = Mock()

    def test_quit_on_q_key(self):
        """Test that pressing 'q' sets should_quit flag."""
        key = Mock()
        key.lower.return_value = "q"

        result = self.handler.handle(key, self.game, self.term)

        self.assertTrue(result.handled)
        self.assertTrue(result.should_quit)

    def test_quit_on_uppercase_q_key(self):
        """Test that pressing 'Q' sets should_quit flag."""
        key = Mock()
        key.lower.return_value = "q"

        result = self.handler.handle(key, self.game, self.term)

        self.assertTrue(result.handled)
        self.assertTrue(result.should_quit)

    def test_other_key_does_not_quit(self):
        """Test that pressing other keys doesn't quit."""
        key = Mock()
        key.lower.return_value = "x"

        result = self.handler.handle(key, self.game, self.term)

        self.assertTrue(result.handled)
        self.assertFalse(result.should_quit)


class TestOverlayHandler(unittest.TestCase):
    """Tests for OverlayHandler."""

    def setUp(self):
        """Set up test fixtures."""
        self.handler = OverlayHandler()
        self.game = Mock()
        self.term = Mock()

    def test_close_inventory_with_v_key(self):
        """Test closing inventory with 'v' key."""
        self.game.active_inventory = True
        self.game.active_snippet = None
        self.game.active_terminal = None

        key = Mock()
        key.lower.return_value = "v"
        key.name = "v"

        result = self.handler.handle(key, self.game, self.term)

        self.assertTrue(result.handled)
        self.assertTrue(result.needs_redraw)
        self.assertFalse(self.game.active_inventory)

    def test_close_inventory_with_escape(self):
        """Test closing inventory with ESC key."""
        self.game.active_inventory = True
        self.game.active_snippet = None
        self.game.active_terminal = None

        key = Mock()
        key.name = "KEY_ESCAPE"

        result = self.handler.handle(key, self.game, self.term)

        self.assertTrue(result.handled)
        self.assertTrue(result.needs_redraw)
        self.assertFalse(self.game.active_inventory)

    def test_close_snippet_with_s_key(self):
        """Test closing snippet with 's' key."""
        self.game.active_inventory = False
        self.game.active_snippet = "test_snippet"
        self.game.active_terminal = None

        key = Mock()
        key.lower.return_value = "s"

        result = self.handler.handle(key, self.game, self.term)

        self.assertTrue(result.handled)
        self.assertTrue(result.needs_redraw)
        self.assertIsNone(self.game.active_snippet)

    def test_close_terminal_with_any_key(self):
        """Test closing terminal with any key."""
        self.game.active_inventory = False
        self.game.active_snippet = None
        self.game.active_terminal = "test_terminal"

        key = Mock()
        key.lower.return_value = "x"

        result = self.handler.handle(key, self.game, self.term)

        self.assertTrue(result.handled)
        self.assertTrue(result.needs_redraw)
        self.assertIsNone(self.game.active_terminal)

    def test_no_overlay_active_returns_not_handled(self):
        """Test that handler returns not handled when no overlay active."""
        self.game.active_inventory = False
        self.game.active_snippet = None
        self.game.active_terminal = None

        key = Mock()

        result = self.handler.handle(key, self.game, self.term)

        self.assertFalse(result.handled)


class TestConversationHandler(unittest.TestCase):
    """Tests for ConversationHandler."""

    def setUp(self):
        """Set up test fixtures."""
        self.handler = ConversationHandler()
        self.game = Mock()
        self.term = Mock()

    def test_no_conversation_returns_not_handled(self):
        """Test handler returns not handled when no conversation active."""
        self.game.active_conversation = None

        # Ensure no lingering response state
        if hasattr(self.game, "last_answer_response"):
            del self.game.last_answer_response

        key = Mock()

        result = self.handler.handle(key, self.game, self.term)

        self.assertFalse(result.handled)

    def test_cleans_up_lingering_response_state(self):
        """Test that handler cleans up lingering response without active conversation."""
        self.game.active_conversation = None
        self.game.last_answer_response = "Old response"

        key = Mock()

        result = self.handler.handle(key, self.game, self.term)

        self.assertTrue(result.handled)
        self.assertTrue(result.needs_redraw)
        self.assertIsNone(self.game.last_answer_response)

    def test_greeting_dismissal_any_key(self):
        """Test that any key dismisses greeting."""
        self.game.active_conversation = Mock()
        self.game.show_greeting = True
        self.game.text_input_buffer = ""

        key = Mock()

        result = self.handler.handle(key, self.game, self.term)

        self.assertTrue(result.handled)
        self.assertFalse(self.game.show_greeting)
        self.assertEqual(self.game.text_input_buffer, "")

    def test_response_dismissal_any_key(self):
        """Test that any key dismisses response."""
        self.game.active_conversation = Mock()
        self.game.show_greeting = False
        self.game.last_answer_response = "Test response"
        self.game.text_input_buffer = ""

        key = Mock()

        result = self.handler.handle(key, self.game, self.term)

        self.assertTrue(result.handled)
        self.assertIsNone(self.game.last_answer_response)
        self.assertEqual(self.game.text_input_buffer, "")

    def test_yes_no_question_y_answer(self):
        """Test answering yes/no question with 'y'."""
        question = Mock()
        question.question_type = QuestionType.YES_NO

        conversation = Mock()
        conversation.get_current_question.return_value = question

        self.game.active_conversation = conversation
        self.game.show_greeting = False
        self.game.last_answer_response = None
        self.game.text_input_buffer = ""
        self.game.answer_text_question.return_value = (True, "Correct!")

        key = Mock()
        key.lower.return_value = "y"

        result = self.handler.handle(key, self.game, self.term)

        self.assertTrue(result.handled)
        self.assertTrue(result.needs_redraw)
        self.game.answer_text_question.assert_called_once_with("yes")
        self.assertEqual(self.game.last_answer_response, "Correct!")

    def test_yes_no_question_n_answer(self):
        """Test answering yes/no question with 'n'."""
        question = Mock()
        question.question_type = QuestionType.YES_NO

        conversation = Mock()
        conversation.get_current_question.return_value = question

        self.game.active_conversation = conversation
        self.game.show_greeting = False
        self.game.last_answer_response = None
        self.game.text_input_buffer = ""
        self.game.answer_text_question.return_value = (False, "Incorrect!")

        key = Mock()
        key.lower.return_value = "n"

        result = self.handler.handle(key, self.game, self.term)

        self.assertTrue(result.handled)
        self.assertTrue(result.needs_redraw)
        self.game.answer_text_question.assert_called_once_with("no")
        self.assertEqual(self.game.last_answer_response, "Incorrect!")

    def test_multiple_choice_answer_selection(self):
        """Test answering multiple choice question with number key."""
        question = Mock()
        question.question_type = QuestionType.MULTIPLE_CHOICE

        conversation = Mock()
        conversation.get_current_question.return_value = question

        self.game.active_conversation = conversation
        self.game.show_greeting = False
        self.game.last_answer_response = None
        self.game.text_input_buffer = ""
        self.game.answer_question.return_value = (True, "Correct!")

        # Use a string "1" directly instead of Mock
        key = "1"

        result = self.handler.handle(key, self.game, self.term)  # type: ignore[arg-type]

        self.assertTrue(result.handled)
        self.assertTrue(result.needs_redraw)
        self.game.answer_question.assert_called_once_with(0)
        self.assertEqual(self.game.last_answer_response, "Correct!")

    def test_multiple_choice_hint_usage(self):
        """Test using hint in multiple choice question."""
        question = Mock()
        question.question_type = QuestionType.MULTIPLE_CHOICE

        conversation = Mock()
        conversation.get_current_question.return_value = question

        self.game.active_conversation = conversation
        self.game.show_greeting = False
        self.game.last_answer_response = None
        self.game.use_hint.return_value = (True, "Hint: Look for Big O notation")

        key = Mock()
        key.lower.return_value = "h"

        result = self.handler.handle(key, self.game, self.term)

        self.assertTrue(result.handled)
        self.assertTrue(result.needs_redraw)
        self.game.use_hint.assert_called_once()
        self.assertEqual(self.game.message, "Hint: Look for Big O notation")

    def test_exit_conversation_with_escape(self):
        """Test exiting conversation with ESC key."""
        question = Mock()
        question.question_type = QuestionType.MULTIPLE_CHOICE

        conversation = Mock()
        conversation.get_current_question.return_value = question

        self.game.active_conversation = conversation
        self.game.show_greeting = False
        self.game.last_answer_response = None
        self.game.text_input_buffer = ""

        key = Mock()
        key.name = "KEY_ESCAPE"
        key.lower.return_value = "escape"

        result = self.handler.handle(key, self.game, self.term)

        self.assertTrue(result.handled)
        self.assertTrue(result.needs_redraw)
        self.game.exit_conversation.assert_called_once()


class TestNormalModeHandler(unittest.TestCase):
    """Tests for NormalModeHandler."""

    def setUp(self):
        """Set up test fixtures."""
        self.handler = NormalModeHandler()
        self.game = Mock()
        self.term = Mock()

    def test_quit_with_q_key(self):
        """Test quitting game with 'q' key."""
        key = Mock()
        key.lower.return_value = "q"

        result = self.handler.handle(key, self.game, self.term)

        self.assertTrue(result.handled)
        self.assertTrue(result.should_quit)

    def test_save_game_success(self):
        """Test saving game successfully."""
        self.game.save_game.return_value = (True, "/path/to/save.json")

        key = Mock()
        key.lower.return_value = "s"

        result = self.handler.handle(key, self.game, self.term)

        self.assertTrue(result.handled)
        self.assertTrue(result.needs_redraw)
        self.assertEqual(result.message, "Game saved to /path/to/save.json")

    def test_save_game_failure(self):
        """Test saving game failure."""
        self.game.save_game.return_value = (False, None)

        key = Mock()
        key.lower.return_value = "s"

        result = self.handler.handle(key, self.game, self.term)

        self.assertTrue(result.handled)
        self.assertTrue(result.needs_redraw)
        self.assertEqual(result.message, "Failed to save game.")

    @patch("neural_dive.game_serializer.GameSerializer")
    @patch("neural_dive.game.Game")
    def test_load_game_success(self, mock_game_class, mock_serializer):
        """Test loading game successfully."""
        mock_serializer.get_default_save_path.return_value = "/path/to/save.json"
        loaded_game = Mock()
        mock_game_class.load_game.return_value = loaded_game

        key = Mock()
        key.lower.return_value = "l"

        result = self.handler.handle(key, self.game, self.term)

        self.assertTrue(result.handled)
        self.assertTrue(result.needs_redraw)
        self.assertEqual(result.message, "Game loaded from /path/to/save.json")
        self.assertEqual(result.new_game, loaded_game)

    @patch("neural_dive.game_serializer.GameSerializer")
    @patch("neural_dive.game.Game")
    def test_load_game_failure(self, mock_game_class, mock_serializer):
        """Test loading game failure."""
        mock_serializer.get_default_save_path.return_value = "/path/to/save.json"
        mock_game_class.load_game.return_value = None

        key = Mock()
        key.lower.return_value = "l"

        result = self.handler.handle(key, self.game, self.term)

        self.assertTrue(result.handled)
        self.assertTrue(result.needs_redraw)
        self.assertEqual(result.message, "No save file found at /path/to/save.json")
        self.assertIsNone(result.new_game)

    def test_toggle_inventory(self):
        """Test toggling inventory."""
        self.game.active_inventory = False

        key = Mock()
        key.lower.return_value = "v"

        result = self.handler.handle(key, self.game, self.term)

        self.assertTrue(result.handled)
        self.assertTrue(result.needs_redraw)
        self.assertTrue(self.game.active_inventory)

    def test_move_up(self):
        """Test moving player up."""
        key = Mock()
        key.name = "KEY_UP"

        result = self.handler.handle(key, self.game, self.term)

        self.assertTrue(result.handled)
        self.game.move_player.assert_called_once_with(0, -1)

    def test_move_down(self):
        """Test moving player down."""
        key = Mock()
        key.name = "KEY_DOWN"

        result = self.handler.handle(key, self.game, self.term)

        self.assertTrue(result.handled)
        self.game.move_player.assert_called_once_with(0, 1)

    def test_move_left(self):
        """Test moving player left."""
        key = Mock()
        key.name = "KEY_LEFT"

        result = self.handler.handle(key, self.game, self.term)

        self.assertTrue(result.handled)
        self.game.move_player.assert_called_once_with(-1, 0)

    def test_move_right(self):
        """Test moving player right."""
        key = Mock()
        key.name = "KEY_RIGHT"

        result = self.handler.handle(key, self.game, self.term)

        self.assertTrue(result.handled)
        self.game.move_player.assert_called_once_with(1, 0)

    def test_use_stairs_with_angle_bracket(self):
        """Test using stairs with '>' character."""
        self.game.use_stairs.return_value = True

        key = Mock()
        key.__eq__ = lambda self, other: other == ">"  # type: ignore[method-assign, misc, assignment]
        key.name = ">"

        result = self.handler.handle(key, self.game, self.term)

        self.assertTrue(result.handled)
        self.assertTrue(result.needs_redraw)
        self.game.use_stairs.assert_called_once()

    def test_interact_starts_conversation(self):
        """Test that interaction starts conversation."""
        self.game.interact.return_value = True
        self.game.active_conversation = Mock()

        key = Mock()
        key.lower.return_value = "i"
        key.name = "i"
        key.__eq__ = lambda self, other: False  # type: ignore[method-assign, misc, assignment]

        result = self.handler.handle(key, self.game, self.term)

        self.assertTrue(result.handled)
        self.game.interact.assert_called_once()
        self.assertTrue(self.game.show_greeting)
        self.assertIsNone(self.game.last_answer_response)

    def test_interact_with_space_key(self):
        """Test interaction with space key."""
        self.game.interact.return_value = True
        self.game.active_conversation = Mock()

        key = Mock()
        key.lower.return_value = " "
        key.__eq__ = lambda self, other: other == " "  # type: ignore[method-assign, misc, assignment]
        key.name = "space"

        result = self.handler.handle(key, self.game, self.term)

        self.assertTrue(result.handled)
        self.game.interact.assert_called_once()


if __name__ == "__main__":
    unittest.main()
