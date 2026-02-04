"""Tests for InteractionHandler."""

import unittest

from neural_dive.difficulty import DifficultyLevel, get_difficulty_settings
from neural_dive.entities import Entity, InfoTerminal, Stairs
from neural_dive.enums import NPCType
from neural_dive.managers.conversation_engine import ConversationEngine
from neural_dive.managers.floor_manager import FloorManager
from neural_dive.managers.interaction_handler import InteractionHandler
from neural_dive.managers.player_manager import PlayerManager
from neural_dive.managers.quest_manager import QuestManager
from neural_dive.models import Answer, Conversation, Question
from neural_dive.question_types import QuestionType


def create_test_question(correct_idx: int = 0) -> Question:
    """Helper to create a test question."""
    return Question(
        question_text="Test question?",
        topic="test",
        question_type=QuestionType.MULTIPLE_CHOICE,
        answers=[
            Answer(text=f"Answer {i}", correct=(i == correct_idx), response="Response")
            for i in range(4)
        ],
    )


class TestInteractionHandlerInitialization(unittest.TestCase):
    """Test InteractionHandler initialization."""

    def test_initialization(self):
        """Test that InteractionHandler initializes correctly."""
        player_manager = PlayerManager()
        conversation_engine = ConversationEngine()
        floor_manager = FloorManager(
            max_floors=3, map_width=80, map_height=24, seed=42, level_data={}
        )
        quest_manager = QuestManager()
        difficulty_settings = get_difficulty_settings(DifficultyLevel.NORMAL)

        handler = InteractionHandler(
            player_manager=player_manager,
            conversation_engine=conversation_engine,
            floor_manager=floor_manager,
            quest_manager=quest_manager,
            difficulty_settings=difficulty_settings,
        )

        self.assertEqual(handler.player_manager, player_manager)
        self.assertEqual(handler.conversation_engine, conversation_engine)
        self.assertEqual(handler.floor_manager, floor_manager)
        self.assertEqual(handler.quest_manager, quest_manager)
        self.assertEqual(handler.difficulty_settings, difficulty_settings)


class TestInteractWithTerminal(unittest.TestCase):
    """Test terminal interactions."""

    def setUp(self):
        """Set up test fixtures."""
        self.handler = InteractionHandler(
            player_manager=PlayerManager(),
            conversation_engine=ConversationEngine(),
            floor_manager=FloorManager(3, 80, 24, 42, {}),
            quest_manager=QuestManager(),
            difficulty_settings=get_difficulty_settings(DifficultyLevel.NORMAL),
        )

    def test_interact_with_terminal(self):
        """Test interacting with a terminal."""
        terminal = InfoTerminal(5, 5, "Test Terminal", ["Line 1", "Line 2"])
        result = self.handler.interact(
            player_pos=(5, 5),
            terminals=[terminal],
            npcs=[],
            stairs=[],
            npc_conversations={},
        )

        self.assertTrue(result.success)
        self.assertIn("Reading", result.message)
        self.assertEqual(result.action, "terminal")
        self.assertEqual(result.terminal, terminal)

    def test_interact_no_nearby_entities(self):
        """Test interaction when no entities are nearby."""
        result = self.handler.interact(
            player_pos=(10, 10),
            terminals=[InfoTerminal(5, 5, "Terminal", [])],
            npcs=[],
            stairs=[],
            npc_conversations={},
        )

        self.assertFalse(result.success)
        self.assertIn("No one nearby", result.message)
        self.assertEqual(result.action, "none")


