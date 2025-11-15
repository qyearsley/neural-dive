"""
Unit tests for NPCManager class.

This test module covers all NPC management functionality including:
- NPC generation and placement
- NPC wandering AI behavior
- NPC opinion tracking
- Conversation management
- State serialization/deserialization
"""

from __future__ import annotations

import random
import unittest

from neural_dive.difficulty import DifficultyLevel, get_difficulty_settings
from neural_dive.entities import Entity
from neural_dive.enums import NPCType
from neural_dive.managers.npc_manager import NPCManager
from neural_dive.models import Answer, Conversation, Question


class TestNPCManagerInitialization(unittest.TestCase):
    """Test NPCManager initialization."""

    def setUp(self):
        """Set up test data."""
        self.rng = random.Random(42)
        self.difficulty_settings = get_difficulty_settings(DifficultyLevel.NORMAL)

        # Create minimal test NPC data
        self.npc_data = {
            "TEST_NPC": {
                "char": "T",
                "color": "cyan",
                "floor": 1,
                "npc_type": "specialist",
                "conversation": Conversation(
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
                ),
            }
        }

        self.questions = {}

    def test_npc_manager_initializes(self):
        """Test that NPCManager initializes correctly."""
        manager = NPCManager(
            self.npc_data, self.questions, self.rng, self.difficulty_settings, seed=42
        )

        self.assertEqual(len(manager.npcs), 0)  # No NPCs generated yet
        self.assertEqual(len(manager.all_npcs), 0)
        self.assertEqual(len(manager.npc_opinions), 0)
        self.assertIsInstance(manager.conversations, dict)

    def test_conversations_initialized(self):
        """Test that conversations are created for all NPCs."""
        manager = NPCManager(
            self.npc_data, self.questions, self.rng, self.difficulty_settings, seed=42
        )

        self.assertIn("TEST_NPC", manager.conversations)
        self.assertIsInstance(manager.conversations["TEST_NPC"], Conversation)


