"""
Manager classes for Neural Dive game.

This package contains manager classes that handle specific aspects of game state:
- PlayerManager: Manages player stats (coherence, knowledge modules)
- NPCManager: Manages NPC placement, relationships, and AI
- ConversationEngine: Manages conversation state and answer processing

These managers are extracted from the main Game class to improve
maintainability, testability, and adherence to Single Responsibility Principle.
"""

from __future__ import annotations

from neural_dive.managers.npc_manager import NPCManager
from neural_dive.managers.player_manager import PlayerManager

__all__ = ["NPCManager", "PlayerManager"]
