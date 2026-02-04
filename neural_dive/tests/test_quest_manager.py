"""Unit tests for QuestManager.

This test module covers quest tracking including:
- Quest activation
- NPC objective completion
- Quest completion checking
- Remaining objectives tracking
- Completion bonus calculation
- Serialization/deserialization
"""

from __future__ import annotations

import unittest

from neural_dive.config import QUEST_COMPLETION_COHERENCE_BONUS, QUEST_TARGET_NPCS
from neural_dive.managers.quest_manager import QuestManager


class TestQuestManagerInitialization(unittest.TestCase):
    """Test QuestManager initialization."""

    def test_default_initialization(self):
        """Test QuestManager initializes with default values."""
        manager = QuestManager()

        self.assertFalse(manager.quest_active)
        self.assertEqual(manager.completed_npcs, set())


class TestQuestActivation(unittest.TestCase):
    """Test quest activation."""

    def test_activate_quest(self):
        """Test activating the quest."""
        manager = QuestManager()

        success, message = manager.activate_quest()

        self.assertTrue(success)
        self.assertTrue(manager.quest_active)
        self.assertIn("activated", message.lower())

    def test_activate_quest_twice(self):
        """Test activating quest when already active returns False."""
        manager = QuestManager()
        manager.activate_quest()

        success, message = manager.activate_quest()

        self.assertFalse(success)
        self.assertIn("already active", message.lower())


class TestNPCObjectiveCompletion(unittest.TestCase):
    """Test NPC objective completion."""

    def test_complete_first_objective(self):
        """Test completing first NPC objective."""
        manager = QuestManager()

        success, message = manager.complete_npc_objective("TEST_ORACLE")

        self.assertTrue(success)
        self.assertIn("TEST_ORACLE", manager.completed_npcs)
        self.assertIn("remaining", message.lower())

    def test_complete_multiple_objectives(self):
        """Test completing multiple objectives."""
        manager = QuestManager()

        manager.complete_npc_objective("TEST_ORACLE")
        manager.complete_npc_objective("WEB_ARCHITECT")
        manager.complete_npc_objective("SYSTEM_CORE")

        self.assertEqual(len(manager.completed_npcs), 3)
        self.assertIn("TEST_ORACLE", manager.completed_npcs)
        self.assertIn("WEB_ARCHITECT", manager.completed_npcs)
        self.assertIn("SYSTEM_CORE", manager.completed_npcs)

    def test_complete_same_objective_twice(self):
        """Test completing the same objective twice."""
        manager = QuestManager()

        manager.complete_npc_objective("TEST_ORACLE")
        success, message = manager.complete_npc_objective("TEST_ORACLE")

        self.assertFalse(success)
        self.assertIn("already completed", message.lower())
        self.assertEqual(len(manager.completed_npcs), 1)

    def test_complete_all_objectives(self):
        """Test completing all quest objectives."""
        manager = QuestManager()

        # Complete all target NPCs
        for npc_name in QUEST_TARGET_NPCS:
            manager.complete_npc_objective(npc_name)

        self.assertEqual(len(manager.completed_npcs), len(QUEST_TARGET_NPCS))
        self.assertTrue(manager.is_quest_complete())

    def test_complete_final_objective_message(self):
        """Test message when completing final objective."""
        manager = QuestManager()

        # Complete all but one
        target_list = list(QUEST_TARGET_NPCS)
        for npc_name in target_list[:-1]:
            manager.complete_npc_objective(npc_name)

        # Complete the final one
        success, message = manager.complete_npc_objective(target_list[-1])

        self.assertTrue(success)
        self.assertIn("complete", message.lower())


class TestQuestCompletion(unittest.TestCase):
    """Test quest completion checking."""

    def test_quest_not_complete_initially(self):
        """Test quest is not complete when no objectives done."""
        manager = QuestManager()

        self.assertFalse(manager.is_quest_complete())

    def test_quest_not_complete_with_some_objectives(self):
        """Test quest not complete with only some objectives."""
        manager = QuestManager()

        manager.complete_npc_objective("TEST_ORACLE")
        manager.complete_npc_objective("WEB_ARCHITECT")

        self.assertFalse(manager.is_quest_complete())

    def test_quest_complete_with_all_objectives(self):
        """Test quest is complete when all objectives done."""
        manager = QuestManager()

        for npc_name in QUEST_TARGET_NPCS:
            manager.complete_npc_objective(npc_name)

        self.assertTrue(manager.is_quest_complete())

    def test_quest_complete_with_extra_npcs(self):
        """Test quest still complete with extra NPCs defeated."""
        manager = QuestManager()

        # Complete all quest targets
        for npc_name in QUEST_TARGET_NPCS:
            manager.complete_npc_objective(npc_name)

        # Add extra non-quest NPCs
        manager.complete_npc_objective("HEAP_MASTER")
        manager.complete_npc_objective("ALGO_SPIRIT")

        self.assertTrue(manager.is_quest_complete())


