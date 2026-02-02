"""Unit tests for data_loader module.

This test module covers data loading functionality including:
- Content set directory resolution
- Content set parameter handling
- Default content set behavior
"""

from __future__ import annotations

from pathlib import Path
import unittest
from unittest.mock import patch

from neural_dive.data_loader import (
    get_content_dir,
    get_data_dir,
    get_default_content_set,
    load_all_game_data,
    load_npcs,
)
from neural_dive.models import Answer, Question


class TestContentSetPaths(unittest.TestCase):
    """Test content set path resolution."""

    def test_get_data_dir_returns_path(self):
        """Test get_data_dir returns a Path object."""
        data_dir = get_data_dir()
        self.assertIsInstance(data_dir, Path)
        self.assertTrue(str(data_dir).endswith("data"))

    def test_get_content_dir_default(self):
        """Test get_content_dir with default content set."""
        content_dir = get_content_dir()
        self.assertIsInstance(content_dir, Path)
        self.assertTrue(str(content_dir).endswith("content/algorithms"))

    def test_get_content_dir_custom(self):
        """Test get_content_dir with custom content set."""
        content_dir = get_content_dir("custom_set")
        self.assertIsInstance(content_dir, Path)
        self.assertTrue(str(content_dir).endswith("content/custom_set"))

    def test_get_content_dir_respects_parameter(self):
        """Test that get_content_dir actually uses the content_set parameter."""
        algorithms_dir = get_content_dir("algorithms")
        other_dir = get_content_dir("other")
        self.assertNotEqual(algorithms_dir, other_dir)
        self.assertIn("algorithms", str(algorithms_dir))
        self.assertIn("other", str(other_dir))


class TestDefaultContentSet(unittest.TestCase):
    """Test default content set behavior."""

    def test_get_default_content_set(self):
        """Test get_default_content_set returns a string."""
        default = get_default_content_set()
        self.assertIsInstance(default, str)
        self.assertEqual(default, "algorithms")


class TestLoadGameData(unittest.TestCase):
    """Test load_all_game_data function."""

    @patch("neural_dive.data_loader.load_questions")
    @patch("neural_dive.data_loader.load_npcs")
    @patch("neural_dive.data_loader.load_levels")
    @patch("neural_dive.data_loader.load_snippets")
    def test_load_all_game_data_default_content_set(
        self, mock_snippets, mock_levels, mock_npcs, mock_questions
    ):
        """Test load_all_game_data uses default content set when None."""
        # Setup mocks
        mock_questions.return_value = {}
        mock_npcs.return_value = {}
        mock_levels.return_value = {}
        mock_snippets.return_value = {}

        # Call without content_set
        load_all_game_data()

        # Verify default content set was used
        mock_questions.assert_called_once_with("algorithms")
        mock_npcs.assert_called_once_with({}, "algorithms")
        mock_levels.assert_called_once_with("algorithms")

    @patch("neural_dive.data_loader.load_questions")
    @patch("neural_dive.data_loader.load_npcs")
    @patch("neural_dive.data_loader.load_levels")
    @patch("neural_dive.data_loader.load_snippets")
    def test_load_all_game_data_respects_content_set_parameter(
        self, mock_snippets, mock_levels, mock_npcs, mock_questions
    ):
        """Test load_all_game_data respects the content_set parameter."""
        # Setup mocks
        mock_questions.return_value = {}
        mock_npcs.return_value = {}
        mock_levels.return_value = {}
        mock_snippets.return_value = {}

        # Call with custom content_set
        load_all_game_data("custom_set")

        # Verify custom content set was used (NOT hardcoded algorithms)
        mock_questions.assert_called_once_with("custom_set")
        mock_npcs.assert_called_once_with({}, "custom_set")
        mock_levels.assert_called_once_with("custom_set")

    @patch("neural_dive.data_loader.load_questions")
    @patch("neural_dive.data_loader.load_npcs")
    @patch("neural_dive.data_loader.load_levels")
    @patch("neural_dive.data_loader.load_snippets")
    def test_load_all_game_data_returns_tuple(
        self, mock_snippets, mock_levels, mock_npcs, mock_questions
    ):
        """Test load_all_game_data returns a tuple of four elements."""
        # Setup mocks
        mock_questions.return_value = {"q1": "question1"}
        mock_npcs.return_value = {"npc1": "npc_data1"}
        mock_levels.return_value = {"floor1": "level1"}
        mock_snippets.return_value = {"snippet1": "snippet_data1"}

        # Call and verify result
        result = load_all_game_data()

        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 4)
        questions, npcs, levels, snippets = result
        self.assertEqual(questions, {"q1": "question1"})
        self.assertEqual(npcs, {"npc1": "npc_data1"})
        self.assertEqual(levels, {"floor1": "level1"})
        self.assertEqual(snippets, {"snippet1": "snippet_data1"})

    @patch("neural_dive.data_loader.importlib.import_module")
    @patch("neural_dive.data_loader.load_questions")
    @patch("neural_dive.data_loader.load_npcs")
    @patch("neural_dive.data_loader.load_levels")
    @patch("neural_dive.data_loader.load_snippets")
    def test_load_all_game_data_handles_missing_validation(
        self, mock_snippets, mock_levels, mock_npcs, mock_questions, mock_import
    ):
        """Test load_all_game_data handles content sets without validation gracefully."""
        # Setup mocks
        mock_questions.return_value = {}
        mock_npcs.return_value = {}
        mock_levels.return_value = {}
        mock_snippets.return_value = {}
        # Simulate missing validation module
        mock_import.side_effect = ImportError("Module not found")

        # Should not raise exception
        try:
            result = load_all_game_data("custom_set")
            self.assertIsInstance(result, tuple)
        except ImportError:
            self.fail("load_all_game_data should handle missing validation gracefully")


