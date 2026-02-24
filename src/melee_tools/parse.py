"""Parse .slp replay files into structured data."""

from pathlib import Path

import pandas as pd
from peppi_py import read_slippi

from melee_tools.enums import character_name, stage_name


def parse_game(filepath: str | Path) -> dict:
    """Parse a single .slp file and return game-level metadata as a dict.

    Returns a flat dict with keys like:
        filename, start_time, stage_id, stage_name, is_teams, num_players,
        duration_frames, duration_seconds, end_method, platform,
        p0_character_id, p0_character, p0_port, p0_type, p0_team_color,
        p0_costume, p0_stocks_start, p0_placement, p0_netplay_code,
        p0_netplay_name, p0_name_tag, ... (same for p1, p2, p3)
    """
    filepath = Path(filepath)
    game = read_slippi(str(filepath))

    start = game.start
    end = game.end
    meta = game.metadata

    # Game-level info
    last_frame = meta.get("lastFrame", 0)
    row = {
        "filename": filepath.name,
        "start_time": meta.get("startAt"),
        "platform": meta.get("playedOn"),
        "slippi_version": ".".join(str(v) for v in start.slippi.version),
        "stage_id": start.stage,
        "stage_name": stage_name(start.stage),
        "is_teams": start.is_teams,
        "duration_frames": last_frame,
        "duration_seconds": round(last_frame / 60, 2) if last_frame else None,
        "end_method": end.method.name if end else None,
        "lras_initiator": end.lras_initiator.value if end and end.lras_initiator is not None else None,
    }

    # Build placement lookup from end data
    placements = {}
    if end and end.players:
        for pe in end.players:
            placements[pe.port.value] = pe.placement

    # Player info
    active_players = [(i, p) for i, p in enumerate(start.players) if p is not None]
    row["num_players"] = len(active_players)

    for idx, (slot, player) in enumerate(active_players):
        prefix = f"p{idx}"
        row[f"{prefix}_port"] = player.port.value if hasattr(player.port, 'value') else player.port
        row[f"{prefix}_character_id"] = player.character
        row[f"{prefix}_character"] = character_name(player.character)
        row[f"{prefix}_type"] = player.type.name if hasattr(player.type, 'name') else player.type
        row[f"{prefix}_stocks_start"] = player.stocks
        row[f"{prefix}_costume"] = player.costume
        row[f"{prefix}_team_color"] = player.team.color if player.team else None
        row[f"{prefix}_placement"] = placements.get(
            player.port.value if hasattr(player.port, 'value') else player.port
        )
        row[f"{prefix}_netplay_code"] = player.netplay.code if player.netplay and player.netplay.code else None
        row[f"{prefix}_netplay_name"] = player.netplay.name if player.netplay and player.netplay.name else None
        row[f"{prefix}_name_tag"] = player.name_tag if player.name_tag else None

    return row


def parse_game_with_stocks(filepath: str | Path) -> dict:
    """Parse a game and add end-of-game stock and percent info from frame data.

    Extends parse_game() output with:
        p0_stocks_end, p0_percent_end, ... for each player
    """
    filepath = Path(filepath)
    game = read_slippi(str(filepath))
    row = parse_game(filepath)

    # Get final stocks/percent from frame data
    active_players = [(i, p) for i, p in enumerate(game.start.players) if p is not None]
    for idx, (slot, _player) in enumerate(active_players):
        prefix = f"p{idx}"
        port_data = game.frames.ports[slot]
        post = port_data.leader.post

        # Walk backwards to find last non-null stocks value
        stocks_list = post.stocks.to_pylist()
        percent_list = post.percent.to_pylist()

        stocks_end = None
        percent_end = None
        for i in range(len(stocks_list) - 1, -1, -1):
            if stocks_list[i] is not None:
                stocks_end = stocks_list[i]
                percent_end = round(percent_list[i], 1) if percent_list[i] is not None else None
                break

        row[f"{prefix}_stocks_end"] = stocks_end
        row[f"{prefix}_percent_end"] = percent_end

    return row


def parse_directory(
    directory: str | Path,
    with_stocks: bool = True,
) -> pd.DataFrame:
    """Parse all .slp files in a directory into a DataFrame.

    Args:
        directory: Path to directory containing .slp files.
        with_stocks: If True, include end-of-game stock/percent data (slightly slower).

    Returns:
        DataFrame with one row per game.
    """
    directory = Path(directory)
    parse_fn = parse_game_with_stocks if with_stocks else parse_game

    rows = []
    errors = []
    for slp_file in sorted(directory.glob("*.slp")):
        try:
            rows.append(parse_fn(slp_file))
        except Exception as e:
            errors.append({"filename": slp_file.name, "error": str(e)})

    if errors:
        print(f"Warning: {len(errors)} file(s) failed to parse:")
        for err in errors:
            print(f"  {err['filename']}: {err['error']}")

    if not rows:
        return pd.DataFrame()

    return pd.DataFrame(rows)


def parse_replays(
    root: str | Path,
    with_stocks: bool = False,
    real_games_only: bool = True,
) -> pd.DataFrame:
    """Recursively parse all .slp files under a root directory.

    Args:
        root: Root directory to search (walks subdirectories).
        with_stocks: If True, include end-of-game stock/percent data.
        real_games_only: If True, filter to RESOLVED/GAME end methods.

    Returns:
        DataFrame with one row per game.
    """
    root = Path(root)
    parse_fn = parse_game_with_stocks if with_stocks else parse_game

    rows = []
    errors = []
    for slp_file in sorted(root.rglob("*.slp")):
        try:
            rows.append(parse_fn(slp_file))
        except Exception as e:
            errors.append({"filename": slp_file.name, "error": str(e)})

    if errors:
        print(f"Warning: {len(errors)} file(s) failed to parse:")
        for err in errors:
            print(f"  {err['filename']}: {err['error']}")

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)
    if real_games_only:
        df = df[df["end_method"].isin(["RESOLVED", "GAME"])].reset_index(drop=True)
    return df
