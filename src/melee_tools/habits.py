"""Multi-game habit analysis for a specific player across 1v1 replays.

These functions scan replay directories and produce DataFrames of
per-event records (rolls, knockdowns, etc.) with directional classification
relative to the opponent.

Typical usage:
    from melee_tools import parse_replays, player_games, analyze_rolls, analyze_knockdowns

    games = parse_replays("replays")
    pg = player_games(games)

    rolls = analyze_rolls("replays", pg, tag="EG＃0")
    knockdowns = analyze_knockdowns("replays", pg, tag="EG＃0")
"""

from pathlib import Path

import numpy as np
import pandas as pd

from melee_tools.action_states import ACTION_STATE_CATEGORIES
from melee_tools.iteration import _iter_1v1_games, classify_direction
from melee_tools.moves import move_name
from melee_tools.techniques import detect_wavedashes


def _get_opp_x(opp_df: pd.DataFrame, frame: int) -> float | None:
    """Get opponent's x position at a specific frame."""
    opp_row = opp_df[opp_df["frame"] == frame]
    if len(opp_row) == 0:
        return None
    return float(opp_row.iloc[0]["position_x"])


# ---------------------------------------------------------------------------
# Roll analysis
# ---------------------------------------------------------------------------

_ROLL_F = 233  # ESCAPE_F — roll in facing direction
_ROLL_B = 234  # ESCAPE_B — roll opposite facing direction


def analyze_rolls(
    replay_root: str | Path,
    pg: pd.DataFrame,
    tag: str,
    character: str | None = None,
) -> pd.DataFrame:
    """Analyze roll direction (toward/away) for a player across 1v1 replays.

    Args:
        replay_root: Root directory of replays.
        pg: Player-game DataFrame from player_games().
        tag: Player tag to filter on.
        character: Optional character filter.

    Returns:
        DataFrame with columns: character, direction ('toward'/'away'),
        roll_type ('forward'/'backward'), percent, filename, frame.
    """
    rows = []

    for gi, my_df, opp_df, char_name in _iter_1v1_games(replay_root, pg, tag, character):
        rolls = my_df[my_df["state"].isin({_ROLL_F, _ROLL_B})].copy()
        rolls = rolls[rolls["state"] != rolls["state"].shift(1)]

        for _, roll in rolls.iterrows():
            opp_x = _get_opp_x(opp_df, roll["frame"])
            if opp_x is None:
                continue

            is_fwd = int(roll["state"]) == _ROLL_F
            direction = classify_direction(
                float(roll["position_x"]), opp_x, float(roll["direction"]), is_fwd,
            )
            rows.append({
                "character": char_name,
                "direction": direction,
                "roll_type": "forward" if is_fwd else "backward",
                "percent": float(roll["percent"]),
                "filename": gi["filename"],
                "frame": int(roll["frame"]),
            })

    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Knockdown / tech analysis
# ---------------------------------------------------------------------------

# Tech options
_TECH_IN_PLACE = 199
_TECH_ROLL_F = 200
_TECH_ROLL_B = 201

# Missed tech
_MISSED_BOUND = {183, 191}  # DOWN_BOUND_U, DOWN_BOUND_D
_MISSED_WAIT = {184, 192}   # DOWN_WAIT_U, DOWN_WAIT_D
_HIT_DOWN = {185, 193}      # DOWN_DAMAGE_U, DOWN_DAMAGE_D

# Missed tech followups
_GETUP = {186, 194}          # DOWN_STAND_U, DOWN_STAND_D
_GETUP_ATTACK = {187, 195}   # DOWN_ATTACK_U, DOWN_ATTACK_D
_DOWN_ROLL_F = {188, 196}    # DOWN_FOWARD_U, DOWN_FOWARD_D
_DOWN_ROLL_B = {189, 197}    # DOWN_BACK_U, DOWN_BACK_D

_FALL_STATES = {29, 30, 31, 32, 33, 34}
_DAMAGE_STATES = set(range(75, 92)) | {357}


