"""Compute game-level and per-stock statistics from frame data."""

from pathlib import Path

import numpy as np
import pandas as pd
from peppi_py import read_slippi

from melee_tools.enums import character_name, stage_name
from melee_tools.frames import _arrow_to_numpy


def compute_player_stats(game, player_index: int) -> dict:
    """Compute per-game stats for one player from frame data.

    Returns dict with keys like:
        damage_dealt, damage_received, stocks_taken, stocks_lost,
        kill_count, death_count, l_cancel_success, l_cancel_total,
        l_cancel_rate, apm, max_combo
    """
    post = game.frames.ports[player_index].leader.post

    percent = _arrow_to_numpy(post.percent)
    stocks = _arrow_to_numpy(post.stocks)
    l_cancel = _arrow_to_numpy(post.l_cancel)
    combo_count = _arrow_to_numpy(post.combo_count)

    # Filter to non-null frames
    valid = ~np.isnan(percent) if percent.dtype.kind == 'f' else np.ones(len(percent), dtype=bool)

    # Stocks lost = starting stocks - ending stocks
    valid_stocks = stocks[~pd.isna(stocks)]
    if len(valid_stocks) > 0:
        stocks_start = int(valid_stocks[0])
        stocks_end = int(valid_stocks[-1])
        stocks_lost = stocks_start - stocks_end
    else:
        stocks_start = stocks_end = stocks_lost = 0

    # Damage received = sum of percent increases (reset on death to 0)
    valid_pct = percent[~np.isnan(percent)] if percent.dtype.kind == 'f' else percent[~pd.isna(percent)]
    damage_received = 0.0
    if len(valid_pct) > 1:
        diffs = np.diff(valid_pct.astype(float))
        # Positive diffs = damage taken. Negative diffs = stock reset (ignore).
        damage_received = float(np.sum(diffs[diffs > 0]))

    # L-cancel stats: 1 = success, 2 = failure, 0 = not applicable
    valid_lc = l_cancel[~pd.isna(l_cancel)].astype(int)
    l_cancel_success = int(np.sum(valid_lc == 1))
    l_cancel_fail = int(np.sum(valid_lc == 2))
    l_cancel_total = l_cancel_success + l_cancel_fail
    l_cancel_rate = round(l_cancel_success / l_cancel_total, 4) if l_cancel_total > 0 else None

    # Max combo count (from the game's built-in combo counter)
    valid_combo = combo_count[~pd.isna(combo_count)].astype(int)
    max_combo = int(np.max(valid_combo)) if len(valid_combo) > 0 else 0

    return {
        "stocks_lost": stocks_lost,
        "damage_received": round(damage_received, 1),
        "l_cancel_success": l_cancel_success,
        "l_cancel_total": l_cancel_total,
        "l_cancel_rate": l_cancel_rate,
        "max_combo": max_combo,
    }


def compute_stock_events(game, player_index: int) -> list[dict]:
    """Extract per-stock data for one player: when each stock was lost, at what %, etc.

    Returns list of dicts, one per stock lost:
        stock_number, death_frame, death_percent, stock_duration_frames
    """
    post = game.frames.ports[player_index].leader.post
    stocks = _arrow_to_numpy(post.stocks)
    percent = _arrow_to_numpy(post.percent)
    frame_ids = _arrow_to_numpy(game.frames.id)

    valid_mask = ~pd.isna(stocks)
    stocks_valid = stocks[valid_mask].astype(int)
    percent_valid = percent[valid_mask].astype(float)
    frames_valid = frame_ids[valid_mask]

    if len(stocks_valid) < 2:
        return []

    # Find frames where stock count decreases
    stock_diffs = np.diff(stocks_valid)
    death_indices = np.where(stock_diffs < 0)[0]

    events = []
    stock_start_idx = 0
    starting_stocks = int(stocks_valid[0])

    for death_idx in death_indices:
        stock_number = starting_stocks - len(events)
        death_percent = float(percent_valid[death_idx])
        death_frame = int(frames_valid[death_idx])
        stock_start_frame = int(frames_valid[stock_start_idx])
        stock_duration = death_frame - stock_start_frame

        events.append({
            "stock_number": stock_number,
            "death_frame": death_frame,
            "death_percent": round(death_percent, 1),
            "stock_duration_frames": stock_duration,
            "stock_duration_seconds": round(stock_duration / 60, 2),
        })

        stock_start_idx = death_idx + 1

    return events


def compute_damage_dealt(game, num_players: int) -> dict[int, float]:
    """Estimate damage dealt by each player.

    Uses the percent increase on OTHER players' frames correlated with
    last_hit_by to attribute damage. Returns {player_index: damage_dealt}.

    Note: last_hit_by uses actual port numbers (0-3), not sequential player
    indices, so we build a port->player_index mapping.
    """
    # Build port number -> player index mapping
    port_to_idx = {}
    for idx, player in enumerate(game.start.players):
        if player is not None:
            port_num = player.port.value if hasattr(player.port, 'value') else player.port
            port_to_idx[port_num] = idx

    damage_dealt = {i: 0.0 for i in range(num_players)}

    for target_idx in range(num_players):
        post = game.frames.ports[target_idx].leader.post
        percent = _arrow_to_numpy(post.percent)
        last_hit_by = _arrow_to_numpy(post.last_hit_by)

        valid_pct = percent.astype(float)

        for i in range(1, len(valid_pct)):
            if np.isnan(valid_pct[i]) or np.isnan(valid_pct[i - 1]):
                continue
            dmg = valid_pct[i] - valid_pct[i - 1]
            if dmg > 0:
                attacker_port = int(last_hit_by[i]) if not pd.isna(last_hit_by[i]) else -1
                attacker_idx = port_to_idx.get(attacker_port, -1)
                if 0 <= attacker_idx < num_players:
                    damage_dealt[attacker_idx] += dmg

    return {k: round(v, 1) for k, v in damage_dealt.items()}


