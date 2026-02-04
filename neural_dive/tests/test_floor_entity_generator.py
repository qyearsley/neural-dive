"""Tests for FloorEntityGenerator."""

import random
import unittest

from neural_dive.entities import InfoTerminal, Stairs
from neural_dive.items import CodeSnippet, HintToken, ItemPickup
from neural_dive.managers.floor_entity_generator import FloorEntityGenerator


class TestFloorEntityGeneratorInitialization(unittest.TestCase):
    """Test FloorEntityGenerator initialization."""

    def test_initialization(self):
        """Test that FloorEntityGenerator initializes correctly."""
        level_data = {1: {"terminal_positions": [(10, 10)]}}
        snippets = {"test_snippet": {"name": "Test", "topic": "testing", "content": "code"}}
        rand = random.Random(42)

        generator = FloorEntityGenerator(level_data, snippets, rand)

        self.assertEqual(generator.level_data, level_data)
        self.assertEqual(generator.snippets, snippets)
        self.assertEqual(generator.rand, rand)


class TestTerminalGeneration(unittest.TestCase):
    """Test terminal generation."""

    def setUp(self):
        """Set up test fixtures."""
        self.level_data = {
            1: {
                "terminal_positions": [(10, 10), (20, 20)],
            }
        }
        self.snippets = {}
        self.rand = random.Random(42)
        self.generator = FloorEntityGenerator(self.level_data, self.snippets, self.rand)

    def test_generate_terminals_with_positions(self):
        """Test terminal generation with defined positions."""
        terminals = self.generator._generate_terminals(floor=1)

        # Should create terminals based on ZONE_TERMINALS for floor 1
        self.assertIsInstance(terminals, list)
        # Floor 1 has terminals defined in ZONE_TERMINALS
        self.assertGreater(len(terminals), 0)
        for terminal in terminals:
            self.assertIsInstance(terminal, InfoTerminal)

    def test_generate_terminals_no_level_data(self):
        """Test terminal generation when no level data exists."""
        terminals = self.generator._generate_terminals(floor=999)

        self.assertEqual(terminals, [])

    def test_generate_terminals_no_positions(self):
        """Test terminal generation when positions not defined."""
        generator = FloorEntityGenerator({1: {}}, {}, random.Random(42))
        terminals = generator._generate_terminals(floor=1)

        self.assertEqual(terminals, [])


