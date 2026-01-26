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

# Conversation rewards and penalties
CORRECT_ANSWER_COHERENCE_GAIN = 8
WRONG_ANSWER_COHERENCE_PENALTY = 30
ENEMY_WRONG_ANSWER_PENALTY = 45
HELPER_COHERENCE_RESTORE = 15
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

# Terminal placement
TERMINAL_PLACEMENT_ATTEMPTS = 50
TERMINAL_X_OFFSET = 3
TERMINAL_Y_OFFSET = 3

# Rendering
OVERLAY_MAX_WIDTH = 80  # Increased from 60 for better readability
OVERLAY_MAX_HEIGHT = 30  # Increased from 25
COMPLETION_OVERLAY_MAX_HEIGHT = 35  # Increased from 30
TERMINAL_OVERLAY_MAX_HEIGHT = 20  # Height for info terminal overlays
INVENTORY_OVERLAY_MAX_HEIGHT = 25  # Height for inventory overlays
UI_BOTTOM_OFFSET = 4
TERMINAL_UI_RESERVED_LINES = 6  # Lines reserved for UI at terminal bottom

# Entity characters
STAIRS_UP_CHAR = "<"
STAIRS_DOWN_CHAR = ">"
STAIRS_COLOR = "yellow"

# Item characters and colors
ITEM_CHAR_HINT_TOKEN = "?"
ITEM_CHAR_CODE_SNIPPET = "S"
ITEM_COLOR_HINT_TOKEN = "magenta"
ITEM_COLOR_CODE_SNIPPET = "cyan"

# Floor completion requirements
FLOOR_REQUIRED_NPCS = {
    1: {"ALGO_SPIRIT", "HEAP_MASTER", "TEST_ORACLE"},
    2: {"WEB_ARCHITECT", "NET_DAEMON", "COMPILER_SAGE", "SYSTEM_CORE"},
    3: set(),  # No requirements for final floor - boss rush with optional NPCs
}

# Quest system
QUEST_TARGET_NPCS = {
    "TEST_ORACLE",
    "WEB_ARCHITECT",
    "SYSTEM_CORE",
    "CLOUD_MIND",
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
