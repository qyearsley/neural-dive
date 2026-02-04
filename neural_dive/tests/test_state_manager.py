"""Tests for StateManager.

This module tests centralized state mutation management and event emission.
"""

from __future__ import annotations

import unittest

from neural_dive.events import (
    CoherenceChanged,
    ConversationStateChanged,
    EventBus,
    FloorChanged,
    GameOver,
    GameWon,
    NPCDefeated,
    PlayerMoved,
    QuestActivated,
    QuestCompleted,
)
from neural_dive.game import Game
from neural_dive.managers.state_manager import StateManager


class TestStateManager(unittest.TestCase):
    """Test StateManager functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.game = Game(
            map_width=50,
            map_height=25,
            seed=42,
            random_npcs=False,
            content_set="algorithms",
        )
        self.event_bus = EventBus()
        self.state_manager = StateManager(self.game, self.event_bus)

        # Track events
        self.events = []

        def track_event(event):
            self.events.append(event)

        # Subscribe to all event types
        for event_type in [
            PlayerMoved,
            CoherenceChanged,
            ConversationStateChanged,
            FloorChanged,
            GameOver,
            GameWon,
            NPCDefeated,
            QuestActivated,
            QuestCompleted,
        ]:
            self.event_bus.subscribe(event_type, track_event)

    def test_move_player_success(self):
        """Test successful player movement."""
        old_x, old_y = self.game.player.x, self.game.player.y

        # Move player right
        success = self.state_manager.move_player(1, 0)

        self.assertTrue(success)
        self.assertEqual(self.game.player.x, old_x + 1)
        self.assertEqual(self.game.player.y, old_y)

        # Check event
        self.assertEqual(len(self.events), 1)
        event = self.events[0]
        self.assertIsInstance(event, PlayerMoved)
        self.assertEqual(event.old_pos, (old_x, old_y))
        self.assertEqual(event.new_pos, (old_x + 1, old_y))

    def test_move_player_blocked(self):
        """Test player movement blocked by wall."""
        # Move player toward wall
        # Keep trying until we hit a wall or edge
        for _ in range(100):
            old_x = self.game.player.x
            success = self.state_manager.move_player(-1, 0)
            if not success:
                # Hit a wall
                self.assertEqual(self.game.player.x, old_x)
                break

    def test_change_coherence_increase(self):
        """Test increasing coherence."""
        old = self.game.coherence
        actual = self.state_manager.change_coherence(10, "test")

        self.assertEqual(actual, 10)
        self.assertEqual(self.game.coherence, old + 10)

        # Check event
        coherence_events = [e for e in self.events if isinstance(e, CoherenceChanged)]
        self.assertEqual(len(coherence_events), 1)
        event = coherence_events[0]
        self.assertEqual(event.old, old)
        self.assertEqual(event.new, old + 10)
        self.assertEqual(event.reason, "test")

    def test_change_coherence_decrease(self):
        """Test decreasing coherence."""
        old = self.game.coherence
        actual = self.state_manager.change_coherence(-10, "penalty")

        self.assertEqual(actual, -10)
        self.assertEqual(self.game.coherence, old - 10)

    def test_change_coherence_capped_at_max(self):
        """Test coherence capped at maximum."""
        old = self.game.coherence
        max_coh = self.game.max_coherence

        # Try to add more than maximum
        actual = self.state_manager.change_coherence(1000, "test")

        self.assertEqual(self.game.coherence, max_coh)
        self.assertEqual(actual, max_coh - old)

    def test_change_coherence_capped_at_zero(self):
        """Test coherence capped at zero."""
        # Reduce coherence to near zero
        self.game.coherence = 5

        actual = self.state_manager.change_coherence(-10, "test")

        self.assertEqual(self.game.coherence, 0)
        self.assertEqual(actual, -5)

        # Check for GameOver event
        game_over_events = [e for e in self.events if isinstance(e, GameOver)]
        self.assertEqual(len(game_over_events), 1)
        self.assertEqual(game_over_events[0].reason, "coherence_lost")

    def test_start_conversation(self):
        """Test starting conversation."""
        # Find an NPC
        if not self.game.npc_conversations:
            self.skipTest("No conversations available")

        npc_name = list(self.game.npc_conversations.keys())[0]
        success = self.state_manager.start_conversation(npc_name)

        self.assertTrue(success)
        self.assertIsNotNone(self.game.active_conversation)
        self.assertEqual(self.game.active_conversation.npc_name, npc_name)
        self.assertTrue(self.game.show_greeting)

        # Check event
        conv_events = [e for e in self.events if isinstance(e, ConversationStateChanged)]
        self.assertEqual(len(conv_events), 1)
        self.assertEqual(conv_events[0].stage, "started")
        self.assertEqual(conv_events[0].npc_name, npc_name)

    def test_start_conversation_already_completed(self):
        """Test cannot start conversation with completed NPC."""
        if not self.game.npc_conversations:
            self.skipTest("No conversations available")

        npc_name = list(self.game.npc_conversations.keys())[0]
        conversation = self.game.npc_conversations[npc_name]
        conversation.completed = True

        success = self.state_manager.start_conversation(npc_name)

        self.assertFalse(success)
        self.assertIsNone(self.game.active_conversation)

    def test_end_conversation(self):
        """Test ending conversation."""
        # Start conversation first
        if not self.game.npc_conversations:
            self.skipTest("No conversations available")

        npc_name = list(self.game.npc_conversations.keys())[0]
        self.state_manager.start_conversation(npc_name)
        self.events.clear()  # Clear start event

        success = self.state_manager.end_conversation()

        self.assertTrue(success)
        self.assertIsNone(self.game.active_conversation)
        self.assertFalse(self.game.show_greeting)

        # Check event
        conv_events = [e for e in self.events if isinstance(e, ConversationStateChanged)]
        self.assertEqual(len(conv_events), 1)
        self.assertEqual(conv_events[0].stage, "ended")

    def test_end_conversation_not_in_conversation(self):
        """Test ending conversation when not in one."""
        success = self.state_manager.end_conversation()

        self.assertFalse(success)

    def test_complete_conversation(self):
        """Test completing conversation emits NPC defeated event."""
        if not self.game.npc_conversations:
            self.skipTest("No conversations available")

        npc_name = list(self.game.npc_conversations.keys())[0]

        self.state_manager.complete_conversation(npc_name, 2, 3)

        # Check event
        npc_events = [e for e in self.events if isinstance(e, NPCDefeated)]
        self.assertEqual(len(npc_events), 1)
        event = npc_events[0]
        self.assertEqual(event.npc_name, npc_name)
        self.assertEqual(event.correct_answers, 2)
        self.assertEqual(event.total_questions, 3)

    def test_toggle_inventory(self):
        """Test toggling inventory."""
        old_state = self.game.active_inventory

        self.state_manager.toggle_inventory()
        self.assertEqual(self.game.active_inventory, not old_state)

        self.state_manager.toggle_inventory()
        self.assertEqual(self.game.active_inventory, old_state)

    def test_close_all_overlays(self):
        """Test closing all overlays."""
        self.game.active_inventory = True
        self.game.active_terminal = "test_terminal"
        self.game.active_snippet = "test_snippet"

        self.state_manager.close_all_overlays()

        self.assertFalse(self.game.active_inventory)
        self.assertIsNone(self.game.active_terminal)
        self.assertIsNone(self.game.active_snippet)

    def test_change_floor(self):
        """Test changing floor."""
        old_floor = self.game.current_floor

        self.state_manager.change_floor(old_floor + 1, "down")

        self.assertEqual(self.game.current_floor, old_floor + 1)

        # Check event
        floor_events = [e for e in self.events if isinstance(e, FloorChanged)]
        self.assertEqual(len(floor_events), 1)
        event = floor_events[0]
        self.assertEqual(event.old_floor, old_floor)
        self.assertEqual(event.new_floor, old_floor + 1)
        self.assertEqual(event.direction, "down")

    def test_activate_quest(self):
        """Test activating quest."""
        success, message = self.state_manager.activate_quest()

        self.assertTrue(success)
        self.assertTrue(self.game.quest_manager.quest_active)

        # Check event
        quest_events = [e for e in self.events if isinstance(e, QuestActivated)]
        self.assertEqual(len(quest_events), 1)
        event = quest_events[0]
        self.assertEqual(event.quest_id, "main_quest")
        self.assertEqual(event.required_npcs, [])

    def test_complete_quest(self):
        """Test completing quest."""
        # Activate quest first
        self.game.quest_manager.quest_active = True

        # Simulate completing required NPCs for quest
        from neural_dive.config import QUEST_TARGET_NPCS

        for npc in QUEST_TARGET_NPCS:
            self.game.quest_manager.completed_npcs.add(npc)

        self.events.clear()  # Clear activation event

        bonus = self.state_manager.complete_quest()

        self.assertGreater(bonus, 0)

        # Check events
        quest_events = [e for e in self.events if isinstance(e, QuestCompleted)]
        self.assertEqual(len(quest_events), 1)
        self.assertEqual(quest_events[0].quest_id, "main_quest")
        self.assertEqual(quest_events[0].bonus_coherence, bonus)

        # Should also have coherence change event
        coherence_events = [e for e in self.events if isinstance(e, CoherenceChanged)]
        self.assertEqual(len(coherence_events), 1)

    def test_trigger_victory(self):
        """Test triggering victory."""
        self.state_manager.trigger_victory()

        self.assertTrue(self.game.game_won)

        # Check event
        win_events = [e for e in self.events if isinstance(e, GameWon)]
        self.assertEqual(len(win_events), 1)
        event = win_events[0]
        self.assertGreater(event.final_score, 0)
        self.assertGreaterEqual(event.time_played, 0)

    def test_trigger_game_over(self):
        """Test triggering game over."""
        self.state_manager.trigger_game_over("quit")

        # Check event
        game_over_events = [e for e in self.events if isinstance(e, GameOver)]
        self.assertEqual(len(game_over_events), 1)
        self.assertEqual(game_over_events[0].reason, "quit")

    def test_is_in_conversation(self):
        """Test checking conversation state."""
        self.assertFalse(self.state_manager.is_in_conversation())

        if not self.game.npc_conversations:
            self.skipTest("No conversations available")

        npc_name = list(self.game.npc_conversations.keys())[0]
        self.state_manager.start_conversation(npc_name)

        self.assertTrue(self.state_manager.is_in_conversation())

    def test_is_overlay_active(self):
        """Test checking overlay state."""
        self.assertFalse(self.state_manager.is_overlay_active())

        self.game.active_inventory = True
        self.assertTrue(self.state_manager.is_overlay_active())

        self.game.active_inventory = False
        self.game.active_terminal = "test"
        self.assertTrue(self.state_manager.is_overlay_active())

    def test_can_move(self):
        """Test checking if player can move."""
        self.assertTrue(self.state_manager.can_move())

        self.game.active_inventory = True
        self.assertFalse(self.state_manager.can_move())

        self.game.active_inventory = False
        if self.game.npc_conversations:
            npc_name = list(self.game.npc_conversations.keys())[0]
            self.state_manager.start_conversation(npc_name)
            self.assertFalse(self.state_manager.can_move())


if __name__ == "__main__":
    unittest.main()