def analyze_knockdowns(
    replay_root: str | Path,
    pg: pd.DataFrame,
    tag: str,
    character: str | None = None,
) -> pd.DataFrame:
    """Analyze all knockdown situations for a player across 1v1 replays.

    Classifies each knockdown into one of:
        tech in place, tech toward, tech away,
        getup, getup attack, roll toward, roll away,
        slideoff, hit while down.

    Args:
        replay_root: Root directory of replays.
        pg: Player-game DataFrame from player_games().
        tag: Player tag to filter on.
        character: Optional character filter.

    Returns:
        DataFrame with columns: character, option, percent, filename, frame.
    """
    rows = []

    for gi, my_df, opp_df, char_name in _iter_1v1_games(replay_root, pg, tag, character):
        states = my_df["state"].values
        frames = my_df["frame"].values
        airborne_vals = my_df["airborne"].values
        percents = my_df["percent"].values
        fname = gi["filename"]

        def _add(option, frame, pct):
            rows.append({"character": char_name, "option": option, "percent": float(pct),
                         "filename": fname, "frame": int(frame)})

        def _direction_at(j, is_fwd):
            opp_x = _get_opp_x(opp_df, frames[j])
            if opp_x is None:
                return None
            return classify_direction(
                float(my_df.iloc[j]["position_x"]), opp_x,
                float(my_df.iloc[j]["direction"]), is_fwd,
            )

        # --- Successful techs ---
        in_tech = my_df["state"].isin({_TECH_IN_PLACE, _TECH_ROLL_F, _TECH_ROLL_B})
        tech_entries = in_tech & ~in_tech.shift(1, fill_value=False)
        for idx in my_df.index[tech_entries]:
            pos = my_df.index.get_loc(idx)
            s = int(states[pos])
            pct = percents[pos]
            if s == _TECH_IN_PLACE:
                _add("tech in place", frames[pos], pct)
            else:
                d = _direction_at(pos, s == _TECH_ROLL_F)
                if d:
                    _add(f"tech {d}", frames[pos], pct)

        # --- Missed techs → followups ---
        in_bound = my_df["state"].isin(_MISSED_BOUND)
        bound_entries = in_bound & ~in_bound.shift(1, fill_value=False)
        for idx in my_df.index[bound_entries]:
            pos = my_df.index.get_loc(idx)
            pct = percents[pos]  # percent at time of knockdown
            for j in range(pos + 1, min(pos + 300, len(my_df))):
                s = int(states[j])
                if s in _MISSED_BOUND or s in _MISSED_WAIT:
                    continue
                if s in _FALL_STATES and not pd.isna(airborne_vals[j]) and bool(airborne_vals[j]):
                    _add("slideoff", frames[j], pct)
                elif s in _HIT_DOWN or s in _DAMAGE_STATES:
                    _add("hit while down", frames[j], pct)
                elif s in _GETUP:
                    _add("getup", frames[j], pct)
                elif s in _GETUP_ATTACK:
                    _add("getup attack", frames[j], pct)
                elif s in _DOWN_ROLL_F or s in _DOWN_ROLL_B:
                    d = _direction_at(j, s in _DOWN_ROLL_F)
                    if d:
                        _add(f"roll {d}", frames[j], pct)
                else:
                    break
                break

    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Hits taken (opponent hits on this player)
# ---------------------------------------------------------------------------

