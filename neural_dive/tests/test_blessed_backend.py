"""Tests for BlessedBackend implementation.

This module tests the concrete implementation of RenderBackend using blessed.Terminal.
"""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, Mock, patch

from neural_dive.backends import BlessedBackend


class TestBlessedBackend(unittest.TestCase):
    """Test suite for BlessedBackend."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_term = MagicMock()
        self.mock_term.width = 80
        self.mock_term.height = 24
        self.backend = BlessedBackend(self.mock_term)

    def test_initialization(self):
        """Test backend initializes with Terminal."""
        self.assertEqual(self.backend.width, 80)
        self.assertEqual(self.backend.height, 24)

    def test_width_property(self):
        """Test width property delegates to Terminal."""
        self.mock_term.width = 120
        self.assertEqual(self.backend.width, 120)

    def test_height_property(self):
        """Test height property delegates to Terminal."""
        self.mock_term.height = 40
        self.assertEqual(self.backend.height, 40)

    def test_clear_screen(self):
        """Test clear_screen delegates to Terminal."""
        self.mock_term.clear = "CLEAR"

        with patch("builtins.print") as mock_print:
            self.backend.clear_screen()
            mock_print.assert_called_once_with("CLEAR", end="", flush=True)

    def test_move_cursor(self):
        """Test move_cursor delegates to Terminal."""
        self.mock_term.move_xy.return_value = "MOVE_10_5"

        with patch("builtins.print") as mock_print:
            self.backend.move_cursor(10, 5)
            self.mock_term.move_xy.assert_called_once_with(10, 5)
            mock_print.assert_called_once_with("MOVE_10_5", end="", flush=False)

    def test_draw_text_basic(self):
        """Test draw_text without color or bold."""
        self.mock_term.move_xy.return_value = "MOVE_5_10"

        with patch("builtins.print") as mock_print:
            self.backend.draw_text(5, 10, "Hello")
            self.mock_term.move_xy.assert_called_once_with(5, 10)
            # Should call print twice: once for move, once for text
            self.assertEqual(mock_print.call_count, 2)
            mock_print.assert_any_call("MOVE_5_10", end="")
            mock_print.assert_any_call("Hello", end="")

    def test_draw_text_with_color(self):
        """Test draw_text with color."""
        self.mock_term.move_xy.return_value = "MOVE_5_10"
        mock_color_func = Mock(return_value="COLORED[Hello]")
        self.mock_term.blue = mock_color_func

        with patch("builtins.print") as mock_print:
            self.backend.draw_text(5, 10, "Hello", color="blue")
            self.mock_term.move_xy.assert_called_once_with(5, 10)
            mock_color_func.assert_called_once_with("Hello")
            # Should call print twice
            self.assertEqual(mock_print.call_count, 2)
            mock_print.assert_any_call("MOVE_5_10", end="")
            mock_print.assert_any_call("COLORED[Hello]", end="")

    def test_draw_text_with_bold(self):
        """Test draw_text with bold."""
        self.mock_term.move_xy.return_value = "MOVE_5_10"
        mock_bold_func = Mock(return_value="BOLD[Hello]")
        self.mock_term.bold_red = mock_bold_func

        with patch("builtins.print") as mock_print:
            self.backend.draw_text(5, 10, "Hello", color="red", bold=True)
            mock_bold_func.assert_called_once_with("Hello")
            # Should call print twice
            self.assertEqual(mock_print.call_count, 2)
            mock_print.assert_any_call("MOVE_5_10", end="")
            mock_print.assert_any_call("BOLD[Hello]", end="")

    def test_draw_with_bg(self):
        """Test draw_with_bg with foreground and background colors."""
        self.mock_term.move_xy.return_value = "MOVE_3_7"
        mock_fg_func = Mock(return_value="FG[BG[Text]]")  # fg wraps bg result
        mock_bg_func = Mock(return_value="BG[Text]")
        self.mock_term.black = mock_fg_func
        self.mock_term.on_white = mock_bg_func

        with patch("builtins.print") as mock_print:
            self.backend.draw_with_bg(3, 7, "Text", "black", "white")
            # Implementation calls: fg(bg(text))
            mock_bg_func.assert_called_once_with("Text")
            mock_fg_func.assert_called_once_with("BG[Text]")
            # Should call print twice
            self.assertEqual(mock_print.call_count, 2)
            mock_print.assert_any_call("MOVE_3_7", end="")
            mock_print.assert_any_call("FG[BG[Text]]", end="")

    def test_flush(self):
        """Test flush delegates to sys.stdout.flush."""
        with patch("sys.stdout.flush") as mock_flush:
            self.backend.flush()
            mock_flush.assert_called_once()

    def test_get_color_func_basic(self):
        """Test get_color_func for basic color."""
        mock_func = Mock()
        self.mock_term.cyan = mock_func

        result = self.backend.get_color_func("cyan")
        self.assertEqual(result, mock_func)

    def test_get_color_func_bold(self):
        """Test get_color_func for bold color."""
        mock_func = Mock()
        self.mock_term.bold_magenta = mock_func

        result = self.backend.get_color_func("magenta", bold=True)
        self.assertEqual(result, mock_func)

    def test_get_color_func_fallback(self):
        """Test get_color_func falls back to normal if color not found."""
        mock_normal = Mock()
        self.mock_term.normal = mock_normal
        # Simulate missing color
        del self.mock_term.invalid_color

        result = self.backend.get_color_func("invalid_color")
        self.assertEqual(result, mock_normal)

    def test_getattr_delegation(self):
        """Test __getattr__ delegates to Terminal for backwards compatibility."""
        self.mock_term.custom_attribute = "CUSTOM_VALUE"

        result = self.backend.custom_attribute
        self.assertEqual(result, "CUSTOM_VALUE")

    def test_getattr_with_method(self):
        """Test __getattr__ delegates methods to Terminal."""
        mock_method = Mock(return_value="METHOD_RESULT")
        self.mock_term.custom_method = mock_method

        result = self.backend.custom_method(1, 2, key="value")
        mock_method.assert_called_once_with(1, 2, key="value")
        self.assertEqual(result, "METHOD_RESULT")


if __name__ == "__main__":
    unittest.main()
