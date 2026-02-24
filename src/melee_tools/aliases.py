"""Move and character alias resolution for natural-language queries.

Maps community nicknames (stomp, knee, shine, etc.) to canonical move IDs
and short names. Supports character aliases (falcon, spacies, puff) and
named combo sequences (ken combo, pillar, stomp knee).

Typical usage:
    from melee_tools.aliases import resolve_move, resolve_character, resolve_move_sequence

    resolve_move("stomp", "Captain Falcon")  # -> 17 (Dair)
    resolve_character("spacies")             # -> ["Fox", "Falco"]
    resolve_move_sequence(["ken combo"])      # -> [14, 17] with character="Marth"
"""

from melee_tools.moves import MOVE_NAMES_SHORT

# Build reverse lookup: short_name -> move_id
_SHORT_TO_ID = {v: k for k, v in MOVE_NAMES_SHORT.items()}


# ---------------------------------------------------------------------------
# Character aliases
# ---------------------------------------------------------------------------

CHARACTER_ALIASES = {
    "falcon": ["Captain Falcon"],
    "cf": ["Captain Falcon"],
    "captain falcon": ["Captain Falcon"],
    "fox": ["Fox"],
    "falco": ["Falco"],
    "spacies": ["Fox", "Falco"],
    "spacie": ["Fox", "Falco"],
    "marth": ["Marth"],
    "sheik": ["Sheik"],
    "puff": ["Jigglypuff"],
    "jiggs": ["Jigglypuff"],
    "jigglypuff": ["Jigglypuff"],
    "peach": ["Peach"],
    "ic": ["Ice Climbers"],
    "ics": ["Ice Climbers"],
    "icies": ["Ice Climbers"],
    "ice climbers": ["Ice Climbers"],
    "pikachu": ["Pikachu"],
    "pika": ["Pikachu"],
    "samus": ["Samus"],
    "yoshi": ["Yoshi"],
    "luigi": ["Luigi"],
    "mario": ["Mario"],
    "doc": ["Dr. Mario"],
    "dr mario": ["Dr. Mario"],
    "dr. mario": ["Dr. Mario"],
    "ganon": ["Ganondorf"],
    "ganondorf": ["Ganondorf"],
    "link": ["Link"],
    "young link": ["Young Link"],
    "yl": ["Young Link"],
    "dk": ["Donkey Kong"],
    "donkey kong": ["Donkey Kong"],
    "roy": ["Roy"],
    "mewtwo": ["Mewtwo"],
    "m2": ["Mewtwo"],
    "gnw": ["Mr. Game & Watch"],
    "game and watch": ["Mr. Game & Watch"],
    "g&w": ["Mr. Game & Watch"],
    "ness": ["Ness"],
    "kirby": ["Kirby"],
    "bowser": ["Bowser"],
    "zelda": ["Zelda"],
    "pichu": ["Pichu"],
}


# ---------------------------------------------------------------------------
# Move aliases: community name -> (character_set or None, short_name)
# character_set=None means the alias is generic (works for any character).
# ---------------------------------------------------------------------------

MOVE_ALIASES = {
    # Character-specific nicknames
    "stomp": ({"Captain Falcon", "Ganondorf"}, "dair"),
    "knee": ({"Captain Falcon"}, "fair"),
    "knee of justice": ({"Captain Falcon"}, "fair"),
    "falcon punch": ({"Captain Falcon"}, "neutral_b"),
    "falcon kick": ({"Captain Falcon"}, "down_b"),
    "raptor boost": ({"Captain Falcon"}, "side_b"),
    "gentleman": ({"Captain Falcon"}, "jab3"),
    "shine": ({"Fox", "Falco"}, "down_b"),
    "reflector": ({"Fox", "Falco"}, "down_b"),
    "laser": ({"Fox", "Falco"}, "neutral_b"),
    "firefox": ({"Fox"}, "up_b"),
    "firebird": ({"Falco"}, "up_b"),
    "phantasm": ({"Falco"}, "side_b"),
    "illusion": ({"Fox"}, "side_b"),
    "rest": ({"Jigglypuff"}, "down_b"),
    "sing": ({"Jigglypuff"}, "neutral_b"),
    "pound": ({"Jigglypuff"}, "side_b"),
    "rollout": ({"Jigglypuff"}, "up_b"),
    "needles": ({"Sheik"}, "neutral_b"),
    "chain": ({"Sheik"}, "side_b"),
    "vanish": ({"Sheik"}, "up_b"),
    "tipper": ({"Marth"}, "fsmash"),
    "shield breaker": ({"Marth", "Roy"}, "neutral_b"),
    "dancing blade": ({"Marth", "Roy"}, "side_b"),
    "dolphin slash": ({"Marth"}, "up_b"),
    "counter": ({"Marth", "Roy"}, "down_b"),
    "toad": ({"Peach"}, "neutral_b"),
    "bomber": ({"Peach"}, "side_b"),
    "parasol": ({"Peach"}, "up_b"),
    "turnip": ({"Peach"}, "down_b"),
    "warlock punch": ({"Ganondorf"}, "neutral_b"),
    "gerudo dragon": ({"Ganondorf"}, "side_b"),
    "wizard foot": ({"Ganondorf"}, "down_b"),
    "thunder": ({"Pikachu", "Pichu"}, "down_b"),
    "charge shot": ({"Samus"}, "neutral_b"),
    "missile": ({"Samus"}, "side_b"),
    "screw attack": ({"Samus"}, "up_b"),
    "bomb": ({"Samus", "Link", "Young Link"}, "down_b"),

    # Generic aliases (short forms -> canonical short names)
    "forward air": (None, "fair"),
    "forward_air": (None, "fair"),
    "back air": (None, "bair"),
    "back_air": (None, "bair"),
    "up air": (None, "uair"),
    "up_air": (None, "uair"),
    "down air": (None, "dair"),
    "down_air": (None, "dair"),
    "neutral air": (None, "nair"),
    "neutral_air": (None, "nair"),
    "forward tilt": (None, "ftilt"),
    "forward_tilt": (None, "ftilt"),
    "up tilt": (None, "utilt"),
    "up_tilt": (None, "utilt"),
    "down tilt": (None, "dtilt"),
    "down_tilt": (None, "dtilt"),
    "forward smash": (None, "fsmash"),
    "forward_smash": (None, "fsmash"),
    "up smash": (None, "usmash"),
    "up_smash": (None, "usmash"),
    "down smash": (None, "dsmash"),
    "down_smash": (None, "dsmash"),
    "forward throw": (None, "fthrow"),
    "forward_throw": (None, "fthrow"),
    "back throw": (None, "bthrow"),
    "back_throw": (None, "bthrow"),
    "up throw": (None, "uthrow"),
    "up_throw": (None, "uthrow"),
    "down throw": (None, "dthrow"),
    "down_throw": (None, "dthrow"),
    "neutral b": (None, "neutral_b"),
    "side b": (None, "side_b"),
    "up b": (None, "up_b"),
    "down b": (None, "down_b"),
}


