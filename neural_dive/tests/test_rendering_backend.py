"""Integration tests for rendering with different backends.

This module demonstrates the backend abstraction by testing rendering
with TestBackend and verifying backend swapping works correctly.

NOTE: Many of these tests are currently skipped because they require
full conversion of rendering.py to use backend.draw_text() instead of
print() statements. This is a future enhancement (Phase 5F).
"""

from __future__ import annotations

import unittest

from neural_dive.backends import TestBackend
from neural_dive.entities import Entity
from neural_dive.entity_renderers import EntityType, get_entity_renderer
from neural_dive.game import Game
from neural_dive.rendering import draw_game
from neural_dive.themes import get_theme


class TestRenderingBackendIntegration(unittest.TestCase):
    """Integration tests for rendering with backend abstraction."""

    def setUp(self):
        """Set up test fixtures."""
        self.backend = TestBackend(width=80, height=30)
        self.game = Game(
            map_width=50,
            map_height=25,
            seed=42,
            random_npcs=False,
            content_set="algorithms",
        )
        self.chars, self.colors = get_theme("cyberpunk", "dark")

    @unittest.skip("Requires full backend conversion - rendering.py still uses print()")
    def test_draw_game_with_test_backend(self):
        """Test that draw_game works with TestBackend."""
        # Should not raise an error
        draw_game(self.backend, self.game, self.chars, self.colors)

        # Should have recorded draw calls
        self.assertGreater(len(self.backend.draw_calls), 0)

    @unittest.skip("Requires full backend conversion - rendering.py still uses print()")
    def test_map_rendering_records_calls(self):
        """Test that map rendering records draw calls for walls and floors."""
        draw_game(self.backend, self.game, self.chars, self.colors)

        # Check that walls were drawn (look for '#' character calls)
        wall_calls = [
            call
            for call in self.backend.draw_calls
            if call.call_type == "text" and call.text == self.chars.wall
        ]
        self.assertGreater(len(wall_calls), 0, "Should have drawn at least one wall")

    @unittest.skip("Requires full backend conversion - rendering.py still uses print()")
    def test_player_rendering(self):
        """Test that player entity is rendered."""
        px, py = self.game.player.x, self.game.player.y
        draw_game(self.backend, self.game, self.chars, self.colors)

        # Find player draw call
        player_call = self.backend.get_draw_at(px, py)
        self.assertIsNotNone(player_call, f"Should have drawn player at ({px}, {py})")
        self.assertEqual(player_call.text, self.chars.player)

    @unittest.skip("Requires full backend conversion - rendering.py still uses print()")
    def test_npc_rendering(self):
        """Test that NPCs are rendered."""
        if not self.game.npcs:
            self.skipTest("No NPCs in game")

        npc = self.game.npcs[0]
        draw_game(self.backend, self.game, self.chars, self.colors)

        # Find NPC draw call
        npc_call = self.backend.get_draw_at(npc.x, npc.y)
        self.assertIsNotNone(npc_call, f"Should have drawn NPC at ({npc.x}, {npc.y})")
        self.assertEqual(npc_call.text, npc.char)

    @unittest.skip("Requires full backend conversion - rendering.py still uses print()")
    def test_stairs_rendering(self):
        """Test that stairs are rendered."""
        if not self.game.stairs:
            self.skipTest("No stairs in game")

        stair = self.game.stairs[0]
        draw_game(self.backend, self.game, self.chars, self.colors)

        # Find stairs draw call
        stair_call = self.backend.get_draw_at(stair.x, stair.y)
        self.assertIsNotNone(stair_call, f"Should have drawn stairs at ({stair.x}, {stair.y})")

    @unittest.skip("Requires full backend conversion - rendering.py still uses print()")
    def test_status_bar_rendering(self):
        """Test that status bar is rendered at bottom."""
        draw_game(self.backend, self.game, self.chars, self.colors)

        # Status bar should be at bottom (y = map_height + some offset)
        # Look for coherence display
        status_calls = [
            call
            for call in self.backend.draw_calls
            if call.call_type == "text" and "Coherence" in call.text
        ]
        self.assertGreater(len(status_calls), 0, "Should have rendered coherence in status bar")

    @unittest.skip("Requires full backend conversion - rendering.py still uses print()")
    def test_floor_indicator_rendering(self):
        """Test that floor indicator is rendered."""
        draw_game(self.backend, self.game, self.chars, self.colors)

        # Look for floor indicator (e.g., "Floor 1")
        floor_calls = [
            call
            for call in self.backend.draw_calls
            if call.call_type == "text" and "Floor" in call.text
        ]
        self.assertGreater(len(floor_calls), 0, "Should have rendered floor indicator")

    @unittest.skip("Requires full backend conversion - rendering.py still uses print()")
    def test_redraw_all_clears_screen(self):
        """Test that redraw_all=True clears screen before drawing."""
        draw_game(self.backend, self.game, self.chars, self.colors, redraw_all=True)

        # First call should be clear
        self.assertGreater(len(self.backend.draw_calls), 0)
        # Note: clear_screen() is called, so check for it
        clear_calls = [call for call in self.backend.draw_calls if call.call_type == "clear"]
        self.assertGreater(len(clear_calls), 0, "Should have cleared screen")

    def test_backend_swapping(self):
        """Test that different backend instances are independent."""
        backend1 = TestBackend(width=80, height=30)
        backend2 = TestBackend(width=120, height=40)

        # Verify backends are independent
        self.assertEqual(backend1.width, 80)
        self.assertEqual(backend2.width, 120)
        self.assertEqual(len(backend1.draw_calls), 0)
        self.assertEqual(len(backend2.draw_calls), 0)

        # Test that draw calls are independent
        backend1.draw_text(5, 10, "Text1")
        backend2.draw_text(10, 20, "Text2")

        self.assertEqual(len(backend1.draw_calls), 1)
        self.assertEqual(len(backend2.draw_calls), 1)
        self.assertEqual(backend1.draw_calls[0].text, "Text1")
        self.assertEqual(backend2.draw_calls[0].text, "Text2")


