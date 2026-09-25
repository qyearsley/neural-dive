"""Tests for the NPC units NPCManager composes.

These exercise spawning, movement, and opinion tracking directly, without
building a Game or an NPCManager -- which is the point of having them separate.
"""

from __future__ import annotations

import random
import unittest

from neural_dive.config import (
    ENEMY_CHASE_RADIUS,
    ENEMY_CHASE_SPEED,
    ENEMY_GIVE_UP_RADIUS,
    NPC_MOVEMENT_SPEEDS,
    NPC_WANDER_RADIUS,
)
from neural_dive.entities import Entity
from neural_dive.managers.npc_movement import NPCMovement
from neural_dive.managers.npc_relationships import NPCRelationships
from neural_dive.managers.npc_spawning import NPCSpawner


def _npc_data() -> dict:
    return {
        "ALPHA": {"char": "A", "color": "cyan", "floor": 1, "npc_type": "specialist"},
        "BETA": {"char": "B", "color": "red", "floor": 1, "npc_type": "enemy"},
        "DEEP": {"char": "D", "color": "blue", "floor": 2, "npc_type": "specialist"},
    }


def _open_map(width: int = 20, height: int = 10) -> list[list[str]]:
    """A map that is all floor except for a wall border."""
    return [
        ["#" if (x in (0, width - 1) or y in (0, height - 1)) else "." for x in range(width)]
        for y in range(height)
    ]


class TestNPCSpawner(unittest.TestCase):
    def setUp(self) -> None:
        self.level_data = {
            1: {"npc_positions": {"A": [(3, 3)], "B": [(5, 5)]}},
            2: {"npc_positions": {"D": [(7, 7)]}},
        }

    def test_places_only_the_npcs_belonging_to_the_floor(self):
        spawner = NPCSpawner(_npc_data(), random.Random(1), self.level_data)

        placed = spawner.generate_for_floor(1, _open_map(), (1, 1), False, 20, 10)

        self.assertEqual(sorted(npc.name for npc in placed), ["ALPHA", "BETA"])

    def test_uses_the_positions_from_the_level_layout(self):
        spawner = NPCSpawner(_npc_data(), random.Random(1), self.level_data)

        placed = spawner.generate_for_floor(1, _open_map(), (1, 1), False, 20, 10)

        by_name = {npc.name: (npc.x, npc.y) for npc in placed}
        self.assertEqual(by_name["ALPHA"], (3, 3))
        self.assertEqual(by_name["BETA"], (5, 5))

    def test_does_not_consume_the_level_data(self):
        # Regenerating a floor must place the same NPCs again -- loading a save
        # generates the saved floor a second time.
        spawner = NPCSpawner(_npc_data(), random.Random(1), self.level_data)

        first = spawner.generate_for_floor(1, _open_map(), (1, 1), False, 20, 10)
        second = spawner.generate_for_floor(1, _open_map(), (1, 1), False, 20, 10)

        self.assertEqual(
            sorted((n.name, n.x, n.y) for n in first),
            sorted((n.name, n.x, n.y) for n in second),
        )

    def test_two_npcs_sharing_a_char_get_different_positions(self):
        npc_data = {
            "TWIN_ONE": {"char": "T", "color": "cyan", "floor": 1, "npc_type": "specialist"},
            "TWIN_TWO": {"char": "T", "color": "cyan", "floor": 1, "npc_type": "specialist"},
        }
        level_data = {1: {"npc_positions": {"T": [(2, 2), (8, 8)]}}}
        spawner = NPCSpawner(npc_data, random.Random(1), level_data)

        placed = spawner.generate_for_floor(1, _open_map(), (1, 1), False, 20, 10)

        positions = {(npc.x, npc.y) for npc in placed}
        self.assertEqual(positions, {(2, 2), (8, 8)})

    def test_remembers_every_npc_it_has_created(self):
        spawner = NPCSpawner(_npc_data(), random.Random(1), self.level_data)

        spawner.generate_for_floor(1, _open_map(), (1, 1), False, 20, 10)
        spawner.generate_for_floor(2, _open_map(), (1, 1), False, 20, 10)

        self.assertEqual(sorted(npc.name for npc in spawner.all_npcs), ["ALPHA", "BETA", "DEEP"])

    def test_does_not_record_the_same_npc_twice(self):
        spawner = NPCSpawner(_npc_data(), random.Random(1), self.level_data)

        spawner.generate_for_floor(1, _open_map(), (1, 1), False, 20, 10)
        spawner.generate_for_floor(1, _open_map(), (1, 1), False, 20, 10)

        self.assertEqual(len(spawner.all_npcs), 2)

    def test_places_randomly_when_the_floor_has_no_layout(self):
        spawner = NPCSpawner(_npc_data(), random.Random(1), level_data={})

        placed = spawner.generate_for_floor(1, _open_map(40, 20), (1, 1), True, 40, 20)

        self.assertEqual(sorted(npc.name for npc in placed), ["ALPHA", "BETA"])
        for npc in placed:
            self.assertEqual(_open_map(40, 20)[npc.y][npc.x], ".")

    def test_places_nothing_without_a_layout_or_random_placement(self):
        spawner = NPCSpawner(_npc_data(), random.Random(1), level_data={})

        placed = spawner.generate_for_floor(1, _open_map(), (1, 1), False, 20, 10)

        self.assertEqual(placed, [])