class TestInteractWithNPC(unittest.TestCase):
    """Test NPC interactions."""

    def setUp(self):
        """Set up test fixtures."""
        self.handler = InteractionHandler(
            player_manager=PlayerManager(coherence=50),
            conversation_engine=ConversationEngine(),
            floor_manager=FloorManager(3, 80, 24, 42, {}),
            quest_manager=QuestManager(),
            difficulty_settings=get_difficulty_settings(DifficultyLevel.NORMAL),
        )

    def test_interact_with_specialist_npc(self):
        """Test interacting with a specialist NPC."""
        npc = Entity(5, 5, "S", "blue", "SPECIALIST_NPC")
        conversation = Conversation(
            npc_name="SPECIALIST_NPC",
            npc_type=NPCType.SPECIALIST,
            greeting="Hello!",
            questions=[create_test_question()],
            completed=False,
        )

        result = self.handler.interact(
            player_pos=(5, 5),
            terminals=[],
            npcs=[npc],
            stairs=[],
            npc_conversations={"SPECIALIST_NPC": conversation},
        )

        self.assertTrue(result.success)
        self.assertEqual(result.message, "Hello!")
        self.assertEqual(result.action, "conversation")
        self.assertEqual(result.conversation, conversation)

    def test_interact_with_helper_npc(self):
        """Test interacting with a helper NPC restores coherence."""
        npc = Entity(5, 5, "H", "green", "HELPER_NPC")
        conversation = Conversation(
            npc_name="HELPER_NPC",
            npc_type=NPCType.HELPER,
            greeting="I'll help!",
            questions=[],
            completed=False,
        )

        initial_coherence = self.handler.player_manager.coherence
        result = self.handler.interact(
            player_pos=(5, 5),
            terminals=[],
            npcs=[npc],
            stairs=[],
            npc_conversations={"HELPER_NPC": conversation},
        )

        self.assertTrue(result.success)
        self.assertIn("restored", result.message)
        self.assertEqual(result.action, "helper")
        self.assertGreater(self.handler.player_manager.coherence, initial_coherence)
        self.assertTrue(conversation.completed)

    def test_interact_with_quest_npc(self):
        """Test interacting with a quest NPC activates quest."""
        npc = Entity(5, 5, "Q", "yellow", "QUEST_NPC")
        conversation = Conversation(
            npc_name="QUEST_NPC",
            npc_type=NPCType.QUEST,
            greeting="I have a quest!",
            questions=[],
            completed=False,
        )

        result = self.handler.interact(
            player_pos=(5, 5),
            terminals=[],
            npcs=[npc],
            stairs=[],
            npc_conversations={"QUEST_NPC": conversation},
        )

        self.assertTrue(result.success)
        self.assertEqual(result.message, "I have a quest!")
        self.assertEqual(result.action, "quest")
        self.assertTrue(conversation.completed)
        self.assertTrue(self.handler.quest_manager.quest_active)

    def test_interact_with_completed_npc(self):
        """Test interacting with an already completed NPC."""
        npc = Entity(5, 5, "S", "blue", "SPECIALIST_NPC")
        conversation = Conversation(
            npc_name="SPECIALIST_NPC",
            npc_type=NPCType.SPECIALIST,
            greeting="Hello!",
            questions=[create_test_question()],
            completed=True,
        )

        result = self.handler.interact(
            player_pos=(5, 5),
            terminals=[],
            npcs=[npc],
            stairs=[],
            npc_conversations={"SPECIALIST_NPC": conversation},
        )

        self.assertTrue(result.success)
        self.assertIn("proven yourself", result.message)
        self.assertEqual(result.action, "none")

    def test_interact_with_npc_no_conversation(self):
        """Test interacting with an NPC that has no conversation."""
        npc = Entity(5, 5, "N", "gray", "RANDOM_NPC")

        result = self.handler.interact(
            player_pos=(5, 5),
            terminals=[],
            npcs=[npc],
            stairs=[],
            npc_conversations={},
        )

        self.assertFalse(result.success)
        self.assertIn("nothing to say", result.message)
        self.assertEqual(result.action, "none")


