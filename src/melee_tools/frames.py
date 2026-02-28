"""Extract per-frame, per-player data from .slp replays into pandas DataFrames."""

from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow as pa
from peppi_py import read_slippi

from melee_tools.enums import character_name, character_name_external, stage_name
from melee_tools.parse import parse_game


def _arrow_to_numpy(arr: pa.Array) -> np.ndarray:
    """Convert a PyArrow array to numpy, handling nulls."""
    if arr.null_count == 0:
        return arr.to_numpy(zero_copy_only=False)
    # For arrays with nulls, convert to pandas (which handles nullable dtypes)
    return arr.to_pandas().values


def _safe_np(arr) -> np.ndarray | None:
    """Convert a peppi_py PyArrow array to numpy, returning None if the array is None.

    Use this instead of _arrow_to_numpy() when reading raw peppi_py game objects
    from the training_data directory, where older Slippi formats leave some fields
    as None (e.g. airborne, l_cancel, last_hit_by).

    Args:
        arr: A PyArrow array or None.

    Returns:
        numpy array, or None if arr is None or conversion fails.
    """
    if arr is None:
        return None
    try:
        if arr.null_count == 0:
            return arr.to_numpy(zero_copy_only=False)
        return arr.to_pandas().values
    except Exception:
        return None


def extract_player_frames(game, player_index: int, port_slot: int) -> pd.DataFrame:
    """Extract all frame data for one player into a DataFrame.

    Args:
        game: A peppi-py game object from read_slippi().
        player_index: Logical player index (0-based, among active players).
        port_slot: The raw port slot (0-3) in game.frames.ports.

    Returns:
        DataFrame with one row per frame, columns for all pre/post fields.
    """
    port_data = game.frames.ports[port_slot]
    if port_data is None or port_data.leader is None:
        return pd.DataFrame()

    post = port_data.leader.post
    pre = port_data.leader.pre
    frame_ids = _arrow_to_numpy(game.frames.id)

    data = {"frame": frame_ids}

    # --- Post-frame fields (after physics) ---
    data["state"] = _arrow_to_numpy(post.state)
    data["character"] = _arrow_to_numpy(post.character)
    data["position_x"] = _arrow_to_numpy(post.position.x)
    data["position_y"] = _arrow_to_numpy(post.position.y)
    data["direction"] = _arrow_to_numpy(post.direction)
    data["percent"] = _arrow_to_numpy(post.percent)
    data["shield"] = _arrow_to_numpy(post.shield)
    data["stocks"] = _arrow_to_numpy(post.stocks)
    data["last_attack_landed"] = _arrow_to_numpy(post.last_attack_landed)
    data["last_hit_by"] = _arrow_to_numpy(post.last_hit_by)
    data["combo_count"] = _arrow_to_numpy(post.combo_count)
    data["state_age"] = _arrow_to_numpy(post.state_age)
    data["airborne"] = _arrow_to_numpy(post.airborne)
    data["ground"] = _arrow_to_numpy(post.ground)
    data["jumps"] = _arrow_to_numpy(post.jumps)
    data["l_cancel"] = _arrow_to_numpy(post.l_cancel)
    data["hitlag"] = _arrow_to_numpy(post.hitlag)
    data["hurtbox_state"] = _arrow_to_numpy(post.hurtbox_state)
    data["animation_index"] = _arrow_to_numpy(post.animation_index)
    data["misc_as"] = _arrow_to_numpy(post.misc_as)

    # Velocities
    if post.velocities is not None:
        for vfield in ["self_x_air", "self_y", "knockback_x", "knockback_y", "self_x_ground"]:
            arr = getattr(post.velocities, vfield, None)
            if arr is not None:
                data[f"velocity_{vfield}"] = _arrow_to_numpy(arr)

    # State flags (5 bitfields)
    if post.state_flags is not None:
        for i, flag_arr in enumerate(post.state_flags):
            if flag_arr is not None:
                data[f"state_flags_{i}"] = _arrow_to_numpy(flag_arr)

    # --- Pre-frame fields (inputs) ---
    data["input_state"] = _arrow_to_numpy(pre.state)
    data["input_buttons"] = _arrow_to_numpy(pre.buttons)
    data["input_buttons_physical"] = _arrow_to_numpy(pre.buttons_physical)
    data["input_joystick_x"] = _arrow_to_numpy(pre.joystick.x)
    data["input_joystick_y"] = _arrow_to_numpy(pre.joystick.y)
    data["input_cstick_x"] = _arrow_to_numpy(pre.cstick.x)
    data["input_cstick_y"] = _arrow_to_numpy(pre.cstick.y)
    data["input_triggers"] = _arrow_to_numpy(pre.triggers)
    data["input_direction"] = _arrow_to_numpy(pre.direction)
    data["input_position_x"] = _arrow_to_numpy(pre.position.x)
    data["input_position_y"] = _arrow_to_numpy(pre.position.y)
    data["input_percent"] = _arrow_to_numpy(pre.percent)

    if pre.triggers_physical is not None:
        data["input_trigger_l"] = _arrow_to_numpy(pre.triggers_physical.l)
        data["input_trigger_r"] = _arrow_to_numpy(pre.triggers_physical.r)

    df = pd.DataFrame(data)
    df["player_index"] = player_index
    df["port"] = port_slot
    return df


def extract_frames(
    filepath: str | Path,
    include_inputs: bool = True,
) -> dict[str, pd.DataFrame | dict]:
    """Extract all frame data from a .slp file.

    Args:
        filepath: Path to .slp file.
        include_inputs: If True, include pre-frame input columns (default True).

    Returns:
        Dict with keys:
            "game_info": dict of game-level metadata (from parse_game)
            "players": dict mapping player_index -> DataFrame of per-frame data
    """
    filepath = Path(filepath)
    game = read_slippi(str(filepath))

    game_info = parse_game(filepath)

    active_players = [(i, p) for i, p in enumerate(game.start.players) if p is not None]

    players = {}
    for idx, (slot, player) in enumerate(active_players):
        df = extract_player_frames(game, idx, slot)

        if not include_inputs:
            input_cols = [c for c in df.columns if c.startswith("input_")]
            df = df.drop(columns=input_cols)

        # Add player context columns
        # Note: start uses internal IDs, frame data uses external IDs
        df["character_id_internal"] = player.character
        df["character_name"] = character_name(player.character)

        players[idx] = df

    return {
        "game_info": game_info,
        "players": players,
    }


def extract_all_players_frames(
    filepath: str | Path,
    include_inputs: bool = True,
) -> pd.DataFrame:
    """Extract frame data for all players stacked into a single DataFrame.

    Useful for queries across players (e.g., "when did any player use fsmash?").

    Returns:
        Single DataFrame with all players' frames stacked, with player_index
        and character_name columns to distinguish them.
    """
    result = extract_frames(filepath, include_inputs=include_inputs)
    if not result["players"]:
        return pd.DataFrame()

    dfs = list(result["players"].values())
    combined = pd.concat(dfs, ignore_index=True)
    combined["filename"] = Path(filepath).name
    return combined