def analyze_hits_taken(
    replay_root: str | Path,
    pg: pd.DataFrame,
    tag: str,
    character: str | None = None,
) -> pd.DataFrame:
    """Detect all hits the opponent lands on this player across 1v1 replays.

    Symmetric to find_move_hits() but from the victim's perspective:
    scans for frames where the player's percent increases, then reads the
    opponent's last_attack_landed to identify the move.

    Args:
        replay_root: Root directory of replays.
        pg: Player-game DataFrame from player_games().
        tag: Player tag.
        character: Optional character filter.

    Returns:
        DataFrame with columns: move, move_id, damage, my_pct,
        frame, filename, character, opp_character.

    Example:
        hits = analyze_hits_taken("replays", pg, "EG＃0", character="Sheik")
        hits.groupby(["opp_character", "move"]).agg(
            count=("damage", "count"), avg_dmg=("damage", "mean")
        ).sort_values("count", ascending=False)
    """
    rows = []
    for gi, my_df, opp_df, char_name in _iter_1v1_games(replay_root, pg, tag, character):
        my_pct = my_df["percent"].values.astype(float)
        my_stocks = my_df["stocks"].values.astype(float)
        my_frames = my_df["frame"].values.astype(int)

        opp_lal = opp_df["last_attack_landed"].values
        opp_frames = opp_df["frame"].values.astype(int)
        opp_lal_map = dict(zip(opp_frames, opp_lal))
        opp_char = opp_df["character_name"].iloc[0]
        fname = gi["filename"]

        for j in range(1, len(my_pct)):
            if my_pct[j] > my_pct[j - 1] and my_stocks[j] == my_stocks[j - 1]:
                frame = int(my_frames[j])
                damage = round(round(my_pct[j], 1) - round(my_pct[j - 1], 1), 1)
                lal_val = opp_lal_map.get(frame)
                if lal_val is None or pd.isna(lal_val):
                    continue
                mid = int(lal_val)
                if mid == 0:
                    continue
                rows.append({
                    "move": move_name(mid),
                    "move_id": mid,
                    "damage": damage,
                    "my_pct": round(my_pct[j - 1], 1),
                    "frame": frame,
                    "filename": fname,
                    "character": char_name,
                    "opp_character": opp_char,
                })

    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Neutral attack detection (hits + whiffs)
# ---------------------------------------------------------------------------

# Map action state category name -> display name (matches moves.py MOVE_NAMES)
_ATTACK_CAT_TO_MOVE = {
    "jab": "Jab",
    "dash_attack": "Dash Attack",
    "ftilt": "F-tilt",
    "utilt": "U-tilt",
    "dtilt": "D-tilt",
    "fsmash": "F-smash",
    "usmash": "U-smash",
    "dsmash": "D-smash",
    "nair": "Nair",
    "fair": "Fair",
    "bair": "Bair",
    "uair": "Uair",
    "dair": "Dair",
}


def analyze_neutral_attacks(
    replay_root: str | Path,
    pg: pd.DataFrame,
    tag: str,
    character: str | None = None,
    hit_window: int = 30,
) -> pd.DataFrame:
    """Detect all attack uses (hits and whiffs) across 1v1 replays.

    Unlike analyze_combos() which only captures hits, this function detects
    every time the player enters an attack animation and records whether it
    connected within hit_window frames.

    Args:
        replay_root: Root directory of replays.
        pg: Player-game DataFrame from player_games().
        tag: Player tag.
        character: Optional character filter.
        hit_window: Frames after attack entry to check for a hit (last_attack_landed
            change on the attacker). Default 30 (~0.5 sec).

    Returns:
        DataFrame with columns:
            move       — attack name (e.g. "Fair", "Nair")
            hit        — True if the attack connected
            opp_pct    — opponent's percent when the attack started
            frame      — game frame of the attack entry
            filename   — source .slp filename
            character  — player's character

    Example:
        attacks = analyze_neutral_attacks("replays", pg, "EG＃0", character="Captain Falcon")
        attacks = add_pct_buckets(attacks, pct_col="opp_pct")
        plot_moves_by_bucket(attacks, title="Falcon Neutral Attacks by %")
    """
    # Build state -> category lookup (only for attack categories)
    state_to_cat: dict[int, str] = {}
    for cat in _ATTACK_CAT_TO_MOVE:
        for s in ACTION_STATE_CATEGORIES[cat]:
            state_to_cat[s] = cat

    rows = []
    for gi, my_df, opp_df, char_name in _iter_1v1_games(replay_root, pg, tag, character):
        my_states = my_df["state"].values
        my_frames = my_df["frame"].values.astype(int)
        my_lal = my_df["last_attack_landed"].values
        opp_pct_arr = opp_df["percent"].values.astype(float)
        opp_frames_arr = opp_df["frame"].values.astype(int)
        fname = gi["filename"]

        opp_pct_map = dict(zip(opp_frames_arr, opp_pct_arr))

        for i in range(1, len(my_states)):
            s = int(my_states[i]) if not pd.isna(my_states[i]) else 0
            prev_s = int(my_states[i - 1]) if not pd.isna(my_states[i - 1]) else 0
            cat = state_to_cat.get(s)
            if cat is None or state_to_cat.get(prev_s) == cat:
                continue  # not an attack state entry

            frame = int(my_frames[i])
            cur_lal = my_lal[i] if not pd.isna(my_lal[i]) else 0
            opp_pct = opp_pct_map.get(frame, np.nan)

            # Hit = last_attack_landed changes within hit_window frames
            hit = False
            for j in range(i + 1, min(i + hit_window + 1, len(my_frames))):
                jlal = my_lal[j] if not pd.isna(my_lal[j]) else 0
                if jlal != cur_lal and jlal != 0:
                    hit = True
                    break

            rows.append({
                "move": _ATTACK_CAT_TO_MOVE[cat],
                "hit": hit,
                "opp_pct": float(opp_pct) if not np.isnan(opp_pct) else np.nan,
                "frame": frame,
                "filename": fname,
                "character": char_name,
            })

    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Attacker response classification
