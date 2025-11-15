"""Unit tests for ConversationEngine class.

This test module covers all ConversationEngine functionality including:
- Conversation state management
- Starting and ending conversations
- Question answering
- Text input buffering
- State serialization/deserialization
"""

from __future__ import annotations

import unittest

from neural_dive.enums import NPCType
from neural_dive.managers.conversation_engine import ConversationEngine
from neural_dive.models import Answer, Conversation, Question


class TestConversationEngineInitialization(unittest.TestCase):
    """Test ConversationEngine initialization."""

    def test_default_initialization(self):
        """Test that ConversationEngine initializes with default state."""
        engine = ConversationEngine()

        self.assertIsNone(engine.active_conversation)
        self.assertIsNone(engine.active_terminal)
        self.assertFalse(engine.show_greeting)
        self.assertIsNone(engine.last_answer_response)
        self.assertEqual(engine.text_input_buffer, "")

    def test_is_active_false_initially(self):
        """Test that is_active() returns False when no conversation."""
        engine = ConversationEngine()

        self.assertFalse(engine.is_active())


class TestConversationEngineStartEnd(unittest.TestCase):
    """Test starting and ending conversations."""

    def setUp(self):
        """Set up test fixtures."""
        self.engine = ConversationEngine()
        self.conversation = Conversation(
            npc_name="TEST_NPC",
            greeting="Hello!",
            questions=[
                Question(
                    question_text="Test?",
                    answers=[Answer("Yes", True, "Correct!")],
                    topic="test",
                )
            ],
            npc_type=NPCType.SPECIALIST,
        )

    def test_start_conversation(self):
        """Test starting a conversation sets correct state."""
        self.engine.start_conversation(self.conversation)

        self.assertEqual(self.engine.active_conversation, self.conversation)
        self.assertTrue(self.engine.show_greeting)
        self.assertIsNone(self.engine.last_answer_response)
        self.assertEqual(self.engine.text_input_buffer, "")

    def test_start_conversation_makes_active(self):
        """Test that starting conversation makes is_active() return True."""
        self.engine.start_conversation(self.conversation)

        self.assertTrue(self.engine.is_active())

    def test_end_conversation(self):
        """Test ending conversation resets all state."""
        self.engine.start_conversation(self.conversation)
        self.engine.text_input_buffer = "test input"
        self.engine.last_answer_response = "test response"

        self.engine.end_conversation()

        self.assertIsNone(self.engine.active_conversation)
        self.assertFalse(self.engine.show_greeting)
        self.assertIsNone(self.engine.last_answer_response)
        self.assertEqual(self.engine.text_input_buffer, "")

    def test_end_conversation_makes_inactive(self):
        """Test that ending conversation makes is_active() return False."""
        self.engine.start_conversation(self.conversation)
        self.engine.end_conversation()

        self.assertFalse(self.engine.is_active())


