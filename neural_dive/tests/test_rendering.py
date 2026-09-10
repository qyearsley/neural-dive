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
from neural_dive.map_renderer import _is_position_occupied
from neural_dive.overlay_renderer import OverlayRenderer, _weak_areas_line
from neural_dive.themes import CharacterSet, ColorScheme


class TestVictoryScreenWeakAreas(unittest.TestCase):
    """Test the weak-areas line added to the victory screen."""

    def _game(self, profile):
        from neural_dive.models import Question
        from neural_dive.question_types import QuestionType

        game = MagicMock()
        game.profile = profile
        game.questions = {
            "a": Question(
                question_text="A?",
                topic="databases",
                question_type=QuestionType.YES_NO,
                question_id="a",
            ),
        }
        return game

    def test_no_profile_adds_no_line(self):
        """Without history the victory screen is exactly what it always was."""
        self.assertIsNone(_weak_areas_line(self._game(None)))

    def test_empty_profile_adds_no_line(self):
        from neural_dive.player_profile import PlayerProfile

        self.assertIsNone(_weak_areas_line(self._game(PlayerProfile())))

    def test_profile_with_no_misses_adds_no_line(self):
        from neural_dive.player_profile import PlayerProfile, QuestionRecord

        profile = PlayerProfile(questions={"a": QuestionRecord(seen=2, correct=2, wrong=0)})

        self.assertIsNone(_weak_areas_line(self._game(profile)))

    def test_missed_topics_are_listed(self):
        from neural_dive.player_profile import PlayerProfile, QuestionRecord

        profile = PlayerProfile(questions={"a": QuestionRecord(seen=3, correct=1, wrong=2)})

        self.assertEqual(_weak_areas_line(self._game(profile)), "Weak areas: databases (2 missed)")

    def test_questions_missing_from_the_content_set_are_skipped(self):
        from neural_dive.player_profile import PlayerProfile, QuestionRecord

        profile = PlayerProfile(questions={"gone": QuestionRecord(seen=3, correct=0, wrong=3)})

        self.assertIsNone(_weak_areas_line(self._game(profile)))


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

    @patch("neural_dive.overlay_renderer.print")
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
        self.game.npc_manager.npcs = [npc1, npc2]

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


class _StubBackend:
    """The blessed-shaped surface the end screens actually use.

    `draw_victory_screen` and `draw_game_over_screen` build escape sequences as
    strings and `print` them, rather than going through `backend.draw_text` --
    which is why `TestBackend` cannot record them and why the twelve tests in
    `test_rendering_backend.py` are still skipped. Until that conversion
    happens, the honest way to test these two is to give them the attributes
    they read and capture stdout.
    """

    width = 100
    height = 40
    home = ""
    clear = ""

    def move_xy(self, x, y):
        return ""

    def bold_black(self, text):
        return text

    def black_on_white(self, text):
        return text

    def get_color_func(self, color, bold=False):
        return lambda text: text

    def __getattr__(self, name):
        # Colour helpers are looked up by name (`bold_green`, `bold_red`, ...),
        # so anything else this reads is an identity function too.
        return lambda text="": text