class TestInteractionPriority(unittest.TestCase):
    """Test entity interaction priority."""

    def setUp(self):
        """Set up test fixtures."""
        self.handler = InteractionHandler(
            player_manager=PlayerManager(),
            conversation_engine=ConversationEngine(),
            floor_manager=FloorManager(3, 80, 24, 42, {}),
            quest_manager=QuestManager(),
            difficulty_settings=get_difficulty_settings(DifficultyLevel.NORMAL),
        )

    def test_npc_priority_over_terminal(self):
        """Test that NPCs have priority over terminals at equal distance."""
        npc = Entity(5, 5, "S", "blue", "NPC")
        terminal = InfoTerminal(6, 5, "Terminal", [])
        conversation = Conversation(
            npc_name="NPC",
            npc_type=NPCType.SPECIALIST,
            greeting="Hello!",
            questions=[create_test_question()],
            completed=False,
        )

        # Both at distance 1 from player at (5, 6)
        result = self.handler.interact(
            player_pos=(5, 6),
            terminals=[terminal],
            npcs=[npc],
            stairs=[],
            npc_conversations={"NPC": conversation},
        )

        self.assertEqual(result.action, "conversation")

    def test_terminal_priority_over_stairs(self):
        """Test that terminals have priority over stairs at equal distance."""
        terminal = InfoTerminal(5, 5, "Terminal", [])
        stairs = Stairs(6, 5, "down")

        # Both at distance 1 from player at (5, 6)
        result = self.handler.interact(
            player_pos=(5, 6),
            terminals=[terminal],
            npcs=[],
            stairs=[stairs],
            npc_conversations={},
        )

        self.assertEqual(result.action, "terminal")

    def test_closest_entity_wins(self):
        """Test that closest entity is chosen regardless of type."""
        npc = Entity(10, 10, "S", "blue", "NPC")
        terminal = InfoTerminal(5, 5, "Terminal", [])
        conversation = Conversation(
            npc_name="NPC",
            npc_type=NPCType.SPECIALIST,
            greeting="Hello!",
            questions=[create_test_question()],
            completed=False,
        )

        # Terminal at distance 1, NPC at distance 6
        result = self.handler.interact(
            player_pos=(5, 6),
            terminals=[terminal],
            npcs=[npc],
            stairs=[],
            npc_conversations={"NPC": conversation},
        )

        self.assertEqual(result.action, "terminal")


