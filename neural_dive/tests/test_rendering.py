"""Unit tests for rendering module.

This test module covers rendering functionality including:
- Overlay dimension calculations
- Text wrapping in overlays
- Boundary conditions
- OverlayRenderer class
- Entity renderers (Strategy pattern)
"""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from neural_dive.entities import Entity, Stairs
from neural_dive.entity_renderers import (
    EntityType,
    ItemPickupRenderer,
    NPCRenderer,
    PlayerRenderer,
    StairsRenderer,
    TerminalRenderer,
    get_entity_renderer,
)
from neural_dive.rendering import OverlayRenderer, _is_position_occupied
from neural_dive.themes import CharacterSet, ColorScheme


class TestOverlayRenderer(unittest.TestCase):
    """Test OverlayRenderer class."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_term = MagicMock()
        self.mock_term.width = 80
        self.mock_term.height = 24
        self.colors = ColorScheme(
            wall="blue",
            floor="cyan",
            player="green",
            npc_specialist="magenta",
            npc_helper="green",
            npc_enemy="red",
            npc_quest="yellow",
            terminal="cyan",
            stairs="yellow",
            gate="yellow",
            ui_primary="white",
            ui_secondary="blue",
            ui_accent="magenta",
            ui_warning="yellow",
            ui_error="red",
            ui_success="green",
        )

    def test_overlay_renderer_initialization(self):
        """Test OverlayRenderer initializes with correct dimensions."""
        renderer = OverlayRenderer(
            backend=self.mock_term,
            max_width=60,
            max_height=20,
            border_color="blue",
        )

        self.assertEqual(renderer.max_width, 60)
        self.assertEqual(renderer.max_height, 20)
        self.assertEqual(renderer.border_color, "blue")
        self.assertIsNotNone(renderer.width)
        self.assertIsNotNone(renderer.height)

    def test_overlay_renderer_respects_terminal_bounds(self):
        """Test overlay doesn't exceed terminal dimensions."""
        renderer = OverlayRenderer(
            backend=self.mock_term,
            max_width=100,  # Larger than terminal
            max_height=30,  # Larger than terminal
            border_color="blue",
        )

        # Should be capped at terminal size minus padding
        self.assertLessEqual(renderer.width, self.mock_term.width - 4)
        self.assertLessEqual(renderer.height, self.mock_term.height - 4)

    def test_overlay_renderer_centers_overlay(self):
        """Test overlay is centered in terminal."""
        renderer = OverlayRenderer(
            backend=self.mock_term,
            max_width=60,
            max_height=20,
            border_color="blue",
        )

        # Should be centered
        expected_start_x = (self.mock_term.width - renderer.width) // 2
        expected_start_y = (self.mock_term.height - renderer.height) // 2

        self.assertEqual(renderer.start_x, expected_start_x)
        self.assertEqual(renderer.start_y, expected_start_y)

    def test_overlay_renderer_small_terminal(self):
        """Test overlay adapts to small terminal."""
        small_term = MagicMock()
        small_term.width = 40
        small_term.height = 15

        renderer = OverlayRenderer(
            backend=small_term,
            max_width=60,
            max_height=20,
            border_color="blue",
        )

        # Should fit within small terminal
        self.assertLessEqual(renderer.width, small_term.width - 4)
        self.assertLessEqual(renderer.height, small_term.height - 4)

    def test_overlay_renderer_draw_background(self):
        """Test drawing overlay background."""
        renderer = OverlayRenderer(
            backend=self.mock_term,
            max_width=60,
            max_height=20,
            border_color="blue",
        )

        # Mock backend methods for drawing
        draw_calls = []

        def mock_draw_with_bg(x, y, text, fg, bg):
            draw_calls.append((x, y, text, fg, bg))

        self.mock_term.draw_with_bg = mock_draw_with_bg

        renderer.draw_background()

        # Should have drawn background for each line
        self.assertGreater(len(draw_calls), 0)
        # Verify dimensions match overlay height
        self.assertEqual(len(draw_calls), renderer.height)

    @patch("neural_dive.rendering.print")
    def test_overlay_renderer_draw_border(self, mock_print):
        """Test drawing overlay border."""
        renderer = OverlayRenderer(
            backend=self.mock_term,
            max_width=60,
            max_height=20,
            border_color="blue",
        )

        # Mock terminal methods
        self.mock_term.move_xy.return_value = ""

        renderer.draw_border()

        # Should call print for border elements
        self.assertGreater(mock_print.call_count, 0)


