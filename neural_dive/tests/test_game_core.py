"""
Unit tests for core Game class functionality.

Tests for conversation, interaction, floor progression, and save/load.
"""

from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from neural_dive.enums import NPCType
from neural_dive.game import Game
from neural_dive.models import Answer, Conversation, Question
from neural_dive.question_types import QuestionType


class TestGameConversations(unittest.TestCase):
    """Test conversation and answer handling."""

    def setUp(self):
        """Set up test game with fixed seed."""
        self.game = Game(seed=42, random_npcs=False)

    def test_answer_question_correct_increases_coherence(self):
        """Test that correct answer increases coherence."""
        # Start a conversation with an NPC
        npc_name = list(self.game.npc_conversations.keys())[0]
        self.game.active_conversation = self.game.npc_conversations[npc_name]

        # Get initial coherence
        initial_coherence = self.game.coherence

        # Answer first question correctly (need to find correct answer index)
        question = self.game.active_conversation.get_current_question()
        if question and question.question_type == QuestionType.MULTIPLE_CHOICE:
            # Find correct answer
            correct_idx = next(i for i, ans in enumerate(question.answers) if ans.correct)

            correct, response = self.game.answer_question(correct_idx)

            self.assertTrue(correct)
            self.assertGreater(self.game.coherence, initial_coherence)

    def test_answer_question_wrong_decreases_coherence(self):
        """Test that wrong answer decreases coherence."""
        # Start a conversation
        npc_name = list(self.game.npc_conversations.keys())[0]
        self.game.active_conversation = self.game.npc_conversations[npc_name]

        initial_coherence = self.game.coherence

        # Answer incorrectly
        question = self.game.active_conversation.get_current_question()
        if question and question.question_type == QuestionType.MULTIPLE_CHOICE:
            # Find wrong answer
            wrong_idx = next(i for i, ans in enumerate(question.answers) if not ans.correct)

            correct, response = self.game.answer_question(wrong_idx)

            self.assertFalse(correct)
            self.assertLess(self.game.coherence, initial_coherence)

    def test_answer_text_question_correct(self):
        """Test answering short answer question correctly."""
        # Create a test conversation with text question
        text_question = Question(
            question_text="What is 2+2?",
            topic="test",
            question_type=QuestionType.SHORT_ANSWER,
            correct_answer="4|four",
            correct_response="Correct!",
            incorrect_response="Wrong!",
        )

        conv = Conversation(
            npc_name="TEST_NPC",
            greeting="Hello",
            questions=[text_question],
            npc_type=NPCType.SPECIALIST,
        )

        self.game.active_conversation = conv
        initial_coherence = self.game.coherence

        correct, response = self.game.answer_text_question("4")

        self.assertTrue(correct)
        self.assertIn("Correct", response)
        self.assertGreater(self.game.coherence, initial_coherence)

    def test_answer_text_question_wrong(self):
        """Test answering short answer question incorrectly."""
        text_question = Question(
            question_text="What is 2+2?",
            topic="test",
            question_type=QuestionType.SHORT_ANSWER,
            correct_answer="4|four",
            correct_response="Correct!",
            incorrect_response="Wrong!",
        )

        conv = Conversation(
            npc_name="TEST_NPC",
            greeting="Hello",
            questions=[text_question],
            npc_type=NPCType.SPECIALIST,
        )

        self.game.active_conversation = conv
        initial_coherence = self.game.coherence

        correct, response = self.game.answer_text_question("5")

        self.assertFalse(correct)
        self.assertIn("Wrong", response)
        self.assertLess(self.game.coherence, initial_coherence)

    def test_conversation_completes_after_all_questions(self):
        """Test that conversation completes after answering all questions."""
        # Create conversation with one question
        question = Question(
            question_text="Test?",
            answers=[Answer("A", True, "Yes!")],
            topic="test",
        )

        conv = Conversation(
            npc_name="TEST_NPC",
            greeting="Hi",
            questions=[question],
            npc_type=NPCType.SPECIALIST,
        )

        self.game.active_conversation = conv

        # Answer the question
        correct, response = self.game.answer_question(0)

        self.assertTrue(conv.completed)
        self.assertIsNone(self.game.active_conversation)

    def test_exit_conversation(self):
        """Test exiting a conversation."""
        # Start conversation
        npc_name = list(self.game.npc_conversations.keys())[0]
        self.game.active_conversation = self.game.npc_conversations[npc_name]

        # Exit
        result = self.game.exit_conversation()

        self.assertTrue(result)
        self.assertIsNone(self.game.active_conversation)


class TestGameInteractions(unittest.TestCase):
    """Test player interactions with NPCs and entities."""

    def setUp(self):
        """Set up test game."""
        self.game = Game(seed=42, random_npcs=False)

    def test_interact_with_no_nearby_entity(self):
        """Test interaction when no entity is nearby."""
        # Move player to empty area (assuming start is empty)
        result = self.game.interact()

        # Should return False if nothing nearby
        if not result:
            self.assertIn("nearby", self.game.message.lower())

    def test_interact_starts_conversation(self):
        """Test that interacting with NPC starts conversation."""
        # Find an NPC and move player adjacent
        if self.game.npcs:
            npc = self.game.npcs[0]
            # Place player next to NPC
            self.game.player.x = npc.x + 1
            self.game.player.y = npc.y

            result = self.game.interact()

            # Should start conversation or show message
            self.assertTrue(result or self.game.message != "")


