"""
Level layouts for Neural Dive game.
Each level is defined as a string map with zones and NPC placements.

Legend:
  # = wall
  . = floor
  @ = player start
  < = stairs up
  > = stairs down
  T = terminal location
  Letters (A, H, O, etc.) = NPC spawn points (must match NPC char in npcs.json)
"""

# Floor 1: Learning Fundamentals
FLOOR_1_LAYOUT = """
##################################################
#.<..............................................#
#.@..............................................#
#......T.........................................#
#.ENTRY.PLAZA....................................#
#................................................#
#................................................#
#................................................#
#.....O...................M......................#
#................................................#
#####......#########......########################
#...#......#.......#......#.........#............#
#.P.#......#...A...#......#....U....#............#
#...#......#.......#......#.........#............#
#...#............................................#
#...#........................T...................#
#...#..........................KNOWLEDGE.SECTOR..#
#...#.........H............................Q.....#
#...#............................................#
#...###############..............................#
#................................................#
#..H....................................>........#
#................................................#
#................................................#
##################################################
"""

# Floor 2: System Architecture
FLOOR_2_LAYOUT = """
##################################################
#..<.............................................#
#.@..............................................#
#......T.........................................#
#.INFRASTRUCTURE.LAYER...........................#
#................................................#
#.H..............................W...............#
#................................................#
#####.........########........####################
#...#.........#......#...........................#
#.C.#.........#......#................N..........#
#...#.........#......#...........................#
#...#.........########........####################
#...#............................................#
#...#.........T..................................#
#...#.........PROTOCOL.NEXUS.....................#
#...#............................................#
#...#.....########..................##############
#.K.#.....#......#..................#............#
#...#.....#......#...............S..#............#
#...#.....#......#..................#............#
#####.....########..................##############
#................................................#
#.........................................>......#
##################################################
"""

# Floor 3: Advanced Concepts - Three boss arenas
FLOOR_3_LAYOUT = """
##################################################
##.<.............................................#
#.@..............................................#
#.T..............................................#
#.THE.CORE.LAYER.................................#
#................................................#
#.H..............................................#
#................................................#
###################........#######################
#................................................#
#.T..............................................#
#.ARENA.1:.......................................#
#.DISTRIBUTED.MIND...............................#
#.........R.........................D............#
#................................................#
###################........#######################
#................................................#
###################........#######################
#.T..............................................#
#.ARENA.2:.......................................#
#.ML.CONSCIOUSNESS...............................#
#..........F.........................L...........#
#................................................#
#.H..............................................#
###################........#######################
#................................................#
#.T..............................................#
#.FINAL.ARENA:..THE.CORE.ENTITY..................#
#................E............B..................#
##################################################
"""

# Zone definitions - what terminal content to show for each zone
ZONE_TERMINALS = {
    1: {  # Floor 1
        "ENTRY": {
            "title": "Welcome to Neural Dive",
            "content": [
                "You have entered the Neural Network Core.",
                "",
                "Your consciousness has been digitized and uploaded",
                "into an AI training system. The neural network is",
                "unstable and fragmenting.",
                "",
                "To escape, you must prove your knowledge and",
                "restore coherence to the system. Answer questions",
                "correctly to gain stability, but beware - wrong",
                "answers will corrupt your data integrity.",
            ],
        },
        "KNOWLEDGE": {
            "title": "Knowledge Sector",
            "content": [
                "You've entered the Knowledge Processing Zone.",
                "",
                "Here you'll encounter specialists in various domains.",
                "",
                "Each NPC holds unique knowledge modules. Prove",
                "yourself to collect them all.",
            ],
        },
    },
    2: {  # Floor 2
        "INFRASTRUCTURE": {
            "title": "Infrastructure Layer",
            "content": [
                "Floor 2: System Architecture Layer",
                "",
                "You've descended into the infrastructure layer.",
                "This is where the network's foundation is built.",
                "",
                "Expect questions about web development, security,",
                "cryptography, and system design. The specialists",
                "here guard critical knowledge modules.",
                "",
                "Complete all required challenges to unlock",
                "passage to the final floor.",
            ],
        },
        "PROTOCOL": {
            "title": "Protocol Nexus",
            "content": [
                "Network Protocol Processing Hub",
                "",
                "Packets flow through this zone like data through",
                "synapses. TCP handshakes, HTTP requests, and",
                "cryptographic protocols are the language here.",
                "",
                "Master the protocols that power communication",
                "and secure the network.",
            ],
        },
    },
    3: {  # Floor 3
        "THE": {
            "title": "The Core Layer",
            "content": [
                "Floor 3: The Neural Core",
                "",
                "You've reached the deepest layer of the network.",
                "The AI's core consciousness resides here.",
                "",
                "This is a BOSS RUSH. Each boss entity will",
                "challenge you with 4 difficult questions instead",
                "of the usual 2-3.",
                "",
                "Steel yourself. Only the most knowledgeable",
                "can escape the Neural Dive.",
            ],
        },
        "ARENA": {
            "title": "Boss Arena",
            "content": [
                "Boss Challenge Zone",
                "",
                "You stand before a powerful entity. This boss",
                "will test your mastery of advanced topics.",
                "",
                "4 questions. No mercy. Prove your worth.",
            ],
        },
        "FINAL": {
            "title": "The Core Entity",
            "content": [
                "Final Boss: Integration Challenge",
                "",
                "The ultimate test. This boss draws from",
                "ALL knowledge domains.",
                "",
                "Victory here means freedom from the Neural Dive.",
                "Defeat means fragmentation and system restart.",
            ],
        },
    },
}

# Topic indicators for NPCs - shown in brackets after their name
NPC_TOPIC_INDICATORS = {
    "ALGO_SPIRIT": "[Algorithms]",
    "HEAP_MASTER": "[Data Structures]",
    "DP_SAGE": "[Dynamic Programming]",
    "NET_DAEMON": "[Networking]",
    "WEB_ARCHITECT": "[Web Dev]",
    "CRYPTO_GUARDIAN": "[Security]",
    "SYSTEM_CORE": "[Systems]",
    "SCALE_MASTER": "[System Design]",
    "COMPILER_SAGE": "[Compilers]",
    "DB_GUARDIAN": "[Databases]",
    "THEORY_BOSS": "[Theory BOSS]",
    "ML_BOSS": "[ML BOSS]",
    "FINAL_BOSS": "[FINAL BOSS]",
    "MEMORY_HEALER": "[Healer]",
    "ORACLE": "[Quest]",
}

# Boss NPCs - these get 4 questions instead of 2-3
BOSS_NPCS = {
    "THEORY_BOSS",
    "ML_BOSS",
    "FINAL_BOSS",
    "RESILIENCE_BOSS",
}


def parse_level(layout_string: str) -> dict:
    """
    Parse a level layout string into structured data.

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