class TestNPCMovement(unittest.TestCase):
    def _wandering_npc(self, x: int = 5, y: int = 5) -> Entity:
        """An NPC primed to move on the next update."""
        npc = Entity(x, y, "A", "cyan", "ALPHA", npc_type="specialist")
        npc.home_x, npc.home_y = x, y
        npc.wander_state = "wander"
        npc.wander_ticks_remaining = 10
        npc.move_cooldown = 0
        return npc

    def test_conversation_freezes_npcs(self):
        movement = NPCMovement(random.Random(1))
        npc = self._wandering_npc()
        before = (npc.x, npc.y)

        movement.update([npc], _open_map(), (1, 1), is_conversation_active=True)

        self.assertEqual((npc.x, npc.y), before)
        self.assertEqual(movement.old_positions, {})

    def test_records_the_tile_an_npc_left(self):
        movement = NPCMovement(random.Random(1))
        npc = self._wandering_npc()
        before = (npc.x, npc.y)

        # Several ticks so at least one move lands
        for _ in range(20):
            movement.update([npc], _open_map(), (1, 1), is_conversation_active=False)

        self.assertIn("ALPHA", movement.old_positions)
        self.assertNotEqual((npc.x, npc.y), before)

    def test_npcs_stay_on_walkable_tiles(self):
        movement = NPCMovement(random.Random(7))
        game_map = _open_map()
        npc = self._wandering_npc()

        for _ in range(200):
            movement.update([npc], game_map, (1, 1), is_conversation_active=False)
            self.assertEqual(game_map[npc.y][npc.x], ".")

    def test_npcs_never_step_onto_the_player(self):
        movement = NPCMovement(random.Random(3))
        game_map = _open_map()
        npc = self._wandering_npc(5, 5)
        player = (6, 5)

        for _ in range(200):
            movement.update([npc], game_map, player, is_conversation_active=False)
            self.assertNotEqual((npc.x, npc.y), player)

    def test_npcs_do_not_stack_on_each_other(self):
        movement = NPCMovement(random.Random(5))
        game_map = _open_map()
        first = self._wandering_npc(5, 5)
        second = self._wandering_npc(6, 5)
        second.name = "BETA"

        for _ in range(200):
            movement.update([first, second], game_map, (1, 1), is_conversation_active=False)
            self.assertNotEqual((first.x, first.y), (second.x, second.y))

    def test_movement_speed_sets_the_cooldown(self):
        movement = NPCMovement(random.Random(1))
        npc = self._wandering_npc()

        movement.update([npc], _open_map(), (1, 1), is_conversation_active=False)

        self.assertEqual(npc.move_cooldown, NPC_MOVEMENT_SPEEDS["specialist"])

    def test_an_npc_far_from_home_heads_back(self):
        movement = NPCMovement(random.Random(1))
        npc = self._wandering_npc(5, 5)
        # Home far to the right, well beyond the wander radius
        npc.home_x = 5 + NPC_WANDER_RADIUS + 5
        npc.home_y = 5
        self.assertTrue(npc.should_return_home(NPC_WANDER_RADIUS))

        start_distance = abs(npc.x - npc.home_x)
        for _ in range(40):
            movement.update([npc], _open_map(40, 10), (1, 1), is_conversation_active=False)

        self.assertLess(abs(npc.x - npc.home_x), start_distance)