# ---------------------------------------------------------------------------

_ATKRESP_CATS = [
    "jab", "ftilt", "utilt", "dtilt", "fsmash", "usmash", "dsmash",
    "dash_attack", "grab", "nair", "fair", "bair", "uair", "dair",
]
_ATKRESP_DISPLAY = {
    "jab": "Jab", "ftilt": "F-tilt", "utilt": "U-tilt", "dtilt": "D-tilt",
    "fsmash": "F-smash", "usmash": "U-smash", "dsmash": "D-smash",
    "dash_attack": "Dash Attack", "grab": "Grab",
    "nair": "Nair", "fair": "Fair", "bair": "Bair", "uair": "U-air", "dair": "D-air",
}
_ATKRESP_STATE_MAP: dict[int, str] = {}
for _cat in _ATKRESP_CATS:
    for _s in ACTION_STATE_CATEGORIES.get(_cat, set()):
        _ATKRESP_STATE_MAP[_s] = _ATKRESP_DISPLAY[_cat]

# Transitional states to skip when looking for first meaningful attacker action
_ATKRESP_SKIP = frozenset({
    14,                         # WAIT
    24,                         # KNEE_BEND (jumpsquat)
    42, 43,                     # LANDING
    15, 16, 17,                 # WALK
    20, 21, 22, 23,             # DASH/RUN
    18, 19,                     # TURN
    25, 26, 27, 28,             # JUMP
    29, 30, 31, 32, 33, 34,    # FALL
})


def classify_attacker_response(
    states: np.ndarray,
    frames: np.ndarray,
    trigger_frame: int,
    window: int = 60,
) -> str:
    """Classify the attacker's first meaningful action after a trigger frame.

    Scans a window of frames for the first non-transitional state and returns
    a human-readable action name. Useful for analyzing what a player does after
    knocking down an opponent.

    Designed to work with raw numpy arrays so it can be called from both
    library multi-game wrappers and custom peppi_py scanners.

    Args:
        states: Array of action state IDs for the attacker.
        frames: Array of frame numbers corresponding to states.
        trigger_frame: Frame at which the event occurred (e.g., knockdown).
        window: Number of frames to search ahead. Default 60 (1 second).

    Returns:
        Action name string (e.g. "Grab", "D-smash", "Wavedash", "Shield"),
        or "Other/None" if no meaningful action found in window.
    """
    start_idx = int(np.searchsorted(frames, trigger_frame))
    end_idx = int(np.searchsorted(frames, trigger_frame + window))
    for i in range(start_idx, min(end_idx, len(states))):
        s = int(states[i]) if not np.isnan(states[i]) else 0
        if s in _ATKRESP_SKIP:
            continue
        if s in _ATKRESP_STATE_MAP:
            return _ATKRESP_STATE_MAP[s]
        if s == 236:            # ESCAPE_AIR — wavedash (no position check here)
            return "Wavedash"
        if s in {178, 179, 180}:  # shield
            return "Shield"
        break
    return "Other/None"


# ---------------------------------------------------------------------------
# Out-of-shield option analysis
# ---------------------------------------------------------------------------

