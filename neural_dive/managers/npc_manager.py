"""
NPC management for Neural Dive.

This module provides the NPCManager class which handles all NPC-related
functionality including generation, placement, movement AI, and relationship tracking.
"""

from __future__ import annotations

import random
from typing import TYPE_CHECKING

from neural_dive.config import (
    NPC_IDLE_TICKS_MAX,
    NPC_IDLE_TICKS_MIN,
    NPC_MIN_DISTANCE_FROM_PLAYER,
    NPC_MOVEMENT_SPEEDS,
    NPC_PLACEMENT_ATTEMPTS,
    NPC_WANDER_ENABLED,
    NPC_WANDER_RADIUS,
    NPC_WANDER_TICKS_MAX,
    NPC_WANDER_TICKS_MIN,
)
from neural_dive.conversation import create_randomized_conversation
from neural_dive.data.levels import BOSS_NPCS
from neural_dive.entities import Entity
from neural_dive.models import Conversation

if TYPE_CHECKING:
    from neural_dive.difficulty import DifficultySettings


class NPCManager:
    """
    Manages all NPC-related functionality.

    The NPCManager encapsulates NPC generation, placement, movement AI,
    and relationship tracking. This makes it easier to:
    - Test NPC mechanics in isolation
    - Add new NPC types and behaviors
    - Track NPC state across floors
    - Modify AI behavior without touching game logic

    Attributes:
        npc_data: Dictionary of NPC definitions from JSON
        npcs: List of NPCs on the current floor
        all_npcs: List of all NPCs across all floors (for persistence)
        conversations: Dictionary mapping NPC names to conversations
        npc_opinions: Dictionary tracking player relationships with NPCs
        old_positions: Dictionary tracking previous NPC positions for rendering
        rng: Random number generator for consistent seeding
    """

    def __init__(
        self,
        npc_data: dict,
        questions: dict,
        rng: random.Random,
        difficulty_settings: DifficultySettings,
        seed: int | None = None,
        level_data: dict | None = None,
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
        """
        self.npc_data = npc_data
        self.questions = questions
        self.rng = rng
        self.difficulty_settings = difficulty_settings
        self.seed = seed
        self.level_data = level_data if level_data is not None else {}

        # Current floor NPCs
        self.npcs: list[Entity] = []

        # All NPCs across all floors (for persistence)
        self.all_npcs: list[Entity] = []

        # Conversations for each NPC
        self.conversations: dict[str, Conversation] = {}

        # NPC relationship tracking
        self.npc_opinions: dict[str, int] = {}

        # Track old NPC positions for rendering cleanup
        self.old_positions: dict[str, tuple[int, int]] = {}

        # Initialize conversations for all NPCs
        self._initialize_conversations()

    def _initialize_conversations(self):
        """Initialize randomized conversations for all NPCs."""
        for npc_name, npc_info in self.npc_data.items():
            conv_template = npc_info["conversation"]

            # Determine number of questions based on NPC type and difficulty
            is_boss = npc_name in BOSS_NPCS
            if is_boss:
                num_questions = self.difficulty_settings.boss_questions
            else:
                min_q, max_q = self.difficulty_settings.questions_per_npc
                num_questions = self.rng.randint(min_q, max_q)

            # Create randomized conversation
            self.conversations[npc_name] = create_randomized_conversation(
                conv_template,
                randomize_question_order=True,
                randomize_answer_order=True,
                num_questions=num_questions,
            )

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
        Generate NPCs for the given floor.

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
        # Clear current floor NPCs
        self.npcs = []

        # Get level data
        level_data = self.level_data.get(floor)

        # Get NPCs for this floor
        floor_npcs = [
            (npc_name, npc_info)
            for npc_name, npc_info in self.npc_data.items()
            if npc_info["floor"] == floor
        ]

        if level_data and "npc_positions" in level_data:
            # Use positions from level layout
            self._generate_from_level_data(floor_npcs, level_data)
        elif random_placement:
            # Random placement (fallback)
            self._generate_random_placement(floor_npcs, game_map, player_pos, map_width, map_height)

        return self.npcs

    def _generate_from_level_data(self, floor_npcs: list[tuple[str, dict]], level_data: dict):
        """Generate NPCs using positions from level data."""
        npc_positions_by_char = level_data["npc_positions"]

        for npc_name, npc_info in floor_npcs:
            npc_char = npc_info["char"]
            positions = npc_positions_by_char.get(npc_char, [])

            if positions:
                # Use first position for this character
                x, y = positions[0]
                # Remove position so next NPC with same char gets different position
                positions.pop(0)

                npc = Entity(
                    x,
                    y,
                    npc_char,
                    npc_info["color"],
                    npc_name,
                    npc_type=npc_info.get("npc_type", "specialist"),
                )
                self.npcs.append(npc)

                # Add to all_npcs if not already there
                if not any(n.name == npc_name for n in self.all_npcs):
                    self.all_npcs.append(npc)

    def _generate_random_placement(
        self,
        floor_npcs: list[tuple[str, dict]],
        game_map: list[list[str]],
        player_pos: tuple[int, int],
        map_width: int,
        map_height: int,
    ):
        """Generate NPCs using random placement with EntityPlacementStrategy."""
        from neural_dive.placement import EntityPlacementStrategy

        strategy = EntityPlacementStrategy(
            game_map=game_map,
            random_mode=True,
            rng=self.rng,
            map_width=map_width,
            map_height=map_height,
        )

        for npc_name, npc_info in floor_npcs:
            # Generate one random position per NPC
            positions = strategy.place_entities(
                level_positions=None,
                default_positions=None,
                num_attempts=NPC_PLACEMENT_ATTEMPTS,
                min_distance_from=player_pos,
                min_distance=NPC_MIN_DISTANCE_FROM_PLAYER,
                x_range=(10, map_width - 2),
                y_range=(5, map_height - 2),
                count=1,
            )

            if positions:
                x, y = positions[0]
                npc = Entity(
                    x,
                    y,
                    npc_info["char"],
                    npc_info["color"],
                    npc_name,
                    npc_type=npc_info.get("npc_type", "specialist"),
                )
                self.npcs.append(npc)

                # Add to all_npcs if not already there
                if not any(n.name == npc_name for n in self.all_npcs):
                    self.all_npcs.append(npc)

    def update_wandering(
        self,
        game_map: list[list[str]],
        player_pos: tuple[int, int],
        is_conversation_active: bool,
    ):
        """
        Update NPC wandering AI.

        NPCs alternate between idle and wander states. During wander state,
        they move slowly in random directions. Different NPC types have different
        movement speeds and behaviors.

        Args:
            game_map: 2D map array for collision detection
            player_pos: (x, y) position of player
            is_conversation_active: Whether a conversation is active (freezes NPCs)
        """
        if not NPC_WANDER_ENABLED:
            return

        # Freeze NPC movement during conversations
        if is_conversation_active:
            return

        player_x, player_y = player_pos

        for npc in self.npcs:
            # Decrement move cooldown
            if npc.move_cooldown > 0:
                npc.move_cooldown -= 1

            # Decrement state timer
            npc.wander_ticks_remaining -= 1

            # Check if need to switch states
            if npc.wander_ticks_remaining <= 0:
                if npc.wander_state == "idle":
                    # Switch to wander
                    npc.wander_state = "wander"
                    npc.wander_ticks_remaining = self.rng.randint(
                        NPC_WANDER_TICKS_MIN, NPC_WANDER_TICKS_MAX
                    )
                else:
                    # Switch to idle
                    npc.wander_state = "idle"
                    npc.wander_ticks_remaining = self.rng.randint(
                        NPC_IDLE_TICKS_MIN, NPC_IDLE_TICKS_MAX
                    )

            # Move if in wander state and cooldown expired
            if npc.wander_state == "wander" and npc.move_cooldown <= 0:
                self._move_npc(npc, game_map, player_x, player_y)

    def _move_npc(
        self,
        npc: Entity,
        game_map: list[list[str]],
        player_x: int,
        player_y: int,
    ):
        """
        Move a single NPC based on AI behavior.

        Args:
            npc: The NPC entity to move
            game_map: 2D map array for collision detection
            player_x: Player X position
            player_y: Player Y position
        """
        # Get movement speed for this NPC type
        npc_type = npc.npc_type or "specialist"
        move_speed = NPC_MOVEMENT_SPEEDS.get(npc_type, 2)

        # Reset cooldown
        npc.move_cooldown = move_speed

        # Determine direction
        # If too far from home, move towards home
        if npc.should_return_home(NPC_WANDER_RADIUS):
            dx, dy = self._get_home_direction(npc)
        else:
            # Random movement
            dx = self.rng.choice([-1, 0, 1])
            dy = self.rng.choice([-1, 0, 1])

        # Try to move
        new_x = npc.x + dx
        new_y = npc.y + dy

        # Check if new position is valid
        if self._is_valid_npc_position(new_x, new_y, game_map, player_x, player_y, npc):
            # Track old position for rendering cleanup
            self.old_positions[npc.name] = (npc.x, npc.y)
            # Move NPC
            npc.x = new_x
            npc.y = new_y

    def _get_home_direction(self, npc: Entity) -> tuple[int, int]:
        """
        Calculate direction towards NPC's home position.

        Args:
            npc: The NPC entity

        Returns:
            Tuple of (dx, dy) movement direction
        """
        dx = 0
        dy = 0

        if npc.x < npc.home_x:
            dx = 1
        elif npc.x > npc.home_x:
            dx = -1

        if npc.y < npc.home_y:
            dy = 1
        elif npc.y > npc.home_y:
            dy = -1

        # Sometimes move in both directions, sometimes just one
        if self.rng.random() < 0.5 and dx != 0:
            dy = 0
        elif dy != 0:
            dx = 0

        return dx, dy

    def _is_valid_npc_position(
        self,
        x: int,
        y: int,
        game_map: list[list[str]],
        player_x: int,
        player_y: int,
        moving_npc: Entity,
    ) -> bool:
        """
        Check if a position is valid for NPC movement.

        Args:
            x: Target X position
            y: Target Y position
            game_map: 2D map array
            player_x: Player X position
            player_y: Player Y position
            moving_npc: The NPC that is moving

        Returns:
            True if position is valid
        """
        # Check bounds
        if y < 0 or y >= len(game_map) or x < 0 or x >= len(game_map[0]):
            return False

        # Check walkable
        if game_map[y][x] == "#":
            return False

        # Check if position is occupied by player
        if x == player_x and y == player_y:
            return False

        # Check if position is occupied by another NPC
        for other_npc in self.npcs:
            if other_npc != moving_npc and other_npc.x == x and other_npc.y == y:
                return False

        return True

    def get_opinion(self, npc_name: str) -> int:
        """
        Get NPC's opinion of the player.

        Args:
            npc_name: Name of the NPC

        Returns:
            Opinion value (0 if not tracked)
        """
        return self.npc_opinions.get(npc_name, 0)

    def update_opinion(self, npc_name: str, delta: int):
        """
        Update NPC's opinion of the player.

        Args:
            npc_name: Name of the NPC
            delta: Change in opinion (positive or negative)
        """
        if npc_name not in self.npc_opinions:
            self.npc_opinions[npc_name] = 0
        self.npc_opinions[npc_name] += delta

    def get_conversation(self, npc_name: str) -> Conversation | None:
        """
        Get conversation for an NPC.

        Args:
            npc_name: Name of the NPC

        Returns:
            Conversation object or None if not found
        """
        return self.conversations.get(npc_name)

    def clear_floor(self):
        """Clear NPCs for current floor (when changing floors)."""
        self.npcs = []

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
                for npc in self.all_npcs
            ],
            "npc_opinions": self.npc_opinions,
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

        Returns:
            Restored NPCManager instance
        """
        manager = cls(npc_data, questions, rng, difficulty_settings, seed, level_data)

        # Restore NPC state
        for npc_data_item in data.get("npcs", []):
            npc = Entity(
                npc_data_item["x"],
                npc_data_item["y"],
                npc_data_item["char"],
                npc_data_item["color"],
                npc_data_item["name"],
                npc_type=npc_data_item.get("npc_type"),
            )
            npc.home_x = npc_data_item.get("home_x", npc.x)
            npc.home_y = npc_data_item.get("home_y", npc.y)
            npc.wander_state = npc_data_item.get("wander_state", "idle")
            npc.wander_ticks_remaining = npc_data_item.get("wander_ticks_remaining", 0)
            npc.move_cooldown = npc_data_item.get("move_cooldown", 0)
            manager.all_npcs.append(npc)

        # Restore opinions
        manager.npc_opinions = data.get("npc_opinions", {})

        # Restore conversation state
        conv_states = data.get("conversations", {})
        for name, state in conv_states.items():
            if name in manager.conversations:
                manager.conversations[name].completed = state.get("completed", False)
                manager.conversations[name].current_question_idx = state.get(
                    "current_question_idx", 0
                )

        return manager
