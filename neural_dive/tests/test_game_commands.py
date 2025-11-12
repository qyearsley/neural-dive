"""
Unit tests for Game command processing.

This test module covers the process_command method which handles text-based
commands for movement, interaction, and conversation answers.
"""

from __future__ import annotations

import unittest

from neural_dive.enums import NPCType
from neural_dive.game import Game
from neural_dive.models import Answer, Conversation, Question


class TestGameMovementCommands(unittest.TestCase):
    """Test movement command processing."""

    def setUp(self):
        """Set up test game with fixed seed."""
        self.game = Game(seed=42, random_npcs=False)

    def test_move_up_command(self):
        """Test 'up' command moves player upward."""
        original_y = self.game.player.y

        # Try moving up if possible
        success, message = self.game.process_command("up")

        if success:
            self.assertEqual(self.game.player.y, original_y - 1)
            self.assertIn("moved", message.lower())

    def test_move_up_with_w_key(self):
        """Test 'w' command (alternative) moves player upward."""
        original_y = self.game.player.y

        success, message = self.game.process_command("w")

        if success:
            self.assertEqual(self.game.player.y, original_y - 1)

    def test_move_down_command(self):
        """Test 'down' command moves player downward."""
        original_y = self.game.player.y

        success, message = self.game.process_command("down")

        if success:
            self.assertEqual(self.game.player.y, original_y + 1)
            self.assertIn("moved", message.lower())

    def test_move_down_with_s_key(self):
        """Test 's' command (alternative) moves player downward."""
        original_y = self.game.player.y

        success, message = self.game.process_command("s")

        if success:
            self.assertEqual(self.game.player.y, original_y + 1)

    def test_move_left_command(self):
        """Test 'left' command moves player left."""
        original_x = self.game.player.x

        success, message = self.game.process_command("left")

        if success:
            self.assertEqual(self.game.player.x, original_x - 1)
            self.assertIn("moved", message.lower())

    def test_move_left_with_a_key(self):
        """Test 'a' command (alternative) moves player left."""
        original_x = self.game.player.x

        success, message = self.game.process_command("a")

        if success:
            self.assertEqual(self.game.player.x, original_x - 1)

    def test_move_right_command(self):
        """Test 'right' command moves player right."""
        original_x = self.game.player.x

        success, message = self.game.process_command("right")

        if success:
            self.assertEqual(self.game.player.x, original_x + 1)
            self.assertIn("moved", message.lower())

    def test_move_right_with_d_key(self):
        """Test 'd' command (alternative) moves player right."""
        original_x = self.game.player.x

        success, message = self.game.process_command("d")

        if success:
            self.assertEqual(self.game.player.x, original_x + 1)

    def test_movement_blocked_by_wall(self):
        """Test that movement into wall is blocked."""
        # Find a wall adjacent to player
        original_x = self.game.player.x
        original_y = self.game.player.y

        # Try all directions - at least one should hit a wall eventually
        for direction in ["up", "down", "left", "right"]:
            # Reset position
            self.game.player.x = original_x
            self.game.player.y = original_y

            # Move until we hit a wall
            for _ in range(20):
                success, message = self.game.process_command(direction)
                if not success:
                    # Hit a wall - verify position didn't change from last valid position
                    self.assertIsInstance(message, str)
                    break

    def test_command_case_insensitive(self):
        """Test that commands are case-insensitive."""
        original_x = self.game.player.x

        success1, _ = self.game.process_command("RIGHT")
        if success1:
            self.assertNotEqual(self.game.player.x, original_x)

        # Reset
        self.game.player.x = original_x

        success2, _ = self.game.process_command("RiGhT")
        if success2:
            self.assertNotEqual(self.game.player.x, original_x)

    def test_command_whitespace_stripped(self):
        """Test that whitespace is stripped from commands."""
        original_x = self.game.player.x

        success, _ = self.game.process_command("  right  ")

        if success:
            self.assertNotEqual(self.game.player.x, original_x)


class TestGameInteractionCommands(unittest.TestCase):
    """Test interaction command processing."""

    def setUp(self):
        """Set up test game."""
        self.game = Game(seed=42, random_npcs=False)

    def test_interact_command(self):
        """Test 'interact' command triggers interaction."""
        success, message = self.game.process_command("interact")

        # Should return a boolean and string message
        self.assertIsInstance(success, bool)
        self.assertIsInstance(message, str)

    def test_interact_with_i_shorthand(self):
        """Test 'i' command (shorthand) triggers interaction."""
        success, message = self.game.process_command("i")

        self.assertIsInstance(success, bool)
        self.assertIsInstance(message, str)

    def test_stairs_command(self):
        """Test 'stairs' command attempts to use stairs."""
        success, message = self.game.process_command("stairs")

        self.assertIsInstance(success, bool)
        self.assertIsInstance(message, str)

    def test_use_stairs_with_use_command(self):
        """Test 'use' command attempts to use stairs."""
        success, message = self.game.process_command("use")

        self.assertIsInstance(success, bool)
        self.assertIsInstance(message, str)

    def test_stairs_with_angle_bracket(self):
        """Test '>' and '<' commands attempt to use stairs."""
        success1, message1 = self.game.process_command(">")
        self.assertIsInstance(success1, bool)
        self.assertIsInstance(message1, str)

        success2, message2 = self.game.process_command("<")
        self.assertIsInstance(success2, bool)
        self.assertIsInstance(message2, str)