class TestStairsGeneration(unittest.TestCase):
    """Test stairs generation."""

    def setUp(self):
        """Set up test fixtures."""
        self.level_data = {
            1: {
                "stairs_down": (50, 50),
                "stairs_up": None,  # No up stairs on floor 1
            },
            2: {
                "stairs_down": (60, 60),
                "stairs_up": (10, 10),
            },
        }
        self.snippets = {}
        self.rand = random.Random(42)
        self.generator = FloorEntityGenerator(self.level_data, self.snippets, self.rand)

        # Create simple test map
        self.game_map = [["." for _ in range(80)] for _ in range(24)]
        self.map_width = 80
        self.map_height = 24
        self.player_pos = (5, 5)

    def test_generate_stairs_floor_1_with_level_data(self):
        """Test stairs generation on floor 1 with level data."""
        stairs = self.generator._generate_stairs(
            floor=1,
            max_floors=3,
            game_map=self.game_map,
            map_width=self.map_width,
            map_height=self.map_height,
            player_pos=self.player_pos,
            random_placement=False,
        )

        # Floor 1 should have down stairs only
        self.assertEqual(len(stairs), 1)
        self.assertEqual(stairs[0].direction, "down")
        self.assertEqual((stairs[0].x, stairs[0].y), (50, 50))

    def test_generate_stairs_floor_2_with_level_data(self):
        """Test stairs generation on floor 2 with level data."""
        stairs = self.generator._generate_stairs(
            floor=2,
            max_floors=3,
            game_map=self.game_map,
            map_width=self.map_width,
            map_height=self.map_height,
            player_pos=self.player_pos,
            random_placement=False,
        )

        # Floor 2 should have both up and down stairs
        self.assertEqual(len(stairs), 2)
        directions = {stair.direction for stair in stairs}
        self.assertEqual(directions, {"up", "down"})

    def test_generate_stairs_final_floor(self):
        """Test stairs generation on final floor."""
        stairs = self.generator._generate_stairs(
            floor=3,
            max_floors=3,
            game_map=self.game_map,
            map_width=self.map_width,
            map_height=self.map_height,
            player_pos=self.player_pos,
            random_placement=True,
        )

        # Final floor should have up stairs only
        self.assertGreater(len(stairs), 0)
        for stair in stairs:
            self.assertEqual(stair.direction, "up")

    def test_generate_stairs_without_level_data(self):
        """Test stairs generation with procedural placement."""
        generator = FloorEntityGenerator({}, {}, random.Random(42))

        stairs = generator._generate_stairs(
            floor=2,
            max_floors=5,
            game_map=self.game_map,
            map_width=self.map_width,
            map_height=self.map_height,
            player_pos=self.player_pos,
            random_placement=True,
        )

        # Should generate both up and down stairs procedurally
        self.assertEqual(len(stairs), 2)
        directions = {stair.direction for stair in stairs}
        self.assertEqual(directions, {"up", "down"})

    def test_add_stairs_from_single_position(self):
        """Test adding stairs from a single position tuple."""
        stairs = self.generator._add_stairs_from_positions((10, 20), "down")

        self.assertEqual(len(stairs), 1)
        self.assertEqual(stairs[0].x, 10)
        self.assertEqual(stairs[0].y, 20)
        self.assertEqual(stairs[0].direction, "down")

    def test_add_stairs_from_multiple_positions(self):
        """Test adding stairs from a list of positions."""
        positions = [(10, 20), (30, 40), (50, 60)]
        stairs = self.generator._add_stairs_from_positions(positions, "up")

        self.assertEqual(len(stairs), 3)
        for i, stair in enumerate(stairs):
            self.assertEqual(stair.x, positions[i][0])
            self.assertEqual(stair.y, positions[i][1])
            self.assertEqual(stair.direction, "up")


class TestItemGeneration(unittest.TestCase):
    """Test item pickup generation."""

    def setUp(self):
        """Set up test fixtures."""
        self.level_data = {}
        self.snippets = {
            "snippet1": {
                "name": "Test Snippet 1",
                "topic": "testing",
                "content": "test code 1",
            },
            "snippet2": {
                "name": "Test Snippet 2",
                "topic": "testing",
                "content": "test code 2",
            },
        }
        self.rand = random.Random(42)
        self.generator = FloorEntityGenerator(self.level_data, self.snippets, self.rand)

        # Create simple test map
        self.game_map = [["." for _ in range(80)] for _ in range(24)]
        self.map_width = 80
        self.map_height = 24
        self.player_pos = (5, 5)

    def test_generate_items_floor_1(self):
        """Test item generation on floor 1."""
        items = self.generator._generate_items(
            floor=1,
            game_map=self.game_map,
            map_width=self.map_width,
            map_height=self.map_height,
            player_pos=self.player_pos,
            random_placement=True,
        )

        # Floor 1: 1 hint token, 0 snippets
        self.assertEqual(len(items), 1)
        self.assertIsInstance(items[0].item, HintToken)

    def test_generate_items_floor_2(self):
        """Test item generation on floor 2."""
        items = self.generator._generate_items(
            floor=2,
            game_map=self.game_map,
            map_width=self.map_width,
            map_height=self.map_height,
            player_pos=self.player_pos,
            random_placement=True,
        )

        # Floor 2: 2 hint tokens (1 + 2//2 = 2), 1 snippet
        self.assertEqual(len(items), 3)

        hint_tokens = [item for item in items if isinstance(item.item, HintToken)]
        snippets = [item for item in items if isinstance(item.item, CodeSnippet)]

        self.assertEqual(len(hint_tokens), 2)
        self.assertEqual(len(snippets), 1)

    def test_generate_items_floor_3(self):
        """Test item generation on floor 3."""
        items = self.generator._generate_items(
            floor=3,
            game_map=self.game_map,
            map_width=self.map_width,
            map_height=self.map_height,
            player_pos=self.player_pos,
            random_placement=True,
        )

        # Floor 3: 2 hint tokens (1 + 3//2), 1 snippet
        self.assertEqual(len(items), 3)

        hint_tokens = [item for item in items if isinstance(item.item, HintToken)]
        snippets = [item for item in items if isinstance(item.item, CodeSnippet)]

        self.assertEqual(len(hint_tokens), 2)
        self.assertEqual(len(snippets), 1)

    def test_generate_items_no_snippets_available(self):
        """Test item generation when no snippets are available."""
        generator = FloorEntityGenerator({}, {}, random.Random(42))

        items = generator._generate_items(
            floor=2,
            game_map=self.game_map,
            map_width=self.map_width,
            map_height=self.map_height,
            player_pos=self.player_pos,
            random_placement=True,
        )

        # Should only have hint tokens, no snippets
        for item in items:
            self.assertIsInstance(item.item, HintToken)

    def test_generate_items_positions_away_from_player(self):
        """Test that items are placed away from player."""
        items = self.generator._generate_items(
            floor=1,
            game_map=self.game_map,
            map_width=self.map_width,
            map_height=self.map_height,
            player_pos=(10, 10),
            random_placement=True,
        )

        # All items should be >8 manhattan distance from player
        for item in items:
            distance = abs(item.x - 10) + abs(item.y - 10)
            self.assertGreater(distance, 8)


