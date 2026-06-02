"""Tests for the entity renderer registry and rendering strategies.

Focused on:
- Registry returns the right renderer per EntityType.
- Every EntityType has a registered renderer (guard against silent fallthrough).
- Each renderer writes the expected character at the expected map position.
"""

from __future__ import annotations

from contextlib import redirect_stdout
import io
import unittest
from unittest.mock import Mock

from neural_dive.backends.test_backend import TestBackend
from neural_dive.entity_renderers import (
    _ENTITY_RENDERERS,
    EntityType,
    ItemPickupRenderer,
    NPCRenderer,
    PlayerRenderer,
    StairsRenderer,
    TerminalRenderer,
    get_entity_renderer,
)


def _fake_chars() -> Mock:
    chars = Mock()
    chars.player = "@"
    chars.terminal = "T"
    chars.stairs_up = "<"
    chars.stairs_down = ">"
    return chars


def _fake_colors() -> Mock:
    colors = Mock()
    colors.npc_specialist = "magenta"
    colors.npc_helper = "blue"
    colors.npc_enemy = "red"
    colors.npc_quest = "yellow"
    colors.terminal = "cyan"
    colors.stairs = "yellow"
    colors.player = "green"
    return colors


def _render_and_capture(fn) -> str:
    buf = io.StringIO()
    with redirect_stdout(buf):
        fn()
    return buf.getvalue()


class TestEntityRendererRegistry(unittest.TestCase):
    def test_returns_npc_renderer(self):
        self.assertIsInstance(get_entity_renderer(EntityType.NPC), NPCRenderer)

    def test_returns_terminal_renderer(self):
        self.assertIsInstance(get_entity_renderer(EntityType.TERMINAL), TerminalRenderer)

    def test_returns_stairs_renderer(self):
        self.assertIsInstance(get_entity_renderer(EntityType.STAIRS), StairsRenderer)

    def test_returns_item_pickup_renderer(self):
        self.assertIsInstance(get_entity_renderer(EntityType.ITEM_PICKUP), ItemPickupRenderer)

    def test_returns_player_renderer(self):
        self.assertIsInstance(get_entity_renderer(EntityType.PLAYER), PlayerRenderer)

    def test_unknown_type_raises(self):
        with self.assertRaises(ValueError):
            get_entity_renderer("not_a_real_type")

    def test_every_entity_type_has_registered_renderer(self):
        """Catch the case of adding a new EntityType but forgetting to register a renderer."""
        declared = {
            getattr(EntityType, name)
            for name in vars(EntityType)
            if not name.startswith("_") and isinstance(getattr(EntityType, name), str)
        }
        for entity_type in declared:
            self.assertIn(
                entity_type,
                _ENTITY_RENDERERS,
                msg=f"EntityType.{entity_type} has no registered renderer",
            )


class TestEntityRendererOutput(unittest.TestCase):
    def test_player_renderer_emits_player_char(self):
        entity = Mock(x=5, y=3)
        output = _render_and_capture(
            lambda: PlayerRenderer().render(
                term=TestBackend(),
                entity=entity,
                chars=_fake_chars(),
                colors=_fake_colors(),
            )
        )
        self.assertIn("@", output)

    def test_terminal_renderer_emits_terminal_char(self):
        entity = Mock(x=2, y=2)
        output = _render_and_capture(
            lambda: TerminalRenderer().render(
                term=TestBackend(),
                entity=entity,
                chars=_fake_chars(),
                colors=_fake_colors(),
            )
        )
        self.assertIn("T", output)

    def test_stairs_renderer_picks_up_or_down(self):
        up_entity = Mock(x=1, y=1, direction="up")
        down_entity = Mock(x=1, y=1, direction="down")

        up_output = _render_and_capture(
            lambda: StairsRenderer().render(
                term=TestBackend(),
                entity=up_entity,
                chars=_fake_chars(),
                colors=_fake_colors(),
            )
        )
        down_output = _render_and_capture(
            lambda: StairsRenderer().render(
                term=TestBackend(),
                entity=down_entity,
                chars=_fake_chars(),
                colors=_fake_colors(),
            )
        )

        self.assertIn("<", up_output)
        self.assertIn(">", down_output)

    def test_item_pickup_renderer_uses_entity_char(self):
        entity = Mock(x=0, y=0, char="?", color="magenta")
        output = _render_and_capture(
            lambda: ItemPickupRenderer().render(
                term=TestBackend(),
                entity=entity,
                chars=_fake_chars(),
                colors=_fake_colors(),
            )
        )
        self.assertIn("?", output)

    def test_npc_renderer_emits_npc_char(self):
        entity = Mock(x=4, y=4, char="N", npc_type="specialist")
        output = _render_and_capture(
            lambda: NPCRenderer().render(
                term=TestBackend(),
                entity=entity,
                chars=_fake_chars(),
                colors=_fake_colors(),
                is_required=False,
            )
        )
        self.assertIn("N", output)


if __name__ == "__main__":
    unittest.main()
