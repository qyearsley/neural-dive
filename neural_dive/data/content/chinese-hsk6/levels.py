"""
Level layouts and entity positions for Chinese HSK 6 content.
Defines the structure and predefined positions for each floor.
"""

# Level 1: Introduction to HSK 6
LEVEL_1 = """
####################################################
#                                                  #
#  @               文                             #
#                                                  #
#                                 T                #
#                                                  #
#                                                  #
#                                                  #
#                                                  #
#                                                  #
#                                          >       #
#                                                  #
####################################################
"""

# Level 2: Idiom Challenge
LEVEL_2 = """
####################################################
#                                                  #
#  <                                               #
#                                                  #
#           成                                     #
#                                                  #
#                        T                         #
#                                                  #
#                                                  #
#                                                  #
#                                          >       #
#                                                  #
####################################################
"""

# Level 3: Grammar Structures
LEVEL_3 = """
####################################################
#                                                  #
#  <                                               #
#                                                  #
#                语                                #
#                                                  #
#                                                  #
#         T                                        #
#                                                  #
#                                                  #
#                                          >       #
#                                                  #
####################################################
"""

# Level 4: Language Guardian
LEVEL_4 = """
####################################################
#                                                  #
#  <                                               #
#                                                  #
#                                                  #
#            言                T                   #
#                                                  #
#                                                  #
#                                                  #
#                                                  #
#                                          >       #
#                                                  #
####################################################
"""

# Level 5: Final Examination
LEVEL_5 = """
####################################################
#                                                  #
#  <                                               #
#                                                  #
#                                                  #
#                      考                          #
#                                                  #
#                                                  #
#         T                                        #
#                                                  #
#                                                  #
#                                                  #
####################################################
"""


# Parse level strings into structured data
def parse_level(level_str: str, floor: int) -> dict:
    """Parse a level string into position data."""
    lines = level_str.strip().split("\n")
    result = {
        "player_start": None,
        "stairs_down": None,
        "stairs_up": None,
        "npc_positions": {},
        "terminal_positions": [],
    }

    for y, line in enumerate(lines):
        for x, char in enumerate(line):
            if char == "@":
                result["player_start"] = (x, y)
            elif char == ">":
                result["stairs_down"] = (x, y)
            elif char == "<":
                result["stairs_up"] = (x, y)
            elif char == "T":
                result["terminal_positions"].append((x, y))
            elif char not in ["#", " ", "\n"]:
                # It's an NPC character
                if char not in result["npc_positions"]:
                    result["npc_positions"][char] = []
                result["npc_positions"][char].append((x, y))

    return result


# Create parsed levels dictionary
PARSED_LEVELS = {
    1: parse_level(LEVEL_1, 1),
    2: parse_level(LEVEL_2, 2),
    3: parse_level(LEVEL_3, 3),
    4: parse_level(LEVEL_4, 4),
    5: parse_level(LEVEL_5, 5),
}

# Terminal content mapping for each zone/floor
ZONE_TERMINALS = {
    1: ["hsk6_intro"],
    2: ["idiom_wisdom"],
    3: ["vocabulary_tips"],
    4: ["vocabulary_tips"],
    5: ["idiom_wisdom"],
}
