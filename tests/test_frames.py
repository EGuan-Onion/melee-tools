"""Tests for melee_tools.frames."""

import pandas as pd

from melee_tools.frames import extract_frames

from .conftest import TEST_SLP


def test_extract_frames_returns_players(frames_result):
    """extract_frames returns a dict with game_info and players."""
    assert "game_info" in frames_result
    assert "players" in frames_result
    assert len(frames_result["players"]) == 2


def test_player_df_has_expected_columns(p0_df):
    """Player DataFrames have the core post-frame columns."""
    expected = [
        "frame", "state", "position_x", "position_y", "direction",
        "percent", "shield", "stocks", "last_attack_landed", "last_hit_by",
        "combo_count", "airborne", "l_cancel", "character_name",
    ]
    for col in expected:
        assert col in p0_df.columns, f"Missing column: {col}"


def test_player_df_has_input_columns(p0_df):
    """When include_inputs=True, input columns are present."""
    input_cols = [
        "input_buttons_physical", "input_joystick_x", "input_joystick_y",
    ]
    for col in input_cols:
        assert col in p0_df.columns, f"Missing input column: {col}"


def test_player_df_frame_count(p0_df, p1_df):
    """Both players should have the same number of frames."""
    assert len(p0_df) == len(p1_df)
    assert len(p0_df) > 1000  # should be a real game


def test_extract_frames_without_inputs():
    """include_inputs=False drops input_ columns."""
    result = extract_frames(str(TEST_SLP), include_inputs=False)
    df = result["players"][0]
    input_cols = [c for c in df.columns if c.startswith("input_")]
    assert len(input_cols) == 0
    # But post-frame columns still present
    assert "state" in df.columns
    assert "percent" in df.columns
