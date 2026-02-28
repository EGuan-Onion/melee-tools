"""Technique execution analysis across 1v1 replays.

Detects and quantifies advanced Melee techniques: L-cancels, SHFFLs,
wavedashes, ledge options, and crouch cancels.

Typical usage:
    from melee_tools import parse_replays, player_games
    from melee_tools.techniques import (
        aerial_stats, wavedash_stats, ledge_options, crouch_cancel_stats,
    )

    games = parse_replays("replays")
    pg = player_games(games)

    aerials = aerial_stats("replays", pg, "EG#0", character="Sheik")
    wds     = wavedash_stats("replays", pg, "EG#0")
    ledge   = ledge_options("replays", pg, "EG#0")
    cc      = crouch_cancel_stats("replays", pg, "EG#0")
"""

from pathlib import Path

import numpy as np
import pandas as pd

from melee_tools.action_states import ACTION_STATE_CATEGORIES
from melee_tools.iteration import _iter_1v1_games

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_AERIAL_CATS = ["nair", "fair", "bair", "uair", "dair"]
_AERIAL_STATE_TO_NAME: dict[int, str] = {}
for _cat in _AERIAL_CATS:
    for _s in ACTION_STATE_CATEGORIES[_cat]:
        _AERIAL_STATE_TO_NAME[_s] = _cat

_AERIAL_STATE_SET = set(_AERIAL_STATE_TO_NAME.keys())

_JUMPSQUAT = 24
_AIRDODGE = 236

# A sudden drop in vel_y this large (in one frame) = fast fall
_FF_VEL_DROP_THRESHOLD = -2.0

# Initial airborne vel_y below this value = short hop (vs full hop)
# Works for most top-tier characters (SH ~1.9–2.1, FH ~2.9–3.1)
_SH_VEL_THRESHOLD = 2.6

_GROUNDED = {14, 20, 21, 22, 23, 39, 40, 41}

_LEDGE_HANG = {253, 362, 363}

_LEDGE_NAMED = {
    254: "getup",
    255: "getup_slow",
    256: "attack",
    257: "attack_slow",
    258: "roll",
    259: "roll_slow",
    260: "jump",
    261: "jump",
    262: "jump",
    263: "jump",
}

_FALL_STATES = {29, 30, 31, 32, 33, 34}
_JUMP_AERIAL = {27, 28}  # JUMP_AERIAL_F, JUMP_AERIAL_B (double jump)

_DAMAGE_STATES = set(range(75, 92)) | {357}
_CROUCH_STATES = {39, 40, 41}

# Wavedash detection thresholds
_MIN_SLIDE_VEL = 0.5  # minimum |velx| at landing to count as a wavedash


# ---------------------------------------------------------------------------
# aerial_stats — L-cancel, short hop, fast fall per aerial
# ---------------------------------------------------------------------------


def aerial_stats(
    replay_root: str | Path,
    pg: pd.DataFrame,
    tag: str,
    character: str | None = None,
) -> pd.DataFrame:
    """Analyze aerial execution quality across 1v1 replays.

    For each L-cancel attempt, records the aerial type and whether the player
    executed a short hop and/or fast fall (i.e., a SHFFL).

    Args:
        replay_root: Root directory of replays.
        pg: Player-game DataFrame from player_games().
        tag: Player tag (e.g. "EG＃0").
        character: Optional character filter.

    Returns:
        DataFrame with columns:
            character, aerial, lc_success, short_hop, fastfall, shffl,
            percent (opponent %), filename
    """
    rows = []

    for gi, my_df, opp_df, char_name in _iter_1v1_games(replay_root, pg, tag, character):
        lc_mask = my_df["l_cancel"].isin([1.0, 2.0])
        if not lc_mask.any():
            continue

        states_arr = my_df["state"].values
        vely_arr = my_df["velocity_self_y"].fillna(0).values.astype(float)
        opp_pct_arr = opp_df["percent"].values.astype(float)
        opp_frames = opp_df["frame"].values.astype(int)
        opp_pct_map = dict(zip(opp_frames, opp_pct_arr))

        for pos, (idx, row) in enumerate(my_df[lc_mask].iterrows()):
            pos = my_df.index.get_loc(idx)
            lc_val = int(row["l_cancel"])
            frame = int(row["frame"])

            aerial_found = None
            fastfall = False
            short_hop = False

            for back in range(pos - 1, max(0, pos - 80), -1):
                s = int(states_arr[back]) if not pd.isna(states_arr[back]) else 0

                if aerial_found is None and s in _AERIAL_STATE_SET:
                    aerial_found = _AERIAL_STATE_TO_NAME[s]

                # Fast fall: sudden large negative velocity change while airborne
                if back > 0:
                    v_now = vely_arr[back]
                    v_prev = vely_arr[back - 1]
                    if (v_now - v_prev) < _FF_VEL_DROP_THRESHOLD:
                        fastfall = True

                # Short hop: jumpsquat exit velocity below full-hop threshold
                if s == _JUMPSQUAT:
                    if back + 1 < len(vely_arr):
                        v_first = vely_arr[back + 1]
                        if v_first < _SH_VEL_THRESHOLD:
                            short_hop = True
                    break

            opp_pct = opp_pct_map.get(frame, np.nan)
            rows.append({
                "character": char_name,
                "aerial": aerial_found or "unknown",
                "lc_success": lc_val == 1,
                "short_hop": short_hop,
                "fastfall": fastfall,
                "shffl": short_hop and fastfall and lc_val == 1,
                "opp_percent": float(opp_pct) if not np.isnan(opp_pct) else np.nan,
                "filename": gi["filename"],
            })

    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# detect_wavedashes — rich per-WD classification for a single game