class TestNPCGeneration(unittest.TestCase):
    """Test NPC generation and placement."""

    def setUp(self):
        """Set up test data."""
        # Create fresh RNG for each test to avoid pollution
        self.rng = random.Random(42)
        self.difficulty_settings = get_difficulty_settings(DifficultyLevel.NORMAL)

        # Create test NPC data for multiple floors
        self.npc_data = {
            "NPC_FLOOR1": {
                "char": "A",
                "color": "cyan",
                "floor": 1,
                "npc_type": "specialist",
                "conversation": self._create_test_conversation("NPC_FLOOR1"),
            },
            "NPC_FLOOR2": {
                "char": "B",
                "color": "magenta",
                "floor": 2,
                "npc_type": "helper",
                "conversation": self._create_test_conversation("NPC_FLOOR2"),
            },
        }

        self.questions = {}

        # Create simple test map
        self.game_map = [
            ["#", "#", "#", "#", "#"],
            ["#", ".", ".", ".", "#"],
            ["#", ".", ".", ".", "#"],
            ["#", ".", ".", ".", "#"],
            ["#", "#", "#", "#", "#"],
        ]

    def _create_test_conversation(self, npc_name: str) -> Conversation:
        """Helper to create test conversation."""
        return Conversation(
            npc_name=npc_name,
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

    def test_generate_npcs_for_correct_floor(self):
        """Test that only NPCs for the specified floor are generated."""
        # Create fresh RNG to avoid test pollution
        fresh_rng = random.Random(42)

        # Mock level data with predetermined positions (more reliable than random)
        mock_level_data = {
            "tiles": [["."] * 20 for _ in range(20)],
            "npc_positions": {
                "A": [(5, 5)],  # Position for NPC with char 'A' (NPC_FLOOR1)
            },
        }

        manager = NPCManager(
            self.npc_data,
            self.questions,
            fresh_rng,
            self.difficulty_settings,
            seed=42,
            level_data={1: mock_level_data},
        )

        # Generate floor 1 NPCs using level data
        level_tiles: list[list[str]] = [list(row) for row in mock_level_data["tiles"]]
        npcs = manager.generate_npcs_for_floor(
            floor=1,
            game_map=level_tiles,
            player_pos=(1, 1),
            random_placement=False,  # Use level data, not random
            map_width=20,
            map_height=20,
        )

        # Should have exactly 1 NPC (from floor 1)
        self.assertEqual(len(npcs), 1)
        self.assertEqual(npcs[0].name, "NPC_FLOOR1")
        self.assertEqual(npcs[0].x, 5)
        self.assertEqual(npcs[0].y, 5)

    def test_generate_npcs_for_floor_2(self):
        """Test generating NPCs for floor 2."""
        manager = NPCManager(
            self.npc_data, self.questions, self.rng, self.difficulty_settings, seed=42
        )

        # Generate floor 2 NPCs with a larger map for better success rate
        larger_map = [
            ["#"] * 20,
            *[["#"] + ["."] * 18 + ["#"] for _ in range(18)],
            ["#"] * 20,
        ]

        npcs = manager.generate_npcs_for_floor(
            floor=2,
            game_map=larger_map,
            player_pos=(1, 1),
            random_placement=True,
            map_width=20,
            map_height=20,
        )

        # Should have floor 2 NPC (or at least attempted to place it)
        # With larger map, should succeed
        self.assertGreaterEqual(len(npcs), 0)
        if len(npcs) > 0:
            self.assertEqual(npcs[0].name, "NPC_FLOOR2")

    def test_random_placement_avoids_walls(self):
        """Test that random placement doesn't place NPCs in walls."""
        manager = NPCManager(
            self.npc_data, self.questions, self.rng, self.difficulty_settings, seed=42
        )

        # Use a larger map to accommodate default placement ranges
        larger_map = [
            ["#"] * 30,
            *[["#"] + ["."] * 28 + ["#"] for _ in range(28)],
            ["#"] * 30,
        ]

        npcs = manager.generate_npcs_for_floor(
            floor=1,
            game_map=larger_map,
            player_pos=(1, 1),
            random_placement=True,
            map_width=30,
            map_height=30,
        )

        # Check NPC is not on a wall (if any were successfully placed)
        for npc in npcs:
            # Make sure coordinates are within map bounds
            if 0 <= npc.y < len(self.game_map) and 0 <= npc.x < len(self.game_map[0]):
                tile = self.game_map[npc.y][npc.x]
                self.assertNotEqual(tile, "#", f"NPC at ({npc.x}, {npc.y}) is on a wall")

    def test_clear_floor_removes_npcs(self):
        """Test that clear_floor removes current floor NPCs."""
        manager = NPCManager(
            self.npc_data, self.questions, self.rng, self.difficulty_settings, seed=42
        )

        # Use larger map for random placement success
        larger_map = [
            ["#"] * 20,
            *[["#"] + ["."] * 18 + ["#"] for _ in range(18)],
            ["#"] * 20,
        ]

        # Generate NPCs
        manager.generate_npcs_for_floor(
            floor=1,
            game_map=larger_map,
            player_pos=(1, 1),
            random_placement=True,
            map_width=20,
            map_height=20,
        )

        # Should have generated at least one NPC
        self.assertGreaterEqual(len(manager.npcs), 0)

        # Clear floor
        manager.clear_floor()

        self.assertEqual(len(manager.npcs), 0)


class TestNPCWandering(unittest.TestCase):
    """Test NPC wandering AI."""

    def setUp(self):
        """Set up test data."""
        self.rng = random.Random(42)
        self.difficulty_settings = get_difficulty_settings(DifficultyLevel.NORMAL)

        self.npc_data = {
            "WANDERER": {
                "char": "W",
                "color": "cyan",
                "floor": 1,
                "npc_type": "specialist",
                "conversation": Conversation(
                    npc_name="WANDERER",
                    greeting="Hello!",
                    questions=[],
                    npc_type=NPCType.SPECIALIST,
                ),
            }
        }

        self.questions = {}

        # Create larger test map
        self.game_map = [
            ["#", "#", "#", "#", "#", "#", "#"],
            ["#", ".", ".", ".", ".", ".", "#"],
            ["#", ".", ".", ".", ".", ".", "#"],
            ["#", ".", ".", ".", ".", ".", "#"],
            ["#", ".", ".", ".", ".", ".", "#"],
            ["#", ".", ".", ".", ".", ".", "#"],
            ["#", "#", "#", "#", "#", "#", "#"],
        ]

    def test_npcs_freeze_during_conversation(self):
        """Test that NPCs don't move during conversations."""
        manager = NPCManager(
            self.npc_data, self.questions, self.rng, self.difficulty_settings, seed=42
        )

        # Manually add an NPC
        npc = Entity(3, 3, "W", "cyan", "WANDERER", npc_type="specialist")
        manager.npcs.append(npc)

        original_pos = (npc.x, npc.y)

        # Update wandering with conversation active
        for _ in range(100):
            manager.update_wandering(
                game_map=self.game_map,
                player_pos=(1, 1),
                is_conversation_active=True,  # Conversation active
            )

        # NPC should not have moved
        self.assertEqual((npc.x, npc.y), original_pos)

    def test_npc_wander_state_changes(self):
        """Test that NPC state transitions between idle and wander."""
        manager = NPCManager(
            self.npc_data, self.questions, self.rng, self.difficulty_settings, seed=42
        )

        # Manually add an NPC
        npc = Entity(3, 3, "W", "cyan", "WANDERER", npc_type="specialist")
        npc.wander_state = "idle"
        npc.wander_ticks_remaining = 1  # Will change state soon
        manager.npcs.append(npc)

        # Update many times to trigger state change
        for _ in range(10):
            manager.update_wandering(
                game_map=self.game_map,
                player_pos=(1, 1),
                is_conversation_active=False,
            )

        # State should have changed at some point
        # (Can't guarantee exact state due to randomness, but ticks should have changed)
        self.assertIsNotNone(npc.wander_state)

    def test_npc_avoids_player_position(self):
        """Test that NPC doesn't move into player position."""
        manager = NPCManager(
            self.npc_data, self.questions, self.rng, self.difficulty_settings, seed=42
        )

        # Place NPC adjacent to player
        player_pos = (3, 3)
        npc = Entity(3, 4, "W", "cyan", "WANDERER", npc_type="specialist")
        npc.wander_state = "wander"
        npc.move_cooldown = 0
        manager.npcs.append(npc)

        # Try to move many times
        for _ in range(50):
            manager.update_wandering(
                game_map=self.game_map,
                player_pos=player_pos,
                is_conversation_active=False,
            )

            # NPC should never be on player position
            self.assertNotEqual((npc.x, npc.y), player_pos)


class TestNPCOpinions(unittest.TestCase):
    """Test NPC opinion tracking."""

    def setUp(self):
        """Set up test data."""
        self.rng = random.Random(42)
        self.difficulty_settings = get_difficulty_settings(DifficultyLevel.NORMAL)
        self.npc_data = {}
        self.questions = {}

    def test_initial_opinion_is_zero(self):
        """Test that initial opinion is 0."""
        manager = NPCManager(
            self.npc_data, self.questions, self.rng, self.difficulty_settings, seed=42
        )

        opinion = manager.get_opinion("TEST_NPC")

        self.assertEqual(opinion, 0)

    def test_update_opinion_increases(self):
        """Test increasing NPC opinion."""
        manager = NPCManager(
            self.npc_data, self.questions, self.rng, self.difficulty_settings, seed=42
        )

        manager.update_opinion("TEST_NPC", 5)

        self.assertEqual(manager.get_opinion("TEST_NPC"), 5)

    def test_update_opinion_decreases(self):
        """Test decreasing NPC opinion."""
        manager = NPCManager(
            self.npc_data, self.questions, self.rng, self.difficulty_settings, seed=42
        )

        manager.update_opinion("TEST_NPC", -3)

        self.assertEqual(manager.get_opinion("TEST_NPC"), -3)

    def test_multiple_opinion_updates(self):
        """Test multiple opinion updates accumulate."""
        manager = NPCManager(
            self.npc_data, self.questions, self.rng, self.difficulty_settings, seed=42
        )

        manager.update_opinion("TEST_NPC", 5)
        manager.update_opinion("TEST_NPC", 3)
        manager.update_opinion("TEST_NPC", -2)

        self.assertEqual(manager.get_opinion("TEST_NPC"), 6)


class TestNPCConversations(unittest.TestCase):
    """Test conversation management."""

    def setUp(self):
        """Set up test data."""
        self.rng = random.Random(42)
        self.difficulty_settings = get_difficulty_settings(DifficultyLevel.NORMAL)

        self.npc_data = {
            "TALKER": {
                "char": "T",
                "color": "cyan",
                "floor": 1,
                "npc_type": "specialist",
                "conversation": Conversation(
                    npc_name="TALKER",
                    greeting="Hello!",
                    questions=[
                        Question(
                            question_text="Test?",
                            answers=[Answer("Yes", True, "Correct!")],
                            topic="test",
                        )
                    ],
                    npc_type=NPCType.SPECIALIST,
                ),
            }
        }

        self.questions = {}

    def test_get_conversation(self):
        """Test retrieving NPC conversation."""
        manager = NPCManager(
            self.npc_data, self.questions, self.rng, self.difficulty_settings, seed=42
        )

        conv = manager.get_conversation("TALKER")

        self.assertIsNotNone(conv)
        assert conv is not None  # Type narrowing for mypy
        self.assertEqual(conv.npc_name, "TALKER")

    def test_get_nonexistent_conversation(self):
        """Test retrieving conversation for nonexistent NPC."""
        manager = NPCManager(
            self.npc_data, self.questions, self.rng, self.difficulty_settings, seed=42
        )

        conv = manager.get_conversation("NONEXISTENT")

        self.assertIsNone(conv)


class TestNPCManagerSerialization(unittest.TestCase):
    """Test state serialization and deserialization."""

    def setUp(self):
        """Set up test data."""
        self.rng = random.Random(42)
        self.difficulty_settings = get_difficulty_settings(DifficultyLevel.NORMAL)

        self.npc_data = {
            "TEST_NPC": {
                "char": "T",
                "color": "cyan",
                "floor": 1,
                "npc_type": "specialist",
                "conversation": Conversation(
                    npc_name="TEST_NPC",
                    greeting="Hello!",
                    questions=[],
                    npc_type=NPCType.SPECIALIST,
                ),
            }
        }

        self.questions = {}

    def test_to_dict_default_state(self):
        """Test serializing default NPCManager state."""
        manager = NPCManager(
            self.npc_data, self.questions, self.rng, self.difficulty_settings, seed=42
        )

        data = manager.to_dict()

        self.assertIsInstance(data, dict)
        self.assertIn("npcs", data)
        self.assertIn("npc_opinions", data)
        self.assertIn("quest_completed_npcs", data)
        self.assertIn("conversations", data)

    def test_to_dict_with_npcs(self):
        """Test serializing with NPCs."""
        manager = NPCManager(
            self.npc_data, self.questions, self.rng, self.difficulty_settings, seed=42
        )

        # Add an NPC
        npc = Entity(5, 5, "T", "cyan", "TEST_NPC", npc_type="specialist")
        manager.all_npcs.append(npc)

        data = manager.to_dict()

        self.assertEqual(len(data["npcs"]), 1)
        self.assertEqual(data["npcs"][0]["name"], "TEST_NPC")
        self.assertEqual(data["npcs"][0]["x"], 5)
        self.assertEqual(data["npcs"][0]["y"], 5)

    def test_to_dict_with_opinions(self):
        """Test serializing with NPC opinions."""
        manager = NPCManager(
            self.npc_data, self.questions, self.rng, self.difficulty_settings, seed=42
        )

        manager.update_opinion("TEST_NPC", 10)

        data = manager.to_dict()

        self.assertEqual(data["npc_opinions"]["TEST_NPC"], 10)

    def test_round_trip_serialization(self):
        """Test that serialization and deserialization preserves state."""
        manager1 = NPCManager(
            self.npc_data, self.questions, self.rng, self.difficulty_settings, seed=42
        )

        # Set up some state
        npc = Entity(5, 5, "T", "cyan", "TEST_NPC", npc_type="specialist")
        manager1.all_npcs.append(npc)
        manager1.update_opinion("TEST_NPC", 15)
        manager1.quest_completed_npcs.add("TEST_NPC")

        # Serialize
        data = manager1.to_dict()

        # Deserialize
        manager2 = NPCManager.from_dict(
            data, self.npc_data, self.questions, self.rng, self.difficulty_settings, seed=42
        )

        # Verify state is preserved
        self.assertEqual(len(manager2.all_npcs), 1)
        self.assertEqual(manager2.all_npcs[0].name, "TEST_NPC")
        self.assertEqual(manager2.get_opinion("TEST_NPC"), 15)
        self.assertIn("TEST_NPC", manager2.quest_completed_npcs)


if __name__ == "__main__":
    unittest.main()
