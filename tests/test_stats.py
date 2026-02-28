"""Tests for melee_tools.stats."""

from melee_tools.stats import (
    compute_button_presses,
    compute_damage_dealt,
    compute_player_stats,
    compute_stock_events,
    game_stats,
)

from .conftest import TEST_SLP


def test_compute_player_stats_schema(p0_df):
    """compute_player_stats returns dict with expected keys."""
    stats = compute_player_stats(p0_df)
    expected = [
        "stocks_lost", "damage_received",
        "l_cancel_success", "l_cancel_total", "l_cancel_rate",
        "max_combo",
    ]
    for key in expected:
        assert key in stats, f"Missing key: {key}"


def test_compute_player_stats_values(p0_df):
    """Spot-check known values from the test fixture (Sheik, 3 deaths)."""
    stats = compute_player_stats(p0_df)
    assert stats["stocks_lost"] == 3
    assert stats["damage_received"] > 0
    assert stats["l_cancel_total"] > 0


def test_l_cancel_rate_in_range(p0_df):
    """L-cancel rate should be between 0 and 1."""
    stats = compute_player_stats(p0_df)
    if stats["l_cancel_rate"] is not None:
        assert 0 <= stats["l_cancel_rate"] <= 1


def test_compute_stock_events(p0_df):
    """compute_stock_events returns events for each death."""
    events = compute_stock_events(p0_df)
    assert len(events) == 3  # Sheik dies 3 times
    for event in events:
        assert event["death_percent"] > 0
        assert event["stock_duration_frames"] > 0


def test_compute_button_presses_nonnegative(p0_df):
    """All button press counts should be non-negative."""
    counts = compute_button_presses(p0_df)
    for key, val in counts.items():
        assert val >= 0, f"Negative count for {key}: {val}"


def test_compute_button_presses_has_buttons(p0_df):
    """Should have A and B button counts."""
    counts = compute_button_presses(p0_df)
    assert "A" in counts
    assert "B" in counts
    assert counts["A"] > 0  # real game, should have A presses


def test_compute_damage_dealt(player_dfs):
    """compute_damage_dealt returns damage for each player."""
    dealt = compute_damage_dealt(player_dfs)
    assert len(dealt) == 2
    # Both players dealt some damage in this game
    for idx, dmg in dealt.items():
        assert dmg >= 0


def test_game_stats_returns_expected_keys():
    """game_stats returns a flat dict with game info and per-player stats."""
    stats = game_stats(str(TEST_SLP))
    assert stats["filename"] == "test_game.slp"
    assert stats["num_players"] == 2
    assert "p0_damage_dealt" in stats
    assert "p1_damage_dealt" in stats
    assert "p0_l_cancel_rate" in stats
    assert "p0_btn_A" in stats