# ---------------------------------------------------------------------------


def detect_wavedashes(
    player_df: pd.DataFrame,
    opp_df: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Detect all wavedashes in a single game's frame data and classify attributes.

    A wavedash is: JUMP_SQUAT (24) → ESCAPE_AIR (236) within a few frames of
    jumpsquat exit → grounded state with |velocity_self_x_ground| ≥ 0.5.

    Args:
        player_df: Frame DataFrame for one player (from extract_frames).
        opp_df: Optional opponent frame DataFrame. If provided, adds toward_opp.

    Returns:
        DataFrame with one row per wavedash:
            frame        — game frame at jumpsquat entry
            end_frame    — game frame at grounded landing
            pos_x        — x position at landing
            velx         — signed velocity at landing (+ = right, − = left)
            slide_vel    — abs(velx); higher = flatter/longer wavedash
            late_frames  — airborne frames before airdodge input (0 = optimal)
            is_late      — bool: late_frames > 0
            facing       — character facing at JS entry (1.0 = right, -1.0 = left)
            forward      — True if WD slides in the facing direction (standard WD)
            toward_opp   — True if WD slides toward opponent (None if opp_df absent)
            angle_cat    — "flat" (≥1.5) / "moderate" (0.8–1.5) / "steep" (0.5–0.8)

    Notes:
        - ``velocity_self_x_ground`` must be present; returns empty DataFrame if not.
        - Thresholds are empirical and not character-specific.  For Sheik/Falcon,
          max WD speed is roughly 2.5–2.9, so "flat" ≥ 1.5 ≈ 53 %+ of max.
    """
    if "velocity_self_x_ground" not in player_df.columns:
        return pd.DataFrame()

    states_arr    = player_df["state"].values
    frames_arr    = player_df["frame"].values.astype(int)
    posx_arr      = player_df["position_x"].fillna(0).values.astype(float)
    direction_arr = player_df["direction"].fillna(1.0).values.astype(float)
    velx_arr      = player_df["velocity_self_x_ground"].fillna(0).values.astype(float)

    opp_x_map: dict[int, float] | None = None
    if opp_df is not None:
        opp_x_map = dict(zip(
            opp_df["frame"].values.astype(int),
            opp_df["position_x"].fillna(0).values.astype(float),
        ))

    def _s(idx: int) -> int:
        v = states_arr[idx]
        return int(v) if not pd.isna(v) else 0

    rows = []
    n = len(states_arr)
    i = 1
    while i < n:
        # Detect jumpsquat entry (first JS frame after a non-JS frame)
        if _s(i) != _JUMPSQUAT or _s(i - 1) == _JUMPSQUAT:
            i += 1
            continue

        js_start_i = i
        facing = float(direction_arr[i]) if not np.isnan(direction_arr[i]) else 1.0

        # Advance through all consecutive JUMPSQUAT frames
        js_end_i = i
        j = i + 1
        while j < min(i + 15, n) and _s(j) == _JUMPSQUAT:
            js_end_i = j
            j += 1
        first_air_i = js_end_i + 1  # first frame no longer in jumpsquat

        # Look for AIRDODGE within a tight window after jumpsquat exit
        airdodge_i: int | None = None
        for j in range(first_air_i, min(first_air_i + 6, n)):
            sj = _s(j)
            if sj == _AIRDODGE:
                airdodge_i = j
                break
            if sj in _GROUNDED:
                break  # landed without airdodging → normal jump, not a WD

        if airdodge_i is None:
            i = first_air_i
            continue

        late_frames = airdodge_i - first_air_i  # 0 = airdodge on first airborne frame

        # Find grounded landing after airdodge
        land_i: int | None = None
        for k in range(airdodge_i + 1, min(airdodge_i + 20, n)):
            if _s(k) in _GROUNDED:
                land_i = k
                break

        if land_i is None:
            i = airdodge_i + 1
            continue

        vx = float(velx_arr[land_i])
        if abs(vx) < _MIN_SLIDE_VEL:
            # Nearly vertical airdodge (wavedown / stall) — skip
            i = land_i + 1
            continue

        pos_x     = float(posx_arr[land_i])
        slide_vel = abs(vx)
        forward   = (vx > 0 and facing > 0) or (vx < 0 and facing < 0)

        toward_opp: bool | None = None
        if opp_x_map is not None:
            opp_x = opp_x_map.get(int(frames_arr[land_i]))
            if opp_x is not None:
                toward_opp = (vx > 0 and opp_x > pos_x) or (vx < 0 and opp_x < pos_x)

        if slide_vel >= 1.5:
            angle_cat = "flat"
        elif slide_vel >= 0.8:
            angle_cat = "moderate"
        else:
            angle_cat = "steep"

        rows.append({
            "frame":       int(frames_arr[js_start_i]),
            "end_frame":   int(frames_arr[land_i]),
            "pos_x":       round(pos_x, 2),
            "velx":        round(vx, 3),
            "slide_vel":   round(slide_vel, 3),
            "late_frames": int(late_frames),
            "is_late":     bool(late_frames > 0),
            "facing":      float(facing),
            "forward":     bool(forward),
            "toward_opp":  toward_opp,
            "angle_cat":   angle_cat,
        })
        i = land_i + 1

    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# analyze_wavedashes — multi-game wrapper
# ---------------------------------------------------------------------------


def analyze_wavedashes(
    replay_root: str | Path,
    pg: pd.DataFrame,
    tag: str,
    character: str | None = None,
) -> pd.DataFrame:
    """Detect and classify wavedashes across all 1v1 replays for a player.

    Wraps detect_wavedashes() with tag-based player filtering across all
    matching games.  Returns every wavedash with full attribute columns.

    Args:
        replay_root: Root directory of replays.
        pg: Player-game DataFrame from player_games().
        tag: Player tag (e.g. "EG＃0").
        character: Optional character filter.

    Returns:
        DataFrame from detect_wavedashes() with character, filename, and
        duration_min columns added.

    Example:
        wds = analyze_wavedashes("replays", pg, "EG＃0", character="Sheik")
        wds["angle_cat"].value_counts()
        wds.groupby("forward")["slide_vel"].mean()
        wds.groupby("character")["is_late"].mean()
    """
    all_rows: list[pd.DataFrame] = []

    for gi, my_df, opp_df, char_name in _iter_1v1_games(replay_root, pg, tag, character):
        wds = detect_wavedashes(my_df, opp_df)
        if len(wds) == 0:
            continue

        frames_arr = my_df["frame"].values.astype(int)
        duration_min = (frames_arr[-1] - frames_arr[0]) / 3600.0

        wds["character"]    = char_name
        wds["filename"]     = gi["filename"]
        wds["duration_min"] = round(duration_min, 3)
        all_rows.append(wds)

    if not all_rows:
        return pd.DataFrame()

    return pd.concat(all_rows, ignore_index=True)


# ---------------------------------------------------------------------------
# wavedash_stats — legacy wrapper (use analyze_wavedashes for full attributes)
# ---------------------------------------------------------------------------


def wavedash_stats(
    replay_root: str | Path,
    pg: pd.DataFrame,
    tag: str,
    character: str | None = None,
) -> pd.DataFrame:
    """Detect wavedashes and record horizontal slide velocity.

    Thin wrapper around analyze_wavedashes() kept for backward compatibility.
    For richer attributes (late_frames, angle_cat, direction, etc.) use
    analyze_wavedashes() directly.

    Args:
        replay_root: Root directory of replays.
        pg: Player-game DataFrame from player_games().
        tag: Player tag.
        character: Optional character filter.

    Returns:
        DataFrame with columns:
            character, frame, slide_vel, pos_x, duration_min, filename
    """
    wds = analyze_wavedashes(replay_root, pg, tag, character)
    if wds.empty:
        return pd.DataFrame()
    return wds[["character", "frame", "slide_vel", "pos_x", "duration_min", "filename"]]


# ---------------------------------------------------------------------------
# ledge_options — classify what a player does from ledge
# ---------------------------------------------------------------------------

_LEDGE_OPTION_LABELS = {
    "getup": {254},
    "getup_slow": {255},
    "attack": {256},
    "attack_slow": {257},
    "roll": {258},
    "roll_slow": {259},
    "jump": {260, 261, 262, 263},
}
_LEDGE_STATE_TO_LABEL: dict[int, str] = {}
for _label, _states in _LEDGE_OPTION_LABELS.items():
    for _s in _states:
        _LEDGE_STATE_TO_LABEL[_s] = _label


def ledge_options(
    replay_root: str | Path,
    pg: pd.DataFrame,
    tag: str,
    character: str | None = None,
) -> pd.DataFrame:
    """Classify ledge get-up options across 1v1 replays.

    Options:
        getup / getup_slow  — stand up from ledge (254–255)
        attack / attack_slow — ledge attack (256–257)
        roll / roll_slow    — ledge roll (258–259)
        jump                — ledge jump (260–263)
        drop_jump           — drop then double jump (FALL → JUMP_AERIAL)
        ledgedash           — drop → jumpsquat → airdodge → land
        drop_other          — drop then some other action

    Args:
        replay_root: Root directory of replays.
        pg: Player-game DataFrame from player_games().
        tag: Player tag.
        character: Optional character filter.

    Returns:
        DataFrame with columns: character, option, percent, filename, frame
    """
    rows = []

    for gi, my_df, opp_df, char_name in _iter_1v1_games(replay_root, pg, tag, character):
        states_arr = my_df["state"].values
        pct_arr = my_df["percent"].fillna(0).values.astype(float)
        frames_arr = my_df["frame"].values.astype(int)
        in_hang = np.isin(states_arr, list(_LEDGE_HANG))

        for i in range(1, len(states_arr) - 15):
            if not in_hang[i]:
                continue
            # Find hang exit: this frame is hang, next is not
            next_idx = i + 1
            if next_idx >= len(states_arr) or in_hang[next_idx]:
                continue

            next_s = int(states_arr[next_idx]) if not pd.isna(states_arr[next_idx]) else 0

            # Named ledge options
            if next_s in _LEDGE_STATE_TO_LABEL:
                option = _LEDGE_STATE_TO_LABEL[next_s]

            elif next_s in _FALL_STATES:
                # Drop from ledge — classify by what follows
                # Ledgedash: drop → DJ → airdodge → land
                # Regrab:    drop → (optional DJ) → fall → ledge grab
                # Drop jump: drop → DJ → (no airdodge, no regrab)
                option = "drop_other"
                found_dj = False
                for j in range(next_idx + 1, min(next_idx + 25, len(states_arr))):
                    sj = int(states_arr[j]) if not pd.isna(states_arr[j]) else 0
                    if sj in _JUMP_AERIAL:
                        found_dj = True
                    elif found_dj and sj == _AIRDODGE:
                        option = "ledgedash"
                        break
                    elif sj in _LEDGE_HANG | {252}:
                        # Grabbed ledge (CLIFF_CATCH or CLIFF_WAIT) = regrab
                        option = "re_grab"
                        break
                    elif found_dj and sj in _FALL_STATES:
                        # DJ → falling = could be fastfall regrab, keep scanning
                        continue
                    elif found_dj:
                        # DJ → something other than airdodge/fall/ledge
                        option = "drop_jump"
                        break
                    elif sj in _DAMAGE_STATES:
                        option = "hit_offstage"
                        break

            else:
                option = "other"

            rows.append({
                "character": char_name,
                "option": option,
                "percent": float(pct_arr[i]),
                "frame": int(frames_arr[i]),
                "filename": gi["filename"],
            })

    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# crouch_cancel_stats — hits taken while crouching
# ---------------------------------------------------------------------------


def crouch_cancel_stats(
    replay_root: str | Path,
    pg: pd.DataFrame,
    tag: str,
    character: str | None = None,
) -> pd.DataFrame:
    """Detect hits absorbed while crouching (crouch cancels) across replays.

    A crouch cancel is detected when the player was in a crouching state
    (39–41) on the frame before entering hitstun with a damage increase.

    Args:
        replay_root: Root directory of replays.
        pg: Player-game DataFrame from player_games().
        tag: Player tag.
        character: Optional character filter.

    Returns:
        DataFrame with columns:
            character, was_crouching, damage, percent_before, filename
    """
    rows = []

    for gi, my_df, opp_df, char_name in _iter_1v1_games(replay_root, pg, tag, character):
        states_arr = my_df["state"].values
        pct_arr = my_df["percent"].values.astype(float)

        for i in range(1, len(states_arr)):
            s_now = int(states_arr[i]) if not pd.isna(states_arr[i]) else 0
            s_prev = int(states_arr[i - 1]) if not pd.isna(states_arr[i - 1]) else 0

            # Entering hitstun from non-hitstun
            if s_now not in _DAMAGE_STATES or s_prev in _DAMAGE_STATES:
                continue

            p_now = pct_arr[i]
            p_prev = pct_arr[i - 1]
            if np.isnan(p_now) or np.isnan(p_prev):
                continue
            damage = p_now - p_prev
            if damage <= 0:
                continue

            rows.append({
                "character": char_name,
                "was_crouching": s_prev in _CROUCH_STATES,
                "damage": round(float(damage), 1),
                "percent_before": round(float(p_prev), 1),
                "filename": gi["filename"],
            })

    return pd.DataFrame(rows)
