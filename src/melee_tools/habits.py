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
        me = me[me.character == character]
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

        if character and char_name != character:
            continue

        yield gi, my_df, opp_df, char_name


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
    from melee_tools.moves import move_name

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
    from melee_tools.action_states import ACTION_STATE_CATEGORIES

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