class TestFloorProgression(unittest.TestCase):
    """Test floor progression and completion."""

    def setUp(self):
        """Set up test game."""
        self.game = Game(seed=42, random_npcs=False, max_floors=3)

    def test_is_floor_complete_initially_false(self):
        """Test that floor is not complete at start."""
        complete = self.game.is_floor_complete()

        # Floor 1 requires certain NPCs to be completed
        self.assertFalse(complete)

    def test_use_stairs_without_completion_fails(self):
        """Test that can't use stairs without completing floor."""
        # Place player on stairs
        if self.game.stairs:
            stairs = self.game.stairs[0]
            self.game.player.x = stairs.x
            self.game.player.y = stairs.y

            initial_floor = self.game.current_floor

            self.game.use_stairs()

            # Should fail if floor not complete
            if not self.game.is_floor_complete():
                self.assertEqual(self.game.current_floor, initial_floor)


class TestSaveLoad(unittest.TestCase):
    """Test game save and load functionality."""

    def test_save_game_creates_file(self):
        """Test that save_game creates a save file."""
        game = Game(seed=42, random_npcs=False)

        with tempfile.TemporaryDirectory() as tmpdir:
            save_path = Path(tmpdir) / "test_save.json"

            success, actual_path = game.save_game(str(save_path))

            self.assertTrue(success)
            self.assertEqual(actual_path, save_path)
            self.assertTrue(save_path.exists())

    def test_save_game_contains_correct_data(self):
        """Test that saved game contains all necessary data."""
        game = Game(seed=42, random_npcs=False)
        game.coherence = 75
        game.current_floor = 2

        with tempfile.TemporaryDirectory() as tmpdir:
            save_path = Path(tmpdir) / "test_save.json"
            success, actual_path = game.save_game(str(save_path))
            self.assertTrue(success)

            with open(save_path) as f:
                save_data = json.load(f)

            # Coherence is stored in player_manager
            self.assertEqual(save_data["player_manager"]["coherence"], 75)
            self.assertEqual(save_data["current_floor"], 2)
            self.assertEqual(save_data["seed"], 42)
            self.assertIn("player_x", save_data)
            self.assertIn("player_y", save_data)

    def test_load_game_restores_state(self):
        """Test that load_game restores game state correctly."""
        # Create and save a game
        game1 = Game(seed=42, random_npcs=False)
        game1.coherence = 60
        game1.current_floor = 1

        with tempfile.TemporaryDirectory() as tmpdir:
            save_path = Path(tmpdir) / "test_save.json"
            success, actual_path = game1.save_game(str(save_path))
            self.assertTrue(success)

            # Load the game
            game2 = Game.load_game(str(save_path))

            self.assertIsNotNone(game2)
            assert game2 is not None  # Type narrowing for mypy
            self.assertEqual(game2.coherence, 60)
            self.assertEqual(game2.current_floor, 1)
            self.assertEqual(game2.seed, 42)

    def test_load_nonexistent_file_returns_none(self):
        """Test that loading nonexistent file returns None."""
        result = Game.load_game("/nonexistent/path/save.json")

        self.assertIsNone(result)

    def test_round_trip_save_load(self):
        """Test complete save/load round trip preserves game state."""
        game1 = Game(seed=99, random_npcs=False)
        game1.coherence = 85
        game1.questions_answered = 5
        game1.questions_correct = 4

        with tempfile.TemporaryDirectory() as tmpdir:
            save_path = Path(tmpdir) / "round_trip.json"

            # Save
            success, actual_path = game1.save_game(str(save_path))
            self.assertTrue(success)
            self.assertEqual(actual_path, save_path)

            # Load
            game2 = Game.load_game(str(save_path))
            self.assertIsNotNone(game2)
            assert game2 is not None  # Type narrowing for mypy

            # Verify state
            self.assertEqual(game2.coherence, 85)
            self.assertEqual(game2.questions_answered, 5)
            self.assertEqual(game2.questions_correct, 4)
            self.assertEqual(game2.seed, 99)


class TestGameStatistics(unittest.TestCase):
    """Test game statistics and scoring."""

    def test_get_final_stats_returns_dict(self):
        """Test that get_final_stats returns dictionary."""
        game = Game(seed=42)
        stats = game.get_final_stats()

        self.assertIsInstance(stats, dict)
        self.assertIn("score", stats)
        self.assertIn("time_played", stats)
        self.assertIn("questions_answered", stats)
        self.assertIn("accuracy", stats)

    def test_final_stats_calculates_accuracy(self):
        """Test that accuracy is calculated correctly."""
        game = Game(seed=42)
        game.questions_answered = 10
        game.questions_correct = 7

        stats = game.get_final_stats()

        self.assertEqual(stats["accuracy"], 70.0)

    def test_final_stats_handles_no_questions(self):
        """Test stats when no questions have been answered."""
        game = Game(seed=42)
        game.questions_answered = 0
        game.questions_correct = 0

        stats = game.get_final_stats()

        self.assertEqual(stats["accuracy"], 0.0)
        self.assertEqual(stats["questions_answered"], 0)


if __name__ == "__main__":
    unittest.main()
