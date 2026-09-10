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
HELP_OVERLAY_MAX_HEIGHT = 30  # Height for the glyph/key legend overlay
VICTORY_SCREEN_MAX_WIDTH = 70  # Maximum width for victory screen
UI_BOTTOM_OFFSET = 4

# End screens (victory and game over).
#
# The panel is sized from its content instead of a fixed height, because a
# fixed height silently dropped the tail of the summary -- including the
# weak-areas line, which is the most useful line on the loss screen.
# END_SCREEN_CHROME_ROWS counts the rows the panel spends on chrome rather than
# summary lines: top border, title, subtitle, one blank, footer, bottom border.
END_SCREEN_CHROME_ROWS = 6
END_SCREEN_MIN_HEIGHT = 10

# Minimum terminal size.
#
# The map is drawn from row 0 and the status panel owns the last
# UI_BOTTOM_OFFSET rows, so the window must be at least as tall as the tallest
# floor layout plus the panel. These are the fallbacks used when the level
# layouts cannot be measured; rendering.required_terminal_size() measures the
# real content and returns the larger figure.
MIN_TERMINAL_WIDTH = DEFAULT_MAP_WIDTH
MIN_TERMINAL_HEIGHT = DEFAULT_MAP_HEIGHT + UI_BOTTOM_OFFSET

# Overlay layout offsets (in character cells)
OVERLAY_SCREEN_MARGIN = 4  # Clearance subtracted from screen w/h when sizing an overlay
OVERLAY_PADDING_X = 2  # Horizontal inset for text from the overlay's left edge
OVERLAY_CONTENT_MARGIN = 4  # Subtracted from overlay width to get the text wrap width
OVERLAY_FOOTER_MARGIN = 2  # Rows above the overlay bottom for the footer prompt

# Entity characters
STAIRS_UP_CHAR = "<"
STAIRS_DOWN_CHAR = ">"
STAIRS_COLOR = "yellow"

# Status panel coherence meter.
#
# Coherence used to print in the terminal's default attribute, which reads the
# same at 5/100 as at 80/100. The bar plus a colour band makes the game's core
# tension visible at a glance. Eight cells is chosen so the whole status line
# still fits an 80-column window; below that the bar is dropped and the numbers
# stay.
COHERENCE_BAR_WIDTH = 8
COHERENCE_BAR_FILLED_CHAR = "█"  # Full block
COHERENCE_BAR_EMPTY_CHAR = "░"  # Light shade
COHERENCE_WARNING_FRACTION = 0.5  # At or below this the meter turns amber
COHERENCE_CRITICAL_FRACTION = 0.25  # At or below this the meter turns red

# Item characters and colors
ITEM_CHAR_HINT_TOKEN = "?"
ITEM_CHAR_CODE_SNIPPET = "S"
ITEM_COLOR_HINT_TOKEN = "magenta"
ITEM_COLOR_CODE_SNIPPET = "cyan"

# Floor requirements are computed dynamically from NPC data; see
# neural_dive.data_loader.compute_floor_requirements.

# Cross-run question history (neural_dive.player_profile).
# Selection weight is QUESTION_WEIGHT_BASE + QUESTION_WEIGHT_MISS_BONUS * miss_rate,
# so a question the player always misses is three times as likely to be picked as
# a fresh one. A question answered correctly QUESTION_MASTERY_CORRECT_COUNT times
# with no misses drops to QUESTION_WEIGHT_MASTERED instead.
QUESTION_WEIGHT_BASE = 1.0
QUESTION_WEIGHT_MISS_BONUS = 2.0
QUESTION_WEIGHT_MASTERED = 0.5
QUESTION_MASTERY_CORRECT_COUNT = 2

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
