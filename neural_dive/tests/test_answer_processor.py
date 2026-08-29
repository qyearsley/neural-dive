"""Tests for AnswerProcessor.

Covers answer validation, coherence/knowledge rewards, NPC opinion tracking,
victory detection on the final floor, the early-exit branches in
``_validate_conversation_state``, and recording outcomes to the cross-run
player profile.
"""

from __future__ import annotations

import random
import unittest
from unittest.mock import Mock

from neural_dive.difficulty import DIFFICULTY_CONFIGS, DifficultyLevel
from neural_dive.enums import NPCType
from neural_dive.managers.answer_processor import AnswerProcessor
from neural_dive.managers.conversation_engine import ConversationEngine
from neural_dive.managers.npc_relationships import NPCRelationships
from neural_dive.managers.player_manager import PlayerManager
from neural_dive.managers.quest_manager import QuestManager
from neural_dive.managers.stats_tracker import StatsTracker
from neural_dive.models import Answer, Conversation, Question
from neural_dive.player_profile import PlayerProfile
from neural_dive.question_types import QuestionType


def _mc_question(correct_idx: int = 0, reward: str | None = None) -> Question:
    """Build a 4-answer multiple-choice question with the given correct index."""
    answers = [
        Answer(
            text=f"Option {i}",
            correct=(i == correct_idx),
            response=f"Response {i}",
            reward_knowledge=reward if i == correct_idx else None,
        )
        for i in range(4)
    ]
    return Question(
        question_text="Test question?",
        topic="algorithms",
        question_type=QuestionType.MULTIPLE_CHOICE,
        answers=answers,
    )


def _short_answer_question(correct: str = "log n") -> Question:
    return Question(
        question_text="Type the answer.",
        topic="algorithms",
        question_type=QuestionType.SHORT_ANSWER,
        correct_answer=correct,
        correct_response="Yes!",
        incorrect_response="No.",
    )


class AnswerProcessorTestBase(unittest.TestCase):
    """Shared fixture wiring real lightweight managers; mocks NPCManager."""

    def setUp(self) -> None:
        self.player_manager = PlayerManager(coherence=80, max_coherence=100)
        self.npc_manager = Mock()
        # Opinion tracking is a small real unit, so let the mock delegate to it
        # rather than returning Mocks -- the tests below assert on the resulting
        # opinion, not just that a call happened.
        self.relationships = NPCRelationships()
        self.npc_manager.relationships = self.relationships
        self.npc_manager.get_opinion.side_effect = self.relationships.get_opinion
        self.npc_manager.update_opinion.side_effect = self.relationships.update_opinion
        self.conversation_engine = ConversationEngine()
        self.stats_tracker = StatsTracker()
        self.quest_manager = QuestManager()
        self.difficulty = DIFFICULTY_CONFIGS[DifficultyLevel.NORMAL]
        self.processor = AnswerProcessor(
            player_manager=self.player_manager,
            npc_manager=self.npc_manager,
            conversation_engine=self.conversation_engine,
            stats_tracker=self.stats_tracker,
            quest_manager=self.quest_manager,
            difficulty_settings=self.difficulty,
            snippets={},
            rand=random.Random(42),
        )

    def start_conversation(
        self,
        questions: list[Question],
        npc_name: str = "ALGO_SPIRIT",
        npc_type: NPCType = NPCType.SPECIALIST,
    ) -> Conversation:
        conv = Conversation(
            npc_name=npc_name,
            greeting="Hello",
            questions=questions,
            npc_type=npc_type,
        )
        self.conversation_engine.active_conversation = conv
        return conv