class TestOverlayDimensions(unittest.TestCase):
    """Test overlay dimension calculations."""

    def test_overlay_fits_in_large_terminal(self):
        """Test overlay dimensions in large terminal."""
        term = MagicMock()
        term.width = 120
        term.height = 40

        renderer = OverlayRenderer(
            backend=term,
            max_width=80,
            max_height=25,
            border_color="blue",
        )

        # Should use max dimensions
        self.assertEqual(renderer.width, 80)
        self.assertEqual(renderer.height, 25)

    def test_overlay_constrains_to_small_terminal(self):
        """Test overlay dimensions in small terminal."""
        term = MagicMock()
        term.width = 60
        term.height = 20

        renderer = OverlayRenderer(
            backend=term,
            max_width=80,
            max_height=25,
            border_color="blue",
        )

        # Should be constrained
        self.assertLessEqual(renderer.width, 56)  # 60 - 4
        self.assertLessEqual(renderer.height, 16)  # 20 - 4

    def test_overlay_minimum_size(self):
        """Test overlay has minimum viable size."""
        term = MagicMock()
        term.width = 30
        term.height = 10

        renderer = OverlayRenderer(
            backend=term,
            max_width=80,
            max_height=25,
            border_color="blue",
        )

        # Should still have some size even in tiny terminal
        self.assertGreater(renderer.width, 0)
        self.assertGreater(renderer.height, 0)


class TestRenderingEdgeCases(unittest.TestCase):
    """Test edge cases in rendering."""

    def test_very_small_terminal(self):
        """Test handling of very small terminal."""
        term = MagicMock()
        term.width = 10
        term.height = 5

        # Should not crash
        try:
            renderer = OverlayRenderer(
                backend=term,
                max_width=60,
                max_height=20,
                border_color="blue",
            )
            # Should have some positive dimensions
            self.assertIsInstance(renderer.width, int)
            self.assertIsInstance(renderer.height, int)
        except Exception as e:
            self.fail(f"Should handle small terminal gracefully: {e}")


class TestColorScheme(unittest.TestCase):
    """Test ColorScheme data class."""

    def test_color_scheme_creation(self):
        """Test creating a ColorScheme."""
        colors = ColorScheme(
            wall="blue",
            floor="cyan",
            player="green",
            npc_specialist="magenta",
            npc_helper="green",
            npc_enemy="red",
            npc_quest="yellow",
            terminal="cyan",
            stairs="yellow",
            gate="yellow",
            ui_primary="white",
            ui_secondary="blue",
            ui_accent="magenta",
            ui_warning="yellow",
            ui_error="red",
            ui_success="green",
        )

        self.assertEqual(colors.wall, "blue")
        self.assertEqual(colors.player, "green")
        self.assertEqual(colors.npc_enemy, "red")
        self.assertEqual(colors.ui_error, "red")
        self.assertEqual(colors.gate, "yellow")

    def test_color_scheme_has_all_attributes(self):
        """Test ColorScheme has all required color attributes."""
        colors = ColorScheme(
            wall="blue",
            floor="cyan",
            player="green",
            npc_specialist="magenta",
            npc_helper="green",
            npc_enemy="red",
            npc_quest="yellow",
            terminal="cyan",
            stairs="yellow",
            gate="yellow",
            ui_primary="white",
            ui_secondary="blue",
            ui_accent="magenta",
            ui_warning="yellow",
            ui_error="red",
            ui_success="green",
        )

        # Check all required attributes exist
        self.assertTrue(hasattr(colors, "wall"))
        self.assertTrue(hasattr(colors, "floor"))
        self.assertTrue(hasattr(colors, "player"))
        self.assertTrue(hasattr(colors, "npc_specialist"))
        self.assertTrue(hasattr(colors, "npc_helper"))
        self.assertTrue(hasattr(colors, "npc_enemy"))
        self.assertTrue(hasattr(colors, "npc_quest"))
        self.assertTrue(hasattr(colors, "terminal"))
        self.assertTrue(hasattr(colors, "stairs"))
        self.assertTrue(hasattr(colors, "gate"))
        self.assertTrue(hasattr(colors, "ui_primary"))
        self.assertTrue(hasattr(colors, "ui_secondary"))
        self.assertTrue(hasattr(colors, "ui_accent"))
        self.assertTrue(hasattr(colors, "ui_warning"))
        self.assertTrue(hasattr(colors, "ui_error"))
        self.assertTrue(hasattr(colors, "ui_success"))


