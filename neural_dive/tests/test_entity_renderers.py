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
    npc_style_name,
)
from neural_dive.themes import get_theme


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
    colors.npc_boss = "bright_red"
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


class TestNPCHighlighting(unittest.TestCase):
    """Required NPCs, bosses and optional NPCs must not look the same.

    The old rule was "bright_<colour> when required, <colour> otherwise", but
    every theme colour already starts with "bright_", so both branches resolved
    to the same attribute and produced byte-identical output. README.md claimed
    required NPCs glowed brighter; no shipped NPC ever did.
    """

    def test_required_and_optional_use_different_styles(self):
        colors = _fake_colors()
        required = npc_style_name("specialist", colors, is_required=True)
        optional = npc_style_name("specialist", colors, is_required=False)

        self.assertNotEqual(required, optional)

    def test_boss_has_its_own_style(self):
        colors = _fake_colors()
        boss = npc_style_name("boss", colors, is_required=False)

        self.assertNotEqual(boss, npc_style_name("specialist", colors, is_required=True))
        self.assertNotEqual(boss, npc_style_name("specialist", colors, is_required=False))
        self.assertNotEqual(boss, npc_style_name("enemy", colors, is_required=True))

    def test_boss_uses_the_boss_colour_not_the_specialist_one(self):
        colors = _fake_colors()

        self.assertIn(colors.npc_boss, npc_style_name("boss", colors, is_required=False))

    def test_every_npc_type_maps_to_a_theme_colour(self):
        colors = get_theme()[1]
        for npc_type in ("specialist", "helper", "enemy", "quest", "boss"):
            style = npc_style_name(npc_type, colors, is_required=False)
            self.assertTrue(style.startswith("bold_"), msg=f"{npc_type} -> {style}")

    def test_unknown_npc_type_falls_back_to_the_specialist_colour(self):
        colors = _fake_colors()

        self.assertEqual(
            npc_style_name("mystery", colors, is_required=False),
            npc_style_name("specialist", colors, is_required=False),
        )

    def test_required_and_optional_emit_different_escape_sequences(self):
        """The regression guard: assert on real terminal output, not the name.

        The previous bug was invisible at the name level too -- both branches
        computed a *valid* attribute name, just the same one. Rendering through
        a real BlessedBackend is what proves the player sees a difference.
        """
        from blessed import Terminal

        from neural_dive.backends import BlessedBackend

        # Pin the terminal kind rather than inheriting $TERM. CI runs with
        # TERM=dumb, where force_styling still reports does_styling == True but
        # every capability is the empty string -- so all three renders came out
        # as a bare "A" and the test failed on the runner only.
        term = Terminal(kind="xterm-256color", force_styling=True)
        if not term.bold:
            self.skipTest("no terminfo entry for xterm-256color")
        backend = BlessedBackend(term)
        colors = get_theme()[1]

        def draw(is_required: bool, npc_type: str = "specialist") -> str:
            entity = Mock(x=0, y=0, char="A", npc_type=npc_type)
            return _render_and_capture(
                lambda: NPCRenderer().render(
                    term=backend,
                    entity=entity,
                    chars=_fake_chars(),
                    colors=colors,
                    is_required=is_required,
                )
            )

        required = draw(True)
        optional = draw(False)
        boss = draw(False, npc_type="boss")

        self.assertNotEqual(required, optional)
        self.assertNotEqual(boss, required)
        self.assertNotEqual(boss, optional)


if __name__ == "__main__":
    unittest.main()