class TestEndScreens(unittest.TestCase):
    """Both endings show the run summary. Only one of them used to.

    The game over screen was twenty lines of raw terminal escapes inline in the
    main loop -- two strings, "SYSTEM FAILURE - COHERENCE LOST" and "Press Q to
    quit", over the still-drawn map. So the score, the accuracy, the time and
    the weak-areas line were all invisible at the one ending where knowing what
    you got wrong helps most.
    """

    def _game(self):
        game = MagicMock()
        game.profile = None
        game.questions = {}
        game.get_final_stats.return_value = {
            "score": 1234,
            "questions_answered": 20,
            "questions_correct": 15,
            "questions_wrong": 5,
            "accuracy": 75.0,
            "npcs_completed": 7,
            "knowledge_modules": 3,
            "final_coherence": 0,
            "time_played": 187,
            "current_floor": 3,
        }
        game.player_manager.max_coherence = 100
        game.floor_manager.max_floors = 3
        return game

    def _render(self, draw):
        from contextlib import redirect_stdout
        import io

        from neural_dive.themes import get_theme

        _chars, colors = get_theme()
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            draw(_StubBackend(), self._game(), colors)
        return buffer.getvalue()

    def test_victory_screen_shows_the_summary(self):
        from neural_dive.overlay_renderer import draw_victory_screen

        output = self._render(draw_victory_screen)
        self.assertIn("VICTORY", output)
        self.assertIn("Final Score: 1234", output)
        self.assertIn("Accuracy: 75.0%", output)

    def test_game_over_screen_shows_the_same_summary(self):
        from neural_dive.overlay_renderer import draw_game_over_screen

        output = self._render(draw_game_over_screen)
        self.assertIn("SYSTEM FAILURE", output)
        self.assertIn("Final Score: 1234", output)
        self.assertIn("Accuracy: 75.0%", output)
        self.assertIn("Questions Answered: 20", output)
        self.assertIn("Deepest Layer: 3/3", output)

    def test_game_over_screen_says_how_to_leave(self):
        from neural_dive.overlay_renderer import draw_game_over_screen

        self.assertIn("Press Q to quit", self._render(draw_game_over_screen))

    def test_the_two_screens_differ_only_in_their_heading(self):
        from neural_dive.overlay_renderer import draw_game_over_screen, draw_victory_screen

        won = self._render(draw_victory_screen)
        lost = self._render(draw_game_over_screen)
        self.assertNotIn("VICTORY", lost)
        self.assertNotIn("SYSTEM FAILURE", won)
        for line in ("Final Score: 1234", "NPCs Defeated: 7", "Time Played: 3m 7s"):
            self.assertIn(line, won)
            self.assertIn(line, lost)


class TestEndScreenFitting(unittest.TestCase):
    """A short window used to lose the tail of the summary, silently.

    Measured before the fix: at 24 rows everything fitted, at 22 rows the
    weak-areas line vanished, and at 20 rows "Time Played", "Deepest Layer" and
    "Weak areas" all went -- the three least likely to be missed being the ones
    that survived.
    """

    def _entries(self, count: int):
        from neural_dive.overlay_renderer import _SummaryLine

        return [_SummaryLine(f"line {i}", priority=i) for i in range(count)]

    def test_everything_is_kept_when_it_fits(self):
        from neural_dive.overlay_renderer import fit_end_screen_lines

        entries = self._entries(5)

        self.assertEqual(len(fit_end_screen_lines(entries, 5)), 5)
        self.assertEqual(len(fit_end_screen_lines(entries, 50)), 5)

    def test_the_lowest_priority_lines_go_first(self):
        from neural_dive.overlay_renderer import fit_end_screen_lines

        kept = fit_end_screen_lines(self._entries(5), 2)

        self.assertEqual(kept, ["line 3", "line 4"])

    def test_surviving_lines_keep_their_original_order(self):
        from neural_dive.overlay_renderer import _SummaryLine, fit_end_screen_lines

        entries = [
            _SummaryLine("first", 100),
            _SummaryLine("second", 1),
            _SummaryLine("third", 50),
        ]

        self.assertEqual(fit_end_screen_lines(entries, 2), ["first", "third"])

    def test_blank_spacers_are_dropped_before_content(self):
        from neural_dive.overlay_renderer import _SummaryLine, fit_end_screen_lines

        entries = [
            _SummaryLine("a", 10),
            _SummaryLine("", 0),
            _SummaryLine("b", 10),
        ]

        self.assertEqual(fit_end_screen_lines(entries, 2), ["a", "b"])

    def test_no_capacity_keeps_nothing(self):
        from neural_dive.overlay_renderer import fit_end_screen_lines

        self.assertEqual(fit_end_screen_lines(self._entries(5), 0), [])
        self.assertEqual(fit_end_screen_lines(self._entries(5), -3), [])

    def test_weak_areas_outranks_every_other_line(self):
        """The loss screen's whole point is telling the player what to study."""
        from neural_dive.overlay_renderer import _end_screen_entries

        game = _stats_game(with_weak_areas=True)
        entries = _end_screen_entries(game)
        weak = next(entry for entry in entries if entry.text.startswith("Weak areas"))

        self.assertEqual(weak.priority, max(entry.priority for entry in entries))

    def test_weak_areas_survives_a_window_that_only_fits_two_lines(self):
        from neural_dive.overlay_renderer import _end_screen_entries, fit_end_screen_lines

        kept = fit_end_screen_lines(_end_screen_entries(_stats_game(with_weak_areas=True)), 2)

        self.assertTrue(any(line.startswith("Weak areas") for line in kept))

    def test_a_short_window_still_shows_the_most_valuable_lines(self):
        from neural_dive.overlay_renderer import draw_game_over_screen

        output = _render_end_screen(draw_game_over_screen, height=22, with_weak_areas=True)

        self.assertIn("Weak areas", output)
        self.assertIn("Final Score", output)

    def test_a_twenty_row_window_still_shows_weak_areas(self):
        from neural_dive.overlay_renderer import draw_game_over_screen

        output = _render_end_screen(draw_game_over_screen, height=20, with_weak_areas=True)

        self.assertIn("Weak areas", output)

    def test_a_tall_window_shows_the_whole_summary(self):
        from neural_dive.overlay_renderer import _end_screen_lines, draw_victory_screen

        output = _render_end_screen(draw_victory_screen, height=40, with_weak_areas=True)

        for line in _end_screen_lines(_stats_game(with_weak_areas=True)):
            if line:
                self.assertIn(line, output)

    def test_the_panel_shrinks_to_the_window_rather_than_overflowing(self):
        from neural_dive.overlay_renderer import draw_game_over_screen

        # Should not raise, and should still say how to leave.
        output = _render_end_screen(draw_game_over_screen, height=12, with_weak_areas=True)

        self.assertIn("Press Q to quit", output)


