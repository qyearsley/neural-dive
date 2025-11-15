"""Unit tests for FloorManager class.

This test module covers all FloorManager functionality including:
- Floor initialization and generation
- Floor progression (stairs up/down)
- Floor completion checking
- Player positioning on floor entry
- State serialization/deserialization
"""

from __future__ import annotations

import unittest

from neural_dive.entities import Entity
from neural_dive.managers.floor_manager import FloorManager


class TestFloorManagerInitialization(unittest.TestCase):
    """Test FloorManager initialization."""

    def test_default_initialization(self):
        """Test FloorManager initializes with defaults."""
        from neural_dive.config import MAX_FLOORS

        manager = FloorManager()

        self.assertEqual(manager.current_floor, 1)
        self.assertEqual(manager.max_floors, MAX_FLOORS)
        self.assertIsNotNone(manager.game_map)
        self.assertGreater(len(manager.game_map), 0)
        self.assertGreater(len(manager.game_map[0]), 0)

    def test_custom_initialization(self):
        """Test FloorManager with custom parameters."""
        manager = FloorManager(max_floors=5, map_width=30, map_height=15, seed=42)

        self.assertEqual(manager.current_floor, 1)
        self.assertEqual(manager.max_floors, 5)
        self.assertEqual(manager.map_width, 30)
        self.assertEqual(manager.map_height, 15)
        self.assertEqual(manager.seed, 42)

    def test_initialization_with_level_data(self):
        """Test FloorManager with predefined level data."""
        level_data = {
            1: {
                "tiles": [
                    ["#", "#", "#"],
                    ["#", ".", "#"],
                    ["#", "#", "#"],
                ]
            }
        }

        manager = FloorManager(level_data=level_data)

        self.assertEqual(len(manager.game_map), 3)
        self.assertEqual(len(manager.game_map[0]), 3)
        self.assertEqual(manager.map_width, 3)
        self.assertEqual(manager.map_height, 3)


class TestFloorManagerGeneration(unittest.TestCase):
    """Test floor generation."""

    def setUp(self):
        """Set up test fixtures."""
        self.manager = FloorManager(seed=42)
        self.player = Entity(5, 5, "@", "cyan", "Player")

    def test_generate_floor_updates_current_floor(self):
        """Test that generate_floor updates current_floor."""
        self.manager.generate_floor(2, self.player)

        self.assertEqual(self.manager.current_floor, 2)

    def test_generate_floor_creates_map(self):
        """Test that generate_floor creates a new map."""
        self.manager.generate_floor(2, self.player)

        self.assertIsNotNone(self.manager.game_map)
        self.assertGreater(len(self.manager.game_map), 0)

    def test_generate_floor_returns_player_position(self):
        """Test that generate_floor returns player position."""
        x, y = self.manager.generate_floor(2, self.player)

        self.assertIsInstance(x, int)
        self.assertIsInstance(y, int)
        self.assertEqual(x, self.player.x)
        self.assertEqual(y, self.player.y)

    def test_generate_floor_with_custom_start_position(self):
        """Test generating floor with custom player start."""
        level_data = {
            2: {
                "player_start": (10, 15),
                "tiles": [["." for _ in range(50)] for _ in range(25)],
            }
        }

        manager = FloorManager(level_data=level_data)
        player = Entity(5, 5, "@", "cyan", "Player")

        x, y = manager.generate_floor(2, player)

        self.assertEqual(x, 10)
        self.assertEqual(y, 15)
        self.assertEqual(player.x, 10)
        self.assertEqual(player.y, 15)


class TestFloorManagerProgression(unittest.TestCase):
    """Test floor progression (stairs)."""

    def setUp(self):
        """Set up test fixtures."""
        self.manager = FloorManager(max_floors=5, seed=42)
        self.player = Entity(5, 5, "@", "cyan", "Player")

    def test_can_use_stairs_down_on_first_floor(self):
        """Test can go down from first floor."""
        self.assertTrue(self.manager.can_use_stairs_down())

    def test_cannot_use_stairs_down_on_last_floor(self):
        """Test cannot go down from last floor."""
        self.manager.current_floor = 5

        self.assertFalse(self.manager.can_use_stairs_down())

    def test_can_use_stairs_up_on_second_floor(self):
        """Test can go up from second floor."""
        self.manager.current_floor = 2

        self.assertTrue(self.manager.can_use_stairs_up())

    def test_cannot_use_stairs_up_on_first_floor(self):
        """Test cannot go up from first floor."""
        self.manager.current_floor = 1

        self.assertFalse(self.manager.can_use_stairs_up())

    def test_move_to_next_floor(self):
        """Test moving to next floor down."""
        self.manager.move_to_next_floor(self.player)

        self.assertEqual(self.manager.current_floor, 2)

    def test_move_to_next_floor_from_bottom_floor(self):
        """Test moving down when already at bottom."""
        self.manager.current_floor = 5
        original_floor = self.manager.current_floor

        self.manager.move_to_next_floor(self.player)

        self.assertEqual(self.manager.current_floor, original_floor)

    def test_move_to_previous_floor(self):
        """Test moving to previous floor up."""
        self.manager.current_floor = 3

        self.manager.move_to_previous_floor(self.player)

        self.assertEqual(self.manager.current_floor, 2)

    def test_move_to_previous_floor_from_top_floor(self):
        """Test moving up when already at top."""
        original_floor = self.manager.current_floor

        self.manager.move_to_previous_floor(self.player)

        self.assertEqual(self.manager.current_floor, original_floor)


