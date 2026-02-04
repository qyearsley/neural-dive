"""Tests for MovementController."""

import unittest

from neural_dive.entities import Entity, Stairs
from neural_dive.items import CodeSnippet, HintToken, ItemPickup
from neural_dive.managers.movement_controller import MovementController, MoveResult
from neural_dive.managers.player_manager import PlayerManager


class TestIsWalkable(unittest.TestCase):
    """Test is_walkable collision detection."""

    def setUp(self):
        """Set up test fixtures."""
        # Simple 5x5 map with walls around edges
        self.game_map = [
            ["#", "#", "#", "#", "#"],
            ["#", ".", ".", ".", "#"],
            ["#", ".", "#", ".", "#"],
            ["#", ".", ".", ".", "#"],
            ["#", "#", "#", "#", "#"],
        ]
        self.controller = MovementController()

    def test_empty_floor_is_walkable(self):
        """Test that empty floor tiles are walkable."""
        self.assertTrue(self.controller.is_walkable(1, 1, self.game_map))
        self.assertTrue(self.controller.is_walkable(2, 1, self.game_map))

    def test_wall_is_not_walkable(self):
        """Test that walls are not walkable."""
        self.assertFalse(self.controller.is_walkable(0, 0, self.game_map))
        self.assertFalse(self.controller.is_walkable(2, 2, self.game_map))

    def test_out_of_bounds_is_not_walkable(self):
        """Test that out of bounds positions are not walkable."""
        self.assertFalse(self.controller.is_walkable(-1, 0, self.game_map))
        self.assertFalse(self.controller.is_walkable(0, -1, self.game_map))
        self.assertFalse(self.controller.is_walkable(10, 10, self.game_map))

    def test_edge_positions(self):
        """Test edge cases at map boundaries."""
        # Top-left corner (wall)
        self.assertFalse(self.controller.is_walkable(0, 0, self.game_map))
        # Bottom-right corner (wall)
        self.assertFalse(self.controller.is_walkable(4, 4, self.game_map))


