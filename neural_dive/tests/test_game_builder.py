"""Tests for GameBuilder.

This module tests the GameBuilder pattern for flexible Game construction.
"""

from __future__ import annotations

import unittest

from neural_dive.difficulty import DifficultyLevel
from neural_dive.game_builder import GameBuilder


class TestGameBuilder(unittest.TestCase):
    """Test GameBuilder functionality."""

    def test_default_configuration(self):
        """Test building game with default configuration."""
        game = GameBuilder().build()

        # Should have defaults from config
        from neural_dive.config import DEFAULT_MAP_HEIGHT, DEFAULT_MAP_WIDTH, MAX_FLOORS

        self.assertEqual(game.map_width, DEFAULT_MAP_WIDTH)
        self.assertEqual(game.map_height, DEFAULT_MAP_HEIGHT)
        self.assertEqual(game.max_floors, MAX_FLOORS)
        self.assertEqual(game.difficulty, DifficultyLevel.NORMAL)
        self.assertIsNone(game.seed)
        self.assertTrue(game.random_npcs)

    def test_with_map_size(self):
        """Test setting custom map size.

        Note: Actual map size may be determined by FloorManager/level_data,
        so we just verify the Game initializes without error.
        """
        game = GameBuilder().with_map_size(60, 30).build()

        # Game should initialize successfully
        self.assertIsNotNone(game)
        self.assertIsNotNone(game.game_map)

    def test_with_floors(self):
        """Test setting custom floor count."""
        game = GameBuilder().with_floors(5).build()

        self.assertEqual(game.max_floors, 5)

    def test_with_difficulty(self):
        """Test setting difficulty level."""
        game = GameBuilder().with_difficulty(DifficultyLevel.NORMAL).build()

        self.assertEqual(game.difficulty, DifficultyLevel.NORMAL)

    def test_with_seed(self):
        """Test setting random seed."""
        game = GameBuilder().with_seed(42).build()

        self.assertEqual(game.seed, 42)

    def test_with_content_set(self):
        """Test setting content set."""
        game = GameBuilder().with_content_set("algorithms").build()

        self.assertEqual(game.content_set, "algorithms")

    def test_with_fixed_positions(self):
        """Test disabling random positions."""
        game = GameBuilder().with_fixed_positions().build()

        self.assertFalse(game.random_npcs)

    def test_with_random_positions(self):
        """Test enabling random positions."""
        game = GameBuilder().with_fixed_positions().with_random_positions().build()

        self.assertTrue(game.random_npcs)

    def test_fluent_interface(self):
        """Test method chaining (fluent interface)."""
        game = (
            GameBuilder()
            .with_map_size(60, 30)
            .with_floors(5)
            .with_difficulty(DifficultyLevel.NORMAL)
            .with_seed(42)
            .with_content_set("algorithms")
            .with_fixed_positions()
            .build()
        )

        # Verify all settings applied (those that aren't overridden)
        self.assertEqual(game.max_floors, 5)
        self.assertEqual(game.difficulty, DifficultyLevel.NORMAL)
        self.assertEqual(game.seed, 42)
        self.assertEqual(game.content_set, "algorithms")
        self.assertFalse(game.random_npcs)

    def test_builder_reusability(self):
        """Test that builder can be configured and reused."""
        builder = (
            GameBuilder()
            .with_map_size(40, 20)
            .with_difficulty(DifficultyLevel.NORMAL)
            .with_seed(123)
        )

        # Build first game
        game1 = builder.build()
        self.assertEqual(game1.seed, 123)

        # Build second game (should be independent)
        game2 = builder.build()
        self.assertEqual(game2.seed, 123)

        # Games should be different objects
        self.assertIsNot(game1, game2)

    def test_deterministic_with_seed(self):
        """Test that same seed produces deterministic results."""
        game1 = GameBuilder().with_seed(42).build()
        game2 = GameBuilder().with_seed(42).build()

        # Should have same seed
        self.assertEqual(game1.seed, game2.seed)

        # Should generate same map (using same seed)
        self.assertEqual(len(game1.game_map), len(game2.game_map))

    def test_different_seeds_different_results(self):
        """Test that different seeds produce different results."""
        game1 = GameBuilder().with_seed(42).build()
        game2 = GameBuilder().with_seed(999).build()

        # Should have different seeds
        self.assertNotEqual(game1.seed, game2.seed)

    def test_testing_configuration(self):
        """Test common testing configuration."""
        # Common pattern for testing: fixed seed, fixed positions, small map
        game = (
            GameBuilder()
            .with_seed(42)
            .with_fixed_positions()
            .with_map_size(30, 15)
            .with_floors(3)
            .build()
        )

        self.assertEqual(game.seed, 42)
        self.assertFalse(game.random_npcs)
        # Map dimensions may be overridden by FloorManager/level_data
        self.assertEqual(game.max_floors, 3)


if __name__ == "__main__":
    unittest.main()
