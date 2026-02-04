"""Answer processing for Neural Dive.

This module provides the AnswerProcessor class which handles answer validation,
scoring, and consequence application (coherence changes, knowledge rewards, etc.).

The AnswerProcessor coordinates between multiple managers to apply the full
effects of answering questions correctly or incorrectly.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from neural_dive.answer_matching import match_answer
from neural_dive.difficulty import DifficultySettings
from neural_dive.enums import NPCType
from neural_dive.models import Answer
from neural_dive.question_types import QuestionType

if TYPE_CHECKING:
    import random

    from neural_dive.managers.conversation_engine import ConversationEngine
    from neural_dive.managers.npc_manager import NPCManager
    from neural_dive.managers.player_manager import PlayerManager
    from neural_dive.managers.quest_manager import QuestManager
    from neural_dive.managers.stats_tracker import StatsTracker
    from neural_dive.models import Conversation, Question


class AnswerProcessor:
    """Processes question answers and applies game consequences.

    The AnswerProcessor is a coordinator that orchestrates the effects of
    answering questions. It updates multiple game systems:
    - Player stats (coherence, knowledge)
    - NPC relationships (opinions)
    - Quest progress
    - Game statistics

    This separation allows answer processing logic to be tested independently
    and keeps the Game class focused on higher-level orchestration.

    Attributes:
        player_manager: Manages player stats (coherence, knowledge, inventory)
        npc_manager: Manages NPCs and their relationships
        conversation_engine: Manages conversation state
        stats_tracker: Tracks game statistics
        quest_manager: Tracks quest progress
    """

    def __init__(
        self,
        player_manager: PlayerManager,
        npc_manager: NPCManager,
        conversation_engine: ConversationEngine,
        stats_tracker: StatsTracker,
        quest_manager: QuestManager,
        difficulty_settings: DifficultySettings,
        snippets: dict,
        rand: random.Random,
    ):
        """Initialize AnswerProcessor with manager dependencies.

        Args:
            player_manager: PlayerManager instance
            npc_manager: NPCManager instance
            conversation_engine: ConversationEngine instance
            stats_tracker: StatsTracker instance
            quest_manager: QuestManager instance
            difficulty_settings: Difficulty settings dict
            snippets: Code snippets dict
            rand: Random number generator
        """
        self.player_manager = player_manager
        self.npc_manager = npc_manager
        self.conversation_engine = conversation_engine
        self.stats_tracker = stats_tracker
        self.quest_manager = quest_manager
        self.difficulty_settings = difficulty_settings
        self.snippets = snippets
        self.rand = rand

    def answer_multiple_choice(
        self, answer_idx: int, npcs_completed: set[str], is_final_floor: bool
    ) -> tuple[bool, str, bool]:
        """Process a multiple choice answer.

        Args:
            answer_idx: Index of the selected answer (0-based)
            npcs_completed: Set of completed NPC names (mutable, updated in place)
            is_final_floor: Whether player is on final floor

        Returns:
            Tuple of (success, message, game_was_won)
        """
        # Validate conversation state
        valid, error_msg, conv, question, is_enemy = self._validate_conversation_state()
        if not valid:
            # Return True for "Conversation completed!" as it's not an error
            return "completed" in error_msg, error_msg, False

        assert conv is not None and question is not None  # Type narrowing

        # Validate answer index
        if answer_idx < 0 or answer_idx >= len(question.answers):
            return False, "Invalid answer choice.", False

        answer = question.answers[answer_idx]

        # Track NPC opinion
        npc_name = conv.npc_name
        if npc_name not in self.npc_manager.npc_opinions:
            self.npc_manager.npc_opinions[npc_name] = 0

        if answer.correct:
            return self._handle_correct_answer(
                conv, answer, npc_name, is_enemy, npcs_completed, is_final_floor
            )
        else:
            success, message, game_was_won = self._handle_wrong_answer(
                conv, answer, npc_name, is_enemy
            )
            return success, message, game_was_won

    def answer_text_question(
        self, user_answer: str, npcs_completed: set[str], is_final_floor: bool
    ) -> tuple[bool, str, bool]:
        """Process a text-based answer.

        Args:
            user_answer: The text answer provided by the user
            npcs_completed: Set of completed NPC names (mutable, updated in place)
            is_final_floor: Whether player is on final floor

        Returns:
            Tuple of (correct, response_message, game_was_won)
        """
        # Validate conversation state
        valid, error_msg, conv, question, is_enemy = self._validate_conversation_state()
        if not valid:
            # Return True for "Conversation completed!" as it's not an error
            return "completed" in error_msg, error_msg, False

        assert conv is not None and question is not None  # Type narrowing

        # Verify this is a text-based question type
        if question.question_type == QuestionType.MULTIPLE_CHOICE:
            return False, "This is a multiple choice question. Use number keys 1-4.", False

        # Check if answer is correct using answer matching
        is_correct = match_answer(
            user_answer,
            question.correct_answer or "",
            match_type=question.match_type,
            case_sensitive=question.case_sensitive,
        )

        # Track NPC opinion
        npc_name = conv.npc_name
        if npc_name not in self.npc_manager.npc_opinions:
            self.npc_manager.npc_opinions[npc_name] = 0

        if is_correct:
            # Create a temporary Answer object for correct response
            temp_answer = Answer(
                text=user_answer,
                correct=True,
                response=question.correct_response or "Correct!",
                reward_knowledge=question.reward_knowledge,
            )
            return self._handle_correct_answer(
                conv, temp_answer, npc_name, is_enemy, npcs_completed, is_final_floor
            )
        else:
            # Create a temporary Answer object for wrong response
            temp_answer = Answer(
                text=user_answer,
                correct=False,
                response=question.incorrect_response or "Not quite.",
                enemy_penalty=self.difficulty_settings.enemy_wrong_answer_penalty,
            )
            success, message, game_was_won = self._handle_wrong_answer(
                conv, temp_answer, npc_name, is_enemy
            )
            return success, message, game_was_won

    def _validate_conversation_state(
        self,
    ) -> tuple[bool, str, Conversation | None, Question | None, bool]:
        """Validate conversation state and return common data needed for answering.

        Returns:
            Tuple of (valid, error_message, conversation, question, is_enemy)
            If valid is False, error_message contains the reason.
        """
        active_conv = self.conversation_engine.active_conversation
        if not active_conv:
            return False, "Not in a conversation.", None, None, False

        conv = active_conv

        # Check if conversation is already complete
        if conv.current_question_idx >= len(conv.questions):
            conv.completed = True
            self.conversation_engine.active_conversation = None
            return False, "Conversation completed!", None, None, False

        # Get current question
        question = conv.questions[conv.current_question_idx]

        # Check if this is an enemy (harsher penalties)
        is_enemy = conv.npc_type == NPCType.ENEMY

        return True, "", conv, question, is_enemy

    def _handle_correct_answer(
        self,
        conv: Conversation,
        answer: Answer,
        npc_name: str,
        is_enemy: bool,
        npcs_completed: set[str],
        is_final_floor: bool,
    ) -> tuple[bool, str, bool]:
        """Handle a correct answer.

        Args:
            conv: The conversation
            answer: The correct answer
            npc_name: Name of the NPC
            is_enemy: Whether the NPC is an enemy
            npcs_completed: Set of completed NPC names (mutable, updated in place)
            is_final_floor: Whether player is on final floor

        Returns:
            Tuple of (True, response_message, game_was_won)
        """
        # Update stats
        coherence_gain = self.difficulty_settings.correct_answer_gain
        self.player_manager.gain_coherence(coherence_gain)
        self.npc_manager.npc_opinions[npc_name] += 1

        # Track score
        self.stats_tracker.record_correct_answer()

        # Build response
        response = answer.response

        # Award knowledge module
        if answer.reward_knowledge:
            was_new = self.player_manager.add_knowledge(answer.reward_knowledge)
            if was_new:
                response += (
                    f"\n\n[+{coherence_gain} Coherence]\n[Gained: {answer.reward_knowledge}]"
                )
            else:
                response += f"\n\n[+{coherence_gain} Coherence]"
        else:
            response += f"\n\n[+{coherence_gain} Coherence]"

        # Move to next question
        conv.current_question_idx += 1

        # Initialize game_won flag
        game_was_won = False

        # Check if conversation is complete
        if conv.current_question_idx >= len(conv.questions):
            conv.completed = True

            # Track completion
            npcs_completed.add(npc_name)

            # Give item rewards based on NPC type
            response = self._give_npc_rewards(conv.npc_type, response)

            # Check for victory condition on final floor
            if is_final_floor:
                # Victory bosses - defeating any of these wins the game
                victory_bosses = {"FINAL_BOSS", "RESILIENCE_BOSS", "ML_BOSS", "THEORY_BOSS"}
                if npc_name in victory_bosses:
                    game_was_won = True

            # Track quest completion for specialists
            if conv.npc_type == NPCType.SPECIALIST:
                self.quest_manager.complete_npc_objective(npc_name)

            self.conversation_engine.active_conversation = None

            # Add completion message
            response += f"\n\n{npc_name}: You have proven your worth. I grant you passage."

        return True, response, game_was_won

    def _handle_wrong_answer(
        self, conv: Conversation, answer: Answer, npc_name: str, is_enemy: bool
    ) -> tuple[bool, str, bool]:
        """Handle a wrong answer.

        Args:
            conv: The conversation
            answer: The wrong answer
            npc_name: Name of the NPC
            is_enemy: Whether the NPC is an enemy

        Returns:
            Tuple of (False, response_message, game_was_won=False)
        """
        # Calculate penalty based on difficulty and NPC type
        penalty = (
            self.difficulty_settings.enemy_wrong_answer_penalty
            if is_enemy
            else self.difficulty_settings.wrong_answer_penalty
        )

        # Update stats
        self.player_manager.lose_coherence(penalty)
        self.npc_manager.npc_opinions[npc_name] -= 1

        # Track score
        self.stats_tracker.record_wrong_answer()

        # Build response
        if is_enemy:
            response = f"{answer.response}\n\n[CRITICAL ERROR! -{penalty} Coherence]"
        else:
            response = f"{answer.response}\n\n[-{penalty} Coherence]"

        # Check for game over
        if self.player_manager.coherence <= 0:
            response += "\n\n[SYSTEM FAILURE - COHERENCE LOST]"
            self.conversation_engine.active_conversation = None

        return False, response, False

    def _give_npc_rewards(self, npc_type: NPCType, response: str) -> str:
        """Give item rewards when completing NPC conversations.

        Args:
            npc_type: Type of NPC being completed
            response: Current response message

        Returns:
            Updated response message with reward information
        """
        from neural_dive.items import CodeSnippet, HintToken

        # Helper NPCs give hint tokens
        if npc_type == NPCType.HELPER:
            hint = HintToken()
            if self.player_manager.add_item(hint):
                response += "\n\n[Received: Hint Token]"
        # Specialists give snippets (if available and inventory not full)
        elif npc_type == NPCType.SPECIALIST and self.snippets:
            # Pick a random snippet
            snippet_id = self.rand.choice(list(self.snippets.keys()))
            snippet_data = self.snippets[snippet_id]
            snippet = CodeSnippet(
                name=snippet_data["name"],
                topic=snippet_data["topic"],
                content=snippet_data["content"],
            )
            if self.player_manager.add_item(snippet):
                response += f"\n\n[Received: {snippet.name}]"

        return response