class TestMovePlayer(unittest.TestCase):
    """Test player movement."""

    def setUp(self):
        """Set up test fixtures."""
        self.game_map = [
            ["#", "#", "#", "#", "#"],
            ["#", ".", ".", ".", "#"],
            ["#", ".", "#", ".", "#"],
            ["#", ".", ".", ".", "#"],
            ["#", "#", "#", "#", "#"],
        ]
        self.controller = MovementController()
        self.player = Entity(1, 1, "@", "cyan", "Player")
        self.player_manager = PlayerManager(coherence=100, max_coherence=100)
        self.item_pickups: list[ItemPickup] = []
        self.stairs: list[Stairs] = []

    def test_move_to_empty_space(self):
        """Test moving to an empty space."""
        result = self.controller.move_player(
            player=self.player,
            dx=1,
            dy=0,
            game_map=self.game_map,
            item_pickups=self.item_pickups,
            stairs=self.stairs,
            player_manager=self.player_manager,
            is_in_conversation=False,
        )

        self.assertTrue(result.success)
        self.assertEqual(result.message, "")
        self.assertEqual(result.old_position, (1, 1))
        self.assertEqual(self.player.x, 2)
        self.assertEqual(self.player.y, 1)

    def test_move_blocked_by_wall(self):
        """Test that moving into a wall fails."""
        # Try to move up into wall from (1, 1) -> (1, 0) which is a wall
        result = self.controller.move_player(
            player=self.player,
            dx=0,
            dy=-1,
            game_map=self.game_map,
            item_pickups=self.item_pickups,
            stairs=self.stairs,
            player_manager=self.player_manager,
            is_in_conversation=False,
        )

        self.assertFalse(result.success)
        self.assertEqual(result.message, "Blocked by firewall!")
        self.assertIsNone(result.old_position)
        # Player position unchanged
        self.assertEqual(self.player.x, 1)
        self.assertEqual(self.player.y, 1)

    def test_move_blocked_during_conversation(self):
        """Test that movement is blocked during conversations."""
        result = self.controller.move_player(
            player=self.player,
            dx=1,
            dy=0,
            game_map=self.game_map,
            item_pickups=self.item_pickups,
            stairs=self.stairs,
            player_manager=self.player_manager,
            is_in_conversation=True,
        )

        self.assertFalse(result.success)
        self.assertIn("conversation", result.message)
        self.assertIsNone(result.old_position)
        # Player position unchanged
        self.assertEqual(self.player.x, 1)
        self.assertEqual(self.player.y, 1)

    def test_move_picks_up_item(self):
        """Test that moving onto an item picks it up."""
        # Place hint token at (2, 1) (one move to the right from (1, 1))
        hint = HintToken()
        pickup = ItemPickup(2, 1, hint)
        self.item_pickups.append(pickup)

        result = self.controller.move_player(
            player=self.player,
            dx=1,
            dy=0,
            game_map=self.game_map,
            item_pickups=self.item_pickups,
            stairs=self.stairs,
            player_manager=self.player_manager,
            is_in_conversation=False,
        )

        self.assertTrue(result.success)
        self.assertEqual(result.message, "Picked up Hint Token!")
        self.assertEqual(result.old_position, (1, 1))
        # Item removed from pickups
        self.assertEqual(len(self.item_pickups), 0)
        # Item added to inventory
        self.assertEqual(len(self.player_manager.inventory), 1)

    def test_move_item_pickup_full_inventory(self):
        """Test item pickup when inventory is full."""
        # Fill inventory (max is 20)
        for _ in range(20):
            self.player_manager.add_item(HintToken())

        # Place item at (2, 1) (one move to the right from (1, 1))
        hint = HintToken()
        pickup = ItemPickup(2, 1, hint)
        self.item_pickups.append(pickup)

        result = self.controller.move_player(
            player=self.player,
            dx=1,
            dy=0,
            game_map=self.game_map,
            item_pickups=self.item_pickups,
            stairs=self.stairs,
            player_manager=self.player_manager,
            is_in_conversation=False,
        )

        self.assertTrue(result.success)
        self.assertEqual(result.message, "Inventory full!")
        # Item not removed from pickups
        self.assertEqual(len(self.item_pickups), 1)
        # Inventory still at max
        self.assertEqual(len(self.player_manager.inventory), 20)

    def test_move_onto_stairs_shows_hint(self):
        """Test that moving onto stairs shows a hint message."""
        # Place stairs at (2, 1) (one move to the right from (1, 1))
        stair = Stairs(2, 1, "down")
        self.stairs.append(stair)

        result = self.controller.move_player(
            player=self.player,
            dx=1,
            dy=0,
            game_map=self.game_map,
            item_pickups=self.item_pickups,
            stairs=self.stairs,
            player_manager=self.player_manager,
            is_in_conversation=False,
        )

        self.assertTrue(result.success)
        self.assertIn("stairs down", result.message)
        self.assertIn("Space", result.message)
        self.assertEqual(result.old_position, (1, 1))

    def test_move_onto_stairs_up(self):
        """Test stairs hint for upward stairs."""
        # Place stairs up at (2, 1) (one move to the right from (1, 1))
        stair = Stairs(2, 1, "up")
        self.stairs.append(stair)

        result = self.controller.move_player(
            player=self.player,
            dx=1,
            dy=0,
            game_map=self.game_map,
            item_pickups=self.item_pickups,
            stairs=self.stairs,
            player_manager=self.player_manager,
            is_in_conversation=False,
        )

        self.assertTrue(result.success)
        self.assertIn("stairs up", result.message)

    def test_multiple_moves_update_old_position(self):
        """Test that old_position is updated correctly across moves."""
        # First move: (1, 1) -> (2, 1)
        result1 = self.controller.move_player(
            player=self.player,
            dx=1,
            dy=0,
            game_map=self.game_map,
            item_pickups=self.item_pickups,
            stairs=self.stairs,
            player_manager=self.player_manager,
            is_in_conversation=False,
        )
        self.assertEqual(result1.old_position, (1, 1))

        # Second move: (2, 1) -> (3, 1)
        result2 = self.controller.move_player(
            player=self.player,
            dx=1,
            dy=0,
            game_map=self.game_map,
            item_pickups=self.item_pickups,
            stairs=self.stairs,
            player_manager=self.player_manager,
            is_in_conversation=False,
        )
        self.assertEqual(result2.old_position, (2, 1))

    def test_move_with_code_snippet(self):
        """Test picking up a code snippet item."""
        snippet = CodeSnippet(
            name="Test Snippet",
            topic="testing",
            content="def test(): pass",
        )
        pickup = ItemPickup(2, 1, snippet)
        self.item_pickups.append(pickup)

        result = self.controller.move_player(
            player=self.player,
            dx=1,
            dy=0,
            game_map=self.game_map,
            item_pickups=self.item_pickups,
            stairs=self.stairs,
            player_manager=self.player_manager,
            is_in_conversation=False,
        )

        self.assertTrue(result.success)
        self.assertEqual(result.message, "Picked up Test Snippet!")
        self.assertEqual(len(self.item_pickups), 0)


class TestMoveResultDataclass(unittest.TestCase):
    """Test MoveResult dataclass."""

    def test_move_result_creation(self):
        """Test creating MoveResult instances."""
        result = MoveResult(success=True, message="Success!", old_position=(1, 2))
        self.assertTrue(result.success)
        self.assertEqual(result.message, "Success!")
        self.assertEqual(result.old_position, (1, 2))

    def test_move_result_default_old_position(self):
        """Test that old_position defaults to None."""
        result = MoveResult(success=False, message="Failed")
        self.assertFalse(result.success)
        self.assertEqual(result.message, "Failed")
        self.assertIsNone(result.old_position)


if __name__ == "__main__":
    unittest.main()
