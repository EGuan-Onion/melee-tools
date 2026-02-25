"""Neutral game analysis: opening detection, approach options, stage control.

"Neutral" is the game phase where neither player has a clear advantage —
both are free to act (not in hitstun, grabbed, spawning, or dead).  A
neutral window ends the moment one player enters hitstun or gets grabbed.

Typical usage:
    from melee_tools import parse_replays, player_games
    from melee_tools.neutral import find_neutral_openings, stage_positions

    games = parse_replays("replays")
    pg = player_games(games)

    openings = find_neutral_openings("replays", pg, "EG#0", character="Sheik")
    print(openings["opener_move"].value_counts())
    print(openings.groupby("outcome")["neutral_frames"].describe())

    pos = stage_positions("replays", pg, "EG#0")
    print(pos.groupby("character")["pos_x"].describe())
"""

from pathlib import Path

import numpy as np
import pandas as pd

from melee_tools.action_states import ACTION_STATE_CATEGORIES
from melee_tools.habits import _iter_1v1_games
from melee_tools.moves import move_name

# ---------------------------------------------------------------------------
# State-eligibility helpers
# ---------------------------------------------------------------------------

_DAMAGE_STATES = set(range(75, 92)) | {357}
_GRABBED_STATES = ACTION_STATE_CATEGORIES.get("grabbed", set()) | {211, 212, 213, 214}
_DEAD_STATES = set(range(0, 11))
_SPAWN_STATES = {12, 13}
_LEDGE_HANG = {253, 362, 363}

# States where a player is NOT in neutral (advantage or disadvantage)
_NON_NEUTRAL_STATES = (
    _DAMAGE_STATES | _GRABBED_STATES | _DEAD_STATES | _SPAWN_STATES
)

# Broad move groupings for neutral opener analysis
OPENER_GROUPS: dict[str, str] = {
    "D-throw": "grab",  "F-throw": "grab", "U-throw": "grab", "B-throw": "grab",
    "Bair": "aerial", "Fair": "aerial", "Nair": "aerial",
    "Uair": "aerial", "Dair": "aerial",
    "Neutral B": "projectile",
    "Side B": "projectile",
    "Jab": "jab", "Jab 2": "jab", "Jab 3": "jab", "Jab 4": "jab",
    "F-tilt": "tilt", "U-tilt": "tilt", "D-tilt": "tilt",
    "Dash Attack": "dash_attack",
    "F-smash": "smash", "U-smash": "smash", "D-smash": "smash",
}


def _is_non_neutral(state: int) -> bool:
    return state in _NON_NEUTRAL_STATES


# ---------------------------------------------------------------------------
# find_neutral_openings
# ---------------------------------------------------------------------------


def find_neutral_openings(
    replay_root: str | Path,
    pg: pd.DataFrame,
    tag: str,
    character: str | None = None,
    min_neutral_frames: int = 15,
) -> pd.DataFrame:
    """Find each time a neutral window ends with a hit, across 1v1 replays.

    A neutral window is a period where both players are free to act (not in
    hitstun, grabbed, dead, or spawning) for at least ``min_neutral_frames``
    consecutive frames.

    Args:
        replay_root: Root directory of replays.
        pg: Player-game DataFrame from player_games().
        tag: Player tag.
        character: Optional character filter.
        min_neutral_frames: Minimum length of neutral window to count.
            Shorter bursts (e.g. brief respite between combo hits) are ignored.

    Returns:
        DataFrame with one row per neutral window that ends with a hit:
            character       — attacker's character
            outcome         — 'won' (tag won neutral) or 'lost' (opponent won)
            neutral_frames  — duration of the neutral window in frames
            opener_move     — move that ended neutral (name)
            opener_group    — broad category: aerial/grab/tilt/etc.
            my_pct          — tag player's percent at start of window
            opp_pct         — opponent's percent at start of window
            my_pos_x        — tag player's x position at window start
            stage           — stage name
            filename
    """
    rows = []

    for gi, my_df, opp_df, char_name in _iter_1v1_games(replay_root, pg, tag, character):
        my_states = my_df["state"].values
        opp_states = opp_df["state"].values
        my_frames = my_df["frame"].values.astype(int)
        opp_frames = opp_df["frame"].values.astype(int)
        my_posx = my_df["position_x"].values.astype(float)
        my_pct = my_df["percent"].values.astype(float)
        opp_pct_arr = opp_df["percent"].values.astype(float)
        my_lal = my_df["last_attack_landed"].values

        frame_set = sorted(set(my_frames) & set(opp_frames))
        my_f2i = {f: i for i, f in enumerate(my_frames)}
        opp_f2i = {f: i for i, f in enumerate(opp_frames)}

        stage = gi.get("stage_name", "Unknown")
        fname = gi["filename"]

        neutral_start_frame = None
        neutral_start_my_pct = 0.0
        neutral_start_opp_pct = 0.0
        neutral_start_my_x = 0.0

        for f in frame_set:
            mi = my_f2i[f]
            oi = opp_f2i[f]

            ms = int(my_states[mi]) if not pd.isna(my_states[mi]) else 0
            os_ = int(opp_states[oi]) if not pd.isna(opp_states[oi]) else 0

            both_free = not _is_non_neutral(ms) and not _is_non_neutral(os_)

            if both_free:
                if neutral_start_frame is None:
                    neutral_start_frame = f
                    neutral_start_my_pct = float(my_pct[mi]) if not np.isnan(my_pct[mi]) else 0.0
                    neutral_start_opp_pct = float(opp_pct_arr[oi]) if not np.isnan(opp_pct_arr[oi]) else 0.0
                    neutral_start_my_x = float(my_posx[mi]) if not np.isnan(my_posx[mi]) else 0.0
            else:
                if neutral_start_frame is not None:
                    nd = f - neutral_start_frame

                    if nd >= min_neutral_frames:
                        # Determine who won neutral
                        if ms in _DAMAGE_STATES and os_ not in _DAMAGE_STATES:
                            outcome = "lost"
                            move_id_val = my_lal[mi]
                        elif os_ in _DAMAGE_STATES and ms not in _DAMAGE_STATES:
                            outcome = "won"
                            move_id_val = my_lal[mi]
                        else:
                            neutral_start_frame = None
                            continue

                        move_id = int(move_id_val) if not pd.isna(move_id_val) else None
                        mv = move_name(move_id) if move_id else "unknown"

                        rows.append({
                            "character": char_name,
                            "outcome": outcome,
                            "neutral_frames": nd,
                            "opener_move": mv,
                            "opener_group": OPENER_GROUPS.get(mv, "other"),
                            "my_pct": neutral_start_my_pct,
                            "opp_pct": neutral_start_opp_pct,
                            "my_pos_x": neutral_start_my_x,
                            "stage": stage,
                            "filename": fname,
                        })

                neutral_start_frame = None

    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# stage_positions — x/y position data during configurable states
