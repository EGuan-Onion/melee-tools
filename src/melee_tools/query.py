"""Query building blocks for frame-level Melee replay analysis.

These functions are composable primitives for answering gameplay questions.
They operate on the DataFrames produced by melee_tools.frames.
"""

from pathlib import Path

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


# ---------------------------------------------------------------------------
# Multi-game helpers
# ---------------------------------------------------------------------------

def find_kills_for_character(
    replay_dir: str | Path,
    character_name: str,
    as_attacker: bool = True,
) -> pd.DataFrame:
    """Find all kills involving a specific character across all replays.

    Args:
        replay_dir: Directory of .slp files.
        character_name: Character name (e.g., "Captain Falcon").
        as_attacker: If True, find kills BY this character. If False, find deaths OF this character.

    Returns:
        DataFrame of kill events.
    """
    from melee_tools.frames import extract_frames

    replay_dir = Path(replay_dir)
    all_kills = []

    for slp_file in sorted(replay_dir.glob("*.slp")):
        try:
            result = extract_frames(str(slp_file), include_inputs=False)
        except Exception:
            continue

        game_info = result["game_info"]
        if game_info.get("end_method") not in ("RESOLVED", "GAME"):
            continue

        # Build port -> player index mapping
        port_to_info = {}
        for idx in result["players"]:
            df = result["players"][idx]
            port = int(df["port"].iloc[0])
            port_to_info[port] = {
                "player_index": idx,
                "character": df["character_name"].iloc[0],
            }

        if as_attacker:
            # Find kills where the attacker is our character
            # We check all victims' deaths and see who killed them
            for idx, df in result["players"].items():
                victim_char = df["character_name"].iloc[0]
                kills = find_kills(df)
                for _, kill in kills.iterrows():
                    attacker_port = kill.get("killed_by_port")
                    attacker_info = port_to_info.get(attacker_port, {})
                    if attacker_info.get("character") == character_name:
                        kill_dict = kill.to_dict()
                        kill_dict["attacker_character"] = character_name
                        kill_dict["victim_character"] = victim_char
                        kill_dict["filename"] = slp_file.name
                        kill_dict["stage"] = game_info.get("stage_name")
                        all_kills.append(kill_dict)
        else:
            # Find deaths of our character
            for idx, df in result["players"].items():
                if df["character_name"].iloc[0] != character_name:
                    continue
                kills = find_kills(df)
                for _, kill in kills.iterrows():
                    attacker_port = kill.get("killed_by_port")
                    attacker_info = port_to_info.get(attacker_port, {})
                    kill_dict = kill.to_dict()
                    kill_dict["attacker_character"] = attacker_info.get("character", "Unknown")
                    kill_dict["victim_character"] = character_name
                    kill_dict["filename"] = slp_file.name
                    kill_dict["stage"] = game_info.get("stage_name")
                    all_kills.append(kill_dict)

    return pd.DataFrame(all_kills) if all_kills else pd.DataFrame()


def post_state_actions(
    replay_dir: str | Path,
    character_name: str,
    trigger_category: str,
    target_category: str = "ground_attack",
    window_frames: int = 300,
) -> pd.DataFrame:
    """Find what action a character takes after exiting a state category.

    Example: post_state_actions(dir, "Fox", "damage", "ground_attack")
    → what ground attack does Fox use after leaving hitstun?

    Args:
        replay_dir: Directory of .slp files.
        character_name: Character to analyze.
        trigger_category: ACTION_STATE_CATEGORIES key for the trigger state.
        target_category: ACTION_STATE_CATEGORIES key for the action to look for.
            Use "any" to capture the very next state regardless.
        window_frames: How far ahead to search (default 300 = 5 seconds).
    """
    from melee_tools.frames import extract_frames

    replay_dir = Path(replay_dir)
    trigger_states = ACTION_STATE_CATEGORIES[trigger_category]

    if target_category == "any":
        # Build set of all non-trigger states
        target_states = set(ACTION_STATES.keys()) - trigger_states
    else:
        target_states = ACTION_STATE_CATEGORIES[target_category]

    all_results = []

    for slp_file in sorted(replay_dir.glob("*.slp")):
        try:
            result = extract_frames(str(slp_file), include_inputs=False)
        except Exception:
            continue

        if result["game_info"].get("end_method") not in ("RESOLVED", "GAME"):
            continue

        for idx, df in result["players"].items():
            if df["character_name"].iloc[0] != character_name:
                continue

            exits = find_state_exits(df, trigger_states)
            if len(exits) == 0:
                continue

            actions = next_action_after(df, exits.index, target_states, window_frames)
            for a in actions:
                a["filename"] = slp_file.name
                a["character"] = character_name
            all_results.extend(actions)

    return pd.DataFrame(all_results) if all_results else pd.DataFrame()
