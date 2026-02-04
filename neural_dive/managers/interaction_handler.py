"""Interaction handling for Neural Dive.

This module provides the InteractionHandler class which handles entity
interactions (terminals, NPCs, stairs) and floor transitions.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

from neural_dive.entities import Entity, InfoTerminal, Stairs
from neural_dive.enums import NPCType

if TYPE_CHECKING:
    from neural_dive.difficulty import DifficultySettings
    from neural_dive.managers.conversation_engine import ConversationEngine
    from neural_dive.managers.floor_manager import FloorManager
    from neural_dive.managers.player_manager import PlayerManager
    from neural_dive.managers.quest_manager import QuestManager
    from neural_dive.models import Conversation


@dataclass
class InteractionResult:
    """Result of an interaction attempt.

    Attributes:
        success: Whether interaction occurred
        message: Message to display
        action: Type of interaction that occurred
        terminal: Terminal to activate (if action == "terminal")
        conversation: Conversation to start (if action == "conversation")
    """

    success: bool
    message: str
    action: Literal["terminal", "conversation", "helper", "quest", "stairs", "none"]
    terminal: InfoTerminal | None = None
    conversation: Conversation | None = None


@dataclass
class StairsResult:
    """Result of using stairs.

    Attributes:
        success: Whether stairs were used
        message: Message to display
        floor_changed: Whether floor transition occurred
        new_floor: New floor number (if floor_changed)
    """

    success: bool
    message: str
    floor_changed: bool = False
    new_floor: int | None = None


class InteractionHandler:
    """Handles entity interactions and floor transitions.

    This class is responsible for:
    - Finding and interacting with nearby entities
    - Handling different NPC types (HELPER, QUEST, SPECIALIST, ENEMY)
    - Managing floor transitions via stairs
    - Checking floor completion requirements

    The handler coordinates between multiple managers but doesn't directly
    mutate game state. Instead, it returns result objects that indicate
    what state changes should occur.
    """

    def __init__(
        self,
        player_manager: PlayerManager,
        conversation_engine: ConversationEngine,
        floor_manager: FloorManager,
        quest_manager: QuestManager,
        difficulty_settings: DifficultySettings,
    ):
        """Initialize InteractionHandler.

        Args:
            player_manager: PlayerManager for coherence/inventory operations
            conversation_engine: ConversationEngine for conversation state
            floor_manager: FloorManager for floor transitions
            quest_manager: QuestManager for quest tracking
            difficulty_settings: Difficulty settings for helper restoration amounts
        """
        self.player_manager = player_manager
        self.conversation_engine = conversation_engine
        self.floor_manager = floor_manager
        self.quest_manager = quest_manager
        self.difficulty_settings = difficulty_settings

    def interact(
        self,
        player_pos: tuple[int, int],
        terminals: list[InfoTerminal],
        npcs: list[Entity],
        stairs: list[Stairs],
        npc_conversations: dict[str, Conversation],
    ) -> InteractionResult:
        """Attempt to interact with nearby entity.

        Prioritizes closest entity. For equal distances: NPC > Terminal > Stairs.

        Args:
            player_pos: Player's (x, y) position
            terminals: List of terminals on current floor
            npcs: List of NPCs on current floor
            stairs: List of stairs on current floor
            npc_conversations: Dictionary of NPC conversations

        Returns:
            InteractionResult describing what happened
        """
        player_x, player_y = player_pos

        # Find all interactable entities with distances
        candidates: list[
            tuple[Literal["terminal"], int, InfoTerminal]
            | tuple[Literal["npc"], int, Entity]
            | tuple[Literal["stairs"], int, Stairs]
        ] = []

        # Check terminals
        for terminal in terminals:
            dist = max(abs(player_x - terminal.x), abs(player_y - terminal.y))
            if dist <= 1:
                candidates.append(("terminal", dist, terminal))

        # Check NPCs
        for npc in npcs:
            dist = max(abs(player_x - npc.x), abs(player_y - npc.y))
            if dist <= 1:
                candidates.append(("npc", dist, npc))

        # Check stairs
        for stair in stairs:
            dist = max(abs(player_x - stair.x), abs(player_y - stair.y))
            if dist <= 1:
                candidates.append(("stairs", dist, stair))

        if not candidates:
            return InteractionResult(
                success=False,
                message="No one nearby to interact with. Look for NPCs or Terminals (▣).",
                action="none",
            )

        # Sort by: distance first, then priority (npc=0, terminal=1, stairs=2)
        priority_map = {"npc": 0, "terminal": 1, "stairs": 2}
        candidates.sort(key=lambda x: (x[1], priority_map[x[0]]))

        # Interact with closest/highest priority entity
        entity_type, dist, entity = candidates[0]

        if entity_type == "terminal":
            assert isinstance(entity, InfoTerminal)
            return InteractionResult(
                success=True,
                message=f"Reading: {entity.title}",
                action="terminal",
                terminal=entity,
            )
        elif entity_type == "npc":
            assert isinstance(entity, Entity)
            return self._interact_with_npc(entity, npc_conversations)
        else:  # entity_type == "stairs"
            return InteractionResult(
                success=True,
                message="Use Space or >/< to use stairs.",
                action="stairs",
            )

    def _interact_with_npc(
        self, npc: Entity, npc_conversations: dict[str, Conversation]
    ) -> InteractionResult:
        """Handle interaction with a specific NPC.

        Args:
            npc: The NPC entity to interact with
            npc_conversations: Dictionary of NPC conversations

        Returns:
            InteractionResult describing what happened
        """
        npc_name = npc.name
        conversation = npc_conversations.get(npc_name)

        if not conversation:
            return InteractionResult(
                success=False,
                message=f"{npc_name}: I have nothing to say.",
                action="none",
            )

        # Handle helper NPCs (restore coherence)
        if conversation.npc_type == NPCType.HELPER and not conversation.completed:
            restore_amount = self.difficulty_settings.helper_restore_amount
            gained = self.player_manager.gain_coherence(restore_amount)
            conversation.completed = True
            return InteractionResult(
                success=True,
                message=(
                    f"{npc_name}: Your coherence has been restored by {gained}. "
                    f"[+{restore_amount} Coherence]"
                ),
                action="helper",
            )

        # Handle quest NPCs
        if conversation.npc_type == NPCType.QUEST:
            return self._handle_quest_npc(npc_name, conversation)

        # Standard interaction for specialists and enemies
        if not conversation.completed:
            return InteractionResult(
                success=True,
                message=conversation.greeting,
                action="conversation",
                conversation=conversation,
            )
        else:
            return InteractionResult(
                success=True,
                message=f"{npc_name}: You have proven yourself. We have nothing more to discuss.",
                action="none",
            )

    def _handle_quest_npc(self, npc_name: str, conversation: Conversation) -> InteractionResult:
        """Handle interaction with a quest-giving NPC.

        Args:
            npc_name: Name of the quest NPC
            conversation: The NPC's conversation

        Returns:
            InteractionResult describing what happened
        """
        if not conversation.completed:
            # Quest NPCs just give info, don't have conversations
            success, message = self.quest_manager.activate_quest()
            # Mark as "completed" since quest NPCs don't have actual questions
            conversation.completed = True
            return InteractionResult(
                success=True,
                message=conversation.greeting,
                action="quest",
            )
        else:
            # Check quest completion
            if self.quest_manager.is_quest_complete():
                bonus = self.quest_manager.get_completion_bonus()
                self.player_manager.gain_coherence(bonus)
                return InteractionResult(
                    success=True,
                    message=(
                        f"{npc_name}: You have completed my quest! "
                        f"The knowledge is yours. [Quest Complete! "
                        f"+{bonus} Coherence]"
                    ),
                    action="quest",
                )
            else:
                remaining = self.quest_manager.get_remaining_objectives()
                return InteractionResult(
                    success=True,
                    message=f"{npc_name}: Seek these guardians still: {', '.join(remaining)}",
                    action="quest",
                )

    def use_stairs(
        self,
        player: Entity,
        player_pos: tuple[int, int],
        stairs: list[Stairs],
        npcs_completed: set[str],
        npc_data: dict,
    ) -> StairsResult:
        """Attempt to use stairs at the player's position.

        Args:
            player: Player entity (position will be updated if stairs used)
            player_pos: Player's (x, y) position
            stairs: List of stairs on current floor
            npcs_completed: Set of completed NPC names
            npc_data: NPC definitions for floor requirements

        Returns:
            StairsResult describing what happened
        """
        # Check if player is standing on stairs
        for stair in stairs:
            if player_pos[0] == stair.x and player_pos[1] == stair.y:
                if stair.direction == "down":
                    return self._descend_stairs(player, npcs_completed, npc_data)
                elif stair.direction == "up":
                    return self._ascend_stairs(player)

        return StairsResult(
            success=False,
            message="No stairs here. Stand on stairs (> or <) and press Enter.",
        )

    def _descend_stairs(
        self, player: Entity, npcs_completed: set[str], npc_data: dict
    ) -> StairsResult:
        """Descend to the next floor.

        Args:
            player: Player entity (position will be updated)
            npcs_completed: Set of completed NPC names
            npc_data: NPC definitions for floor requirements

        Returns:
            StairsResult describing what happened
        """
        if not self.floor_manager.can_use_stairs_down():
            return StairsResult(
                success=False,
                message="No deeper layers exist.",
            )

        # Check if floor objectives are complete
        if not self.is_floor_complete(npcs_completed, npc_data):
            current_floor = self.floor_manager.current_floor
            required = self.floor_manager.floor_requirements.get(current_floor, set())
            incomplete = [npc for npc in required if npc not in npcs_completed]
            return StairsResult(
                success=False,
                message=f"Cannot descend! Complete conversations with: {', '.join(incomplete)}",
            )

        # Descend using floor manager (generates new floor map and updates player position)
        self.floor_manager.move_to_next_floor(player)
        new_floor = self.floor_manager.current_floor

        return StairsResult(
            success=True,
            message=f"Descended to Neural Layer {new_floor}",
            floor_changed=True,
            new_floor=new_floor,
        )

    def _ascend_stairs(self, player: Entity) -> StairsResult:
        """Ascend to the previous floor.

        Args:
            player: Player entity (position will be updated)

        Returns:
            StairsResult describing what happened
        """
        if not self.floor_manager.can_use_stairs_up():
            return StairsResult(
                success=False,
                message="This is the top layer.",
            )

        # Ascend using floor manager (generates new floor map and updates player position)
        self.floor_manager.move_to_previous_floor(player)
        new_floor = self.floor_manager.current_floor

        return StairsResult(
            success=True,
            message=f"Ascended to Neural Layer {new_floor}",
            floor_changed=True,
            new_floor=new_floor,
        )

    def is_floor_complete(self, npcs_completed: set[str], npc_data: dict) -> bool:
        """Check if the current floor's objectives are complete.

        Args:
            npcs_completed: Set of completed NPC names
            npc_data: NPC definitions for floor requirements

        Returns:
            True if all required NPCs have been talked to, False otherwise
        """
        return self.floor_manager.is_floor_complete(npcs_completed, npc_data)
