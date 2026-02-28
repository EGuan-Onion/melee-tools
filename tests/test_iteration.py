"""Tests for melee_tools.iteration."""

import pandas as pd

from melee_tools.iteration import _iter_1v1_games, classify_direction
from melee_tools.parse import parse_replays
from melee_tools.players import player_games

from .conftest import FIXTURE_DIR


def test_classify_direction_toward():
    """Player facing opponent → forward action → toward."""
    assert classify_direction(0.0, 10.0, 1.0, True) == "toward"
    assert classify_direction(10.0, 0.0, -1.0, True) == "toward"


def test_classify_direction_away():
    """Player facing opponent → backward action → away."""
    assert classify_direction(0.0, 10.0, 1.0, False) == "away"
    assert classify_direction(10.0, 0.0, -1.0, False) == "away"


def test_classify_direction_reversed():
    """Player facing away from opponent → forward action → away."""
    assert classify_direction(0.0, 10.0, -1.0, True) == "away"
    assert classify_direction(10.0, 0.0, 1.0, True) == "away"


def test_iter_1v1_games_yields_tuples():
    """_iter_1v1_games yields (game_info, my_df, opp_df, char_name) tuples."""
    games = parse_replays(str(FIXTURE_DIR))
    pg = player_games(games)

    # Find a tag in the fixture
    tag = pg["tag"].iloc[0]

    results = list(_iter_1v1_games(str(FIXTURE_DIR), pg, tag))
    assert len(results) > 0

    gi, my_df, opp_df, char_name = results[0]
    assert isinstance(gi, dict)
    assert isinstance(my_df, pd.DataFrame)
    assert isinstance(opp_df, pd.DataFrame)
    assert isinstance(char_name, str)
    assert "filepath" in gi
    assert "frame" in my_df.columns
    assert "frame" in opp_df.columns


def test_iter_1v1_games_character_filter():
    """Character filter restricts results."""
    games = parse_replays(str(FIXTURE_DIR))
    pg = player_games(games)
    tag = pg["tag"].iloc[0]

    all_results = list(_iter_1v1_games(str(FIXTURE_DIR), pg, tag))
    if not all_results:
        return

    char = all_results[0][3]  # char_name from first result
    filtered = list(_iter_1v1_games(str(FIXTURE_DIR), pg, tag, character=char))
    assert len(filtered) <= len(all_results)
    for _, _, _, cn in filtered:
        assert cn == char