def _stats_game(with_weak_areas: bool = False):
    """A game stub with the final stats the end screens read."""
    game = MagicMock()
    game.get_final_stats.return_value = {
        "score": 1234,
        "questions_answered": 20,
        "questions_correct": 15,
        "questions_wrong": 5,
        "accuracy": 75.0,
        "npcs_completed": 7,
        "knowledge_modules": 3,
        "final_coherence": 0,
        "time_played": 187,
        "current_floor": 3,
    }
    game.player_manager.max_coherence = 100
    game.floor_manager.max_floors = 3

    if with_weak_areas:
        from neural_dive.models import Question
        from neural_dive.player_profile import PlayerProfile, QuestionRecord
        from neural_dive.question_types import QuestionType

        game.profile = PlayerProfile(questions={"a": QuestionRecord(seen=3, correct=0, wrong=3)})
        game.questions = {
            "a": Question(
                question_text="A?",
                topic="graphs",
                question_type=QuestionType.YES_NO,
                question_id="a",
            )
        }
    else:
        game.profile = None
        game.questions = {}
    return game


def _render_end_screen(draw, height: int, with_weak_areas: bool = False) -> str:
    from contextlib import redirect_stdout
    import io

    from neural_dive.themes import get_theme

    backend = _StubBackend()
    backend.height = height
    _chars, colors = get_theme()
    buffer = io.StringIO()
    with redirect_stdout(buffer):
        draw(backend, _stats_game(with_weak_areas), colors)
    return buffer.getvalue()


class TestHelpOverlay(unittest.TestCase):
    """There was no in-game legend at all before this.

    The only key to the glyphs was an author-facing docstring in the level
    data, which a player never sees.
    """

    def _render(self, width: int = 100, height: int = 40) -> str:
        from contextlib import redirect_stdout
        import io

        from neural_dive.backends.test_backend import TestBackend
        from neural_dive.overlay_renderer import draw_help_overlay
        from neural_dive.themes import get_theme

        chars, colors = get_theme()
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            draw_help_overlay(TestBackend(width=width, height=height), chars, colors)
        return buffer.getvalue()

    def test_names_itself(self):
        self.assertIn("HELP", self._render())

    def test_explains_the_map_glyphs(self):
        from neural_dive.themes import get_theme

        chars, _colors = get_theme()
        output = self._render()

        for glyph in (chars.player, chars.terminal, chars.stairs_up, chars.stairs_down):
            self.assertIn(glyph, output)

    def test_disambiguates_the_glyphs_the_map_reuses(self):
        """ "?" and "S" are items, but "S" is also the layer-2 NPC SYSTEM_CORE."""
        output = self._render()

        self.assertIn("SYSTEM_CORE", output)
        self.assertIn("reverse video", output)

    def test_explains_coherence(self):
        output = self._render()

        self.assertIn("COHERENCE", output)
        self.assertIn("zero", output)

    def test_explains_what_gates_the_stairs(self):
        output = self._render()

        self.assertIn("stairs down only open", output)

    def test_lists_the_keys(self):
        output = self._render()

        for key in ("Arrows", "Inventory", "Save", "Quit", "1-4"):
            self.assertIn(key, output)

    def test_says_how_to_close_itself(self):
        self.assertIn("close", self._render())

    def test_renders_in_a_short_window_without_raising(self):
        # 34 rows is the minimum the game will start at; the overlay must not
        # need more than the window it lives in.
        self.assertTrue(self._render(width=50, height=34))

    def test_renders_in_a_very_short_window_without_raising(self):
        self.assertIsInstance(self._render(width=30, height=10), str)

    def test_lines_fit_the_overlay_width(self):
        from neural_dive.config import OVERLAY_CONTENT_MARGIN, OVERLAY_MAX_WIDTH
        from neural_dive.overlay_renderer import help_overlay_lines
        from neural_dive.themes import get_theme

        chars, _colors = get_theme()
        limit = OVERLAY_MAX_WIDTH - OVERLAY_CONTENT_MARGIN

        for line in help_overlay_lines(chars):
            self.assertLessEqual(len(line), limit, msg=line)

    def test_every_line_fits_the_minimum_supported_window(self):
        """34 rows is the floor the game starts at, so help must fit in 34."""
        from neural_dive.config import (
            HELP_OVERLAY_MAX_HEIGHT,
            OVERLAY_FOOTER_MARGIN,
            OVERLAY_SCREEN_MARGIN,
        )
        from neural_dive.overlay_renderer import help_overlay_lines
        from neural_dive.themes import get_theme

        chars, _colors = get_theme()
        overlay_height = min(HELP_OVERLAY_MAX_HEIGHT, 34 - OVERLAY_SCREEN_MARGIN)
        # Content runs from row 2 of the overlay to the footer margin.
        rows = overlay_height - 2 - OVERLAY_FOOTER_MARGIN

        self.assertLessEqual(len(help_overlay_lines(chars)), rows)


