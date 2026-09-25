"""An enemy that reaches the player opens its conversation, and fleeing stuns it."""

from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from neural_dive.config import ENEMY_STUN_TICKS
from neural_dive.entities import Entity
from neural_dive.game import Game


class TestEnemyAmbush(unittest.TestCase):
    def setUp(self) -> None:
        self.game = Game(seed=42, random_npcs=False)
        self.enemy = self._floor_enemy()

    def _floor_enemy(self) -> Entity:
        enemies = [npc for npc in self.game.npc_manager.npcs if npc.npc_type == "enemy"]
        self.assertTrue(enemies, "floor 1 should have an enemy")
        return enemies[0]

    def _stand_next_to_enemy(self) -> None:
        self.game.player.x = self.enemy.x - 1
        self.game.player.y = self.enemy.y

    def test_contact_opens_the_enemys_conversation(self):
        self._stand_next_to_enemy()

        self.assertTrue(self.game.check_ambush())

        active = self.game.conversation_engine.active_conversation
        assert active is not None
        self.assertEqual(active.npc_name, self.enemy.name)
        self.assertIn("corners you", self.game.message)

    def test_no_ambush_from_a_distance(self):
        self.game.player.x = self.enemy.x - 3
        self.game.player.y = self.enemy.y

        self.assertFalse(self.game.check_ambush())
        self.assertIsNone(self.game.conversation_engine.active_conversation)

    def test_fleeing_stuns_the_enemy(self):
        self._stand_next_to_enemy()
        self.game.check_ambush()

        self.game.exit_conversation()

        self.assertEqual(self.enemy.stun_ticks, ENEMY_STUN_TICKS)
        self.assertFalse(self.game.check_ambush())

    def test_a_beaten_enemy_does_not_ambush(self):
        self.game.npc_manager.conversations[self.enemy.name].completed = True
        self._stand_next_to_enemy()

        self.assertFalse(self.game.check_ambush())

    def test_no_ambush_while_an_answer_response_is_on_screen(self):
        self.game.conversation_engine.last_answer_response = "Correct!"
        self._stand_next_to_enemy()

        self.assertFalse(self.game.check_ambush())

    def test_the_stun_survives_a_save(self):
        self.enemy.stun_ticks = 17

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "save.json"
            ok, _ = self.game.save_game(path)
            self.assertTrue(ok)
            loaded = Game.load_game(path)

        assert loaded is not None
        restored = next(npc for npc in loaded.npc_manager.npcs if npc.name == self.enemy.name)
        self.assertEqual(restored.stun_ticks, 17)


if __name__ == "__main__":
    unittest.main()