class TestMultipleChoiceCorrect(AnswerProcessorTestBase):
    def test_correct_answer_gains_coherence(self):
        self.start_conversation([_mc_question(correct_idx=1), _mc_question()])
        starting = self.player_manager.coherence

        success, _, won = self.processor.answer_multiple_choice(
            answer_idx=1, npcs_completed=set(), is_final_floor=False
        )

        self.assertTrue(success)
        self.assertFalse(won)
        self.assertEqual(
            self.player_manager.coherence,
            starting + self.difficulty.correct_answer_gain,
        )

    def test_correct_answer_increments_npc_opinion(self):
        self.start_conversation([_mc_question(correct_idx=2)])

        self.processor.answer_multiple_choice(
            answer_idx=2, npcs_completed=set(), is_final_floor=False
        )

        self.assertEqual(self.npc_manager.get_opinion("ALGO_SPIRIT"), 1)

    def test_correct_answer_records_in_stats(self):
        self.start_conversation([_mc_question(correct_idx=0)])

        self.processor.answer_multiple_choice(
            answer_idx=0, npcs_completed=set(), is_final_floor=False
        )

        self.assertEqual(self.stats_tracker.questions_correct, 1)
        self.assertEqual(self.stats_tracker.questions_wrong, 0)

    def test_correct_answer_grants_knowledge_module(self):
        self.start_conversation([_mc_question(correct_idx=1, reward="big_o")])

        _, response, _ = self.processor.answer_multiple_choice(
            answer_idx=1, npcs_completed=set(), is_final_floor=False
        )

        self.assertIn("big_o", self.player_manager.knowledge_modules)
        self.assertIn("Gained: big_o", response)

    def test_completing_conversation_marks_npc_completed(self):
        self.start_conversation([_mc_question(correct_idx=0)])
        completed: set[str] = set()

        self.processor.answer_multiple_choice(
            answer_idx=0, npcs_completed=completed, is_final_floor=False
        )

        self.assertIn("ALGO_SPIRIT", completed)


class TestMultipleChoiceWrong(AnswerProcessorTestBase):
    def test_wrong_answer_loses_coherence(self):
        self.start_conversation([_mc_question(correct_idx=0)])
        starting = self.player_manager.coherence

        success, _, won = self.processor.answer_multiple_choice(
            answer_idx=2, npcs_completed=set(), is_final_floor=False
        )

        self.assertFalse(success)
        self.assertFalse(won)
        self.assertEqual(
            self.player_manager.coherence,
            starting - self.difficulty.wrong_answer_penalty,
        )

    def test_wrong_answer_to_enemy_uses_harsher_penalty(self):
        self.start_conversation(
            [_mc_question(correct_idx=0)],
            npc_name="CODE_AUDITOR",
            npc_type=NPCType.ENEMY,
        )
        starting = self.player_manager.coherence

        self.processor.answer_multiple_choice(
            answer_idx=1, npcs_completed=set(), is_final_floor=False
        )

        self.assertEqual(
            self.player_manager.coherence,
            starting - self.difficulty.enemy_wrong_answer_penalty,
        )

    def test_wrong_answer_decrements_npc_opinion(self):
        self.start_conversation([_mc_question(correct_idx=0)])

        self.processor.answer_multiple_choice(
            answer_idx=2, npcs_completed=set(), is_final_floor=False
        )

        self.assertEqual(self.npc_manager.get_opinion("ALGO_SPIRIT"), -1)

    def test_invalid_answer_index_returns_error(self):
        self.start_conversation([_mc_question()])

        success, message, _ = self.processor.answer_multiple_choice(
            answer_idx=99, npcs_completed=set(), is_final_floor=False
        )

        self.assertFalse(success)
        self.assertIn("Invalid", message)

    def test_no_active_conversation_returns_error(self):
        success, message, _ = self.processor.answer_multiple_choice(
            answer_idx=0, npcs_completed=set(), is_final_floor=False
        )

        self.assertFalse(success)
        self.assertIn("Not in a conversation", message)


class TestVictoryDetection(AnswerProcessorTestBase):
    def test_completing_final_boss_on_final_floor_wins(self):
        self.start_conversation(
            [_mc_question(correct_idx=0)],
            npc_name="FINAL_BOSS",
            npc_type=NPCType.BOSS,
        )

        _, _, won = self.processor.answer_multiple_choice(
            answer_idx=0, npcs_completed=set(), is_final_floor=True
        )

        self.assertTrue(won)

    def test_completing_final_boss_on_earlier_floor_does_not_win(self):
        self.start_conversation(
            [_mc_question(correct_idx=0)],
            npc_name="FINAL_BOSS",
            npc_type=NPCType.BOSS,
        )

        _, _, won = self.processor.answer_multiple_choice(
            answer_idx=0, npcs_completed=set(), is_final_floor=False
        )

        self.assertFalse(won)

    def test_completing_specialist_on_final_floor_does_not_win(self):
        self.start_conversation(
            [_mc_question(correct_idx=0)],
            npc_name="ALGO_SPIRIT",
            npc_type=NPCType.SPECIALIST,
        )

        _, _, won = self.processor.answer_multiple_choice(
            answer_idx=0, npcs_completed=set(), is_final_floor=True
        )

        self.assertFalse(won)


