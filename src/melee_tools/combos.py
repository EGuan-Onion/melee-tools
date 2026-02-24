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
        attacker_df: Attacker's frame DataFrame (used for last_attack_landed).
        defender_df: Defender's frame DataFrame with percent, stocks, and
            frame columns.
        gap_frames: Max idle frames between hits before ending a combo.

    Returns:
        DataFrame with one row per combo: start_frame, end_frame, damage,
        num_hits, started_by, ended_by, killed, start_pct, end_pct.
    """
    pct = defender_df["percent"].values.astype(float)
    stocks = defender_df["stocks"].values.astype(float)
    frames = defender_df["frame"].values.astype(int)

    # last_attack_landed means "last attack THIS player landed on someone",
    # so we must read it from the attacker's frames, not the defender's.
    # Build a frame-aligned lookup from attacker_df.
    atk_frames = attacker_df["frame"].values.astype(int)
    atk_lal = attacker_df["last_attack_landed"].values
    _atk_lal_map = dict(zip(atk_frames, atk_lal))

    def _make_combo(sf, ef, sp, ep, nh, sb, eb, killed, hit_seq):
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
            "hit_moves": [move_name(mid) for _, mid in hit_seq],
            "hit_frames": [f for f, _ in hit_seq],
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
    hit_sequence = []

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
            atk_val = _atk_lal_map.get(int(frames[i]))
            move_id = int(atk_val) if atk_val is not None and not pd.isna(atk_val) else 0
            if not in_combo:
                in_combo = True
                start_frame = int(frames[i])
                start_pct = float(pct[i - 1])
                started_by = move_id
                num_hits = 1
                hit_sequence = [(int(frames[i]), move_id)]
            else:
                num_hits += 1
                hit_sequence.append((int(frames[i]), move_id))
            ended_by = move_id
            last_hit_frame = int(frames[i])
            current_pct = float(pct[i])

        if in_combo and stock_lost:
            # Stock lost while combo is still active — clear kill
            combos.append(_make_combo(
                start_frame, int(frames[i]), start_pct, current_pct,
                num_hits, started_by, ended_by, True, hit_sequence,
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
                num_hits, started_by, ended_by, False, hit_sequence,
            ))
            in_combo = False

    # Close any open combo at end of game
    if in_combo:
        combos.append(_make_combo(
            start_frame, last_hit_frame, start_pct, current_pct,
            num_hits, started_by, ended_by, False, hit_sequence,
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


# ---------------------------------------------------------------------------
# Combo sequence analysis helpers
# ---------------------------------------------------------------------------

def move_followups(combos: pd.DataFrame, move: str) -> pd.Series:
    """Count what moves follow `move` in combo hit sequences.

    Args:
        combos: DataFrame from detect_combos() or analyze_combos().
        move: Move name to look up (e.g. "D-throw", "F-tilt").

    Returns:
        Series of counts, sorted descending.

    Example:
        combos = analyze_combos("replays", pg, "EG＃0", character="Sheik")
        move_followups(combos, "D-throw")
    """
    from collections import Counter
    counts = Counter()
    for moves in combos["hit_moves"]:
        for i, m in enumerate(moves):
            if m == move and i + 1 < len(moves):
                counts[moves[i + 1]] += 1
    return pd.Series(counts).sort_values(ascending=False)


def move_setups(combos: pd.DataFrame, move: str) -> pd.Series:
    """Count what moves precede `move` in combo hit sequences.

    Args:
        combos: DataFrame from detect_combos() or analyze_combos().
        move: Move name to look up (e.g. "U-smash", "Fair").

    Returns:
        Series of counts, sorted descending.
    """
    from collections import Counter
    counts = Counter()
    for moves in combos["hit_moves"]:
        for i, m in enumerate(moves):
            if m == move and i > 0:
                counts[moves[i - 1]] += 1
    return pd.Series(counts).sort_values(ascending=False)


def kill_finishers(combos: pd.DataFrame) -> pd.Series:
    """Count the final move of all kill combos.

    Args:
        combos: DataFrame from detect_combos() or analyze_combos().

    Returns:
        Series of counts, sorted descending.
    """
    from collections import Counter
    kills = combos[combos["killed"] == True]
    counts = Counter(
        moves[-1] for moves in kills["hit_moves"] if moves
    )
    return pd.Series(counts).sort_values(ascending=False)