class TestStairsUsage(unittest.TestCase):
    """Test stairs usage and floor transitions."""

    def setUp(self):
        """Set up test fixtures."""
        self.player = Entity(10, 10, "@", "cyan", "Player")
        self.floor_manager = FloorManager(
            max_floors=3,
            map_width=80,
            map_height=24,
            seed=42,
            level_data={},
        )
        self.handler = InteractionHandler(
            player_manager=PlayerManager(),
            conversation_engine=ConversationEngine(),
            floor_manager=self.floor_manager,
            quest_manager=QuestManager(),
            difficulty_settings=get_difficulty_settings(DifficultyLevel.NORMAL),
        )

    def test_use_stairs_not_on_stairs(self):
        """Test using stairs when not standing on them."""
        stairs = [Stairs(5, 5, "down")]
        result = self.handler.use_stairs(
            player=self.player,
            player_pos=(10, 10),
            stairs=stairs,
            npcs_completed=set(),
            npc_data={},
        )

        self.assertFalse(result.success)
        self.assertIn("No stairs", result.message)
        self.assertFalse(result.floor_changed)

    def test_descend_stairs_success(self):
        """Test successfully descending stairs."""
        stairs = [Stairs(10, 10, "down")]
        self.floor_manager.current_floor = 1

        result = self.handler.use_stairs(
            player=self.player,
            player_pos=(10, 10),
            stairs=stairs,
            npcs_completed=set(),
            npc_data={},
        )

        self.assertTrue(result.success)
        self.assertIn("Descended", result.message)
        self.assertTrue(result.floor_changed)
        self.assertEqual(result.new_floor, 2)

    def test_descend_stairs_incomplete_floor(self):
        """Test descending stairs with incomplete floor objectives."""
        stairs = [Stairs(10, 10, "down")]
        self.floor_manager.current_floor = 1
        self.floor_manager.floor_requirements = {1: {"NPC1", "NPC2"}}

        result = self.handler.use_stairs(
            player=self.player,
            player_pos=(10, 10),
            stairs=stairs,
            npcs_completed={"NPC1"},  # Only completed 1 of 2
            npc_data={"NPC1": {}, "NPC2": {}},
        )

        self.assertFalse(result.success)
        self.assertIn("Cannot descend", result.message)
        self.assertFalse(result.floor_changed)

    def test_descend_stairs_at_bottom(self):
        """Test descending stairs when at bottom floor."""
        stairs = [Stairs(10, 10, "down")]
        self.floor_manager.current_floor = 3  # Max floors

        result = self.handler.use_stairs(
            player=self.player,
            player_pos=(10, 10),
            stairs=stairs,
            npcs_completed=set(),
            npc_data={},
        )

        self.assertFalse(result.success)
        self.assertIn("No deeper", result.message)
        self.assertFalse(result.floor_changed)

    def test_ascend_stairs_success(self):
        """Test successfully ascending stairs."""
        stairs = [Stairs(10, 10, "up")]
        self.floor_manager.current_floor = 2

        result = self.handler.use_stairs(
            player=self.player,
            player_pos=(10, 10),
            stairs=stairs,
            npcs_completed=set(),
            npc_data={},
        )

        self.assertTrue(result.success)
        self.assertIn("Ascended", result.message)
        self.assertTrue(result.floor_changed)
        self.assertEqual(result.new_floor, 1)

    def test_ascend_stairs_at_top(self):
        """Test ascending stairs when at top floor."""
        stairs = [Stairs(10, 10, "up")]
        self.floor_manager.current_floor = 1

        result = self.handler.use_stairs(
            player=self.player,
            player_pos=(10, 10),
            stairs=stairs,
            npcs_completed=set(),
            npc_data={},
        )

        self.assertFalse(result.success)
        self.assertIn("top layer", result.message)
        self.assertFalse(result.floor_changed)


class TestFloorCompletion(unittest.TestCase):
    """Test floor completion checking."""

    def setUp(self):
        """Set up test fixtures."""
        self.floor_manager = FloorManager(
            max_floors=3,
            map_width=80,
            map_height=24,
            seed=42,
            level_data={},
            floor_requirements={1: {"NPC1", "NPC2"}, 2: {"NPC3"}},
        )
        self.handler = InteractionHandler(
            player_manager=PlayerManager(),
            conversation_engine=ConversationEngine(),
            floor_manager=self.floor_manager,
            quest_manager=QuestManager(),
            difficulty_settings=get_difficulty_settings(DifficultyLevel.NORMAL),
        )

    def test_floor_complete_all_npcs_done(self):
        """Test floor completion when all required NPCs are completed."""
        self.floor_manager.current_floor = 1
        result = self.handler.is_floor_complete(
            npcs_completed={"NPC1", "NPC2"},
            npc_data={"NPC1": {"floor": 1}, "NPC2": {"floor": 1}},
        )
        self.assertTrue(result)

    def test_floor_incomplete_missing_npcs(self):
        """Test floor is incomplete when NPCs are missing."""
        self.floor_manager.current_floor = 1
        result = self.handler.is_floor_complete(
            npcs_completed={"NPC1"},  # Missing NPC2
            npc_data={"NPC1": {"floor": 1}, "NPC2": {"floor": 1}},
        )
        self.assertFalse(result)

    def test_floor_complete_no_requirements(self):
        """Test floor completion when there are no requirements."""
        self.floor_manager.current_floor = 3  # No requirements for floor 3
        result = self.handler.is_floor_complete(
            npcs_completed=set(),
            npc_data={},
        )
        self.assertTrue(result)


if __name__ == "__main__":
    unittest.main()
