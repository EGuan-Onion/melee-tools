"""Tests for melee_tools.parse."""

from pathlib import Path

import pytest

from melee_tools.parse import parse_game

from .conftest import TEST_SLP


def test_parse_game_returns_expected_fields(game_info):
    """parse_game returns a dict with required metadata fields."""
    required = [
        "filename", "num_players", "duration_frames",
        "stage_name", "end_method",
        "p0_character", "p1_character",
    ]
    for field in required:
        assert field in game_info, f"Missing field: {field}"


def test_parse_game_values(game_info):
    """Spot-check known values from the test fixture."""
    assert game_info["num_players"] == 2
    assert game_info["end_method"] == "GAME"
    assert game_info["stage_name"] == "Battlefield"
    assert game_info["p0_character"] == "Sheik"
    assert game_info["p1_character"] == "Falco"
    assert game_info["duration_frames"] > 0


def test_parse_game_bad_file():
    """parse_game raises on a non-existent file."""
    with pytest.raises(Exception):
        parse_game("/nonexistent/fake.slp")
