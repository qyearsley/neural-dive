"""
Level layouts for Geography content set.
Each level is defined as a string map with zones and NPC placements.

Legend:
  # = wall
  . = floor
  @ = player start
  < = stairs up
  > = stairs down
  T = terminal location
  Letters = NPC spawn points (must match NPC char in npcs.json)
"""

# Floor 1: World Geography Basics
FLOOR_1_LAYOUT = """
##################################################
#.<..............................................#
#.@..............................................#
#................................................#
#................................................#
#................................................#
#................................................#
#..................T.............................#
#................................................#
#..........M.....................................#
#................................................#
#................................................#
#.....O..........................................#
#................................................#
#####......#########......########################
#...#......#.......#......#.........#............#
#...#......#.......#......#.........#............#
#...#......#.......#......#.........#............#
#...#......#########......#.........#............#
#...#............................................#
#...#............................................#
#...#............................................#
#...#..........................C.................#
#...##########################################...#
#................................................#
#.........................................>......#
##################################################
"""

# Floor 2: Advanced Geography
FLOOR_2_LAYOUT = """
##################################################
##.<.............................................#
#.@..............................................#
#................................................#
#................................................#
#................................................#
#..................T.............................#
#................................................#
#................................................#
#####.........########........####################
#...#.........#......#........#..................#
#...#.........#......#........#..................#
#...#.........#......#........#..................#
#...#.........########........####################
#...#............................................#
#...#...........S................................#
#...#............................................#
#...#............................................#
#...#.....########..................##############
#...#.....#......#..................#............#
#...#.....#......#..................#............#
#...#.....#......#..........W.......#............#
#...#.....#......#..................#............#
#####.....########..................##############
#................................................#
#.........................................>......#
##################################################
"""

# Floor 3: Geography Master Challenge
FLOOR_3_LAYOUT = """
##################################################
##.<.............................................#
#.@..............................................#
#................................................#
#................................................#
#................................................#
#..................T.............................#
#................................................#
#................................................#
#................G...............................#
#................................................#
#................................................#
#................................................#
##################################################
"""

# Zone definitions - what terminal content to show for each zone
ZONE_TERMINALS = {
    1: {
        "WORLD": {
            "title": "Welcome to Geography Quest",
            "content": [
                "Welcome to the World of Geography!",
                "",
                "You have entered a knowledge realm where understanding",
                "of Earth's features, countries, and cultures is key.",
                "",
                "To progress, you must prove your knowledge of",
                "world geography, capitals, and physical features.",
                "",
                "Master the basics to unlock advanced challenges.",
            ],
        },
        "GEOGRAPHY": {
            "title": "Geography Hall",
            "content": [
                "You've entered the Geography Hall.",
                "",
                "Here you'll encounter keepers of geographical knowledge:",
                "from physical features to political boundaries.",
                "",
                "Each specialist holds unique geographical insights.",
                "Prove yourself to gain their knowledge.",
            ],
        },
    },
    2: {
        "ADVANCED": {
            "title": "Advanced Geography Zone",
            "content": [
                "Floor 2: Advanced Geography",
                "",
                "You've reached the advanced knowledge layer.",
                "Continental divisions, global exploration,",
                "and comprehensive world knowledge await.",
                "",
                "Only those with solid foundations",
                "can master these challenges.",
            ],
        },
        "CONTINENTAL": {
            "title": "Continental Study",
            "content": [
                "Advanced Continental Knowledge",
                "",
                "This area tests deeper understanding",
                "of continental geography, countries,",
                "and their relationships.",
                "",
                "Prove your expertise to face the final challenge.",
            ],
        },
    },
    3: {
        "MASTER": {
            "title": "Master Geographer Chamber",
            "content": [
                "Final Challenge: Geography Mastery",
                "",
                "You stand before the ultimate test.",
                "The Master Geographer will challenge",
                "your complete knowledge of Earth.",
                "",
                "Victory here proves true geographical mastery.",
            ],
        },
    },
}

# Boss NPCs - these get 4 questions instead of 2-3
BOSS_NPCS = {
    "GEO_MASTER",
}


def parse_level(layout_string: str) -> dict:
    """Parse a level layout string into structured data.

    Returns:
        dict with keys:
            - tiles: 2D list of characters
            - player_start: (x, y) tuple
            - npc_positions: dict of {npc_char: [(x, y), ...]}
            - terminal_positions: list of (x, y) tuples
            - stairs_up: list of (x, y) tuples
            - stairs_down: list of (x, y) tuples
    """
    lines = list(layout_string.strip().split("\n"))
    width = max(len(line) for line in lines) if lines else 0

    # Normalize line lengths
    lines = [line.ljust(width) for line in lines]

    tiles = []
    player_start = None
    npc_positions: dict[str, list[tuple[int, int]]] = {}
    terminal_positions = []
    stairs_up = []
    stairs_down = []

    for y, line in enumerate(lines):
        row = []
        for x, char in enumerate(line):
            if char == "@":
                player_start = (x, y)
                row.append(".")
            elif char == "T":
                terminal_positions.append((x, y))
                row.append(".")
            elif char == "<":
                stairs_up.append((x, y))
                row.append(".")
            elif char == ">":
                stairs_down.append((x, y))
                row.append(".")
            elif char.isalpha() and char not in ["T"]:
                # NPC position
                if char not in npc_positions:
                    npc_positions[char] = []
                npc_positions[char].append((x, y))
                row.append(".")
            elif char == "#":
                row.append("#")
            else:
                row.append(".")
        tiles.append(row)

    return {
        "tiles": tiles,
        "player_start": player_start,
        "npc_positions": npc_positions,
        "terminal_positions": terminal_positions,
        "stairs_up": stairs_up,
        "stairs_down": stairs_down,
    }


# Parse all levels at module load time
PARSED_LEVELS = {
    1: parse_level(FLOOR_1_LAYOUT),
    2: parse_level(FLOOR_2_LAYOUT),
    3: parse_level(FLOOR_3_LAYOUT),
}
