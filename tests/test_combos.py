"""Tests for melee_tools.combos."""

import numpy as np
import pandas as pd

from melee_tools.combos import detect_combos


def test_detect_combos_returns_dataframe(p0_df, p1_df):
    """detect_combos returns a DataFrame."""
    combos = detect_combos(p0_df, p1_df, gap_frames=45)
    assert isinstance(combos, pd.DataFrame)


def test_detect_combos_has_expected_columns(p0_df, p1_df):
    """Combo DataFrame has the expected columns."""
    combos = detect_combos(p0_df, p1_df, gap_frames=45)
    if len(combos) == 0:
        return  # skip if no combos detected
    expected = ["start_frame", "end_frame", "num_hits", "damage", "start_pct", "end_pct"]
    for col in expected:
        assert col in combos.columns, f"Missing column: {col}"


def test_detect_combos_damage_nonnegative(p0_df, p1_df):
    """Combo damage should be non-negative."""
    combos = detect_combos(p0_df, p1_df, gap_frames=45)
    for _, combo in combos.iterrows():
        assert combo["damage"] >= 0, f"Negative damage: {combo['damage']}"


def test_detect_combos_damage_matches_pct(p0_df, p1_df):
    """Combo damage should approximately match end_pct - start_pct."""
    combos = detect_combos(p0_df, p1_df, gap_frames=45)
    for _, combo in combos.iterrows():
        expected = combo["end_pct"] - combo["start_pct"]
        # Allow small floating point tolerance
        assert abs(combo["damage"] - expected) < 1.0, (
            f"Damage {combo['damage']} doesn't match pct diff {expected}"
        )


def test_detect_combos_frame_ordering(p0_df, p1_df):
    """start_frame should be <= end_frame for each combo."""
    combos = detect_combos(p0_df, p1_df, gap_frames=45)
    for _, combo in combos.iterrows():
        assert combo["start_frame"] <= combo["end_frame"]


def test_detect_combos_num_hits_positive(p0_df, p1_df):
    """Each combo should have at least 1 hit."""
    combos = detect_combos(p0_df, p1_df, gap_frames=45)
    for _, combo in combos.iterrows():
        assert combo["num_hits"] >= 1
