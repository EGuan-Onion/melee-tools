"""Query building blocks for frame-level Melee replay analysis.

These functions are composable primitives for answering gameplay questions.
They operate on the DataFrames produced by melee_tools.frames.
"""

import numpy as np
import pandas as pd

from melee_tools.action_states import (
    ACTION_STATE_CATEGORIES,
    ACTION_STATES,
    FRIENDLY_NAMES,
)
from melee_tools.moves import MOVE_NAMES, move_name


# ---------------------------------------------------------------------------
# State transition primitives
# ---------------------------------------------------------------------------

def find_state_entries(df: pd.DataFrame, states: set[int]) -> pd.DataFrame:
    """Find frames where a player ENTERS one of the given states.

    Returns rows from df where the state is in `states` but the previous
    frame's state was not.
    """
    in_states = df["state"].isin(states)
    entered = in_states & ~in_states.shift(1, fill_value=False)
    return df[entered].copy()


def find_state_exits(df: pd.DataFrame, states: set[int]) -> pd.DataFrame:
    """Find frames where a player EXITS one of the given states.

    Returns the last frame in each contiguous run of `states`.
    """
    in_states = df["state"].isin(states)
    exiting = in_states & ~in_states.shift(-1, fill_value=False)
    return df[exiting].copy()


def next_action_after(
    df: pd.DataFrame,
    trigger_indices: pd.Index,
    target_states: set[int],
    window_frames: int = 300,
) -> list[dict]:
    """For each trigger frame, find the first target state within a time window.

    Args:
        df: Player frame DataFrame.
        trigger_indices: DataFrame indices marking trigger events.
        target_states: States to look for after the trigger.
        window_frames: Max frames to search ahead (default 300 = 5 seconds).

    Returns:
        List of dicts with trigger_frame, action_frame, state, state_name, frames_after.
    """
    results = []
    frames = df["frame"].values
    states = df["state"].values

    for idx in trigger_indices:
        pos = df.index.get_loc(idx)
        trigger_frame = frames[pos]

        for j in range(pos + 1, min(pos + window_frames + 1, len(df))):
            if frames[j] - trigger_frame > window_frames:
                break
            if states[j] in target_states:
                state = int(states[j])
                results.append({
                    "trigger_frame": int(trigger_frame),
                    "action_frame": int(frames[j]),
                    "state": state,
                    "state_name": FRIENDLY_NAMES.get(
                        state, ACTION_STATES.get(state, f"Unknown({state})")
                    ),
                    "frames_after": int(frames[j] - trigger_frame),
                })
                break

    return results


# ---------------------------------------------------------------------------
# Kill analysis
# ---------------------------------------------------------------------------

BLASTZONE_MAP = {
    0: "bottom",   # DEAD_DOWN
    1: "left",     # DEAD_LEFT
    2: "right",    # DEAD_RIGHT
    3: "top",      # DEAD_UP
    4: "top",      # DEAD_UP_STAR
    5: "top",      # DEAD_UP_STAR_ICE
    6: "top",      # DEAD_UP_FALL
    7: "top",      # DEAD_UP_FALL_HIT_CAMERA
    8: "top",      # DEAD_UP_FALL_HIT_CAMERA_FLAT
    9: "top",      # DEAD_UP_FALL_ICE
    10: "top",     # DEAD_UP_FALL_HIT_CAMERA_ICE
}


def find_kills(df: pd.DataFrame, attacker_df: pd.DataFrame | None = None) -> pd.DataFrame:
    """Find all stock loss events for a player.

    Args:
        df: Victim's frame DataFrame.
        attacker_df: Attacker's frame DataFrame. If provided, killing_move is
            read from the attacker's last_attack_landed (correct). If None,
            killing_move is read from the victim's field (may be inaccurate).

    Returns DataFrame with one row per death:
        frame, death_percent, death_state, blastzone, killing_move_id, killing_move,
        killed_by_port, position_x, position_y
    """
    stocks = df["stocks"].values.astype(float)
    diffs = np.diff(stocks)
    death_indices = np.where(diffs < 0)[0]

    # Build attacker frame lookup if available
    _atk_lal_map = None
    if attacker_df is not None:
        atk_frames = attacker_df["frame"].values.astype(int)
        atk_lal = attacker_df["last_attack_landed"].values
        _atk_lal_map = dict(zip(atk_frames, atk_lal))

    rows = []
    for di in death_indices:
        pre_death = df.iloc[di]       # last frame alive
        post_death = df.iloc[di + 1] if di + 1 < len(df) else pre_death

        death_state = int(post_death["state"]) if not pd.isna(post_death["state"]) else None

        # Get killing move from attacker if available, else fall back to victim's field
        move_id = None
        if _atk_lal_map is not None:
            atk_val = _atk_lal_map.get(int(pre_death["frame"]))
            if atk_val is not None and not pd.isna(atk_val):
                move_id = int(atk_val)
        if move_id is None:
            val = pre_death["last_attack_landed"]
            move_id = int(val) if not pd.isna(val) else None

        rows.append({
            "frame": int(pre_death["frame"]),
            "stock_lost": int(pre_death["stocks"]),
            "death_percent": round(float(pre_death["percent"]), 1) if not pd.isna(pre_death["percent"]) else None,
            "death_state": death_state,
            "blastzone": BLASTZONE_MAP.get(death_state),
            "killing_move_id": move_id,
            "killing_move": move_name(move_id) if move_id is not None else None,
            "killed_by_port": int(pre_death["last_hit_by"]) if not pd.isna(pre_death["last_hit_by"]) else None,
            "death_x": float(post_death["position_x"]) if not pd.isna(post_death["position_x"]) else None,
            "death_y": float(post_death["position_y"]) if not pd.isna(post_death["position_y"]) else None,
        })

    return pd.DataFrame(rows)