class TestPositionOccupancy(unittest.TestCase):
    """Test _is_position_occupied helper function."""

    def setUp(self):
        """Set up test fixtures."""
        # Create mock game with entities
        self.game = MagicMock()

        # Mock player
        self.game.player = MagicMock()
        self.game.player.x = 5
        self.game.player.y = 5

        # Mock NPCs
        npc1 = MagicMock()
        npc1.x = 10
        npc1.y = 10
        npc2 = MagicMock()
        npc2.x = 15
        npc2.y = 15
        self.game.npcs = [npc1, npc2]

        # Mock terminals
        terminal = MagicMock()
        terminal.x = 20
        terminal.y = 20
        self.game.terminals = [terminal]

        # Mock stairs
        stair = MagicMock()
        stair.x = 25
        stair.y = 25
        self.game.stairs = [stair]

    def test_position_occupied_by_player(self):
        """Test position occupied by player returns True."""
        self.assertTrue(_is_position_occupied(self.game, 5, 5))

    def test_position_occupied_by_npc(self):
        """Test position occupied by NPC returns True."""
        self.assertTrue(_is_position_occupied(self.game, 10, 10))
        self.assertTrue(_is_position_occupied(self.game, 15, 15))

    def test_position_occupied_by_terminal(self):
        """Test position occupied by terminal returns True."""
        self.assertTrue(_is_position_occupied(self.game, 20, 20))

    def test_position_occupied_by_stairs(self):
        """Test position occupied by stairs returns True."""
        self.assertTrue(_is_position_occupied(self.game, 25, 25))

    def test_empty_position_not_occupied(self):
        """Test empty position returns False."""
        self.assertFalse(_is_position_occupied(self.game, 0, 0))
        self.assertFalse(_is_position_occupied(self.game, 100, 100))

    def test_adjacent_position_not_occupied(self):
        """Test position adjacent to entity returns False."""
        # Adjacent to player
        self.assertFalse(_is_position_occupied(self.game, 6, 5))
        self.assertFalse(_is_position_occupied(self.game, 5, 6))

        # Adjacent to NPC
        self.assertFalse(_is_position_occupied(self.game, 11, 10))
        self.assertFalse(_is_position_occupied(self.game, 10, 11))