# ---------------------------------------------------------------------------
# Named combo sequences: name -> (character_set, [move_short_names])
# ---------------------------------------------------------------------------

NAMED_COMBOS = {
    "ken combo": ({"Marth"}, ["fair", "dair"]),
    "pillar": ({"Fox", "Falco"}, ["dair", "down_b"]),
    "pillars": ({"Fox", "Falco"}, ["dair", "down_b"]),
    "stomp knee": ({"Captain Falcon"}, ["dair", "fair"]),
    "stomp to knee": ({"Captain Falcon"}, ["dair", "fair"]),
    "stomp into knee": ({"Captain Falcon"}, ["dair", "fair"]),
    "chaingrab": ({"Marth", "Sheik", "Ice Climbers"}, ["dthrow", "dthrow"]),
    "upthrow rest": ({"Jigglypuff"}, ["uthrow", "down_b"]),
    "upthrow upair": ({"Fox"}, ["uthrow", "uair"]),
    "shine spike": ({"Fox", "Falco"}, ["down_b"]),
    "waveshine": ({"Fox", "Falco"}, ["down_b"]),
}


# ---------------------------------------------------------------------------
# Resolver functions
# ---------------------------------------------------------------------------

def resolve_character(name: str) -> list[str]:
    """Resolve a character alias to canonical name(s).

    Args:
        name: Character name or alias (case-insensitive).

    Returns:
        List of canonical character names. "spacies" -> ["Fox", "Falco"].

    Raises:
        ValueError: If the alias is not recognized.
    """
    result = CHARACTER_ALIASES.get(name.lower())
    if result is None:
        raise ValueError(f"Unknown character alias: {name!r}")
    return result


def resolve_move(name: str, character: str | None = None) -> int | None:
    """Resolve a move alias to a move ID.

    Checks in order:
    1. Direct match in MOVE_NAMES_SHORT (e.g. "fair" -> 14)
    2. MOVE_ALIASES lookup (e.g. "knee" -> 14 for Captain Falcon)

    Args:
        name: Move name or alias (case-insensitive).
        character: Optional character name for character-specific aliases.

    Returns:
        Move ID (int), or None if not resolved.
    """
    key = name.lower().strip()

    # Direct short name match
    if key in _SHORT_TO_ID:
        return _SHORT_TO_ID[key]

    # Alias lookup
    alias = MOVE_ALIASES.get(key)
    if alias is not None:
        char_set, short_name = alias
        if char_set is not None and character is not None and character not in char_set:
            return None
        return _SHORT_TO_ID.get(short_name)

    return None


def resolve_move_sequence(
    names: list[str],
    character: str | None = None,
) -> tuple[list[int], str | None]:
    """Resolve a list of move names/aliases to move IDs.

    Also expands named combos: ["ken combo"] -> [14, 17] with character hint.

    Args:
        names: Move names, aliases, or a single named combo.
        character: Optional character filter. May be inferred from named combos.

    Returns:
        Tuple of (move_ids, inferred_character). inferred_character is set if
        a named combo implies a specific character and no character was given.

    Raises:
        ValueError: If any move name can't be resolved.
    """
    inferred_char = character

    # Check if the entire input is a single named combo
    if len(names) == 1:
        combo = NAMED_COMBOS.get(names[0].lower().strip())
        if combo is not None:
            char_set, short_names = combo
            if inferred_char is None and len(char_set) == 1:
                inferred_char = next(iter(char_set))
            move_ids = []
            for sn in short_names:
                mid = _SHORT_TO_ID.get(sn)
                if mid is None:
                    raise ValueError(f"Named combo references unknown move: {sn!r}")
                move_ids.append(mid)
            return move_ids, inferred_char

    # Resolve each name individually
    move_ids = []
    for name in names:
        mid = resolve_move(name, character=inferred_char)
        if mid is None:
            raise ValueError(f"Could not resolve move: {name!r}")
        move_ids.append(mid)

    return move_ids, inferred_char
