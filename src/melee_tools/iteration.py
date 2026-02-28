"""Shared iteration utilities for scanning 1v1 replays by player tag.

The canonical _iter_1v1_games() iterator is used by combos, clips, habits,
hitboxes, neutral, and techniques modules.
"""

from pathlib import Path

import numpy as np
import pandas as pd

from melee_tools.frames import extract_frames


# ---------------------------------------------------------------------------
# Directional helper
# ---------------------------------------------------------------------------

def classify_direction(
    my_x: float,
    opp_x: float,
    facing: float,
    is_forward: bool,
) -> str:
    """Classify a directional action as 'toward' or 'away' from the opponent.

    Args:
        my_x: Player's x position.
        opp_x: Opponent's x position.
        facing: Player's facing direction (1.0 = right, -1.0 = left).
        is_forward: Whether the action goes in the facing direction.

    Returns:
        'toward' or 'away'.
    """
    opp_in_facing_dir = (facing > 0 and opp_x > my_x) or (facing < 0 and opp_x < my_x)
    if opp_in_facing_dir:
        return "toward" if is_forward else "away"
    return "away" if is_forward else "toward"


# ---------------------------------------------------------------------------
# Replay iteration helper
# ---------------------------------------------------------------------------

def _iter_1v1_games(
    replay_root: str | Path,
    pg: pd.DataFrame,
    tag: str,
    character: str | None = None,
):
    """Yield (game_info, my_df, opp_df, character_name) for each 1v1 game the player is in.

    Args:
        replay_root: Root directory of replays.
        pg: Player-game DataFrame from player_games().
        tag: Player tag to filter on (e.g. "EG＃0").
        character: Optional character filter. If None, include all characters.
    """
    me = pg[(pg.tag == tag) & pg.opp_character.notna()]
    if character:
        me = me[me.character.str.lower() == character.lower()]
    filenames = set(me.filename)

    slp_lookup = {f.name: f for f in Path(replay_root).rglob("*.slp")}

    for fname in sorted(filenames):
        fpath = slp_lookup.get(fname)
        if not fpath:
            continue
        try:
            result = extract_frames(str(fpath), include_inputs=False)
        except Exception:
            continue

        gi = result["game_info"]
        gi["filepath"] = str(fpath)
        if gi["num_players"] != 2:
            continue

        my_idx = None
        for i in range(2):
            t = gi.get(f"p{i}_netplay_code") or gi.get(f"p{i}_netplay_name") or gi.get(f"p{i}_name_tag") or ""
            if t == tag:
                my_idx = i
                break
        if my_idx is None:
            continue

        opp_idx = 1 - my_idx
        my_df = result["players"][my_idx]
        opp_df = result["players"][opp_idx]
        char_name = my_df["character_name"].iloc[0]

        if character and char_name.lower() != character.lower():
            continue

        yield gi, my_df, opp_df, char_name