_BUTTON_MASKS = {
    "A": 0x0100,
    "B": 0x0200,
    "X": 0x0400,
    "Y": 0x0800,
    "Z": 0x0010,
    "L_digital": 0x0040,
    "R_digital": 0x0020,
    "dpad_up": 0x0008,
    "dpad_down": 0x0004,
    "dpad_left": 0x0001,
    "dpad_right": 0x0002,
}

_COMPASS_LABELS = [
    "joy_E", "joy_ENE", "joy_NE", "joy_NNE",
    "joy_N", "joy_NNW", "joy_NW", "joy_WNW",
    "joy_W", "joy_WSW", "joy_SW", "joy_SSW",
    "joy_S", "joy_SSE", "joy_SE", "joy_ESE",
]


def compute_button_presses(game, player_index: int) -> dict:
    """Count rising-edge button presses for one player.

    Tracks digital buttons, analog triggers (>0.5 threshold),
    and joystick directions (16 compass bins, deadzone 0.3).
    """
    pre = game.frames.ports[player_index].leader.pre

    buttons = _arrow_to_numpy(pre.buttons_physical).astype(np.int64)
    counts = {}

    # Digital buttons — rising edge detection
    for name, mask in _BUTTON_MASKS.items():
        pressed = (buttons & mask) != 0
        counts[name] = int(np.sum(pressed[1:] & ~pressed[:-1]))

    # Soft triggers — rising edge on analog > 0.5
    if pre.triggers_physical is not None:
        for side, arr in [("soft_L", pre.triggers_physical.l), ("soft_R", pre.triggers_physical.r)]:
            vals = _arrow_to_numpy(arr).astype(float)
            active = vals > 0.5
            counts[side] = int(np.sum(active[1:] & ~active[:-1]))

    # Joystick directions — 16 compass bins, deadzone 0.3
    joy_x = _arrow_to_numpy(pre.joystick.x).astype(float)
    joy_y = _arrow_to_numpy(pre.joystick.y).astype(float)
    magnitude = np.sqrt(joy_x ** 2 + joy_y ** 2)
    outside = magnitude > 0.3

    # Rising edge = transition from inside deadzone to outside
    entering = outside[1:] & ~outside[:-1]
    entering_indices = np.where(entering)[0] + 1  # +1 because diff shifts by 1

    # Initialize all compass counts to 0
    for label in _COMPASS_LABELS:
        counts[label] = 0

    if len(entering_indices) > 0:
        angles = np.degrees(np.arctan2(joy_y[entering_indices], joy_x[entering_indices]))
        # Round to nearest 22.5° and map to bin index (0–15)
        bins = np.round(angles / 22.5).astype(int) % 16
        for b in bins:
            counts[_COMPASS_LABELS[b]] += 1

    return counts


def game_stats(filepath: str | Path) -> dict:
    """Compute comprehensive stats for a single game.

    Returns a dict combining game metadata with per-player stats.
    """
    filepath = Path(filepath)
    game = read_slippi(str(filepath))

    from melee_tools.parse import parse_game
    info = parse_game(filepath)
    info["duration_minutes"] = round(info["duration_frames"] / 3600, 4) if info.get("duration_frames") else None

    num_players = info["num_players"]
    damage_dealt = compute_damage_dealt(game, num_players)

    for idx in range(num_players):
        prefix = f"p{idx}"
        pstats = compute_player_stats(game, idx)
        stock_events = compute_stock_events(game, idx)
        btn = compute_button_presses(game, idx)

        for key, val in btn.items():
            info[f"{prefix}_btn_{key}"] = val

        info[f"{prefix}_damage_dealt"] = damage_dealt[idx]
        info[f"{prefix}_damage_received"] = pstats["damage_received"]
        info[f"{prefix}_stocks_lost"] = pstats["stocks_lost"]
        info[f"{prefix}_l_cancel_success"] = pstats["l_cancel_success"]
        info[f"{prefix}_l_cancel_total"] = pstats["l_cancel_total"]
        info[f"{prefix}_l_cancel_rate"] = pstats["l_cancel_rate"]
        info[f"{prefix}_max_combo"] = pstats["max_combo"]

        # Per-stock death percents
        for i, event in enumerate(stock_events):
            info[f"{prefix}_stock{event['stock_number']}_death_pct"] = event["death_percent"]
            info[f"{prefix}_stock{event['stock_number']}_duration_sec"] = event["stock_duration_seconds"]

    return info


def game_stats_directory(directory: str | Path) -> pd.DataFrame:
    """Compute stats for all .slp files in a directory.

    Returns DataFrame with one row per game, including per-player stats.
    """
    directory = Path(directory)
    rows = []
    errors = []

    for slp_file in sorted(directory.glob("*.slp")):
        try:
            rows.append(game_stats(slp_file))
        except Exception as e:
            errors.append({"filename": slp_file.name, "error": str(e)})

    if errors:
        print(f"Warning: {len(errors)} file(s) failed:")
        for err in errors:
            print(f"  {err['filename']}: {err['error']}")

    if not rows:
        return pd.DataFrame()

    return pd.DataFrame(rows)
