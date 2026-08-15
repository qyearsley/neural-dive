"""Configuration constants for Neural Dive game.

Centralizes magic numbers for easy tuning.
"""

# Game dimensions
DEFAULT_MAP_WIDTH = 50
DEFAULT_MAP_HEIGHT = 25
MAX_FLOORS = 3

# Player stats
STARTING_COHERENCE = 80
MAX_COHERENCE = 100

# Conversation rewards and penalties.
#
# NOTE: The per-answer coherence gain/penalty and helper-restore amounts are
# owned by the difficulty system (neural_dive.difficulty.DifficultySettings),
# which is the source of truth consulted at runtime by AnswerProcessor and
# friends. Do not add coherence-tuning constants here expecting them to affect
# gameplay -- edit DifficultySettings instead. Only the two values still
# referenced directly live here:
#   - ENEMY_WRONG_ANSWER_PENALTY: default for the Answer.enemy_penalty data field
#   - QUEST_COMPLETION_COHERENCE_BONUS: applied by QuestManager on quest completion
ENEMY_WRONG_ANSWER_PENALTY = 45
QUEST_COMPLETION_COHERENCE_BONUS = 50

# Player starting position
PLAYER_START_X = 5
PLAYER_START_Y = 5

# Stairs positions (used when descending/ascending)
STAIRS_DOWN_DEFAULT_X = 45
STAIRS_DOWN_DEFAULT_Y = 20
STAIRS_UP_DEFAULT_X = 10
STAIRS_UP_DEFAULT_Y = 5

# NPC placement
NPC_MIN_DISTANCE_FROM_PLAYER = 5
NPC_PLACEMENT_ATTEMPTS = 100


# Rendering
OVERLAY_MAX_WIDTH = 80  # Increased from 60 for better readability
OVERLAY_MAX_HEIGHT = 30  # Increased from 25
COMPLETION_OVERLAY_MAX_HEIGHT = 35  # Increased from 30
TERMINAL_OVERLAY_MAX_HEIGHT = 20  # Height for info terminal overlays
INVENTORY_OVERLAY_MAX_HEIGHT = 25  # Height for inventory overlays
VICTORY_SCREEN_MAX_WIDTH = 70  # Maximum width for victory screen
VICTORY_SCREEN_MAX_HEIGHT = 20  # Maximum height for victory screen
UI_BOTTOM_OFFSET = 4

# Overlay layout offsets (in character cells)
OVERLAY_SCREEN_MARGIN = 4  # Clearance subtracted from screen w/h when sizing an overlay
OVERLAY_PADDING_X = 2  # Horizontal inset for text from the overlay's left edge
OVERLAY_CONTENT_MARGIN = 4  # Subtracted from overlay width to get the text wrap width
OVERLAY_FOOTER_MARGIN = 2  # Rows above the overlay bottom for the footer prompt

# Entity characters
STAIRS_UP_CHAR = "<"
STAIRS_DOWN_CHAR = ">"
STAIRS_COLOR = "yellow"

# Item characters and colors
ITEM_CHAR_HINT_TOKEN = "?"
ITEM_CHAR_CODE_SNIPPET = "S"
ITEM_COLOR_HINT_TOKEN = "magenta"
ITEM_COLOR_CODE_SNIPPET = "cyan"

# Floor requirements are computed dynamically from NPC data; see
# neural_dive.data_loader.compute_floor_requirements.

# Quest system
QUEST_TARGET_NPCS = {
    "TEST_ORACLE",
    "WEB_ARCHITECT",
    "SYSTEM_CORE",
    "CLOUD_MIND",
}

# Victory condition -- defeating any of these bosses on the final floor wins
VICTORY_BOSS_NAMES: set[str] = {
    "FINAL_BOSS",
    "RESILIENCE_BOSS",
    "ML_BOSS",
}

# NPC Wandering System
# NPCs alternate between idle and wander states for natural movement
NPC_WANDER_ENABLED = True  # Set to False to disable all NPC movement
NPC_IDLE_TICKS_MIN = 10  # Minimum ticks to stay idle (balanced for natural movement)
NPC_IDLE_TICKS_MAX = 20  # Maximum ticks to stay idle (balanced for natural movement)
NPC_WANDER_TICKS_MIN = 2  # Minimum ticks to wander (brief movement)
NPC_WANDER_TICKS_MAX = 3  # Maximum ticks to wander (brief movement)
NPC_WANDER_RADIUS = 3  # Maximum distance from spawn point (reduced to keep NPCs close)

# NPC movement speeds by type (ticks between moves, lower = faster)
NPC_MOVEMENT_SPEEDS = {
    "specialist": 12,  # Very slow - scholars occasionally shift positions
    "helper": 15,  # Very slow - helpers meander slightly
    "enemy": 6,  # Moderate speed - enemies patrol (slowed from 3)
    "quest": 999,  # Stationary - important quest givers stay put
    "boss": 999,  # Stationary - bosses wait in their chambers
}
