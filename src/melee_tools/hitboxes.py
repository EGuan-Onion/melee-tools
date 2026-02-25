"""Hitbox classification for moves with distinct strong/weak hitboxes.

Many Melee moves have distinct "strong" vs "weak" hitboxes (Falcon knee
sweetspot/sourspot, Marth tipper/non-tipper, clean/late aerials).  Slippi
replays don't record which hitbox connected — only the move ID and resulting
damage.  Because damage delta cleanly separates strong from weak hits, we
can classify each hit using a per-move damage threshold.

Typical usage:
    from melee_tools import find_move_hits, classify_hit, player_games, parse_replays

    games = parse_replays("replays")
    pg = player_games(games)
    hits = find_move_hits("replays", pg, "EG＃0", move="knee", character="falcon")
    print(hits["label"].value_counts())
"""

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from melee_tools.aliases import resolve_character, resolve_move
from melee_tools.habits import _iter_1v1_games
from melee_tools.moves import MOVE_NAMES, move_name


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class HitboxInfo:
    """Defines the strong/weak classification for a single move."""
    strong_label: str       # "sweetspot" / "tipper" / "clean" / "spike"
    weak_label: str         # "sourspot" / "non-tipper" / "late"
    strong_damage: float    # fresh (unstaled) damage for strong hit
    weak_damage: float      # fresh (unstaled) damage for weak hit
    threshold: float        # damage >= threshold → strong; < threshold → weak
    notes: str = ""


# Keyed by canonical character name -> move_id -> HitboxInfo.
MOVE_HITBOXES: dict[str, dict[int, HitboxInfo]] = {
    "Captain Falcon": {
        14: HitboxInfo("sweetspot", "sourspot", 18.0, 6.0, 12.0, "Knee. Sweetspot sends horizontal, sourspot floats up."),
        17: HitboxInfo("spike", "nipple spike", 15.0, 10.0, 12.5, "Dair. True spike vs nipple spike (sends forward ~45 deg)."),
    },
    "Marth": {
        14: HitboxInfo("tipper", "non-tipper", 13.0, 9.0, 11.0),
        10: HitboxInfo("tipper", "non-tipper", 20.0, 14.0, 17.0, "F-smash."),
        15: HitboxInfo("tipper", "non-tipper", 13.0, 9.0, 11.0),
        17: HitboxInfo("tipper", "non-tipper", 13.0, 9.0, 11.0, "Dair spike tipper."),
        16: HitboxInfo("tipper", "non-tipper", 13.0, 9.0, 11.0),
        7:  HitboxInfo("tipper", "non-tipper", 13.0, 9.0, 11.0),
    },
    "Fox": {
        15: HitboxInfo("clean", "late", 15.0, 9.0, 12.0),
        11: HitboxInfo("sweetspot", "sourspot", 18.0, 13.0, 15.5, "Usmash."),
    },
    "Falco": {
        17: HitboxInfo("spike", "late", 12.0, 9.0, 10.5, "Dair spike."),
        15: HitboxInfo("clean", "late", 15.0, 9.0, 12.0),
    },
}

# Multi-hit moves that should NOT be classified (sequential hits, not sweet/sour).
MULTI_HIT_EXCLUSIONS: dict[str, set[int]] = {
    "Fox": {16, 14},       # Uair (multi-hit), Fair (multi-hit)
    "Falco": {16, 14},     # Uair (multi-hit), Fair (multi-hit)
}


# ---------------------------------------------------------------------------
# Single-hit classifier
# ---------------------------------------------------------------------------

def classify_hit(
    character: str,
    move_id: int,
    damage: float,
) -> dict:
    """Classify a single hit as strong or weak based on damage.

    Args:
        character: Canonical character name (e.g. "Captain Falcon").
        move_id: Move ID from last_attack_landed.
        damage: Damage dealt by this hit.

    Returns:
        Dict with keys: label (str), has_data (bool), is_strong (bool|None),
        move_name (str).
    """
    mn = move_name(move_id)
    char_moves = MOVE_HITBOXES.get(character, {})
    info = char_moves.get(move_id)

    if info is None:
        return {"label": mn, "has_data": False, "is_strong": None, "move_name": mn}

    is_strong = damage >= info.threshold
    label = info.strong_label if is_strong else info.weak_label
    return {"label": label, "has_data": True, "is_strong": is_strong, "move_name": mn}


# ---------------------------------------------------------------------------
# Multi-game hit finder
# ---------------------------------------------------------------------------