_OOS_SHIELD_STATES = frozenset(ACTION_STATE_CATEGORIES.get("shield", {178, 179, 180, 349}))
_OOS_GRAB_STATES   = frozenset(ACTION_STATE_CATEGORIES.get("grab",   {212, 213, 214, 215}))
_OOS_ROLL_ST       = frozenset({233, 234})
_OOS_SPOTDODGE_ST  = frozenset({235})
_OOS_FALL_ST       = frozenset({29, 30, 31, 32, 33, 34})
_OOS_GROUNDED_ST   = frozenset({14, 20, 21, 22, 23, 39, 40, 41})
_OOS_JS            = 24   # JUMPSQUAT

_OOS_AERIAL_ST: set[int] = set()
for _cat in ["nair", "fair", "bair", "uair", "dair"]:
    _OOS_AERIAL_ST |= set(ACTION_STATE_CATEGORIES.get(_cat, set()))

_OOS_ATTACK_ST: set[int] = set()
for _cat in ["jab", "ftilt", "utilt", "dtilt", "fsmash", "usmash", "dsmash", "dash_attack"]:
    _OOS_ATTACK_ST |= set(ACTION_STATE_CATEGORIES.get(_cat, set()))


def _classify_oos_exit(states_arr: np.ndarray, frames_arr: np.ndarray, i: int, wd_frame_set: set) -> "str | None":
    """Classify a single shield exit at array index i."""
    n = len(states_arr)
    s = int(states_arr[i]) if not pd.isna(states_arr[i]) else 0

    if s in _OOS_GRAB_STATES:  return "grab OOS"
    if s in _OOS_ATTACK_ST:    return "attack OOS"
    if s in _OOS_ROLL_ST:      return "roll OOS"
    if s in _OOS_SPOTDODGE_ST: return "spotdodge OOS"
    if s in _OOS_FALL_ST:      return "shield drop"

    if s == _OOS_JS:
        js_frame = int(frames_arr[i])
        if js_frame in wd_frame_set:
            return None  # wavedash rows already added separately
        for j in range(i + 1, min(i + 25, n)):
            sj = int(states_arr[j]) if not pd.isna(states_arr[j]) else 0
            if sj in _OOS_AERIAL_ST:
                return "aerial OOS"
            if sj in _OOS_GROUNDED_ST or sj in _OOS_ROLL_ST or sj in _OOS_SPOTDODGE_ST:
                break
        return "jump → other"

    return None


def analyze_oos_options(
    replay_root,
    pg: pd.DataFrame,
    tag: str,
    character: "str | None" = None,
) -> pd.DataFrame:
    """Analyze out-of-shield options for a player across 1v1 replays.

    Classifies each shield exit as one of:
        wavedash toward, wavedash back, aerial OOS,
        grab OOS, attack OOS, roll OOS,
        spotdodge OOS, jump → other, shield drop.

    Wavedash exits are detected via detect_wavedashes() and separated from
    other jumpsquat exits.

    Args:
        replay_root: Root directory of replays.
        pg: Player-game DataFrame from player_games().
        tag: Player tag.
        character: Optional character filter.

    Returns:
        DataFrame with columns: character, option.
        Aggregate with: df.groupby(["character", "option"]).size()
    """
    rows = []
    for gi, my_df, opp_df, char_name in _iter_1v1_games(replay_root, pg, tag, character):
        states_arr = my_df["state"].values
        frames_arr = my_df["frame"].values.astype(int)

        wds = detect_wavedashes(my_df, opp_df)
        wd_frame_set = set(wds["frame"].values) if len(wds) > 0 else set()

        for _, wd in wds.iterrows():
            if wd["toward_opp"] is not None:
                opt = "wavedash toward" if wd["toward_opp"] else "wavedash back"
            else:
                opt = "wavedash OOS"
            rows.append({"character": char_name, "option": opt})

        for i in range(1, len(states_arr)):
            s_prev = int(states_arr[i - 1]) if not pd.isna(states_arr[i - 1]) else 0
            s_curr = int(states_arr[i])     if not pd.isna(states_arr[i])     else 0
            if s_prev in _OOS_SHIELD_STATES and s_curr not in _OOS_SHIELD_STATES:
                opt = _classify_oos_exit(states_arr, frames_arr, i, wd_frame_set)
                if opt:
                    rows.append({"character": char_name, "option": opt})

    return pd.DataFrame(rows) if rows else pd.DataFrame(columns=["character", "option"])
