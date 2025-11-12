"""
Tests for PlayerManager class.

This test module covers all player state management functionality including:
- Coherence gain/loss with caps
- Knowledge module acquisition
- State serialization/deserialization
- Edge cases and error conditions
"""

from __future__ import annotations

import unittest

from neural_dive.config import MAX_COHERENCE, STARTING_COHERENCE
from neural_dive.managers.player_manager import PlayerManager


class TestPlayerManagerInitialization(unittest.TestCase):
    """Test PlayerManager initialization."""

    def test_default_initialization(self):
        """Test PlayerManager initializes with default values."""
        pm = PlayerManager()

        self.assertEqual(pm.coherence, STARTING_COHERENCE)
        self.assertEqual(pm.max_coherence, MAX_COHERENCE)
        self.assertEqual(len(pm.knowledge_modules), 0)
        self.assertIsInstance(pm.knowledge_modules, set)

    def test_custom_initialization(self):
        """Test PlayerManager initializes with custom values."""
        pm = PlayerManager(
            coherence=50, max_coherence=120, knowledge_modules={"algorithms", "data_structures"}
        )

        self.assertEqual(pm.coherence, 50)
        self.assertEqual(pm.max_coherence, 120)
        self.assertEqual(len(pm.knowledge_modules), 2)
        self.assertIn("algorithms", pm.knowledge_modules)


class TestPlayerManagerCoherence(unittest.TestCase):
    """Test coherence gain/loss mechanics."""

    def test_gain_coherence_normal(self):
        """Test gaining coherence normally."""
        pm = PlayerManager(coherence=50)

        gained = pm.gain_coherence(10)

        self.assertEqual(gained, 10)
        self.assertEqual(pm.coherence, 60)

    def test_gain_coherence_capped_at_max(self):
        """Test that coherence gain is capped at maximum."""
        pm = PlayerManager(coherence=95, max_coherence=100)

        gained = pm.gain_coherence(10)

        self.assertEqual(gained, 5)  # Only gained 5
        self.assertEqual(pm.coherence, 100)  # Capped at max

    def test_gain_coherence_when_already_at_max(self):
        """Test gaining coherence when already at maximum."""
        pm = PlayerManager(coherence=100, max_coherence=100)

        gained = pm.gain_coherence(10)

        self.assertEqual(gained, 0)  # No gain
        self.assertEqual(pm.coherence, 100)  # Still at max

    def test_gain_coherence_negative_raises_error(self):
        """Test that gaining negative coherence raises ValueError."""
        pm = PlayerManager()

        with self.assertRaises(ValueError):
            pm.gain_coherence(-10)

    def test_gain_coherence_zero(self):
        """Test gaining zero coherence."""
        pm = PlayerManager(coherence=50)

        gained = pm.gain_coherence(0)

        self.assertEqual(gained, 0)
        self.assertEqual(pm.coherence, 50)

    def test_lose_coherence_normal(self):
        """Test losing coherence normally."""
        pm = PlayerManager(coherence=50)

        lost = pm.lose_coherence(10)

        self.assertEqual(lost, 10)
        self.assertEqual(pm.coherence, 40)

    def test_lose_coherence_floored_at_zero(self):
        """Test that coherence loss is floored at zero."""
        pm = PlayerManager(coherence=10)

        lost = pm.lose_coherence(30)

        self.assertEqual(lost, 10)  # Only lost 10
        self.assertEqual(pm.coherence, 0)  # Floored at 0

    def test_lose_coherence_when_already_at_zero(self):
        """Test losing coherence when already at zero."""
        pm = PlayerManager(coherence=0)

        lost = pm.lose_coherence(10)

        self.assertEqual(lost, 0)  # No loss
        self.assertEqual(pm.coherence, 0)  # Still at 0

    def test_lose_coherence_negative_raises_error(self):
        """Test that losing negative coherence raises ValueError."""
        pm = PlayerManager()

        with self.assertRaises(ValueError):
            pm.lose_coherence(-10)

    def test_lose_coherence_zero(self):
        """Test losing zero coherence."""
        pm = PlayerManager(coherence=50)

        lost = pm.lose_coherence(0)

        self.assertEqual(lost, 0)
        self.assertEqual(pm.coherence, 50)


