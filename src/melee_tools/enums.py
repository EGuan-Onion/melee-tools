"""Melee character and stage ID mappings.

Character IDs = internal character IDs from the .slp format (game start).
Note: metadata uses *external* character IDs which differ (e.g. Sheik=19 externally but 19 internally too,
while Zelda=18 externally). The `start.players[i].character` field uses internal IDs.
"""

# Internal character IDs (from game start event)
CHARACTER_NAMES = {
    0: "Captain Falcon",
    1: "Donkey Kong",
    2: "Fox",
    3: "Mr. Game & Watch",
    4: "Kirby",
    5: "Bowser",
    6: "Link",
    7: "Luigi",
    8: "Mario",
    9: "Marth",
    10: "Mewtwo",
    11: "Ness",
    12: "Peach",
    13: "Pikachu",
    14: "Ice Climbers",
    15: "Jigglypuff",
    16: "Samus",
    17: "Yoshi",
    18: "Zelda",
    19: "Sheik",
    20: "Falco",
    21: "Young Link",
    22: "Dr. Mario",
    23: "Roy",
    24: "Pichu",
    25: "Ganondorf",
    26: "Master Hand",
    27: "Wireframe Male",
    28: "Wireframe Female",
    29: "Giga Bowser",
    30: "Crazy Hand",
    31: "Sandbag",
    32: "Popo",
}

STAGE_NAMES = {
    2: "Fountain of Dreams",
    3: "Pokemon Stadium",
    4: "Princess Peach's Castle",
    5: "Kongo Jungle",
    6: "Brinstar",
    7: "Corneria",
    8: "Yoshi's Story",
    9: "Onett",
    10: "Mute City",
    11: "Rainbow Cruise",
    12: "Jungle Japes",
    13: "Great Bay",
    14: "Hyrule Temple",
    15: "Brinstar Depths",
    16: "Yoshi's Island",
    17: "Green Greens",
    18: "Fourside",
    19: "Mushroom Kingdom I",
    20: "Mushroom Kingdom II",
    22: "Venom",
    23: "Poke Floats",
    24: "Big Blue",
    25: "Icicle Mountain",
    26: "Icetop",
    27: "Flat Zone",
    28: "Dream Land N64",
    29: "Yoshi's Island N64",
    30: "Kongo Jungle N64",
    31: "Battlefield",
    32: "Final Destination",
}

# Competitive stage list
LEGAL_STAGES = {2, 3, 8, 28, 31, 32}


def character_name(char_id: int) -> str:
    return CHARACTER_NAMES.get(char_id, f"Unknown ({char_id})")


def stage_name(stage_id: int) -> str:
    return STAGE_NAMES.get(stage_id, f"Unknown ({stage_id})")
