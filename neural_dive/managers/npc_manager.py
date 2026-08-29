"""
NPC management for Neural Dive.

``NPCManager`` composes the three NPC concerns and owns the save format for all
of them:

- :class:`~neural_dive.managers.npc_spawning.NPCSpawner` -- creating and placing NPCs
- :class:`~neural_dive.managers.npc_movement.NPCMovement` -- wandering AI
- :class:`~neural_dive.managers.npc_relationships.NPCRelationships` -- opinions

Reach through to the unit that owns what you need (``manager.movement.old_positions``,
``manager.spawner.all_npcs``) rather than adding a forwarding property here.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from neural_dive.conversation import create_randomized_conversation
from neural_dive.data.levels import BOSS_NPCS
from neural_dive.entities import Entity
from neural_dive.managers.npc_movement import NPCMovement
from neural_dive.managers.npc_relationships import NPCRelationships
from neural_dive.managers.npc_spawning import NPCSpawner
from neural_dive.models import Conversation

if TYPE_CHECKING:
    import random

    from neural_dive.difficulty import DifficultySettings
    from neural_dive.player_profile import PlayerProfile


class NPCManager:
    """
    Composition root for NPC behaviour.

    Attributes:
        npcs: NPCs on the current floor
        conversations: Dictionary mapping NPC names to conversations
        spawner: Creates NPCs and holds ``all_npcs``
        movement: Wandering AI, holds ``old_positions``
        relationships: Opinion tracking
        profile: Cross-run question history used to bias question selection
    """

    def __init__(
        self,
        npc_data: dict,
        questions: dict,
        rng: random.Random,
        difficulty_settings: DifficultySettings,
        seed: int | None = None,
        level_data: dict | None = None,
        profile: PlayerProfile | None = None,
    ):
        """
        Initialize NPCManager.

        Args:
            npc_data: Dictionary of NPC definitions
            questions: Dictionary of all questions
            rng: Random number generator instance
            difficulty_settings: Difficulty settings for question counts
            seed: Random seed for reproducibility
            level_data: Dictionary of parsed level data (PARSED_LEVELS)
            profile: Cross-run question history. None -- or an empty profile --
                leaves question selection uniform, exactly as it was before
                history existed.
        """
        self.npc_data = npc_data
        self.questions = questions
        self.rng = rng
        self.difficulty_settings = difficulty_settings
        self.seed = seed
        self.level_data = level_data if level_data is not None else {}
        self.profile = profile

        self.spawner = NPCSpawner(npc_data, rng, self.level_data)
        self.movement = NPCMovement(rng)
        self.relationships = NPCRelationships()

        # NPCs on the current floor
        self.npcs: list[Entity] = []

        # One randomized conversation per NPC, built up front
        self.conversations: dict[str, Conversation] = self._build_conversations()

    def _build_conversations(self) -> dict[str, Conversation]:
        """Build a randomized conversation for every NPC in the content set.

        Which questions an NPC asks is drawn from that NPC's own pool, so the
        floor and topic structure is unaffected. When the player has history,
        the draw is weighted toward questions they have missed before.
        """
        # An empty profile is deliberately not passed through: it would produce
        # all-equal weights but consume the RNG differently, so a first-time
        # player's seeded run would no longer match previous builds.
        question_weight = None
        if self.profile is not None and not self.profile.is_empty:
            question_weight = self.profile.question_weighter()

        conversations: dict[str, Conversation] = {}
        for npc_name, npc_info in self.npc_data.items():
            if npc_name in BOSS_NPCS:
                num_questions = self.difficulty_settings.boss_questions
            else:
                min_q, max_q = self.difficulty_settings.questions_per_npc
                num_questions = self.rng.randint(min_q, max_q)

            conversations[npc_name] = create_randomized_conversation(
                npc_info["conversation"],
                randomize_question_order=True,
                randomize_answer_order=True,
                num_questions=num_questions,
                question_weight=question_weight,
            )
        return conversations

    def generate_npcs_for_floor(
        self,
        floor: int,
        game_map: list[list[str]],
        player_pos: tuple[int, int],
        random_placement: bool,
        map_width: int,
        map_height: int,
    ) -> list[Entity]:
        """
        Replace the current floor's NPCs with the ones belonging to ``floor``.

        Args:
            floor: Floor number to generate NPCs for
            game_map: 2D map array for collision detection
            player_pos: (x, y) position of player
            random_placement: Whether to use random placement (fallback mode)
            map_width: Map width for random placement
            map_height: Map height for random placement

        Returns:
            List of generated NPC entities
        """
        self.npcs = self.spawner.generate_for_floor(
            floor, game_map, player_pos, random_placement, map_width, map_height
        )
        return self.npcs

    def update_wandering(
        self,
        game_map: list[list[str]],
        player_pos: tuple[int, int],
        is_conversation_active: bool,
    ) -> None:
        """
        Update NPC wandering AI for the current floor.

        Args:
            game_map: 2D map array for collision detection
            player_pos: (x, y) position of player
            is_conversation_active: Whether a conversation is active (freezes NPCs)
        """
        self.movement.update(self.npcs, game_map, player_pos, is_conversation_active)

    def get_opinion(self, npc_name: str) -> int:
        """
        Get NPC's opinion of the player.

        Args:
            npc_name: Name of the NPC

        Returns:
            Opinion value (0 if not tracked)
        """
        return self.relationships.get_opinion(npc_name)

    def update_opinion(self, npc_name: str, delta: int) -> None:
        """
        Update NPC's opinion of the player.

        Args:
            npc_name: Name of the NPC
            delta: Change in opinion (positive or negative)
        """
        self.relationships.update_opinion(npc_name, delta)

    def get_conversation(self, npc_name: str) -> Conversation | None:
        """
        Get conversation for an NPC.

        Args:
            npc_name: Name of the NPC

        Returns:
            Conversation object or None if not found
        """
        return self.conversations.get(npc_name)

    def to_dict(self) -> dict:
        """
        Serialize NPCManager state to dictionary.

        Returns:
            Dictionary containing all NPCManager state
        """
        return {
            "npcs": [
                {
                    "name": npc.name,
                    "x": npc.x,
                    "y": npc.y,
                    "char": npc.char,
                    "color": npc.color,
                    "npc_type": npc.npc_type,
                    "home_x": npc.home_x,
                    "home_y": npc.home_y,
                    "wander_state": npc.wander_state,
                    "wander_ticks_remaining": npc.wander_ticks_remaining,
                    "move_cooldown": npc.move_cooldown,
                }
                for npc in self.spawner.all_npcs
            ],
            "npc_opinions": self.relationships.opinions,
            "conversations": {
                name: {
                    "completed": conv.completed,
                    "current_question_idx": conv.current_question_idx,
                }
                for name, conv in self.conversations.items()
            },
        }

    @classmethod
    def from_dict(
        cls,
        data: dict,
        npc_data: dict,
        questions: dict,
        rng: random.Random,
        difficulty_settings: DifficultySettings,
        seed: int | None = None,
        level_data: dict | None = None,
        profile: PlayerProfile | None = None,
    ) -> NPCManager:
        """
        Create NPCManager from serialized dictionary.

        Args:
            data: Serialized NPCManager state
            npc_data: NPC definitions
            questions: All questions
            rng: Random number generator
            difficulty_settings: Difficulty settings
            seed: Random seed
            level_data: Dictionary of parsed level data
            profile: Cross-run question history (None for none)

        Returns:
            Restored NPCManager instance
        """
        manager = cls(npc_data, questions, rng, difficulty_settings, seed, level_data, profile)

        # Restore NPC state
        for saved in data.get("npcs", []):
            npc = Entity(
                saved["x"],
                saved["y"],
                saved["char"],
                saved["color"],
                saved["name"],
                npc_type=saved.get("npc_type"),
            )
            npc.home_x = saved.get("home_x", npc.x)
            npc.home_y = saved.get("home_y", npc.y)
            npc.wander_state = saved.get("wander_state", "idle")
            npc.wander_ticks_remaining = saved.get("wander_ticks_remaining", 0)
            npc.move_cooldown = saved.get("move_cooldown", 0)
            manager.spawner.all_npcs.append(npc)

        # Restore opinions
        manager.relationships.opinions = data.get("npc_opinions", {})

        # Restore conversation state
        for name, state in data.get("conversations", {}).items():
            if name in manager.conversations:
                manager.conversations[name].completed = state.get("completed", False)
                manager.conversations[name].current_question_idx = state.get(
                    "current_question_idx", 0
                )

        return manager