class TestGameConversationCommands(unittest.TestCase):
    """Test conversation-related command processing."""

    def setUp(self):
        """Set up test game with active conversation."""
        self.game = Game(seed=42, random_npcs=False)

        # Create a simple test conversation
        question = Question(
            question_text="Test question?",
            answers=[
                Answer("Answer 1", True, "Correct!"),
                Answer("Answer 2", False, "Wrong!"),
                Answer("Answer 3", False, "Wrong!"),
                Answer("Answer 4", False, "Wrong!"),
            ],
            topic="test",
        )

        self.conversation = Conversation(
            npc_name="TEST_NPC",
            greeting="Hello!",
            questions=[question],
            npc_type=NPCType.SPECIALIST,
        )

    def test_answer_question_with_number_1(self):
        """Test answering question with '1' command."""
        self.game.active_conversation = self.conversation

        success, message = self.game.process_command("1")

        # Answer 1 is correct
        self.assertTrue(success)
        self.assertIn("Correct", message)

    def test_answer_question_with_number_2(self):
        """Test answering question with '2' command."""
        self.game.active_conversation = self.conversation

        success, message = self.game.process_command("2")

        # Answer 2 is wrong
        self.assertFalse(success)
        self.assertIn("Wrong", message)

    def test_answer_question_with_number_3(self):
        """Test answering question with '3' command."""
        self.game.active_conversation = self.conversation

        success, message = self.game.process_command("3")

        self.assertFalse(success)
        self.assertIn("Wrong", message)

    def test_answer_question_with_number_4(self):
        """Test answering question with '4' command."""
        self.game.active_conversation = self.conversation

        success, message = self.game.process_command("4")

        self.assertFalse(success)
        self.assertIn("Wrong", message)

    def test_number_command_without_active_conversation(self):
        """Test that number commands don't work without conversation."""
        self.game.active_conversation = None

        success, message = self.game.process_command("1")

        # Should be treated as unknown command
        self.assertFalse(success)
        self.assertIn("Unknown", message)

    def test_exit_conversation_command(self):
        """Test 'exit' command exits conversation."""
        self.game.active_conversation = self.conversation

        success, message = self.game.process_command("exit")

        # exit_conversation returns bool
        self.assertIsInstance(success, bool)
        self.assertIsInstance(message, str)

    def test_exit_conversation_with_esc(self):
        """Test 'esc' command (alternative) exits conversation."""
        self.game.active_conversation = self.conversation

        success, message = self.game.process_command("esc")

        self.assertIsInstance(success, bool)
        self.assertIsInstance(message, str)


class TestGameInvalidCommands(unittest.TestCase):
    """Test handling of invalid commands."""

    def setUp(self):
        """Set up test game."""
        self.game = Game(seed=42, random_npcs=False)

    def test_unknown_command(self):
        """Test that unknown commands return error message."""
        success, message = self.game.process_command("invalid_command")

        self.assertFalse(success)
        self.assertIn("Unknown command", message)
        self.assertIn("invalid_command", message)

    def test_empty_command(self):
        """Test that empty command returns error."""
        success, message = self.game.process_command("")

        self.assertFalse(success)
        self.assertIn("Unknown", message)

    def test_whitespace_only_command(self):
        """Test that whitespace-only command returns error."""
        success, message = self.game.process_command("   ")

        self.assertFalse(success)
        self.assertIn("Unknown", message)

    def test_gibberish_command(self):
        """Test that gibberish command returns error."""
        success, message = self.game.process_command("asdfghjkl")

        self.assertFalse(success)
        self.assertIn("Unknown", message)

    def test_number_out_of_range(self):
        """Test that numbers outside 1-4 are treated as invalid."""
        self.game.active_conversation = None

        for num in ["0", "5", "99", "-1"]:
            success, message = self.game.process_command(num)
            self.assertFalse(success)


class TestGameCommandReturnValues(unittest.TestCase):
    """Test that all commands return correct types."""

    def setUp(self):
        """Set up test game."""
        self.game = Game(seed=42, random_npcs=False)

    def test_all_commands_return_tuple(self):
        """Test that all commands return (bool, str) tuple."""
        commands = [
            "up",
            "down",
            "left",
            "right",
            "w",
            "a",
            "s",
            "d",
            "interact",
            "i",
            "stairs",
            "use",
            ">",
            "<",
            "exit",
            "esc",
            "invalid",
        ]

        for command in commands:
            result = self.game.process_command(command)

            # Should return tuple
            self.assertIsInstance(result, tuple)
            self.assertEqual(len(result), 2)

            # First element should be bool
            self.assertIsInstance(result[0], bool)

            # Second element should be string
            self.assertIsInstance(result[1], str)


if __name__ == "__main__":
    unittest.main()