class TestNPCValidation(unittest.TestCase):
    """Test NPC question reference validation."""

    def _create_test_question(self, question_id: str) -> Question:
        """Helper to create a test question."""
        return Question(
            question_text=f"Test question {question_id}?",
            topic="test",
            answers=[
                Answer(text="Answer 1", correct=True, response="Correct!"),
                Answer(text="Answer 2", correct=False, response="Wrong!"),
            ],
        )

    @patch("builtins.open", new_callable=unittest.mock.mock_open)
    @patch("neural_dive.data_loader.json.load")
    def test_load_npcs_with_valid_questions(self, mock_json_load, mock_open):
        """Test loading NPCs with all valid question references."""
        # Setup test data
        questions = {
            "q1": self._create_test_question("q1"),
            "q2": self._create_test_question("q2"),
        }

        npc_data = {
            "TEST_NPC": {
                "char": "T",
                "color": "cyan",
                "floor": 1,
                "npc_type": "specialist",
                "greeting": "Hello!",
                "questions": ["q1", "q2"],
            }
        }

        mock_json_load.return_value = npc_data

        # Load NPCs
        npcs = load_npcs(questions, "test")

        # Verify NPC was loaded with both questions
        self.assertIn("TEST_NPC", npcs)
        self.assertEqual(len(npcs["TEST_NPC"]["conversation"].questions), 2)

    @patch("builtins.open", new_callable=unittest.mock.mock_open)
    @patch("neural_dive.data_loader.json.load")
    @patch("neural_dive.data_loader.logger")
    def test_load_npcs_with_missing_questions(self, mock_logger, mock_json_load, mock_open):
        """Test loading NPCs with some missing question references logs warnings."""
        # Setup test data
        questions = {
            "q1": self._create_test_question("q1"),
        }

        npc_data = {
            "TEST_NPC": {
                "char": "T",
                "color": "cyan",
                "floor": 1,
                "npc_type": "specialist",
                "greeting": "Hello!",
                "questions": ["q1", "q2", "q3"],  # q2 and q3 don't exist
            }
        }

        mock_json_load.return_value = npc_data

        # Load NPCs
        npcs = load_npcs(questions, "test")

        # Verify NPC was loaded with only valid question
        self.assertIn("TEST_NPC", npcs)
        self.assertEqual(len(npcs["TEST_NPC"]["conversation"].questions), 1)

        # Verify warning was logged
        mock_logger.warning.assert_called()
        warning_call = mock_logger.warning.call_args_list[0]
        self.assertIn("TEST_NPC", str(warning_call))
        self.assertIn("non-existent questions", str(warning_call))

    @patch("builtins.open", new_callable=unittest.mock.mock_open)
    @patch("neural_dive.data_loader.json.load")
    @patch("neural_dive.data_loader.logger")
    def test_load_npcs_with_all_missing_questions(self, mock_logger, mock_json_load, mock_open):
        """Test loading NPCs with all missing questions logs warnings."""
        # Setup test data - no questions available
        questions: dict[str, Question] = {}

        npc_data = {
            "TEST_NPC": {
                "char": "T",
                "color": "cyan",
                "floor": 1,
                "npc_type": "specialist",
                "greeting": "Hello!",
                "questions": ["q1", "q2"],  # Both don't exist
            }
        }

        mock_json_load.return_value = npc_data

        # Load NPCs
        npcs = load_npcs(questions, "test")

        # Verify NPC was loaded with no questions
        self.assertIn("TEST_NPC", npcs)
        self.assertEqual(len(npcs["TEST_NPC"]["conversation"].questions), 0)

        # Verify warnings were logged (one for missing questions, one for no valid questions)
        self.assertEqual(mock_logger.warning.call_count, 2)

    @patch("builtins.open", new_callable=unittest.mock.mock_open)
    @patch("neural_dive.data_loader.json.load")
    def test_load_npcs_with_no_questions_list(self, mock_json_load, mock_open):
        """Test loading NPCs without questions list doesn't crash."""
        # Setup test data
        questions = {
            "q1": self._create_test_question("q1"),
        }

        npc_data = {
            "TEST_NPC": {
                "char": "T",
                "color": "cyan",
                "floor": 1,
                "npc_type": "helper",
                "greeting": "Hello!",
                # No questions field
            }
        }

        mock_json_load.return_value = npc_data

        # Load NPCs - should not crash
        npcs = load_npcs(questions, "test")

        # Verify NPC was loaded with no questions
        self.assertIn("TEST_NPC", npcs)
        self.assertEqual(len(npcs["TEST_NPC"]["conversation"].questions), 0)


if __name__ == "__main__":
    unittest.main()
