"""Tests for TestBackend implementation.

This module tests the mock backend used for unit testing rendering logic.
"""

from __future__ import annotations

import unittest

from neural_dive.backends import DrawCall, TestBackend


class TestTestBackend(unittest.TestCase):
    """Test suite for TestBackend."""

    def setUp(self):
        """Set up test fixtures."""
        self.backend = TestBackend(width=80, height=24)

    def test_initialization(self):
        """Test backend initializes with specified dimensions."""
        self.assertEqual(self.backend.width, 80)
        self.assertEqual(self.backend.height, 24)
        self.assertEqual(len(self.backend.draw_calls), 0)

    def test_initialization_defaults(self):
        """Test backend uses default dimensions."""
        backend = TestBackend()
        self.assertEqual(backend.width, 80)
        self.assertEqual(backend.height, 24)

    def test_clear_screen(self):
        """Test clear_screen records draw call."""
        self.backend.clear_screen()

        self.assertEqual(len(self.backend.draw_calls), 1)
        call = self.backend.draw_calls[0]
        self.assertEqual(call.call_type, "clear")

    def test_move_cursor(self):
        """Test move_cursor records draw call."""
        self.backend.move_cursor(10, 5)

        self.assertEqual(len(self.backend.draw_calls), 1)
        call = self.backend.draw_calls[0]
        self.assertEqual(call.call_type, "move")
        self.assertEqual(call.x, 10)
        self.assertEqual(call.y, 5)

    def test_draw_text_basic(self):
        """Test draw_text records draw call without color or bold."""
        self.backend.draw_text(5, 10, "Hello")

        self.assertEqual(len(self.backend.draw_calls), 1)
        call = self.backend.draw_calls[0]
        self.assertEqual(call.call_type, "text")
        self.assertEqual(call.x, 5)
        self.assertEqual(call.y, 10)
        self.assertEqual(call.text, "Hello")
        self.assertIsNone(call.color)
        self.assertFalse(call.bold)

    def test_draw_text_with_color(self):
        """Test draw_text records color information."""
        self.backend.draw_text(5, 10, "Hello", color="blue")

        call = self.backend.draw_calls[0]
        self.assertEqual(call.color, "blue")
        self.assertFalse(call.bold)

    def test_draw_text_with_bold(self):
        """Test draw_text records bold information."""
        self.backend.draw_text(5, 10, "Hello", color="red", bold=True)

        call = self.backend.draw_calls[0]
        self.assertEqual(call.color, "red")
        self.assertTrue(call.bold)

    def test_draw_with_bg(self):
        """Test draw_with_bg records foreground and background colors."""
        self.backend.draw_with_bg(3, 7, "Text", "black", "white")

        self.assertEqual(len(self.backend.draw_calls), 1)
        call = self.backend.draw_calls[0]
        self.assertEqual(call.call_type, "text_bg")  # Actual call_type used
        self.assertEqual(call.x, 3)
        self.assertEqual(call.y, 7)
        self.assertEqual(call.text, "Text")
        self.assertEqual(call.fg, "black")
        self.assertEqual(call.bg, "white")

    def test_flush(self):
        """Test flush is a no-op for TestBackend."""
        # Should not raise an error
        self.backend.flush()
        # Should not record a draw call (no-op)
        self.assertEqual(len(self.backend.draw_calls), 0)

    def test_get_color_func(self):
        """Test get_color_func returns identity function."""
        color_func = self.backend.get_color_func("cyan")
        result = color_func("Test")
        self.assertEqual(result, "Test")

    def test_get_color_func_bold(self):
        """Test get_color_func with bold returns identity function."""
        color_func = self.backend.get_color_func("magenta", bold=True)
        result = color_func("Test")
        self.assertEqual(result, "Test")

    def test_get_draw_at_single_call(self):
        """Test get_draw_at returns most recent call at position."""
        self.backend.draw_text(5, 10, "Hello")

        call = self.backend.get_draw_at(5, 10)
        self.assertIsNotNone(call)
        self.assertEqual(call.text, "Hello")

    def test_get_draw_at_multiple_calls(self):
        """Test get_draw_at returns most recent call when multiple exist."""
        self.backend.draw_text(5, 10, "First")
        self.backend.draw_text(5, 10, "Second")
        self.backend.draw_text(5, 10, "Third")

        call = self.backend.get_draw_at(5, 10)
        self.assertIsNotNone(call)
        self.assertEqual(call.text, "Third")

    def test_get_draw_at_no_match(self):
        """Test get_draw_at returns None when no call at position."""
        self.backend.draw_text(5, 10, "Hello")

        call = self.backend.get_draw_at(20, 15)
        self.assertIsNone(call)

    def test_get_draw_at_with_move_cursor(self):
        """Test get_draw_at works with move_cursor calls."""
        self.backend.move_cursor(10, 5)
        self.backend.draw_text(10, 5, "Text")

        call = self.backend.get_draw_at(10, 5)
        self.assertIsNotNone(call)
        self.assertEqual(call.call_type, "text")

    def test_multiple_operations(self):
        """Test backend records multiple operations in order."""
        self.backend.clear_screen()
        self.backend.move_cursor(0, 0)
        self.backend.draw_text(5, 10, "Hello")
        self.backend.draw_with_bg(3, 7, "Bg", "white", "black")

        self.assertEqual(len(self.backend.draw_calls), 4)
        self.assertEqual(self.backend.draw_calls[0].call_type, "clear")
        self.assertEqual(self.backend.draw_calls[1].call_type, "move")
        self.assertEqual(self.backend.draw_calls[2].call_type, "text")
        self.assertEqual(self.backend.draw_calls[3].call_type, "text_bg")  # Actual call_type

    def test_draw_call_dataclass(self):
        """Test DrawCall dataclass has correct default values."""
        call = DrawCall(call_type="text")
        self.assertEqual(call.call_type, "text")
        self.assertEqual(call.x, 0)
        self.assertEqual(call.y, 0)
        self.assertEqual(call.text, "")
        self.assertIsNone(call.color)
        self.assertIsNone(call.fg)
        self.assertIsNone(call.bg)
        self.assertFalse(call.bold)


class TestDrawCall(unittest.TestCase):
    """Test suite for DrawCall dataclass."""

    def test_creation_minimal(self):
        """Test creating DrawCall with minimal parameters."""
        call = DrawCall(call_type="clear")
        self.assertEqual(call.call_type, "clear")

    def test_creation_full(self):
        """Test creating DrawCall with all parameters."""
        call = DrawCall(
            call_type="text",
            x=10,
            y=20,
            text="Hello",
            color="blue",
            fg="white",
            bg="black",
            bold=True,
        )
        self.assertEqual(call.call_type, "text")
        self.assertEqual(call.x, 10)
        self.assertEqual(call.y, 20)
        self.assertEqual(call.text, "Hello")
        self.assertEqual(call.color, "blue")
        self.assertEqual(call.fg, "white")
        self.assertEqual(call.bg, "black")
        self.assertTrue(call.bold)

    def test_equality(self):
        """Test DrawCall equality comparison."""
        call1 = DrawCall(call_type="text", x=5, y=10, text="Hello")
        call2 = DrawCall(call_type="text", x=5, y=10, text="Hello")
        self.assertEqual(call1, call2)

    def test_inequality(self):
        """Test DrawCall inequality comparison."""
        call1 = DrawCall(call_type="text", x=5, y=10, text="Hello")
        call2 = DrawCall(call_type="text", x=5, y=10, text="World")
        self.assertNotEqual(call1, call2)


if __name__ == "__main__":
    unittest.main()