# ---------------------------------------------------------------------------


def stage_positions(
    replay_root: str | Path,
    pg: pd.DataFrame,
    tag: str,
    character: str | None = None,
    state_filter: str | set[int] | None = "neutral",
    sample_every: int = 10,
) -> pd.DataFrame:
    """Collect per-frame position data for heat-map analysis.

    Args:
        replay_root: Root directory of replays.
        pg: Player-game DataFrame from player_games().
        tag: Player tag.
        character: Optional character filter.
        state_filter:
            - "neutral"  — only frames where both players are neutral-eligible (default)
            - "all"      — all frames
            - A set of action state IDs to filter to specific states
        sample_every: Keep 1 in every N frames to reduce dataset size.

    Returns:
        DataFrame with columns: character, frame, pos_x, pos_y, filename
    """
    rows = []

    for gi, my_df, opp_df, char_name in _iter_1v1_games(replay_root, pg, tag, character):
        my_states = my_df["state"].values
        opp_states = opp_df["state"].values
        my_frames = my_df["frame"].values.astype(int)
        opp_frames = opp_df["frame"].values.astype(int)
        my_posx = my_df["position_x"].values.astype(float)
        my_posy = my_df["position_y"].values.astype(float)
        fname = gi["filename"]

        if state_filter == "neutral":
            frame_set = sorted(set(my_frames) & set(opp_frames))
            my_f2i = {f: i for i, f in enumerate(my_frames)}
            opp_f2i = {f: i for i, f in enumerate(opp_frames)}

            for idx_f, f in enumerate(frame_set):
                if idx_f % sample_every != 0:
                    continue
                mi = my_f2i[f]
                oi = opp_f2i[f]
                ms = int(my_states[mi]) if not pd.isna(my_states[mi]) else 0
                os_ = int(opp_states[oi]) if not pd.isna(opp_states[oi]) else 0
                if _is_non_neutral(ms) or _is_non_neutral(os_):
                    continue
                rows.append({
                    "character": char_name,
                    "frame": f,
                    "pos_x": float(my_posx[mi]),
                    "pos_y": float(my_posy[mi]),
                    "filename": fname,
                })

        elif state_filter == "all":
            for i in range(0, len(my_frames), sample_every):
                rows.append({
                    "character": char_name,
                    "frame": int(my_frames[i]),
                    "pos_x": float(my_posx[i]),
                    "pos_y": float(my_posy[i]),
                    "filename": fname,
                })

        else:
            # Custom state set
            target_states = set(state_filter)
            for i in range(0, len(my_states), sample_every):
                s = int(my_states[i]) if not pd.isna(my_states[i]) else 0
                if s in target_states:
                    rows.append({
                        "character": char_name,
                        "frame": int(my_frames[i]),
                        "pos_x": float(my_posx[i]),
                        "pos_y": float(my_posy[i]),
                        "filename": fname,
                    })

    return pd.DataFrame(rows)
