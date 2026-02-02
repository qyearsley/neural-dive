"""
Theme system for Neural Dive.

Defines visual themes with support for light and dark terminal backgrounds.
Uses widely-supported Unicode characters for maximum compatibility.
"""

from dataclasses import dataclass


@dataclass
class ColorScheme:
    """Color scheme for a specific terminal background mode.

    Attributes:
        player: Color for player character (@)
        npc_specialist: Color for specialist NPCs (teach knowledge modules)
        npc_helper: Color for helper NPCs (provide hints)
        npc_enemy: Color for enemy NPCs (reduce coherence on wrong answers)
        npc_quest: Color for quest-giving NPCs
        wall: Color for wall tiles (#)
        floor: Color for walkable floor tiles (.)
        stairs: Color for staircase tiles (< >)
        terminal: Color for information terminals
        gate: Color for locked gates between floors
        ui_primary: Primary text color for UI elements
        ui_secondary: Secondary text color for less important UI
        ui_accent: Accent color for highlights and emphasis
        ui_warning: Color for warning messages
        ui_error: Color for error messages
        ui_success: Color for success messages
    """

    # Entity colors
    player: str
    npc_specialist: str
    npc_helper: str
    npc_enemy: str
    npc_quest: str

    # Environment colors
    wall: str
    floor: str
    stairs: str
    terminal: str
    gate: str

    # UI colors
    ui_primary: str
    ui_secondary: str
    ui_accent: str
    ui_warning: str
    ui_error: str
    ui_success: str


@dataclass
class CharacterSet:
    """Character glyphs used for rendering."""

    # Entities
    player: str
    npc_default: str  # Fallback if no specific char defined
    stairs_up: str
    stairs_down: str
    terminal: str
    gate_locked: str
    gate_unlocked: str

    # Environment
    wall: str
    floor: str
    wall_alt: str  # For variety/pattern

    # UI
    separator: str


@dataclass
class Theme:
    """Complete theme with characters and color schemes."""

    name: str
    characters: CharacterSet
    dark_colors: ColorScheme
    light_colors: ColorScheme


# ============================================================================
# CHARACTER SETS
# ============================================================================

# Unicode Box Drawing - Cyberpunk style
# Uses widely-supported characters from Unicode blocks:
# - Box Drawing (U+2500-U+257F)
# - Geometric Shapes (U+25A0-U+25FF)
CYBERPUNK_CHARS = CharacterSet(
    # Entities - geometric shapes for visibility
    player="◆",  # U+25C6 Black Diamond
    npc_default="◇",  # U+25C7 White Diamond
    stairs_up="▲",  # U+25B2 Black Up-Pointing Triangle
    stairs_down="▼",  # U+25BC Black Down-Pointing Triangle
    terminal="▣",  # U+25A3 White Square with Horizontal Fill
    gate_locked="█",  # U+2588 Full Block
    gate_unlocked="▒",  # U+2592 Medium Shade
    # Environment - box drawing for walls
    wall="█",  # U+2588 Full Block
    floor="·",  # U+00B7 Middle Dot (very widely supported)
    wall_alt="▓",  # U+2593 Dark Shade (for variety if needed)
    # UI
    separator="─",  # U+2500 Box Drawing Light Horizontal
)


# ============================================================================
# COLOR SCHEMES - CYBERPUNK
# ============================================================================

# Dark mode - neon colors on dark background
CYBERPUNK_DARK = ColorScheme(
    # Entities - bright neon colors
    player="bright_green",  # Electric green
    npc_specialist="bright_magenta",  # Neon magenta
    npc_helper="bright_cyan",  # Bright cyan
    npc_enemy="bright_red",  # Danger red
    npc_quest="bright_yellow",  # Important yellow
    # Environment - darker tones for depth
    wall="blue",  # Dark blue walls
    floor="cyan",  # Subtle cyan floor
    stairs="yellow",  # Visible stairs
    terminal="cyan",  # Info terminals
    gate="magenta",  # Locked gates
    # UI - high contrast
    ui_primary="white",
    ui_secondary="cyan",
    ui_accent="bright_magenta",
    ui_warning="yellow",
    ui_error="red",
    ui_success="green",
)

# Light mode - darker colors on light background
CYBERPUNK_LIGHT = ColorScheme(
    # Entities - darker but still vibrant
    player="green",  # Rich green
    npc_specialist="magenta",  # Deep magenta
    npc_helper="blue",  # Deep blue for visibility
    npc_enemy="red",  # Strong red
    npc_quest="blue",  # Dark blue instead of yellow
    # Environment - visible on light
    wall="blue",  # Blue walls
    floor="cyan",  # Subtle cyan floor
    stairs="magenta",  # Visible stairs
    terminal="blue",  # Info terminals
    gate="magenta",  # Locked gates
    # UI - readable on light (blue instead of black to avoid bold_black gray issue)
    ui_primary="blue",
    ui_secondary="cyan",
    ui_accent="magenta",
    ui_warning="red",  # Red instead of yellow for visibility
    ui_error="red",
    ui_success="green",
)


def get_theme(
    theme_name: str = "cyberpunk", background: str = "dark"
) -> tuple[CharacterSet, ColorScheme]:
    """Get character set and color scheme (hardcoded to cyberpunk dark).

    Args:
        theme_name: Ignored (kept for compatibility)
        background: Ignored (kept for compatibility)

    Returns:
        Tuple of (CYBERPUNK_CHARS, CYBERPUNK_DARK)
    """
    return CYBERPUNK_CHARS, CYBERPUNK_DARK
