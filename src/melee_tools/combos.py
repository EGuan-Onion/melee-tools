"""Combo and conversion detection from per-frame player DataFrames.

Detects sequences of hits (percent increases on the defender) grouped by
a tunable gap parameter.  Strictness presets range from true combos
(gap=0, continuous hitstun) to ledgeguard-level sequences (gap=180).

Typical usage:
    from melee_tools import detect_combos, analyze_combos

    # Single game — from extract_frames output
    combos = detect_combos(attacker_df, defender_df, gap_frames=45)

    # Multi-game — across a replay directory
    all_combos = analyze_combos("replays", pg, "EG＃0")
"""

from pathlib import Path

import numpy as np
import pandas as pd

from melee_tools.moves import move_name

_STRICTNESS_PRESETS = {
    0: 0,    # true combo — continuous hitstun
    1: 45,   # default — slippi-js style
    2: 90,   # tech chase
    3: 180,  # ledgeguard / scramble
}


def detect_combos(
    attacker_df: pd.DataFrame,
    defender_df: pd.DataFrame,
    gap_frames: int = 45,
) -> pd.DataFrame:
    """Detect combos from frame data.

    A combo starts when the defender's percent increases and ends when
    ``gap_frames`` pass with no new hit, or the defender loses a stock.

    Args:
        attacker_df: Attacker's frame DataFrame (unused currently, reserved).
        defender_df: Defender's frame DataFrame with percent, stocks,
            last_attack_landed, and frame columns.
        gap_frames: Max idle frames between hits before ending a combo.

    Returns:
        DataFrame with one row per combo: start_frame, end_frame, damage,
        num_hits, started_by, ended_by, killed, start_pct, end_pct.
    """
    pct = defender_df["percent"].values.astype(float)
    stocks = defender_df["stocks"].values.astype(float)
    frames = defender_df["frame"].values.astype(int)
    last_attack = defender_df["last_attack_landed"].values

    def _make_combo(sf, ef, sp, ep, nh, sb, eb, killed):
        return {
            "start_frame": sf,
            "end_frame": ef,
            "damage": round(round(ep, 1) - round(sp, 1), 1),
            "num_hits": nh,
            "started_by": move_name(sb),
            "ended_by": move_name(eb),
            "killed": killed,
            "start_pct": round(sp, 1),
            "end_pct": round(ep, 1),
        }

    combos = []
    in_combo = False
    start_frame = 0
    start_pct = 0.0
    last_hit_frame = 0
    num_hits = 0
    started_by = 0
    ended_by = 0
    current_pct = 0.0

    # Max frames between last hit and stock loss to attribute as a kill.
    # Blast zone travel can take 100+ frames after the final hit.
    _KILL_WINDOW = 150

    for i in range(1, len(pct)):
        if np.isnan(pct[i]) or np.isnan(pct[i - 1]):
            continue

        dmg = pct[i] - pct[i - 1]
        hit = dmg > 0
        stock_lost = (not np.isnan(stocks[i]) and not np.isnan(stocks[i - 1])
                      and stocks[i] < stocks[i - 1])

        if hit:
            move_id = int(last_attack[i]) if not pd.isna(last_attack[i]) else 0
            if not in_combo:
                in_combo = True
                start_frame = int(frames[i])
                start_pct = float(pct[i - 1])
                started_by = move_id
                num_hits = 1
            else:
                num_hits += 1
            ended_by = move_id
            last_hit_frame = int(frames[i])
            current_pct = float(pct[i])

        if in_combo and stock_lost:
            # Stock lost while combo is still active — clear kill
            combos.append(_make_combo(
                start_frame, int(frames[i]), start_pct, current_pct,
                num_hits, started_by, ended_by, True,
            ))
            in_combo = False
            continue

        if not in_combo and stock_lost and combos:
            # Stock lost shortly after a combo ended — retroactively mark as kill
            last = combos[-1]
            if not last["killed"] and (int(frames[i]) - last["end_frame"]) <= _KILL_WINDOW:
                last["killed"] = True
                last["end_frame"] = int(frames[i])
            continue

        if in_combo and not hit and (int(frames[i]) - last_hit_frame) > gap_frames:
            combos.append(_make_combo(
                start_frame, last_hit_frame, start_pct, current_pct,
                num_hits, started_by, ended_by, False,
            ))
            in_combo = False

    # Close any open combo at end of game
    if in_combo:
        combos.append(_make_combo(
            start_frame, last_hit_frame, start_pct, current_pct,
            num_hits, started_by, ended_by, False,
        ))

    return pd.DataFrame(combos)


def detect_combos_by_strictness(
    attacker_df: pd.DataFrame,
    defender_df: pd.DataFrame,
    strictness: int = 1,
) -> pd.DataFrame:
    """Detect combos using a strictness preset.

    Strictness levels:
        0 — true combo (gap=0, continuous hitstun)
        1 — default slippi-js style (gap=45)
        2 — tech chase (gap=90)
        3 — ledgeguard / scramble (gap=180)
    """
    gap = _STRICTNESS_PRESETS.get(strictness, 45)
    df = detect_combos(attacker_df, defender_df, gap_frames=gap)
    df["strictness_level"] = strictness
    return df


def analyze_combos(
    replay_root: str | Path,
    pg: pd.DataFrame,
    tag: str,
    character: str | None = None,
    gap_frames: int = 45,
    as_attacker: bool = True,
) -> pd.DataFrame:
    """Detect combos across all 1v1 replays for a player.

    Args:
        replay_root: Root directory of replays.
        pg: Player-game DataFrame from player_games().
        tag: Player tag to filter on.
        character: Optional character filter.
        gap_frames: Max idle frames between hits.
        as_attacker: If True, find combos this player performed (opponent is
            defender). If False, find combos done TO this player.

    Returns:
        DataFrame of combos with character, filename, gap_frames columns added.
    """
    from melee_tools.habits import _iter_1v1_games

    all_combos = []

    for gi, my_df, opp_df, char_name in _iter_1v1_games(replay_root, pg, tag, character):
        if as_attacker:
            combos = detect_combos(my_df, opp_df, gap_frames=gap_frames)
        else:
            combos = detect_combos(opp_df, my_df, gap_frames=gap_frames)

        if len(combos) > 0:
            combos["character"] = char_name
            combos["filename"] = gi["filename"]
            combos["gap_frames"] = gap_frames
            all_combos.append(combos)

    if not all_combos:
        return pd.DataFrame()

    return pd.concat(all_combos, ignore_index=True)