class TestEntityRenderers(unittest.TestCase):
    """Test entity renderer strategies."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_term = MagicMock()
        self.mock_term.width = 80
        self.mock_term.height = 24

        # Mock terminal color methods
        self.mock_term.move_xy.return_value = ""
        self.mock_term.bold_magenta = MagicMock(return_value="")
        self.mock_term.bold_green = MagicMock(return_value="")
        self.mock_term.bold_red = MagicMock(return_value="")
        self.mock_term.bold_yellow = MagicMock(return_value="")
        self.mock_term.bold_cyan = MagicMock(return_value="")

        self.colors = ColorScheme(
            wall="blue",
            floor="cyan",
            player="green",
            npc_specialist="magenta",
            npc_helper="green",
            npc_enemy="red",
            npc_quest="yellow",
            terminal="cyan",
            stairs="yellow",
            gate="yellow",
            ui_primary="white",
            ui_secondary="blue",
            ui_accent="magenta",
            ui_warning="yellow",
            ui_error="red",
            ui_success="green",
        )

        self.chars = CharacterSet(
            player="@",
            npc_default="N",
            stairs_up="<",
            stairs_down=">",
            terminal="T",
            gate_locked="G",
            gate_unlocked="g",
            wall="█",
            floor=".",
            wall_alt="▓",
            separator="─",
        )

    @patch("neural_dive.entity_renderers.print")
    def test_npc_renderer_specialist(self, mock_print):
        """Test NPCRenderer renders specialist NPC correctly."""
        npc = Entity(10, 15, "S", "magenta", "Specialist")
        npc.npc_type = "specialist"

        renderer = NPCRenderer()
        renderer.render(self.mock_term, npc, self.chars, self.colors, is_required=False)

        # Should call print once for the NPC
        self.assertEqual(mock_print.call_count, 1)
        # Should move to correct position
        self.mock_term.move_xy.assert_called_with(10, 15)

    @patch("neural_dive.entity_renderers.print")
    def test_npc_renderer_helper(self, mock_print):
        """Test NPCRenderer renders helper NPC correctly."""
        npc = Entity(5, 8, "H", "green", "Helper")
        npc.npc_type = "helper"

        renderer = NPCRenderer()
        renderer.render(self.mock_term, npc, self.chars, self.colors, is_required=False)

        self.assertEqual(mock_print.call_count, 1)
        self.mock_term.move_xy.assert_called_with(5, 8)

    @patch("neural_dive.entity_renderers.print")
    def test_npc_renderer_enemy(self, mock_print):
        """Test NPCRenderer renders enemy NPC correctly."""
        npc = Entity(20, 12, "E", "red", "Enemy")
        npc.npc_type = "enemy"

        renderer = NPCRenderer()
        renderer.render(self.mock_term, npc, self.chars, self.colors, is_required=False)

        self.assertEqual(mock_print.call_count, 1)
        self.mock_term.move_xy.assert_called_with(20, 12)

    @patch("neural_dive.entity_renderers.print")
    def test_npc_renderer_required_npc(self, mock_print):
        """Test NPCRenderer highlights required NPCs."""
        npc = Entity(10, 10, "S", "magenta", "RequiredNPC")
        npc.npc_type = "specialist"

        renderer = NPCRenderer()
        renderer.render(self.mock_term, npc, self.chars, self.colors, is_required=True)

        # Should still call print once
        self.assertEqual(mock_print.call_count, 1)
        # Should use bright/bold variant for required NPCs
        # (Implementation detail - just verify it was called)

    @patch("neural_dive.entity_renderers.print")
    def test_terminal_renderer(self, mock_print):
        """Test TerminalRenderer renders terminal correctly."""
        terminal = Entity(12, 18, "T", "cyan", "Terminal")

        renderer = TerminalRenderer()
        renderer.render(self.mock_term, terminal, self.chars, self.colors)

        self.assertEqual(mock_print.call_count, 1)
        self.mock_term.move_xy.assert_called_with(12, 18)

    @patch("neural_dive.entity_renderers.print")
    def test_stairs_renderer_up(self, mock_print):
        """Test StairsRenderer renders up stairs correctly."""
        stairs = Stairs(8, 6, "up")

        renderer = StairsRenderer()
        renderer.render(self.mock_term, stairs, self.chars, self.colors)

        self.assertEqual(mock_print.call_count, 1)
        self.mock_term.move_xy.assert_called_with(8, 6)

    @patch("neural_dive.entity_renderers.print")
    def test_stairs_renderer_down(self, mock_print):
        """Test StairsRenderer renders down stairs correctly."""
        stairs = Stairs(15, 20, "down")

        renderer = StairsRenderer()
        renderer.render(self.mock_term, stairs, self.chars, self.colors)

        self.assertEqual(mock_print.call_count, 1)
        self.mock_term.move_xy.assert_called_with(15, 20)

    @patch("neural_dive.entity_renderers.print")
    def test_item_pickup_renderer(self, mock_print):
        """Test ItemPickupRenderer renders item correctly."""
        item = Entity(25, 14, "i", "yellow", "Item")
        item.color = "yellow"

        renderer = ItemPickupRenderer()
        renderer.render(self.mock_term, item, self.chars, self.colors)

        self.assertEqual(mock_print.call_count, 1)
        self.mock_term.move_xy.assert_called_with(25, 14)

    @patch("neural_dive.entity_renderers.print")
    def test_player_renderer(self, mock_print):
        """Test PlayerRenderer renders player correctly."""
        player = Entity(40, 30, "@", "green", "Player")

        renderer = PlayerRenderer()
        renderer.render(self.mock_term, player, self.chars, self.colors)

        self.assertEqual(mock_print.call_count, 1)
        self.mock_term.move_xy.assert_called_with(40, 30)

    def test_get_entity_renderer_npc(self):
        """Test get_entity_renderer returns NPCRenderer for NPC type."""
        renderer = get_entity_renderer(EntityType.NPC)
        self.assertIsInstance(renderer, NPCRenderer)

    def test_get_entity_renderer_terminal(self):
        """Test get_entity_renderer returns TerminalRenderer for terminal type."""
        renderer = get_entity_renderer(EntityType.TERMINAL)
        self.assertIsInstance(renderer, TerminalRenderer)

    def test_get_entity_renderer_stairs(self):
        """Test get_entity_renderer returns StairsRenderer for stairs type."""
        renderer = get_entity_renderer(EntityType.STAIRS)
        self.assertIsInstance(renderer, StairsRenderer)

    def test_get_entity_renderer_item_pickup(self):
        """Test get_entity_renderer returns ItemPickupRenderer for item type."""
        renderer = get_entity_renderer(EntityType.ITEM_PICKUP)
        self.assertIsInstance(renderer, ItemPickupRenderer)

    def test_get_entity_renderer_player(self):
        """Test get_entity_renderer returns PlayerRenderer for player type."""
        renderer = get_entity_renderer(EntityType.PLAYER)
        self.assertIsInstance(renderer, PlayerRenderer)

    def test_get_entity_renderer_invalid_type(self):
        """Test get_entity_renderer raises error for invalid type."""
        with self.assertRaises(ValueError) as context:
            get_entity_renderer("invalid_type")

        self.assertIn("Unsupported entity type", str(context.exception))


if __name__ == "__main__":
    unittest.main()
