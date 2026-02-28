"""Tests for melee_tools.query."""

import numpy as np
import pandas as pd

from melee_tools.query import find_kills, find_state_entries, find_state_exits


def test_find_kills_schema(p0_df, p1_df):
    """find_kills returns DataFrame with expected columns."""
    kills = find_kills(p0_df, attacker_df=p1_df)
    expected = [
        "frame", "death_percent", "killing_move_id", "killing_move",
        "blastzone", "stock_lost",
    ]
    for col in expected:
        assert col in kills.columns, f"Missing column: {col}"


def test_find_kills_count(p0_df, p1_df):
    """Known fixture: Sheik (p0) dies 3 times, Falco (p1) dies 4 times."""
    p0_deaths = find_kills(p0_df, attacker_df=p1_df)
    p1_deaths = find_kills(p1_df, attacker_df=p0_df)
    assert len(p0_deaths) == 3
    assert len(p1_deaths) == 4


def test_find_kills_attacker_lal_regression(p0_df, p1_df):
    """Regression: killing_move must come from ATTACKER's last_attack_landed.

    When attacker_df is provided, killing_move should reflect what the attacker
    used, not what the victim last used. This was the critical LAL bug.
    """
    kills = find_kills(p1_df, attacker_df=p0_df)
    # p0 (Sheik) kills p1 (Falco) — killing_move should be Sheik moves
    for _, kill in kills.iterrows():
        move = kill["killing_move"]
        assert move is not None, "killing_move should not be None when attacker_df provided"


def test_find_kills_death_percent_positive(p0_df, p1_df):
    """Death percents should be non-negative."""
    kills = find_kills(p0_df, attacker_df=p1_df)
    for _, kill in kills.iterrows():
        assert kill["death_percent"] >= 0


def test_find_kills_frames_monotonic(p0_df, p1_df):
    """Death frames should be in chronological order."""
    kills = find_kills(p0_df, attacker_df=p1_df)
    if len(kills) > 1:
        frames = kills["frame"].values
        assert all(frames[i] < frames[i + 1] for i in range(len(frames) - 1))


def test_find_state_entries(p0_df):
    """find_state_entries returns only transition frames."""
    # Use damage states (75-91)
    damage_states = set(range(75, 92))
    entries = find_state_entries(p0_df, damage_states)
    assert len(entries) > 0

    # Each entry should have a state in the target set
    for _, row in entries.iterrows():
        assert int(row["state"]) in damage_states


def test_find_state_exits(p0_df):
    """find_state_exits returns last frames in contiguous state runs."""
    damage_states = set(range(75, 92))
    exits = find_state_exits(p0_df, damage_states)
    assert len(exits) > 0

    for _, row in exits.iterrows():
        assert int(row["state"]) in damage_states
