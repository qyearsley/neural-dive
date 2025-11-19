"""
Conversation state management for Neural Dive.

This module provides the ConversationEngine class which handles all conversation-related
state including active conversations, greetings, responses, and text input.
"""

from __future__ import annotations

from neural_dive.models import Conversation


class ConversationEngine:
    """Manages conversation state and flow.

    The ConversationEngine encapsulates all conversation-related state and provides
    a clean interface for conversation management. This makes it easier to:
    - Test conversation logic in isolation
    - Add dialogue trees and branching conversations
    - Track conversation history
    - Implement conversation-related UI state

    Attributes:
        active_conversation: Current active conversation, if any
        active_terminal: Currently viewing info terminal, if any
        active_inventory: Whether inventory UI is currently displayed
        show_greeting: Whether to display conversation greeting
        last_answer_response: Last response text from answering a question
        text_input_buffer: Buffer for text-based question answers
    """

    def __init__(self):
        """Initialize ConversationEngine with default state."""
        self.active_conversation: Conversation | None = None
        self.active_terminal = None  # InfoTerminal type, avoiding circular import
        self.active_inventory: bool = False
        self.active_snippet: dict | None = None  # Currently viewing snippet
        self.show_greeting: bool = False
        self.last_answer_response: str | None = None
        self.text_input_buffer: str = ""
        self.eliminated_answers: set[int] = set()  # Track eliminated answer indices

    def start_conversation(self, conversation: Conversation) -> None:
        """Start a new conversation.

        Args:
            conversation: The conversation to start
        """
        self.active_conversation = conversation
        self.show_greeting = True
        self.last_answer_response = None
        self.text_input_buffer = ""
        self.eliminated_answers = set()  # Clear eliminated answers

    def end_conversation(self) -> None:
        """End the current conversation and reset state."""
        self.active_conversation = None
        self.show_greeting = False
        self.last_answer_response = None
        self.text_input_buffer = ""
        self.eliminated_answers = set()  # Clear eliminated answers

    def answer_question(self, answer_idx: int) -> tuple[bool, str]:
        """
        Process answer to current question.

        Args:
            answer_idx: Index of the selected answer

        Returns:
            Tuple of (is_correct, response_text)
        """
        if not self.active_conversation:
            return False, "No active conversation"

        conv = self.active_conversation

        # Check if conversation is complete
        if conv.current_question_idx >= len(conv.questions):
            return False, "No more questions"

        question = conv.questions[conv.current_question_idx]

        # Validate answer index
        if answer_idx < 0 or answer_idx >= len(question.answers):
            return False, "Invalid answer"

        # Get the answer
        answer = question.answers[answer_idx]

        # Advance to next question
        conv.current_question_idx += 1
        self.eliminated_answers = set()  # Clear eliminated answers for next question

        # Check if conversation is now complete
        if conv.current_question_idx >= len(conv.questions):
            conv.completed = True

        # Store response for display
        self.last_answer_response = answer.response
        self.show_greeting = False

        return answer.correct, answer.response

    def is_active(self) -> bool:
        """Check if a conversation is currently active.

        Returns:
            True if conversation is active
        """
        return self.active_conversation is not None

    def use_hint_token(self, num_to_eliminate: int = 1) -> tuple[bool, str]:
        """Use a hint token to eliminate wrong answers in the current question.

        Args:
            num_to_eliminate: Number of wrong answers to eliminate (default 1)

        Returns:
            Tuple of (success, message)
        """
        if not self.active_conversation:
            return False, "No active conversation"

        conv = self.active_conversation
        if conv.current_question_idx >= len(conv.questions):
            return False, "No more questions"

        question = conv.questions[conv.current_question_idx]

        # Only works for multiple choice questions
        from neural_dive.question_types import QuestionType

        if question.question_type != QuestionType.MULTIPLE_CHOICE:
            return False, "Hints only work for multiple choice questions"

        # Find wrong answers that haven't been eliminated yet
        wrong_answers = [
            i
            for i, answer in enumerate(question.answers)
            if not answer.correct and i not in self.eliminated_answers
        ]

        if not wrong_answers:
            return False, "No wrong answers left to eliminate"

        # Eliminate up to num_to_eliminate wrong answers
        import random

        to_eliminate = min(num_to_eliminate, len(wrong_answers))
        eliminated = random.sample(wrong_answers, to_eliminate)
        self.eliminated_answers.update(eliminated)

        return True, f"Eliminated {to_eliminate} wrong answer(s)"

    def get_current_question(self):
        """
        Get the current question in the active conversation.

        Returns:
            Current Question object, or None if no active conversation
        """
        if not self.active_conversation:
            return None

        return self.active_conversation.get_current_question()

    def to_dict(self) -> dict:
        """
        Serialize conversation engine state to dictionary.

        Returns:
            Dictionary containing conversation state
        """
        return {
            "active_conversation_npc": (
                self.active_conversation.npc_name if self.active_conversation else None
            ),
            "show_greeting": self.show_greeting,
            "last_answer_response": self.last_answer_response,
            "text_input_buffer": self.text_input_buffer,
        }

    @classmethod
    def from_dict(
        cls, data: dict, npc_conversations: dict[str, Conversation]
    ) -> ConversationEngine:
        """
        Create ConversationEngine from serialized dictionary.

        Args:
            data: Serialized conversation engine state
            npc_conversations: Map of NPC names to conversations

        Returns:
            Restored ConversationEngine instance
        """
        engine = cls()

        # Restore active conversation
        active_npc = data.get("active_conversation_npc")
        if active_npc and active_npc in npc_conversations:
            engine.active_conversation = npc_conversations[active_npc]

        # Restore UI state
        engine.show_greeting = data.get("show_greeting", False)
        engine.last_answer_response = data.get("last_answer_response")
        engine.text_input_buffer = data.get("text_input_buffer", "")

        return engine
