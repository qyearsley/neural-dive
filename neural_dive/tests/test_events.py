"""Tests for the event system: ItemPickedUp and the EventBus dispatcher."""

from __future__ import annotations

import unittest

from neural_dive.events import EventBus, GameEvent, ItemPickedUp


class TestItemPickedUp(unittest.TestCase):
    def test_item_picked_up_event(self):
        """Test ItemPickedUp event creation."""
        event = ItemPickedUp("Hint Token", "hint_token")
        self.assertEqual(event.item_name, "Hint Token")
        self.assertEqual(event.item_type, "hint_token")
        self.assertIsInstance(event, GameEvent)


class TestEventBus(unittest.TestCase):
    """Test EventBus dispatcher."""

    def setUp(self):
        self.event_bus = EventBus()

    def test_subscribe_and_publish(self):
        received: list[GameEvent] = []
        self.event_bus.subscribe(ItemPickedUp, received.append)
        event = ItemPickedUp("Hint Token", "hint_token")
        self.event_bus.publish(event)
        self.assertEqual(received, [event])

    def test_multiple_subscribers(self):
        received1: list[GameEvent] = []
        received2: list[GameEvent] = []
        self.event_bus.subscribe(ItemPickedUp, received1.append)
        self.event_bus.subscribe(ItemPickedUp, received2.append)
        event = ItemPickedUp("Hint Token", "hint_token")
        self.event_bus.publish(event)
        self.assertEqual(received1, [event])
        self.assertEqual(received2, [event])

    def test_subscriber_only_gets_its_event_type(self):
        class Other(GameEvent):
            pass

        received: list[GameEvent] = []
        self.event_bus.subscribe(ItemPickedUp, received.append)
        self.event_bus.publish(Other())
        self.assertEqual(received, [])

    def test_publish_without_subscribers(self):
        """Publishing with no subscribers does not raise."""
        self.event_bus.publish(ItemPickedUp("Hint Token", "hint_token"))


if __name__ == "__main__":
    unittest.main()