class TestInventoryTruncation(unittest.TestCase):
    """Item lists used to stop after three with no sign of the rest."""

    def _render(self, hint_count: int, snippet_count: int) -> str:
        from contextlib import redirect_stdout
        import io

        from neural_dive.backends.test_backend import TestBackend
        from neural_dive.items import ItemType
        from neural_dive.overlay_renderer import draw_inventory_overlay
        from neural_dive.themes import get_theme

        hints = [MagicMock(description=f"hint {i}") for i in range(hint_count)]
        snippets = [MagicMock(name=f"snip {i}") for i in range(snippet_count)]
        for i, snippet in enumerate(snippets):
            snippet.name = f"snip {i}"

        game = MagicMock()
        game.player_manager.get_inventory_count.return_value = hint_count + snippet_count
        game.player_manager.max_inventory_size = 20
        game.player_manager.get_items_by_type.side_effect = lambda kind: (
            hints if kind == ItemType.HINT_TOKEN else snippets
        )

        _chars, colors = get_theme()
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            draw_inventory_overlay(TestBackend(width=100, height=40), game, colors)
        return buffer.getvalue()

    def test_three_or_fewer_items_show_no_indicator(self):
        output = self._render(hint_count=3, snippet_count=0)

        self.assertIn("hint 2", output)
        self.assertNotIn("more", output)

    def test_extra_hint_tokens_are_counted(self):
        output = self._render(hint_count=7, snippet_count=0)

        self.assertIn("+4 more", output)

    def test_extra_snippets_are_counted(self):
        output = self._render(hint_count=0, snippet_count=5)

        self.assertIn("+2 more", output)

    def test_both_lists_get_their_own_indicator(self):
        output = self._render(hint_count=5, snippet_count=6)

        self.assertIn("+2 more", output)
        self.assertIn("+3 more", output)


class TestFormatTime(unittest.TestCase):
    """Was a closure inside `draw_victory_screen`, so it could not be tested and
    the game over screen could not reuse it."""

    def test_under_a_minute(self):
        from neural_dive.overlay_renderer import format_time

        self.assertEqual(format_time(45), "0m 45s")

    def test_whole_minutes(self):
        from neural_dive.overlay_renderer import format_time

        self.assertEqual(format_time(120), "2m 0s")

    def test_minutes_and_seconds(self):
        from neural_dive.overlay_renderer import format_time

        self.assertEqual(format_time(187), "3m 7s")

    def test_fractional_seconds_are_dropped(self):
        from neural_dive.overlay_renderer import format_time

        self.assertEqual(format_time(59.9), "0m 59s")

    def test_zero(self):
        from neural_dive.overlay_renderer import format_time

        self.assertEqual(format_time(0), "0m 0s")