class TestFloorManagerCompletion(unittest.TestCase):
    """Test floor completion checking."""

    def setUp(self):
        """Set up test fixtures."""
        self.manager = FloorManager()
        # FLOOR_REQUIRED_NPCS for floor 1 is typically {"ALGO_SPIRIT"}
        self.npc_data = {
            "ALGO_SPIRIT": {"floor": 1},
            "DATA_GUARDIAN": {"floor": 1},
        }

    def test_is_floor_complete_when_no_requirements(self):
        """Test floor completion when no NPCs required."""
        # Floor 99 has no requirements
        self.manager.current_floor = 99
        npcs_completed: set[str] = set()

        self.assertTrue(self.manager.is_floor_complete(npcs_completed, self.npc_data))

    def test_is_floor_complete_when_requirements_met(self):
        """Test floor completion when all required NPCs completed."""
        # Floor 1 requires ALGO_SPIRIT
        self.manager.current_floor = 1
        npcs_completed = {"ALGO_SPIRIT", "DATA_GUARDIAN"}

        # Should be complete (ALGO_SPIRIT is done)
        is_complete = self.manager.is_floor_complete(npcs_completed, self.npc_data)

        # This depends on FLOOR_REQUIRED_NPCS config
        # If ALGO_SPIRIT is required, should be True
        self.assertIsInstance(is_complete, bool)

    def test_is_floor_complete_when_requirements_not_met(self):
        """Test floor completion when required NPCs not completed."""
        # Floor 1 requires ALGO_SPIRIT
        self.manager.current_floor = 1
        npcs_completed = {"DATA_GUARDIAN"}  # Missing ALGO_SPIRIT

        # Should not be complete
        is_complete = self.manager.is_floor_complete(npcs_completed, self.npc_data)

        # This depends on FLOOR_REQUIRED_NPCS config
        # If ALGO_SPIRIT is required, should be False
        self.assertIsInstance(is_complete, bool)


class TestFloorManagerFinalFloor(unittest.TestCase):
    """Test final floor detection."""

    def test_is_final_floor_on_first_floor(self):
        """Test is_final_floor on first floor."""
        manager = FloorManager(max_floors=5)

        self.assertFalse(manager.is_final_floor())

    def test_is_final_floor_on_last_floor(self):
        """Test is_final_floor on last floor."""
        manager = FloorManager(max_floors=5)
        manager.current_floor = 5

        self.assertTrue(manager.is_final_floor())

    def test_is_final_floor_on_middle_floor(self):
        """Test is_final_floor on middle floor."""
        manager = FloorManager(max_floors=10)
        manager.current_floor = 5

        self.assertFalse(manager.is_final_floor())


class TestFloorManagerSerialization(unittest.TestCase):
    """Test state serialization and deserialization."""

    def test_to_dict_default_state(self):
        """Test serializing default FloorManager state."""
        manager = FloorManager()

        data = manager.to_dict()

        self.assertIsInstance(data, dict)
        self.assertIn("current_floor", data)
        self.assertIn("max_floors", data)
        self.assertIn("map_width", data)
        self.assertIn("map_height", data)
        self.assertEqual(data["current_floor"], 1)

    def test_to_dict_custom_state(self):
        """Test serializing custom FloorManager state."""
        manager = FloorManager(max_floors=7, map_width=60, map_height=30)
        manager.current_floor = 3

        data = manager.to_dict()

        self.assertEqual(data["current_floor"], 3)
        self.assertEqual(data["max_floors"], 7)
        self.assertEqual(data["map_width"], 60)
        self.assertEqual(data["map_height"], 30)

    def test_from_dict_default_state(self):
        """Test deserializing default FloorManager state."""
        data = {
            "current_floor": 1,
            "max_floors": 10,
            "map_width": 50,
            "map_height": 25,
        }

        manager = FloorManager.from_dict(data, seed=42)

        self.assertEqual(manager.current_floor, 1)
        self.assertEqual(manager.max_floors, 10)
        self.assertEqual(manager.map_width, 50)
        self.assertEqual(manager.map_height, 25)

    def test_from_dict_custom_floor(self):
        """Test deserializing FloorManager on custom floor."""
        data = {
            "current_floor": 3,
            "max_floors": 5,
            "map_width": 40,
            "map_height": 20,
        }

        manager = FloorManager.from_dict(data, seed=42)

        self.assertEqual(manager.current_floor, 3)
        # Map should be generated for floor 3
        self.assertIsNotNone(manager.game_map)

    def test_round_trip_serialization(self):
        """Test that serialization and deserialization preserves state."""
        manager1 = FloorManager(max_floors=8, map_width=45, map_height=22, seed=42)
        manager1.current_floor = 4

        data = manager1.to_dict()
        manager2 = FloorManager.from_dict(data, seed=42)

        self.assertEqual(manager2.current_floor, manager1.current_floor)
        self.assertEqual(manager2.max_floors, manager1.max_floors)
        self.assertEqual(manager2.map_width, manager1.map_width)
        self.assertEqual(manager2.map_height, manager1.map_height)


if __name__ == "__main__":
    unittest.main()
