"""Compute game-level and per-stock statistics from frame data."""

from pathlib import Path

import numpy as np
import pandas as pd

from melee_tools.frames import extract_frames
from melee_tools.parse import parse_game


def compute_player_stats(player_df: pd.DataFrame) -> dict:
    """Compute per-game stats for one player from a frame DataFrame.

    Args:
        player_df: Player frame DataFrame from extract_frames().

    Returns dict with keys:
        stocks_lost, damage_received, l_cancel_success, l_cancel_total,
        l_cancel_rate, max_combo
    """
    percent = player_df["percent"].values.astype(float)
    stocks = player_df["stocks"].values.astype(float)

    # Stocks lost = starting stocks - ending stocks
    valid_stocks = stocks[~np.isnan(stocks)]
    if len(valid_stocks) > 0:
        stocks_lost = int(valid_stocks[0]) - int(valid_stocks[-1])
    else:
        stocks_lost = 0

    # Damage received = sum of percent increases (reset on death to 0)
    valid_pct = percent[~np.isnan(percent)]
    damage_received = 0.0
    if len(valid_pct) > 1:
        diffs = np.diff(valid_pct)
        damage_received = float(np.sum(diffs[diffs > 0]))

    # L-cancel stats: 1 = success, 2 = failure, 0 = not applicable
    lc = player_df["l_cancel"].dropna().values.astype(int)
    l_cancel_success = int(np.sum(lc == 1))
    l_cancel_fail = int(np.sum(lc == 2))
    l_cancel_total = l_cancel_success + l_cancel_fail
    l_cancel_rate = round(l_cancel_success / l_cancel_total, 4) if l_cancel_total > 0 else None

    # Max combo count (from the game's built-in combo counter)
    combo = player_df["combo_count"].dropna().values.astype(int)
    max_combo = int(np.max(combo)) if len(combo) > 0 else 0

    return {
        "stocks_lost": stocks_lost,
        "damage_received": round(damage_received, 1),
        "l_cancel_success": l_cancel_success,
        "l_cancel_total": l_cancel_total,
        "l_cancel_rate": l_cancel_rate,
        "max_combo": max_combo,
    }


def compute_stock_events(player_df: pd.DataFrame) -> list[dict]:
    """Extract per-stock data for one player: when each stock was lost, at what %, etc.

    Args:
        player_df: Player frame DataFrame from extract_frames().

    Returns list of dicts, one per stock lost:
        stock_number, death_frame, death_percent, stock_duration_frames,
        stock_duration_seconds
    """
    stocks = player_df["stocks"].values.astype(float)
    percent = player_df["percent"].values.astype(float)
    frames = player_df["frame"].values.astype(int)

    valid_mask = ~np.isnan(stocks)
    stocks_valid = stocks[valid_mask].astype(int)
    percent_valid = percent[valid_mask]
    frames_valid = frames[valid_mask]

    if len(stocks_valid) < 2:
        return []

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


def compute_damage_dealt(player_dfs: dict[int, pd.DataFrame]) -> dict[int, float]:
    """Estimate damage dealt by each player.

    Uses the percent increase on OTHER players' frames correlated with
    last_hit_by to attribute damage. Returns {player_index: damage_dealt}.

    Args:
        player_dfs: Dict mapping player_index -> player frame DataFrame.

    Note: last_hit_by uses actual port numbers (0-3), not sequential player
    indices, so we build a port->player_index mapping.
    """
    # Build port number -> player index mapping
    port_to_idx = {}
    for idx, df in player_dfs.items():
        port = int(df["port"].iloc[0])
        port_to_idx[port] = idx

    damage_dealt = {idx: 0.0 for idx in player_dfs}

    for target_idx, target_df in player_dfs.items():
        pct = target_df["percent"].values.astype(float)
        last_hit_by = target_df["last_hit_by"].values

        for i in range(1, len(pct)):
            if np.isnan(pct[i]) or np.isnan(pct[i - 1]):
                continue
            dmg = pct[i] - pct[i - 1]
            if dmg > 0:
                attacker_port = int(last_hit_by[i]) if not pd.isna(last_hit_by[i]) else -1
                attacker_idx = port_to_idx.get(attacker_port, -1)
                if attacker_idx in damage_dealt:
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


def compute_button_presses(player_df: pd.DataFrame) -> dict:
    """Count rising-edge button presses for one player.

    Args:
        player_df: Player frame DataFrame from extract_frames(include_inputs=True).
            Requires input_* columns.

    Tracks digital buttons, analog triggers (>0.5 threshold),
    and joystick directions (16 compass bins, deadzone 0.3).
    """
    buttons = player_df["input_buttons_physical"].values.astype(np.int64)
    counts = {}

    # Digital buttons — rising edge detection
    for name, mask in _BUTTON_MASKS.items():
        pressed = (buttons & mask) != 0
        counts[name] = int(np.sum(pressed[1:] & ~pressed[:-1]))

    # Soft triggers — rising edge on analog > 0.5
    if "input_trigger_l" in player_df.columns:
        for side, col in [("soft_L", "input_trigger_l"), ("soft_R", "input_trigger_r")]:
            vals = player_df[col].values.astype(float)
            active = vals > 0.5
            counts[side] = int(np.sum(active[1:] & ~active[:-1]))

    # Joystick directions — 16 compass bins, deadzone 0.3
    joy_x = player_df["input_joystick_x"].values.astype(float)
    joy_y = player_df["input_joystick_y"].values.astype(float)
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

    Parses the replay once via extract_frames() and computes all stats from
    the resulting DataFrames.

    Returns a dict combining game metadata with per-player stats.
    """
    filepath = Path(filepath)

    result = extract_frames(str(filepath), include_inputs=True)
    info = result["game_info"]
    info["duration_minutes"] = round(info["duration_frames"] / 3600, 4) if info.get("duration_frames") else None

    player_dfs = result["players"]
    damage_dealt = compute_damage_dealt(player_dfs)

    for idx, player_df in player_dfs.items():
        prefix = f"p{idx}"
        pstats = compute_player_stats(player_df)
        stock_events = compute_stock_events(player_df)
        btn = compute_button_presses(player_df)

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

    for slp_file in sorted(directory.rglob("*.slp")):
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
