"""Player-level views built from game-level DataFrames."""

import pandas as pd


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
