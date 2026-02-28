"""Player-level views built from game-level DataFrames."""

from pathlib import Path

import pandas as pd

from melee_tools.stats import game_stats


def player_games(games: pd.DataFrame) -> pd.DataFrame:
    """Unpivot a game-level DataFrame into one row per player-game.

    Columns returned:
        filename, start_time, stage, duration_seconds, is_teams,
        tag, character, placement, won,
        opp_character, opp_tag (1v1 only, NaN for FFA/teams)

    Args:
        games: DataFrame from parse_directory / parse_replays.
    """
    rows = []
    for _, row in games.iterrows():
        n = int(row["num_players"])
        for i in range(n):
            p = f"p{i}"
            tag = row.get(f"{p}_netplay_code") or row.get(f"{p}_netplay_name") or row.get(f"{p}_name_tag")
            # Convert nan-like values to None
            if pd.isna(tag):
                tag = None

            entry = {
                "filename": row["filename"],
                "start_time": row.get("start_time"),
                "stage": row.get("stage_name"),
                "duration_seconds": row.get("duration_seconds"),
                "is_teams": row.get("is_teams"),
                "tag": tag,
                "character": row.get(f"{p}_character"),
                "placement": row.get(f"{p}_placement"),
                "won": row.get(f"{p}_placement") == 0,
            }

            # Opponent info for 1v1s
            if n == 2:
                j = 1 - i
                q = f"p{j}"
                opp_tag = row.get(f"{q}_netplay_code") or row.get(f"{q}_netplay_name") or row.get(f"{q}_name_tag")
                if pd.isna(opp_tag):
                    opp_tag = None
                entry["opp_character"] = row.get(f"{q}_character")
                entry["opp_tag"] = opp_tag

            rows.append(entry)

    df = pd.DataFrame(rows)
    if "start_time" in df.columns:
        df["start_time"] = pd.to_datetime(df["start_time"], errors="coerce")
    return df


def player_stats(
    replay_root: str | Path,
    tag: str,
) -> pd.DataFrame:
    """Return per-game stats for a specific player tag.

    Reads all .slp files in ``replay_root`` (recursively), extracts game-level
    stats, and returns one row per 1v1 game where the player with ``tag`` was
    involved.  Includes performance columns from game_stats() alongside
    opponent info.

    Args:
        replay_root: Root directory of replays (searched recursively).
        tag: Player tag to filter on (e.g. "EG＃0").

    Returns:
        DataFrame with columns:
            filename, stage, duration_minutes, won,
            character, opp_character, opp_tag,
            damage_dealt, damage_received, stocks_lost,
            l_cancel_rate, max_combo,
            stock4_death_pct … stock1_death_pct  (per-stock death percents)
    """
    replay_root = Path(replay_root)
    rows = []

    for slp_file in sorted(replay_root.rglob("*.slp")):
        try:
            info = game_stats(slp_file)
        except Exception:
            continue

        if info.get("end_method") not in ("RESOLVED", "GAME"):
            continue
        if int(info.get("num_players", 0)) != 2:
            continue

        # Find the player index for this tag
        my_idx = None
        for i in range(2):
            t = info.get(f"p{i}_netplay_code") or info.get(f"p{i}_netplay_name") or info.get(f"p{i}_name_tag") or ""
            if t == tag:
                my_idx = i
                break
        if my_idx is None:
            continue

        opp_idx = 1 - my_idx
        p = f"p{my_idx}"
        q = f"p{opp_idx}"

        opp_tag = info.get(f"{q}_netplay_code") or info.get(f"{q}_netplay_name") or info.get(f"{q}_name_tag") or ""

        row = {
            "filename": info["filename"],
            "stage": info.get("stage_name"),
            "duration_minutes": info.get("duration_minutes"),
            "won": info.get(f"{p}_placement") == 0,
            "character": info.get(f"{p}_character"),
            "opp_character": info.get(f"{q}_character"),
            "opp_tag": opp_tag or None,
            "damage_dealt": info.get(f"{p}_damage_dealt"),
            "damage_received": info.get(f"{p}_damage_received"),
            "stocks_lost": info.get(f"{p}_stocks_lost"),
            "l_cancel_rate": info.get(f"{p}_l_cancel_rate"),
            "max_combo": info.get(f"{p}_max_combo"),
        }
        # Per-stock death percents
        for s in range(4, 0, -1):
            key = f"{p}_stock{s}_death_pct"
            row[f"stock{s}_death_pct"] = info.get(key)
            row[f"stock{s}_duration_sec"] = info.get(f"{p}_stock{s}_duration_sec")

        rows.append(row)

    return pd.DataFrame(rows)