class TestRemainingObjectives(unittest.TestCase):
    """Test tracking remaining objectives."""

    def test_all_remaining_initially(self):
        """Test all objectives remain initially."""
        manager = QuestManager()

        remaining = manager.get_remaining_objectives()

        self.assertEqual(remaining, QUEST_TARGET_NPCS)

    def test_remaining_after_one_complete(self):
        """Test remaining objectives after completing one."""
        manager = QuestManager()

        manager.complete_npc_objective("TEST_ORACLE")
        remaining = manager.get_remaining_objectives()

        self.assertNotIn("TEST_ORACLE", remaining)
        self.assertEqual(len(remaining), len(QUEST_TARGET_NPCS) - 1)

    def test_remaining_after_multiple_complete(self):
        """Test remaining objectives after completing multiple."""
        manager = QuestManager()

        manager.complete_npc_objective("TEST_ORACLE")
        manager.complete_npc_objective("WEB_ARCHITECT")
        remaining = manager.get_remaining_objectives()

        self.assertNotIn("TEST_ORACLE", remaining)
        self.assertNotIn("WEB_ARCHITECT", remaining)
        self.assertEqual(len(remaining), len(QUEST_TARGET_NPCS) - 2)

    def test_no_remaining_when_complete(self):
        """Test no remaining objectives when quest complete."""
        manager = QuestManager()

        for npc_name in QUEST_TARGET_NPCS:
            manager.complete_npc_objective(npc_name)

        remaining = manager.get_remaining_objectives()

        self.assertEqual(len(remaining), 0)


class TestCompletionBonus(unittest.TestCase):
    """Test completion bonus calculation."""

    def test_no_bonus_initially(self):
        """Test no bonus when quest not complete."""
        manager = QuestManager()

        bonus = manager.get_completion_bonus()

        self.assertEqual(bonus, 0)

    def test_no_bonus_with_partial_completion(self):
        """Test no bonus with partial quest completion."""
        manager = QuestManager()

        manager.complete_npc_objective("TEST_ORACLE")
        manager.complete_npc_objective("WEB_ARCHITECT")

        bonus = manager.get_completion_bonus()

        self.assertEqual(bonus, 0)

    def test_bonus_when_complete(self):
        """Test bonus is awarded when quest complete."""
        manager = QuestManager()

        for npc_name in QUEST_TARGET_NPCS:
            manager.complete_npc_objective(npc_name)

        bonus = manager.get_completion_bonus()

        self.assertEqual(bonus, QUEST_COMPLETION_COHERENCE_BONUS)
        self.assertGreater(bonus, 0)


class TestQuestReset(unittest.TestCase):
    """Test quest reset functionality."""

    def test_reset_clears_state(self):
        """Test reset clears all quest state."""
        manager = QuestManager()

        manager.activate_quest()
        manager.complete_npc_objective("TEST_ORACLE")
        manager.complete_npc_objective("WEB_ARCHITECT")

        manager.reset()

        self.assertFalse(manager.quest_active)
        self.assertEqual(len(manager.completed_npcs), 0)

    def test_reset_allows_reactivation(self):
        """Test quest can be reactivated after reset."""
        manager = QuestManager()

        manager.activate_quest()
        manager.reset()

        success, _ = manager.activate_quest()

        self.assertTrue(success)
        self.assertTrue(manager.quest_active)


class TestSerialization(unittest.TestCase):
    """Test serialization and deserialization."""

    def test_to_dict(self):
        """Test converting QuestManager to dictionary."""
        manager = QuestManager()
        manager.activate_quest()
        manager.complete_npc_objective("TEST_ORACLE")
        manager.complete_npc_objective("WEB_ARCHITECT")

        data = manager.to_dict()

        self.assertTrue(data["quest_active"])
        self.assertEqual(len(data["completed_npcs"]), 2)
        self.assertIn("TEST_ORACLE", data["completed_npcs"])
        self.assertIn("WEB_ARCHITECT", data["completed_npcs"])

    def test_from_dict(self):
        """Test creating QuestManager from dictionary."""
        data = {
            "quest_active": True,
            "completed_npcs": ["TEST_ORACLE", "WEB_ARCHITECT"],
        }

        manager = QuestManager.from_dict(data)

        self.assertTrue(manager.quest_active)
        self.assertEqual(len(manager.completed_npcs), 2)
        self.assertIn("TEST_ORACLE", manager.completed_npcs)
        self.assertIn("WEB_ARCHITECT", manager.completed_npcs)

    def test_from_dict_with_defaults(self):
        """Test from_dict uses defaults for missing keys."""
        data: dict[str, bool | list[str]] = {}

        manager = QuestManager.from_dict(data)

        self.assertFalse(manager.quest_active)
        self.assertEqual(len(manager.completed_npcs), 0)

    def test_round_trip_serialization(self):
        """Test serialization round-trip preserves state."""
        original = QuestManager()
        original.activate_quest()
        original.complete_npc_objective("TEST_ORACLE")
        original.complete_npc_objective("SYSTEM_CORE")

        data = original.to_dict()
        restored = QuestManager.from_dict(data)

        self.assertEqual(restored.quest_active, original.quest_active)
        self.assertEqual(restored.completed_npcs, original.completed_npcs)
        self.assertEqual(restored.is_quest_complete(), original.is_quest_complete())


if __name__ == "__main__":
    unittest.main()
