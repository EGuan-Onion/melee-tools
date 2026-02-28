"""Shared setup for analysis scripts.

Provides the parsed replay data and common config constants.

Usage:
    from analysis.common import ROOT, TAG, games, pg
"""

from pathlib import Path

import matplotlib
matplotlib.use("Agg")

from melee_tools import parse_replays, player_games

# ─── Config ──────────────────────────────────────────────────────────────────

ROOT = "replays/Replays Onion-Desktop"
TAG = "EG＃0"
CHARS = ["Sheik", "Captain Falcon"]

# ─── Parse replays (shared across all charts) ────────────────────────────────

print("Parsing replays ...")
games = parse_replays(ROOT)
pg = player_games(games)
print(f"  {len(pg)} player-games ({len(pg[pg.tag == TAG])} for {TAG})\n")