class TestEntityRenderingWithBackend(unittest.TestCase):
    """Test entity renderers work with backend abstraction.

    NOTE: These tests are skipped because entity renderers still use print()
    directly instead of backend.draw_text(). This is a future enhancement.
    """

    def setUp(self):
        """Set up test fixtures."""
        self.backend = TestBackend(width=80, height=30)
        _, self.colors = get_theme("cyberpunk", "dark")
        self.chars, _ = get_theme("cyberpunk", "dark")

    @unittest.skip("Entity renderers use print() instead of backend.draw_text()")
    def test_player_renderer_with_backend(self):
        """Test PlayerRenderer works with TestBackend."""
        player = Entity(10, 5, "@", "green", "Player")
        renderer = get_entity_renderer(EntityType.PLAYER)

        renderer.render(self.backend, player, self.chars, self.colors)

        call = self.backend.get_draw_at(10, 5)
        self.assertIsNotNone(call)
        self.assertEqual(call.text, self.chars.player)

    @unittest.skip("Entity renderers use print() instead of backend.draw_text()")
    def test_npc_renderer_with_backend(self):
        """Test NPCRenderer works with TestBackend."""
        npc = Entity(15, 8, "N", "magenta", "Test NPC", npc_type="specialist")
        renderer = get_entity_renderer(EntityType.NPC)

        renderer.render(self.backend, npc, self.chars, self.colors, is_required=False)

        call = self.backend.get_draw_at(15, 8)
        self.assertIsNotNone(call)
        self.assertEqual(call.text, "N")

    @unittest.skip("Entity renderers use print() instead of backend.draw_text()")
    def test_terminal_renderer_with_backend(self):
        """Test TerminalRenderer works with TestBackend."""
        from neural_dive.entities import InfoTerminal

        terminal = InfoTerminal(20, 10, "Test Terminal", ["Line 1", "Line 2"])
        renderer = get_entity_renderer(EntityType.TERMINAL)

        renderer.render(self.backend, terminal, self.chars, self.colors)

        call = self.backend.get_draw_at(20, 10)
        self.assertIsNotNone(call)
        self.assertEqual(call.text, self.chars.terminal)

    @unittest.skip("Entity renderers use print() instead of backend.draw_text()")
    def test_stairs_renderer_with_backend(self):
        """Test StairsRenderer works with TestBackend."""
        from neural_dive.entities import Stairs

        stairs = Stairs(12, 6, "down")
        renderer = get_entity_renderer(EntityType.STAIRS)

        renderer.render(self.backend, stairs, self.chars, self.colors)

        call = self.backend.get_draw_at(12, 6)
        self.assertIsNotNone(call)
        self.assertEqual(call.text, self.chars.stairs_down)


class TestBackendColorHandling(unittest.TestCase):
    """Test color handling across backends."""

    def setUp(self):
        """Set up test fixtures."""
        self.backend = TestBackend()

    def test_basic_color(self):
        """Test basic color is recorded."""
        self.backend.draw_text(5, 10, "Text", color="blue")

        call = self.backend.get_draw_at(5, 10)
        self.assertEqual(call.color, "blue")
        self.assertFalse(call.bold)

    def test_bold_color(self):
        """Test bold color is recorded."""
        self.backend.draw_text(5, 10, "Text", color="red", bold=True)

        call = self.backend.get_draw_at(5, 10)
        self.assertEqual(call.color, "red")
        self.assertTrue(call.bold)

    def test_background_color(self):
        """Test background color is recorded."""
        self.backend.draw_with_bg(5, 10, "Text", "black", "white")

        call = self.backend.get_draw_at(5, 10)
        self.assertEqual(call.fg, "black")
        self.assertEqual(call.bg, "white")

    def test_color_func_returns_identity(self):
        """Test get_color_func returns identity function."""
        color_func = self.backend.get_color_func("cyan", bold=True)
        result = color_func("Test")
        self.assertEqual(result, "Test")


if __name__ == "__main__":
    unittest.main()