class TestConversationEngineQuestionAnswering(unittest.TestCase):
    """Test question answering functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.engine = ConversationEngine()
        self.conversation = Conversation(
            npc_name="TEST_NPC",
            greeting="Hello!",
            questions=[
                Question(
                    question_text="Question 1?",
                    answers=[
                        Answer("Correct", True, "Right!"),
                        Answer("Wrong", False, "Nope!"),
                    ],
                    topic="test",
                ),
                Question(
                    question_text="Question 2?",
                    answers=[Answer("Yes", True, "Good!")],
                    topic="test",
                ),
            ],
            npc_type=NPCType.SPECIALIST,
        )

    def test_answer_question_without_active_conversation(self):
        """Test answering question with no active conversation."""
        is_correct, response = self.engine.answer_question(0)

        self.assertFalse(is_correct)
        self.assertEqual(response, "No active conversation")

    def test_answer_correct_question(self):
        """Test answering question correctly."""
        self.engine.start_conversation(self.conversation)

        is_correct, response = self.engine.answer_question(0)

        self.assertTrue(is_correct)
        self.assertEqual(response, "Right!")
        self.assertEqual(self.engine.last_answer_response, "Right!")
        self.assertFalse(self.engine.show_greeting)

    def test_answer_wrong_question(self):
        """Test answering question incorrectly."""
        self.engine.start_conversation(self.conversation)

        is_correct, response = self.engine.answer_question(1)

        self.assertFalse(is_correct)
        self.assertEqual(response, "Nope!")
        self.assertEqual(self.engine.last_answer_response, "Nope!")

    def test_answer_question_invalid_index(self):
        """Test answering with invalid answer index."""
        self.engine.start_conversation(self.conversation)

        is_correct, response = self.engine.answer_question(5)

        self.assertFalse(is_correct)
        self.assertEqual(response, "Invalid answer")

    def test_answer_question_negative_index(self):
        """Test answering with negative answer index."""
        self.engine.start_conversation(self.conversation)

        is_correct, response = self.engine.answer_question(-1)

        self.assertFalse(is_correct)
        self.assertEqual(response, "Invalid answer")

    def test_answer_advances_to_next_question(self):
        """Test that answering advances to next question."""
        self.engine.start_conversation(self.conversation)

        self.engine.answer_question(0)

        self.assertEqual(self.conversation.current_question_idx, 1)

    def test_answer_last_question_completes_conversation(self):
        """Test that answering last question marks conversation complete."""
        self.engine.start_conversation(self.conversation)

        # Answer first question
        self.engine.answer_question(0)
        self.assertFalse(self.conversation.completed)

        # Answer second (last) question
        self.engine.answer_question(0)
        self.assertTrue(self.conversation.completed)

    def test_answer_when_already_complete(self):
        """Test answering when conversation already complete."""
        self.engine.start_conversation(self.conversation)
        self.engine.answer_question(0)
        self.engine.answer_question(0)  # Complete conversation

        is_correct, response = self.engine.answer_question(0)

        self.assertFalse(is_correct)
        self.assertEqual(response, "No more questions")


class TestConversationEngineCurrentQuestion(unittest.TestCase):
    """Test getting current question."""

    def setUp(self):
        """Set up test fixtures."""
        self.engine = ConversationEngine()
        self.conversation = Conversation(
            npc_name="TEST_NPC",
            greeting="Hello!",
            questions=[
                Question(
                    question_text="Question 1?",
                    answers=[Answer("Yes", True, "Good!")],
                    topic="test",
                ),
                Question(
                    question_text="Question 2?",
                    answers=[Answer("Yes", True, "Great!")],
                    topic="test",
                ),
            ],
            npc_type=NPCType.SPECIALIST,
        )

    def test_get_current_question_no_conversation(self):
        """Test getting current question when no conversation active."""
        question = self.engine.get_current_question()

        self.assertIsNone(question)

    def test_get_current_question_first(self):
        """Test getting first question in conversation."""
        self.engine.start_conversation(self.conversation)

        question = self.engine.get_current_question()

        self.assertIsNotNone(question)
        self.assertEqual(question.question_text, "Question 1?")

    def test_get_current_question_after_answer(self):
        """Test getting current question after answering one."""
        self.engine.start_conversation(self.conversation)
        self.engine.answer_question(0)

        question = self.engine.get_current_question()

        self.assertIsNotNone(question)
        self.assertEqual(question.question_text, "Question 2?")

    def test_get_current_question_when_complete(self):
        """Test getting current question when conversation complete."""
        self.engine.start_conversation(self.conversation)
        self.engine.answer_question(0)
        self.engine.answer_question(0)

        question = self.engine.get_current_question()

        self.assertIsNone(question)


class TestConversationEngineSerialization(unittest.TestCase):
    """Test state serialization and deserialization."""

    def setUp(self):
        """Set up test fixtures."""
        self.engine = ConversationEngine()
        self.conversation = Conversation(
            npc_name="TEST_NPC",
            greeting="Hello!",
            questions=[
                Question(
                    question_text="Test?",
                    answers=[Answer("Yes", True, "Good!")],
                    topic="test",
                )
            ],
            npc_type=NPCType.SPECIALIST,
        )

    def test_to_dict_default_state(self):
        """Test serializing default state."""
        data = self.engine.to_dict()

        self.assertIsInstance(data, dict)
        self.assertIn("active_conversation_npc", data)
        self.assertIn("show_greeting", data)
        self.assertIn("last_answer_response", data)
        self.assertIn("text_input_buffer", data)
        self.assertIsNone(data["active_conversation_npc"])
        self.assertFalse(data["show_greeting"])
        self.assertIsNone(data["last_answer_response"])
        self.assertEqual(data["text_input_buffer"], "")

    def test_to_dict_with_active_conversation(self):
        """Test serializing with active conversation."""
        self.engine.start_conversation(self.conversation)

        data = self.engine.to_dict()

        self.assertEqual(data["active_conversation_npc"], "TEST_NPC")
        self.assertTrue(data["show_greeting"])

    def test_to_dict_with_text_input(self):
        """Test serializing with text input buffer."""
        self.engine.text_input_buffer = "user input"

        data = self.engine.to_dict()

        self.assertEqual(data["text_input_buffer"], "user input")

    def test_to_dict_with_last_response(self):
        """Test serializing with last answer response."""
        self.engine.start_conversation(self.conversation)
        self.engine.answer_question(0)

        data = self.engine.to_dict()

        self.assertEqual(data["last_answer_response"], "Good!")

    def test_from_dict_default_state(self):
        """Test deserializing default state."""
        data = {
            "active_conversation_npc": None,
            "show_greeting": False,
            "last_answer_response": None,
            "text_input_buffer": "",
        }

        npc_conversations: dict[str, Conversation] = {}

        engine = ConversationEngine.from_dict(data, npc_conversations)

        self.assertIsNone(engine.active_conversation)
        self.assertFalse(engine.show_greeting)
        self.assertIsNone(engine.last_answer_response)
        self.assertEqual(engine.text_input_buffer, "")

    def test_from_dict_with_active_conversation(self):
        """Test deserializing with active conversation."""
        data = {
            "active_conversation_npc": "TEST_NPC",
            "show_greeting": True,
            "last_answer_response": None,
            "text_input_buffer": "",
        }
        npc_conversations = {"TEST_NPC": self.conversation}

        engine = ConversationEngine.from_dict(data, npc_conversations)

        self.assertEqual(engine.active_conversation, self.conversation)
        self.assertTrue(engine.show_greeting)

    def test_from_dict_missing_npc_conversation(self):
        """Test deserializing when NPC not in conversations map."""
        data = {
            "active_conversation_npc": "MISSING_NPC",
            "show_greeting": True,
            "last_answer_response": None,
            "text_input_buffer": "",
        }

        npc_conversations: dict[str, Conversation] = {}

        engine = ConversationEngine.from_dict(data, npc_conversations)

        self.assertIsNone(engine.active_conversation)

    def test_round_trip_serialization(self):
        """Test that serialization and deserialization preserves state."""
        self.engine.start_conversation(self.conversation)
        self.engine.text_input_buffer = "test input"
        self.engine.answer_question(0)

        data = self.engine.to_dict()
        restored_engine = ConversationEngine.from_dict(data, {"TEST_NPC": self.conversation})

        self.assertEqual(restored_engine.active_conversation, self.conversation)
        self.assertEqual(restored_engine.show_greeting, self.engine.show_greeting)
        self.assertEqual(restored_engine.last_answer_response, self.engine.last_answer_response)
        self.assertEqual(restored_engine.text_input_buffer, self.engine.text_input_buffer)


if __name__ == "__main__":
    unittest.main()
