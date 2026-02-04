"""Tests for event system.

This module tests the event-driven architecture including event classes
and the EventBus dispatcher.
"""

from __future__ import annotations

import unittest

from neural_dive.events import (
    CoherenceChanged,
    ConversationStateChanged,
    EventBus,
    FloorChanged,
    GameEvent,
    GameOver,
    GameWon,
    ItemPickedUp,
    NPCDefeated,
    PlayerMoved,
    QuestActivated,
    QuestCompleted,
)


class TestEventClasses(unittest.TestCase):
    """Test event dataclasses."""

    def test_player_moved_event(self):
        """Test PlayerMoved event creation."""
        event = PlayerMoved((5, 10), (6, 10))
        self.assertEqual(event.old_pos, (5, 10))
        self.assertEqual(event.new_pos, (6, 10))
        self.assertIsInstance(event, GameEvent)

    def test_coherence_changed_event(self):
        """Test CoherenceChanged event creation."""
        event = CoherenceChanged(80, 90, "correct_answer")
        self.assertEqual(event.old, 80)
        self.assertEqual(event.new, 90)
        self.assertEqual(event.reason, "correct_answer")

    def test_conversation_state_changed_event(self):
        """Test ConversationStateChanged event creation."""
        event = ConversationStateChanged("started", "ALGO_SPIRIT")
        self.assertEqual(event.stage, "started")
        self.assertEqual(event.npc_name, "ALGO_SPIRIT")

    def test_item_picked_up_event(self):
        """Test ItemPickedUp event creation."""
        event = ItemPickedUp("Hint Token", "hint_token")
        self.assertEqual(event.item_name, "Hint Token")
        self.assertEqual(event.item_type, "hint_token")

    def test_floor_changed_event(self):
        """Test FloorChanged event creation."""
        event = FloorChanged(1, 2, "down")
        self.assertEqual(event.old_floor, 1)
        self.assertEqual(event.new_floor, 2)
        self.assertEqual(event.direction, "down")

    def test_game_won_event(self):
        """Test GameWon event creation."""
        event = GameWon(1500, 300.5)
        self.assertEqual(event.final_score, 1500)
        self.assertEqual(event.time_played, 300.5)

    def test_game_over_event(self):
        """Test GameOver event creation."""
        event = GameOver("coherence_lost")
        self.assertEqual(event.reason, "coherence_lost")

    def test_npc_defeated_event(self):
        """Test NPCDefeated event creation."""
        event = NPCDefeated("ALGO_SPIRIT", "specialist", 3, 3)
        self.assertEqual(event.npc_name, "ALGO_SPIRIT")
        self.assertEqual(event.npc_type, "specialist")
        self.assertEqual(event.correct_answers, 3)
        self.assertEqual(event.total_questions, 3)

    def test_quest_activated_event(self):
        """Test QuestActivated event creation."""
        event = QuestActivated("main_quest", ["NPC1", "NPC2"])
        self.assertEqual(event.quest_id, "main_quest")
        self.assertEqual(event.required_npcs, ["NPC1", "NPC2"])

    def test_quest_completed_event(self):
        """Test QuestCompleted event creation."""
        event = QuestCompleted("main_quest", 20)
        self.assertEqual(event.quest_id, "main_quest")
        self.assertEqual(event.bonus_coherence, 20)


class TestEventBus(unittest.TestCase):
    """Test EventBus dispatcher."""

    def setUp(self):
        """Set up test fixtures."""
        self.event_bus = EventBus()

    def test_subscribe_and_publish(self):
        """Test subscribing to and publishing events."""
        received_events = []

        def handler(event: PlayerMoved):
            received_events.append(event)

        self.event_bus.subscribe(PlayerMoved, handler)
        event = PlayerMoved((5, 10), (6, 10))
        self.event_bus.publish(event)

        self.assertEqual(len(received_events), 1)
        self.assertEqual(received_events[0], event)

    def test_multiple_subscribers(self):
        """Test multiple subscribers for same event type."""
        received1 = []
        received2 = []

        def handler1(event: PlayerMoved):
            received1.append(event)

        def handler2(event: PlayerMoved):
            received2.append(event)

        self.event_bus.subscribe(PlayerMoved, handler1)
        self.event_bus.subscribe(PlayerMoved, handler2)

        event = PlayerMoved((5, 10), (6, 10))
        self.event_bus.publish(event)

        self.assertEqual(len(received1), 1)
        self.assertEqual(len(received2), 1)
        self.assertEqual(received1[0], event)
        self.assertEqual(received2[0], event)

    def test_different_event_types(self):
        """Test subscribing to different event types."""
        player_moves = []
        coherence_changes = []

        def move_handler(event: PlayerMoved):
            player_moves.append(event)

        def coherence_handler(event: CoherenceChanged):
            coherence_changes.append(event)

        self.event_bus.subscribe(PlayerMoved, move_handler)
        self.event_bus.subscribe(CoherenceChanged, coherence_handler)

        move_event = PlayerMoved((5, 10), (6, 10))
        coherence_event = CoherenceChanged(80, 90, "correct_answer")

        self.event_bus.publish(move_event)
        self.event_bus.publish(coherence_event)

        self.assertEqual(len(player_moves), 1)
        self.assertEqual(len(coherence_changes), 1)
        self.assertEqual(player_moves[0], move_event)
        self.assertEqual(coherence_changes[0], coherence_event)

    def test_unsubscribe(self):
        """Test unsubscribing from events."""
        received = []

        def handler(event: PlayerMoved):
            received.append(event)

        self.event_bus.subscribe(PlayerMoved, handler)
        event1 = PlayerMoved((5, 10), (6, 10))
        self.event_bus.publish(event1)

        self.assertEqual(len(received), 1)

        # Unsubscribe
        self.event_bus.unsubscribe(PlayerMoved, handler)
        event2 = PlayerMoved((6, 10), (7, 10))
        self.event_bus.publish(event2)

        # Should still be 1
        self.assertEqual(len(received), 1)

    def test_publish_without_subscribers(self):
        """Test publishing event with no subscribers (should not error)."""
        event = PlayerMoved((5, 10), (6, 10))
        # Should not raise an error
        self.event_bus.publish(event)

    def test_clear_all(self):
        """Test clearing all event listeners."""
        received = []

        def handler(event: PlayerMoved):
            received.append(event)

        self.event_bus.subscribe(PlayerMoved, handler)
        self.event_bus.clear_all()

        event = PlayerMoved((5, 10), (6, 10))
        self.event_bus.publish(event)

        # Should receive nothing
        self.assertEqual(len(received), 0)

    def test_get_listener_count(self):
        """Test getting listener count."""
        self.assertEqual(self.event_bus.get_listener_count(PlayerMoved), 0)

        def handler1(event: PlayerMoved):
            pass

        def handler2(event: PlayerMoved):
            pass

        self.event_bus.subscribe(PlayerMoved, handler1)
        self.assertEqual(self.event_bus.get_listener_count(PlayerMoved), 1)

        self.event_bus.subscribe(PlayerMoved, handler2)
        self.assertEqual(self.event_bus.get_listener_count(PlayerMoved), 2)

        self.event_bus.unsubscribe(PlayerMoved, handler1)
        self.assertEqual(self.event_bus.get_listener_count(PlayerMoved), 1)


if __name__ == "__main__":
    unittest.main()
