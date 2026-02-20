"""Move ID mappings for the last_attack_landed field in Slippi frame data.

These are NOT action state IDs — they are a separate ID system for attack types.
Source: slippi-js moves.json (project-slippi/slippi-js)
"""

MOVE_NAMES = {
    1: "Misc",
    2: "Jab",
    3: "Jab 2",
    4: "Jab 3",
    5: "Rapid Jabs",
    6: "Dash Attack",
    7: "F-tilt",
    8: "U-tilt",
    9: "D-tilt",
    10: "F-smash",
    11: "U-smash",
    12: "D-smash",
    13: "Nair",
    14: "Fair",
    15: "Bair",
    16: "Uair",
    17: "Dair",
    18: "Neutral B",
    19: "Side B",
    20: "Up B",
    21: "Down B",
    50: "Getup Attack",
    51: "Getup Attack (Slow)",
    52: "Pummel",
    53: "F-throw",
    54: "B-throw",
    55: "U-throw",
    56: "D-throw",
    61: "Edge Attack (Slow)",
    62: "Edge Attack",
}

MOVE_NAMES_SHORT = {
    1: "misc",
    2: "jab",
    3: "jab2",
    4: "jab3",
    5: "rapid_jab",
    6: "dash_attack",
    7: "ftilt",
    8: "utilt",
    9: "dtilt",
    10: "fsmash",
    11: "usmash",
    12: "dsmash",
    13: "nair",
    14: "fair",
    15: "bair",
    16: "uair",
    17: "dair",
    18: "neutral_b",
    19: "side_b",
    20: "up_b",
    21: "down_b",
    50: "getup_attack",
    51: "getup_attack_slow",
    52: "pummel",
    53: "fthrow",
    54: "bthrow",
    55: "uthrow",
    56: "dthrow",
    61: "edge_attack_slow",
    62: "edge_attack",
}


def move_name(move_id: int) -> str:
    """Resolve a move ID (from last_attack_landed) to a human-readable name."""
    return MOVE_NAMES.get(move_id, f"Unknown ({move_id})")