def find_move_hits(
    replay_root: str | Path,
    pg: pd.DataFrame,
    tag: str,
    move: str | None = None,
    character: str | None = None,
) -> pd.DataFrame:
    """Find all hits of a move across replays and classify strong/weak.

    Scans replays for the given player/character, identifies frames where
    the opponent's percent increased, reads the attacker's last_attack_landed
    to determine the move, computes damage delta, and classifies each hit.

    Args:
        replay_root: Root directory of replays.
        pg: Player-game DataFrame from player_games().
        tag: Player tag to filter on (e.g. "EG＃0").
        move: Optional move name/alias to filter (e.g. "knee", "fair").
            If None, returns all hits.
        character: Optional character name/alias to filter.

    Returns:
        DataFrame with columns: move_name, move_id, damage, label, is_strong,
        has_data, opp_pct, frame, filename, character, opp_character.
    """
    # Resolve character alias
    char_filter = None
    if character:
        chars = resolve_character(character)
        if len(chars) == 1:
            char_filter = chars[0]
        else:
            char_filter = chars  # list for multi-char aliases like "spacies"

    # Resolve move alias (needs a single character for character-specific aliases)
    move_id_filter = None
    if move:
        resolve_char = char_filter if isinstance(char_filter, str) else None
        move_id_filter = resolve_move(move, character=resolve_char)
        if move_id_filter is None:
            raise ValueError(f"Could not resolve move: {move!r}")

    # Determine canonical character(s) for iteration
    iter_char = None
    if isinstance(char_filter, str):
        iter_char = char_filter
    # If char_filter is a list, we pass None and filter per-game below.

    rows = []
    for gi, my_df, opp_df, char_name in _iter_1v1_games(replay_root, pg, tag, character=iter_char):
        # If char_filter is a list (e.g. spacies), skip non-matching characters
        if isinstance(char_filter, list) and char_name not in char_filter:
            continue

        # Check multi-hit exclusions
        excluded = MULTI_HIT_EXCLUSIONS.get(char_name, set())

        opp_pct = opp_df["percent"].values.astype(float)
        opp_stocks = opp_df["stocks"].values.astype(float)
        opp_frames = opp_df["frame"].values.astype(int)

        # Build attacker's last_attack_landed lookup (frame -> move_id)
        atk_frames = my_df["frame"].values.astype(int)
        atk_lal = my_df["last_attack_landed"].values
        atk_lal_map = dict(zip(atk_frames, atk_lal))

        opp_char = opp_df["character_name"].iloc[0]
        fname = Path(gi["filepath"]).name

        # Find frames where opponent's percent increased (hit landed)
        for j in range(1, len(opp_pct)):
            if opp_pct[j] > opp_pct[j - 1] and opp_stocks[j] == opp_stocks[j - 1]:
                frame = int(opp_frames[j])
                damage = round(round(opp_pct[j], 1) - round(opp_pct[j - 1], 1), 1)

                # Get the move from attacker's last_attack_landed
                mid = int(atk_lal_map.get(frame, 0))
                if mid == 0:
                    continue

                # Skip multi-hit moves
                if mid in excluded:
                    continue

                # Filter to specific move if requested
                if move_id_filter is not None and mid != move_id_filter:
                    continue

                result = classify_hit(char_name, mid, damage)

                rows.append({
                    "move_name": result["move_name"],
                    "move_id": mid,
                    "damage": damage,
                    "label": result["label"],
                    "is_strong": result["is_strong"],
                    "has_data": result["has_data"],
                    "opp_pct": round(opp_pct[j - 1], 1),
                    "frame": frame,
                    "filename": fname,
                    "character": char_name,
                    "opp_character": opp_char,
                })

    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Coverage helper
# ---------------------------------------------------------------------------

def hitbox_coverage(character: str) -> list[dict]:
    """List which moves have hitbox classification data for a character.

    Args:
        character: Character name or alias.

    Returns:
        List of dicts with keys: move_id, move_name, strong_label,
        weak_label, threshold.
    """
    chars = resolve_character(character)
    results = []
    for char in chars:
        char_moves = MOVE_HITBOXES.get(char, {})
        for mid, info in sorted(char_moves.items()):
            results.append({
                "character": char,
                "move_id": mid,
                "move_name": move_name(mid),
                "strong_label": info.strong_label,
                "weak_label": info.weak_label,
                "threshold": info.threshold,
            })
    return results