class TestTextAnswers(AnswerProcessorTestBase):
    def test_correct_text_answer_gains_coherence(self):
        self.start_conversation([_short_answer_question(correct="log n")])
        starting = self.player_manager.coherence

        success, _, _ = self.processor.answer_text_question(
            user_answer="log n", npcs_completed=set(), is_final_floor=False
        )

        self.assertTrue(success)
        self.assertEqual(
            self.player_manager.coherence,
            starting + self.difficulty.correct_answer_gain,
        )

    def test_wrong_text_answer_loses_coherence(self):
        self.start_conversation([_short_answer_question(correct="log n")])
        starting = self.player_manager.coherence

        success, _, _ = self.processor.answer_text_question(
            user_answer="quadratic", npcs_completed=set(), is_final_floor=False
        )

        self.assertFalse(success)
        self.assertEqual(
            self.player_manager.coherence,
            starting - self.difficulty.wrong_answer_penalty,
        )

    def test_text_answer_on_multiple_choice_question_rejected(self):
        self.start_conversation([_mc_question()])

        success, message, _ = self.processor.answer_text_question(
            user_answer="anything", npcs_completed=set(), is_final_floor=False
        )

        self.assertFalse(success)
        self.assertIn("multiple choice", message.lower())


class TestQuestionHistoryRecording(AnswerProcessorTestBase):
    """Test that answers are written to the cross-run profile."""

    def setUp(self) -> None:
        super().setUp()
        self.profile = PlayerProfile()
        self.processor.profile = self.profile

    def test_correct_answer_is_recorded(self):
        question = _mc_question(correct_idx=1)
        question.question_id = "mutex_purpose"
        self.start_conversation([question])

        self.processor.answer_multiple_choice(
            answer_idx=1, npcs_completed=set(), is_final_floor=False
        )

        record = self.profile.get("mutex_purpose")
        assert record is not None
        self.assertEqual((record.seen, record.correct, record.wrong), (1, 1, 0))

    def test_wrong_answer_is_recorded(self):
        question = _mc_question(correct_idx=1)
        question.question_id = "mutex_purpose"
        self.start_conversation([question])

        self.processor.answer_multiple_choice(
            answer_idx=2, npcs_completed=set(), is_final_floor=False
        )

        record = self.profile.get("mutex_purpose")
        assert record is not None
        self.assertEqual((record.seen, record.correct, record.wrong), (1, 0, 1))

    def test_text_answers_are_recorded(self):
        question = _short_answer_question(correct="log n")
        question.question_id = "binary_search_complexity"
        self.start_conversation([question])

        self.processor.answer_text_question(
            user_answer="quadratic", npcs_completed=set(), is_final_floor=False
        )

        record = self.profile.get("binary_search_complexity")
        assert record is not None
        self.assertEqual(record.wrong, 1)

    def test_question_without_an_id_is_not_recorded(self):
        # Questions built in code rather than loaded from a content set have no
        # stable identity, so there is nothing to attribute history to.
        self.start_conversation([_mc_question(correct_idx=0)])

        self.processor.answer_multiple_choice(
            answer_idx=0, npcs_completed=set(), is_final_floor=False
        )

        self.assertTrue(self.profile.is_empty)

    def test_an_invalid_answer_index_records_nothing(self):
        question = _mc_question()
        question.question_id = "mutex_purpose"
        self.start_conversation([question])

        self.processor.answer_multiple_choice(
            answer_idx=99, npcs_completed=set(), is_final_floor=False
        )

        self.assertTrue(self.profile.is_empty)

    def test_without_a_profile_nothing_is_recorded_and_nothing_breaks(self):
        self.processor.profile = None
        question = _mc_question(correct_idx=1)
        question.question_id = "mutex_purpose"
        self.start_conversation([question])

        success, _, _ = self.processor.answer_multiple_choice(
            answer_idx=1, npcs_completed=set(), is_final_floor=False
        )

        self.assertTrue(success)
        self.assertTrue(self.profile.is_empty)


if __name__ == "__main__":
    unittest.main()
