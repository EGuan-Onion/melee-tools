"""Melee replay analysis toolkit."""

from melee_tools.action_states import (
    ACTION_STATE_BY_NAME,
    ACTION_STATE_CATEGORIES,
    ACTION_STATES,
    FRIENDLY_NAMES,
)
from melee_tools.combos import analyze_combos, detect_combos, detect_combos_by_strictness
from melee_tools.enums import (
    CHARACTER_NAMES,
    CHARACTER_NAMES_EXTERNAL,
    STAGE_NAMES,
    character_name,
    character_name_external,
    stage_name,
)
from melee_tools.frames import extract_all_players_frames, extract_frames, extract_player_frames
from melee_tools.habits import analyze_knockdowns, analyze_rolls, classify_direction
from melee_tools.moves import MOVE_NAMES, move_name
from melee_tools.parse import parse_directory, parse_game, parse_game_with_stocks, parse_replays
from melee_tools.players import player_games
from melee_tools.query import (
    find_kills,
    find_kills_for_character,
    find_state_entries,
    find_state_exits,
    next_action_after,
    post_state_actions,
)
from melee_tools.aliases import resolve_character, resolve_move, resolve_move_sequence
from melee_tools.clips import (
    export_dolphin_json,
    find_edgeguards,
    find_kills_by_move,
    find_move_sequences,
    find_tech_chases,
)
from melee_tools.plotting import bucket_percent, compute_option_frequencies, plot_options_by_percent
from melee_tools.stages import STAGE_GEOMETRY
from melee_tools.stats import game_stats, game_stats_directory
