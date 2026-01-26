"""Enumerations for Neural Dive game.

This module defines enum types used throughout the game for
type safety and consistent value handling.

Enums:
    NPCType: Types of NPCs with different behaviors and interactions
    QuestionType: Question formats (multiple choice, code output, etc.)
    ItemType: Types of collectible items in the game

Using enums instead of strings provides:
- Type checking and validation
- IDE autocompletion
- Compile-time error detection
- Centralized value definitions

Example usage:
    from neural_dive.enums import NPCType, ItemType

    # Create an NPC type
    npc_type = NPCType.SPECIALIST

    # Check item type
    if item.item_type == ItemType.HINT_TOKEN:
        use_hint()
"""

from enum import Enum


class NPCType(Enum):
    """Different types of NPCs with different behaviors."""

    SPECIALIST = "specialist"  # Standard quiz NPC
    HELPER = "helper"  # Gives hints, restores coherence
    ENEMY = "enemy"  # Hostile, harsher penalties
    QUEST = "quest"  # Gives quests to find other NPCs
    BOSS = "boss"  # Boss NPCs with 4 questions instead of 2-3