class TestPlayerManagerKnowledge(unittest.TestCase):
    """Test knowledge module acquisition."""

    def test_add_knowledge_new_module(self):
        """Test adding a new knowledge module."""
        pm = PlayerManager()

        result = pm.add_knowledge("algorithms")

        self.assertTrue(result)  # Returns True for new module
        self.assertIn("algorithms", pm.knowledge_modules)
        self.assertEqual(pm.get_knowledge_count(), 1)

    def test_add_knowledge_duplicate_module(self):
        """Test adding a duplicate knowledge module."""
        pm = PlayerManager()
        pm.add_knowledge("algorithms")

        result = pm.add_knowledge("algorithms")  # Add again

        self.assertFalse(result)  # Returns False for duplicate
        self.assertEqual(pm.get_knowledge_count(), 1)  # Still only 1

    def test_add_multiple_knowledge_modules(self):
        """Test adding multiple different knowledge modules."""
        pm = PlayerManager()

        pm.add_knowledge("algorithms")
        pm.add_knowledge("data_structures")
        pm.add_knowledge("systems")

        self.assertEqual(pm.get_knowledge_count(), 3)
        self.assertIn("algorithms", pm.knowledge_modules)
        self.assertIn("data_structures", pm.knowledge_modules)
        self.assertIn("systems", pm.knowledge_modules)

    def test_has_knowledge_existing(self):
        """Test checking for existing knowledge module."""
        pm = PlayerManager()
        pm.add_knowledge("algorithms")

        result = pm.has_knowledge("algorithms")

        self.assertTrue(result)

    def test_has_knowledge_non_existing(self):
        """Test checking for non-existing knowledge module."""
        pm = PlayerManager()

        result = pm.has_knowledge("algorithms")

        self.assertFalse(result)

    def test_get_knowledge_count_empty(self):
        """Test getting knowledge count when empty."""
        pm = PlayerManager()

        count = pm.get_knowledge_count()

        self.assertEqual(count, 0)

    def test_get_knowledge_count_multiple(self):
        """Test getting knowledge count with multiple modules."""
        pm = PlayerManager()
        pm.add_knowledge("mod1")
        pm.add_knowledge("mod2")
        pm.add_knowledge("mod3")

        count = pm.get_knowledge_count()

        self.assertEqual(count, 3)


class TestPlayerManagerStatus(unittest.TestCase):
    """Test player status checks."""

    def test_is_alive_with_positive_coherence(self):
        """Test is_alive returns True with positive coherence."""
        pm = PlayerManager(coherence=50)

        self.assertTrue(pm.is_alive())

    def test_is_alive_with_zero_coherence(self):
        """Test is_alive returns False with zero coherence."""
        pm = PlayerManager(coherence=0)

        self.assertFalse(pm.is_alive())

    def test_is_alive_at_max_coherence(self):
        """Test is_alive returns True at maximum coherence."""
        pm = PlayerManager(coherence=100, max_coherence=100)

        self.assertTrue(pm.is_alive())

    def test_is_alive_after_taking_fatal_damage(self):
        """Test is_alive returns False after coherence drops to zero."""
        pm = PlayerManager(coherence=30)

        pm.lose_coherence(30)

        self.assertFalse(pm.is_alive())


class TestPlayerManagerSerialization(unittest.TestCase):
    """Test state serialization and deserialization."""

    def test_to_dict_default_state(self):
        """Test serializing default player state."""
        pm = PlayerManager()

        data = pm.to_dict()

        self.assertEqual(data["coherence"], STARTING_COHERENCE)
        self.assertEqual(data["max_coherence"], MAX_COHERENCE)
        self.assertEqual(len(data["knowledge_modules"]), 0)

    def test_to_dict_with_knowledge(self):
        """Test serializing player state with knowledge modules."""
        pm = PlayerManager()
        pm.add_knowledge("algorithms")
        pm.add_knowledge("data_structures")

        data = pm.to_dict()

        self.assertEqual(len(data["knowledge_modules"]), 2)
        self.assertIn("algorithms", data["knowledge_modules"])
        self.assertIn("data_structures", data["knowledge_modules"])

    def test_to_dict_with_modified_coherence(self):
        """Test serializing player state with modified coherence."""
        pm = PlayerManager(coherence=65)
        pm.gain_coherence(10)

        data = pm.to_dict()

        self.assertEqual(data["coherence"], 75)

    def test_from_dict_default_values(self):
        """Test deserializing with default values."""
        data = {"coherence": 85, "max_coherence": 100, "knowledge_modules": []}

        pm = PlayerManager.from_dict(data)

        self.assertEqual(pm.coherence, 85)
        self.assertEqual(pm.max_coherence, 100)
        self.assertEqual(pm.get_knowledge_count(), 0)

    def test_from_dict_with_knowledge(self):
        """Test deserializing with knowledge modules."""
        data = {
            "coherence": 90,
            "max_coherence": 100,
            "knowledge_modules": ["algorithms", "data_structures", "systems"],
        }

        pm = PlayerManager.from_dict(data)

        self.assertEqual(pm.coherence, 90)
        self.assertEqual(pm.get_knowledge_count(), 3)
        self.assertTrue(pm.has_knowledge("algorithms"))
        self.assertTrue(pm.has_knowledge("data_structures"))
        self.assertTrue(pm.has_knowledge("systems"))

    def test_from_dict_missing_keys_uses_defaults(self):
        """Test deserializing with missing keys uses default values."""
        data: dict[str, object] = {}  # Empty dict

        pm = PlayerManager.from_dict(data)

        self.assertEqual(pm.coherence, STARTING_COHERENCE)
        self.assertEqual(pm.max_coherence, MAX_COHERENCE)
        self.assertEqual(pm.get_knowledge_count(), 0)

    def test_round_trip_serialization(self):
        """Test that serialization and deserialization preserves state."""
        original = PlayerManager(coherence=75, max_coherence=120)
        original.add_knowledge("algorithms")
        original.add_knowledge("data_structures")

        # Serialize then deserialize
        data = original.to_dict()
        restored = PlayerManager.from_dict(data)

        # Verify state is preserved
        self.assertEqual(restored.coherence, 75)
        self.assertEqual(restored.max_coherence, 120)
        self.assertEqual(restored.get_knowledge_count(), 2)
        self.assertTrue(restored.has_knowledge("algorithms"))
        self.assertTrue(restored.has_knowledge("data_structures"))


if __name__ == "__main__":
    unittest.main()