class TestFullEntityGeneration(unittest.TestCase):
    """Test full entity generation workflow."""

    def setUp(self):
        """Set up test fixtures."""
        self.level_data = {
            1: {
                "terminal_positions": [(15, 15)],
                "stairs_down": (50, 50),
            }
        }
        self.snippets = {
            "test_snippet": {
                "name": "Test Snippet",
                "topic": "testing",
                "content": "test code",
            }
        }
        self.rand = random.Random(42)
        self.generator = FloorEntityGenerator(self.level_data, self.snippets, self.rand)

        # Create simple test map
        self.game_map = [["." for _ in range(80)] for _ in range(24)]
        self.map_width = 80
        self.map_height = 24
        self.player_pos = (5, 5)

    def test_generate_all_entities(self):
        """Test generating all entities at once."""
        stairs, terminals, items = self.generator.generate_all_entities(
            floor=1,
            max_floors=3,
            game_map=self.game_map,
            map_width=self.map_width,
            map_height=self.map_height,
            player_pos=self.player_pos,
            random_placement=True,  # Use random placement to ensure items are generated
        )

        # Verify stairs
        self.assertGreater(len(stairs), 0)
        self.assertIsInstance(stairs[0], Stairs)

        # Verify terminals
        self.assertGreater(len(terminals), 0)
        self.assertIsInstance(terminals[0], InfoTerminal)

        # Verify items
        self.assertGreater(len(items), 0)
        self.assertIsInstance(items[0], ItemPickup)

    def test_generate_all_entities_deterministic(self):
        """Test that generation is deterministic with same seed."""
        stairs1, terminals1, items1 = self.generator.generate_all_entities(
            floor=2,
            max_floors=3,
            game_map=self.game_map,
            map_width=self.map_width,
            map_height=self.map_height,
            player_pos=self.player_pos,
            random_placement=True,
        )

        # Create new generator with same seed
        generator2 = FloorEntityGenerator(self.level_data, self.snippets, random.Random(42))
        stairs2, terminals2, items2 = generator2.generate_all_entities(
            floor=2,
            max_floors=3,
            game_map=self.game_map,
            map_width=self.map_width,
            map_height=self.map_height,
            player_pos=self.player_pos,
            random_placement=True,
        )

        # Should generate identical results
        self.assertEqual(len(stairs1), len(stairs2))
        self.assertEqual(len(terminals1), len(terminals2))
        self.assertEqual(len(items1), len(items2))


if __name__ == "__main__":
    unittest.main()