class TestNPCRelationships(unittest.TestCase):
    def test_an_unknown_npc_is_neutral(self):
        self.assertEqual(NPCRelationships().get_opinion("NOBODY"), 0)

    def test_update_starts_an_unknown_npc_from_neutral(self):
        relationships = NPCRelationships()

        relationships.update_opinion("ALPHA", 1)

        self.assertEqual(relationships.get_opinion("ALPHA"), 1)

    def test_opinions_accumulate(self):
        relationships = NPCRelationships()

        relationships.update_opinion("ALPHA", 2)
        relationships.update_opinion("ALPHA", -3)

        self.assertEqual(relationships.get_opinion("ALPHA"), -1)

    def test_npcs_are_tracked_separately(self):
        relationships = NPCRelationships()

        relationships.update_opinion("ALPHA", 1)
        relationships.update_opinion("BETA", -1)

        self.assertEqual(relationships.get_opinion("ALPHA"), 1)
        self.assertEqual(relationships.get_opinion("BETA"), -1)


if __name__ == "__main__":
    unittest.main()


class TestEnemyPursuit(unittest.TestCase):
    def _enemy(self, x: int = 5, y: int = 5) -> Entity:
        """An idle enemy, so any move it makes comes from the chase."""
        npc = Entity(x, y, "B", "red", "BETA", npc_type="enemy")
        npc.wander_state = "idle"
        npc.wander_ticks_remaining = 1000
        return npc

    def _tick(self, movement: NPCMovement, npc: Entity, game_map, player, beaten=()) -> None:
        movement.update([npc], game_map, player, is_conversation_active=False, beaten=beaten)

    def test_an_enemy_in_range_closes_in(self):
        movement = NPCMovement(random.Random(1))
        npc = self._enemy(5, 5)
        player = (5 + ENEMY_CHASE_RADIUS, 5)

        for _ in range(ENEMY_CHASE_SPEED * 10):
            self._tick(movement, npc, _open_map(), player)

        # Stops next to the player, never on it
        self.assertEqual((npc.x, npc.y), (player[0] - 1, 5))

    def test_chasing_uses_the_chase_speed(self):
        movement = NPCMovement(random.Random(1))
        npc = self._enemy(5, 5)

        self._tick(movement, npc, _open_map(), (9, 5))

        self.assertEqual((npc.x, npc.y), (6, 5))
        self.assertEqual(npc.move_cooldown, ENEMY_CHASE_SPEED)

    def test_an_enemy_out_of_range_does_not_chase(self):
        movement = NPCMovement(random.Random(1))
        npc = self._enemy(2, 2)

        self._tick(movement, npc, _open_map(), (2 + ENEMY_CHASE_RADIUS + 1, 2))

        self.assertEqual((npc.x, npc.y), (2, 2))

    def test_a_chase_once_started_runs_out_to_the_give_up_radius(self):
        npc = self._enemy(2, 2)
        player = (2 + ENEMY_CHASE_RADIUS + 1, 2)
        self.assertFalse(NPCMovement.is_chasing(npc, player, ()))

        npc.chasing = True
        self.assertTrue(NPCMovement.is_chasing(npc, player, ()))
        self.assertFalse(NPCMovement.is_chasing(npc, (2 + ENEMY_GIVE_UP_RADIUS + 1, 2), ()))

    def test_a_beaten_enemy_does_not_chase(self):
        movement = NPCMovement(random.Random(1))
        npc = self._enemy(5, 5)

        self._tick(movement, npc, _open_map(), (9, 5), beaten={"BETA"})

        self.assertEqual((npc.x, npc.y), (5, 5))

    def test_a_stunned_enemy_does_not_chase_until_the_stun_ends(self):
        movement = NPCMovement(random.Random(1))
        npc = self._enemy(5, 5)
        npc.stun_ticks = 2

        self._tick(movement, npc, _open_map(), (9, 5))
        self.assertEqual((npc.x, npc.y), (5, 5))
        self._tick(movement, npc, _open_map(), (9, 5))
        self.assertEqual((npc.x, npc.y), (6, 5))

    def test_specialists_never_chase(self):
        npc = Entity(5, 5, "A", "cyan", "ALPHA", npc_type="specialist")

        self.assertFalse(NPCMovement.is_chasing(npc, (6, 5), ()))

    def test_an_enemy_steps_around_a_wall(self):
        movement = NPCMovement(random.Random(1))
        game_map = _open_map()
        # A wall between the enemy and the player, open above and below
        game_map[5][6] = "#"
        npc = self._enemy(5, 5)

        self._tick(movement, npc, game_map, (9, 5))

        self.assertNotEqual((npc.x, npc.y), (5, 5))
        self.assertEqual(game_map[npc.y][npc.x], ".")
