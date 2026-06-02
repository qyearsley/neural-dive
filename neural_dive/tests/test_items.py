"""Tests for the inventory item system.

Covers Item / HintToken / CodeSnippet construction and the ItemPickup
display-table dispatch (char + color resolved from ItemType).
"""

from __future__ import annotations

import unittest

from neural_dive.config import (
    ITEM_CHAR_CODE_SNIPPET,
    ITEM_CHAR_HINT_TOKEN,
    ITEM_COLOR_CODE_SNIPPET,
    ITEM_COLOR_HINT_TOKEN,
)
from neural_dive.items import (
    CodeSnippet,
    HintToken,
    Item,
    ItemPickup,
    ItemType,
)


class TestHintToken(unittest.TestCase):
    def test_default_eliminates_one(self):
        token = HintToken()
        self.assertEqual(token.answers_to_eliminate, 1)
        self.assertEqual(token.item_type, ItemType.HINT_TOKEN)
        self.assertEqual(token.name, "Hint Token")

    def test_custom_eliminate_count_in_description(self):
        token = HintToken(answers_to_eliminate=2)
        self.assertEqual(token.answers_to_eliminate, 2)
        self.assertIn("2", token.description)


class TestCodeSnippet(unittest.TestCase):
    def test_constructor_assigns_fields(self):
        snippet = CodeSnippet(
            name="DFS Reference",
            topic="algorithms",
            content=["line 1", "line 2"],
        )
        self.assertEqual(snippet.name, "DFS Reference")
        self.assertEqual(snippet.topic, "algorithms")
        self.assertEqual(snippet.content, ["line 1", "line 2"])
        self.assertEqual(snippet.item_type, ItemType.CODE_SNIPPET)
        self.assertIn("algorithms", snippet.description)


class TestItemPickup(unittest.TestCase):
    def test_hint_token_pickup_uses_hint_display(self):
        pickup = ItemPickup(3, 4, HintToken())
        self.assertEqual(pickup.x, 3)
        self.assertEqual(pickup.y, 4)
        self.assertEqual(pickup.char, ITEM_CHAR_HINT_TOKEN)
        self.assertEqual(pickup.color, ITEM_COLOR_HINT_TOKEN)

    def test_code_snippet_pickup_uses_snippet_display(self):
        snippet = CodeSnippet(name="Snip", topic="t", content=[])
        pickup = ItemPickup(0, 0, snippet)
        self.assertEqual(pickup.char, ITEM_CHAR_CODE_SNIPPET)
        self.assertEqual(pickup.color, ITEM_COLOR_CODE_SNIPPET)

    def test_repr_contains_item_name_and_position(self):
        pickup = ItemPickup(7, 9, HintToken())
        rep = repr(pickup)
        self.assertIn("Hint Token", rep)
        self.assertIn("7", rep)
        self.assertIn("9", rep)

    def test_display_table_covers_every_item_type(self):
        """Guard against adding a new ItemType without updating the dispatch table."""
        for item_type in ItemType:
            self.assertIn(
                item_type,
                ItemPickup._DISPLAY_BY_TYPE,
                msg=f"ItemPickup display table missing entry for {item_type}",
            )


class TestBaseItem(unittest.TestCase):
    def test_default_use_returns_false(self):
        item = Item(name="x", description="y", item_type=ItemType.HINT_TOKEN)
        self.assertFalse(item.use())


if __name__ == "__main__":
    unittest.main()
