"""Shared pytest fixtures for melee-tools tests."""

from pathlib import Path

import pytest

from melee_tools.frames import extract_frames
from melee_tools.parse import parse_game

FIXTURE_DIR = Path(__file__).parent / "fixtures"
TEST_SLP = FIXTURE_DIR / "test_game.slp"


@pytest.fixture(scope="session")
def game_info():
    """Parsed game metadata from a real .slp file."""
    return parse_game(TEST_SLP)


@pytest.fixture(scope="session")
def frames_result():
    """Full extract_frames() output (with inputs) from a real .slp file."""
    return extract_frames(str(TEST_SLP), include_inputs=True)


@pytest.fixture(scope="session")
def player_dfs(frames_result):
    """Dict of player_index -> DataFrame from extract_frames()."""
    return frames_result["players"]


@pytest.fixture(scope="session")
def p0_df(player_dfs):
    """Player 0 DataFrame (Sheik / EG#0)."""
    return player_dfs[0]


@pytest.fixture(scope="session")
def p1_df(player_dfs):
    """Player 1 DataFrame (Falco / BIRD#254)."""
    return player_dfs[1]
