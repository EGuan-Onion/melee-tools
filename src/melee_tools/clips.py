"""Pattern finders and Dolphin COMM_SPEC JSON exporter for replay clips.

Each pattern finder returns a DataFrame with a standardized schema:
    filepath, filename, start_frame, end_frame, character, opp_character,
    pattern_type, description, metadata

Export clips to Dolphin-compatible JSON for back-to-back playback:
    clips = find_move_sequences(...)
    export_dolphin_json(clips, "output.json")
    # Then: dolphin -i output.json

Typical usage:
    from melee_tools import parse_replays, player_games
    from melee_tools.clips import find_move_sequences, export_dolphin_json

    games = parse_replays("replays")
    pg = player_games(games)
    clips = find_move_sequences("replays", pg, "EG＃0", moves=["dair", "fair"], character="Falcon")
    export_dolphin_json(clips, "stomp_knee.json")
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd

from melee_tools.aliases import resolve_character, resolve_move, resolve_move_sequence
from melee_tools.combos import detect_combos
from melee_tools.habits import _iter_1v1_games
from melee_tools.moves import MOVE_NAMES, move_name
from melee_tools.query import find_kills
from melee_tools.stages import STAGE_GEOMETRY


# ---------------------------------------------------------------------------
# Clip DataFrame helpers
# ---------------------------------------------------------------------------

def _clip_row(
    filepath: str,
    start_frame: int,
    end_frame: int,
    character: str,
    opp_character: str,
    pattern_type: str,
    description: str,
    metadata: dict | None = None,
) -> dict:
    """Build a single clip row dict matching the standard schema."""
    return {
        "filepath": filepath,
        "filename": Path(filepath).name,
        "start_frame": start_frame,
        "end_frame": end_frame,
        "character": character,
        "opp_character": opp_character,
        "pattern_type": pattern_type,
        "description": description,
        "metadata": metadata or {},
    }


def _is_subsequence(needle: list, haystack: list) -> bool:
    """Check if needle appears as a contiguous subsequence in haystack.

    >>> _is_subsequence(["Dair", "Fair"], ["Nair", "Dair", "Fair", "Uair"])
    True
    >>> _is_subsequence(["Dair", "Fair"], ["Dair", "Uair", "Fair"])
    False
    """
    n = len(needle)
    for i in range(len(haystack) - n + 1):
        if haystack[i:i + n] == needle:
            return True
    return False


# ---------------------------------------------------------------------------
# Dolphin COMM_SPEC JSON export
# ---------------------------------------------------------------------------

def export_dolphin_json(
    clips: pd.DataFrame,
    output_path: str | Path,
    pad_before: int = 120,
    pad_after: int = 60,
) -> Path:
    """Export clips to Dolphin COMM_SPEC JSON for back-to-back replay playback.

    Args:
        clips: DataFrame with at least filepath, start_frame, end_frame columns.
        output_path: Path to write the JSON file.
        pad_before: Context frames to add before the clip (default 120 = 2 sec).
        pad_after: Context frames to add after the clip (default 60 = 1 sec).

    Returns:
        Path to the written JSON file.
    """
    queue = []
    for _, row in clips.iterrows():
        start = max(-123, int(row["start_frame"]) - pad_before)
        end = int(row["end_frame"]) + pad_after
        queue.append({
            "path": str(row["filepath"]),
            "startFrame": start,
            "endFrame": end,
        })

    output_path = Path(output_path)
    output_path.write_text(json.dumps({
        "mode": "queue",
        "queue": queue,
    }, indent=2))

    return output_path


# ---------------------------------------------------------------------------
# Pattern finder: move sequences in combos
# ---------------------------------------------------------------------------

def find_move_sequences(
    replay_root: str | Path,
    pg: pd.DataFrame,
    tag: str,
    moves: list[str],
    character: str | None = None,
    gap_frames: int = 45,
    as_attacker: bool = True,
    killed: bool | None = None,
    min_damage: float | None = None,
) -> pd.DataFrame:
    """Find combos containing a specific move subsequence.

    Args:
        replay_root: Root directory of replays.
        pg: Player-game DataFrame from player_games().
        tag: Player tag (e.g. "EG＃0").
        moves: Move names/aliases (e.g. ["dair", "fair"]) or a named combo
            (e.g. ["ken combo"]).
        character: Player character filter (supports aliases like "falcon").
        gap_frames: Max idle frames between hits for combo detection.
        as_attacker: If True, find combos this player performed.
        killed: None=any, True=only kills, False=only non-kills.
        min_damage: Minimum combo damage filter.

    Returns:
        Clip DataFrame with standardized schema.
    """
    # Resolve character alias
    char_filter = None
    if character:
        try:
            chars = resolve_character(character)
            char_filter = chars[0] if len(chars) == 1 else None
        except ValueError:
            char_filter = character

    # Resolve move sequence (may expand named combos)
    move_ids, inferred_char = resolve_move_sequence(moves, character=char_filter)
    if char_filter is None and inferred_char:
        char_filter = inferred_char

    # Build target move name list for subsequence matching
    target_names = [move_name(mid) for mid in move_ids]

    rows = []
    for gi, my_df, opp_df, char_name in _iter_1v1_games(replay_root, pg, tag, char_filter):
        opp_char = opp_df["character_name"].iloc[0]

        if as_attacker:
            combos = detect_combos(my_df, opp_df, gap_frames=gap_frames)
        else:
            combos = detect_combos(opp_df, my_df, gap_frames=gap_frames)

        if len(combos) == 0:
            continue

        for _, combo in combos.iterrows():
            hit_moves = combo["hit_moves"]

            if not _is_subsequence(target_names, hit_moves):
                continue

            if killed is not None and combo["killed"] != killed:
                continue

            if min_damage is not None and combo["damage"] < min_damage:
                continue

            desc_parts = [" -> ".join(hit_moves)]
            if combo["killed"]:
                desc_parts.append(f"killed, {combo['end_pct']}%")
            else:
                desc_parts.append(f"{combo['damage']}% damage")

            rows.append(_clip_row(
                filepath=gi["filepath"],
                start_frame=int(combo["start_frame"]),
                end_frame=int(combo["end_frame"]),
                character=char_name,
                opp_character=opp_char,
                pattern_type="move_sequence",
                description=f"{desc_parts[0]} ({desc_parts[1]})",
                metadata={
                    "hit_moves": hit_moves,
                    "hit_frames": combo["hit_frames"],
                    "damage": combo["damage"],
                    "num_hits": combo["num_hits"],
                    "killed": combo["killed"],
                    "start_pct": combo["start_pct"],
                    "end_pct": combo["end_pct"],
                },
            ))

    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Pattern finder: kills by specific move
# ---------------------------------------------------------------------------

def find_kills_by_move(
    replay_root: str | Path,
    pg: pd.DataFrame,
    tag: str,
    move: str,
    character: str | None = None,
    as_attacker: bool = True,
) -> pd.DataFrame:
    """Find kills by a specific move across replays.

    Wraps query.find_kills() with move alias resolution.

    Args:
        replay_root: Root directory of replays.
        pg: Player-game DataFrame from player_games().
        tag: Player tag.
        move: Move name or alias (e.g. "knee", "fair", "rest").
        character: Player character filter (supports aliases).
        as_attacker: If True, find kills BY this player with the move.

    Returns:
        Clip DataFrame with standardized schema.
    """
    char_filter = None
    if character:
        try:
            chars = resolve_character(character)
            char_filter = chars[0] if len(chars) == 1 else None
        except ValueError:
            char_filter = character

    move_id = resolve_move(move, character=char_filter)
    if move_id is None:
        raise ValueError(f"Could not resolve move: {move!r}")

    target_move_name = move_name(move_id)

    rows = []
    for gi, my_df, opp_df, char_name in _iter_1v1_games(replay_root, pg, tag, char_filter):
        opp_char = opp_df["character_name"].iloc[0]

        if as_attacker:
            # Kills on the opponent = deaths of the opponent
            kills_df = find_kills(opp_df, attacker_df=my_df)
        else:
            kills_df = find_kills(my_df, attacker_df=opp_df)

        if len(kills_df) == 0:
            continue

        for _, kill in kills_df.iterrows():
            if kill.get("killing_move_id") != move_id:
                continue

            rows.append(_clip_row(
                filepath=gi["filepath"],
                start_frame=int(kill["frame"]),
                end_frame=int(kill["frame"]),
                character=char_name,
                opp_character=opp_char,
                pattern_type="kill",
                description=f"Kill with {target_move_name} at {kill['death_percent']}%",
                metadata={
                    "killing_move": target_move_name,
                    "killing_move_id": move_id,
                    "death_percent": kill["death_percent"],
                    "blastzone": kill.get("blastzone"),
                    "stock_lost": kill.get("stock_lost"),
                },
            ))

    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Pattern finder: edgeguards
# ---------------------------------------------------------------------------

def find_edgeguards(
    replay_root: str | Path,
    pg: pd.DataFrame,
    tag: str,
    character: str | None = None,
    killed: bool | None = None,
) -> pd.DataFrame:
    """Find edgeguard sequences where the player hits an offstage opponent.

    Args:
        replay_root: Root directory of replays.
        pg: Player-game DataFrame from player_games().
        tag: Player tag.
        character: Player character filter (supports aliases).
        killed: None=any, True=only edgeguards that killed, False=only survived.

    Returns:
        Clip DataFrame with standardized schema.
    """
    char_filter = None
    if character:
        try:
            chars = resolve_character(character)
            char_filter = chars[0] if len(chars) == 1 else None
        except ValueError:
            char_filter = character

    rows = []
    for gi, my_df, opp_df, char_name in _iter_1v1_games(replay_root, pg, tag, char_filter):
        stage_id = gi.get("stage_id")
        stage = STAGE_GEOMETRY.get(stage_id)
        if stage is None:
            continue

        edge_x = stage["edge_x"]
        opp_char = opp_df["character_name"].iloc[0]

        opp_x = opp_df["position_x"].values.astype(float)
        opp_y = opp_df["position_y"].values.astype(float)
        opp_pct = opp_df["percent"].values.astype(float)
        opp_stocks = opp_df["stocks"].values.astype(float)
        opp_frames = opp_df["frame"].values.astype(int)

        offstage = (np.abs(opp_x) > edge_x) | (opp_y < -10)

        # Walk through offstage regions, detect hits (percent increases)
        _GAP = 60  # frames gap to merge nearby offstage hits into one sequence
        edgeguards = []
        current_eg = None

        for i in range(1, len(opp_pct)):
            if np.isnan(opp_pct[i]) or np.isnan(opp_pct[i - 1]):
                continue

            is_offstage = bool(offstage[i])
            dmg = opp_pct[i] - opp_pct[i - 1]
            hit_offstage = is_offstage and dmg > 0

            stock_lost = (
                not np.isnan(opp_stocks[i]) and not np.isnan(opp_stocks[i - 1])
                and opp_stocks[i] < opp_stocks[i - 1]
            )

            if hit_offstage:
                if current_eg is None:
                    current_eg = {
                        "start_frame": int(opp_frames[i]),
                        "end_frame": int(opp_frames[i]),
                        "hits": 1,
                        "damage": round(dmg, 1),
                        "killed": False,
                    }
                elif (int(opp_frames[i]) - current_eg["end_frame"]) <= _GAP:
                    current_eg["end_frame"] = int(opp_frames[i])
                    current_eg["hits"] += 1
                    current_eg["damage"] = round(current_eg["damage"] + dmg, 1)
                else:
                    edgeguards.append(current_eg)
                    current_eg = {
                        "start_frame": int(opp_frames[i]),
                        "end_frame": int(opp_frames[i]),
                        "hits": 1,
                        "damage": round(dmg, 1),
                        "killed": False,
                    }

            if stock_lost and current_eg is not None:
                if (int(opp_frames[i]) - current_eg["end_frame"]) <= 150:
                    current_eg["end_frame"] = int(opp_frames[i])
                    current_eg["killed"] = True
                    edgeguards.append(current_eg)
                    current_eg = None
                else:
                    edgeguards.append(current_eg)
                    current_eg = None

        if current_eg is not None:
            edgeguards.append(current_eg)

        for eg in edgeguards:
            if killed is not None and eg["killed"] != killed:
                continue

            desc = f"Edgeguard: {eg['hits']} hit(s), {eg['damage']}%"
            if eg["killed"]:
                desc += " (killed)"

            rows.append(_clip_row(
                filepath=gi["filepath"],
                start_frame=eg["start_frame"],
                end_frame=eg["end_frame"],
                character=char_name,
                opp_character=opp_char,
                pattern_type="edgeguard",
                description=desc,
                metadata={
                    "hits": eg["hits"],
                    "damage": eg["damage"],
                    "killed": eg["killed"],
                },
            ))

    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Pattern finder: tech chases
# ---------------------------------------------------------------------------

# Knockdown and tech states (from habits.py)
_MISSED_BOUND = {183, 191}
_MISSED_WAIT = {184, 192}
_TECH_IN_PLACE = 199
_TECH_ROLL_F = 200
_TECH_ROLL_B = 201
_GETUP = {186, 194}
_GETUP_ATTACK = {187, 195}
_DOWN_ROLL_F = {188, 196}
_DOWN_ROLL_B = {189, 197}


def find_tech_chases(
    replay_root: str | Path,
    pg: pd.DataFrame,
    tag: str,
    character: str | None = None,
    followup_window: int = 90,
    tech_option: str | None = None,
) -> pd.DataFrame:
    """Find tech chase situations where the player follows up on a knockdown.

    Args:
        replay_root: Root directory of replays.
        pg: Player-game DataFrame from player_games().
        tag: Player tag.
        character: Player character filter (supports aliases).
        followup_window: Frames after tech option to check for a follow-up hit.
        tech_option: Filter by specific option: "tech in place", "tech away",
            "tech toward", "missed tech", "getup", "getup attack", "roll toward",
            "roll away". None=any.

    Returns:
        Clip DataFrame with standardized schema.
    """
    from melee_tools.habits import classify_direction

    char_filter = None
    if character:
        try:
            chars = resolve_character(character)
            char_filter = chars[0] if len(chars) == 1 else None
        except ValueError:
            char_filter = character

    rows = []
    for gi, my_df, opp_df, char_name in _iter_1v1_games(replay_root, pg, tag, char_filter):
        opp_char = opp_df["character_name"].iloc[0]
        opp_states = opp_df["state"].values
        opp_frames = opp_df["frame"].values.astype(int)
        opp_pct = opp_df["percent"].values.astype(float)
        opp_x = opp_df["position_x"].values.astype(float)
        opp_dir = opp_df["direction"].values.astype(float)

        my_x_vals = my_df["position_x"].values.astype(float)
        my_frames_arr = my_df["frame"].values.astype(int)

        def _get_my_x(frame):
            idx = np.searchsorted(my_frames_arr, frame)
            if idx < len(my_frames_arr) and my_frames_arr[idx] == frame:
                return float(my_x_vals[idx])
            return None

        # Find knockdown entries (missed tech bounces)
        for i in range(1, len(opp_states)):
            s = int(opp_states[i]) if not pd.isna(opp_states[i]) else 0
            prev_s = int(opp_states[i - 1]) if not pd.isna(opp_states[i - 1]) else 0

            if s not in _MISSED_BOUND or prev_s in _MISSED_BOUND:
                continue

            knockdown_frame = int(opp_frames[i])
            knockdown_pct = float(opp_pct[i]) if not np.isnan(opp_pct[i]) else 0.0

            # Classify opponent's tech option
            option_name = None
            option_frame = None

            for j in range(i + 1, min(i + 300, len(opp_states))):
                sj = int(opp_states[j]) if not pd.isna(opp_states[j]) else 0

                if sj in _MISSED_BOUND or sj in _MISSED_WAIT:
                    continue

                if sj == _TECH_IN_PLACE:
                    option_name = "tech in place"
                    option_frame = int(opp_frames[j])
                elif sj in {_TECH_ROLL_F, _TECH_ROLL_B}:
                    my_x = _get_my_x(int(opp_frames[j]))
                    if my_x is not None:
                        d = classify_direction(
                            float(opp_x[j]), my_x, float(opp_dir[j]),
                            sj == _TECH_ROLL_F,
                        )
                        option_name = f"tech {d}"
                    else:
                        option_name = "tech roll"
                    option_frame = int(opp_frames[j])
                elif sj in _GETUP:
                    option_name = "getup"
                    option_frame = int(opp_frames[j])
                elif sj in _GETUP_ATTACK:
                    option_name = "getup attack"
                    option_frame = int(opp_frames[j])
                elif sj in _DOWN_ROLL_F or sj in _DOWN_ROLL_B:
                    my_x = _get_my_x(int(opp_frames[j]))
                    if my_x is not None:
                        d = classify_direction(
                            float(opp_x[j]), my_x, float(opp_dir[j]),
                            sj in _DOWN_ROLL_F,
                        )
                        option_name = f"roll {d}"
                    else:
                        option_name = "missed tech roll"
                    option_frame = int(opp_frames[j])
                else:
                    # Missed tech — stayed on ground then transitioned to something else
                    option_name = "missed tech"
                    option_frame = int(opp_frames[j])
                break

            if option_name is None:
                continue

            if tech_option is not None and option_name != tech_option:
                continue

            # Check for follow-up hit within window
            followup_hit = False
            followup_move = None
            search_start = option_frame if option_frame else knockdown_frame

            for j in range(i, min(i + 300 + followup_window, len(opp_pct))):
                if int(opp_frames[j]) < search_start:
                    continue
                if int(opp_frames[j]) > search_start + followup_window:
                    break
                if j > 0 and not np.isnan(opp_pct[j]) and not np.isnan(opp_pct[j - 1]):
                    if opp_pct[j] > opp_pct[j - 1]:
                        followup_hit = True
                        last_atk = opp_df["last_attack_landed"].values[j]
                        if not pd.isna(last_atk):
                            followup_move = move_name(int(last_atk))
                        break

            desc = f"Tech chase: {option_name}"
            if followup_hit:
                desc += f" -> {followup_move or 'hit'}"
            else:
                desc += " (no followup)"

            rows.append(_clip_row(
                filepath=gi["filepath"],
                start_frame=knockdown_frame,
                end_frame=search_start + followup_window,
                character=char_name,
                opp_character=opp_char,
                pattern_type="tech_chase",
                description=desc,
                metadata={
                    "tech_option": option_name,
                    "knockdown_pct": knockdown_pct,
                    "followup_hit": followup_hit,
                    "followup_move": followup_move,
                },
            ))

    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Pattern finder: confirmed events (trigger → outcome)
# ---------------------------------------------------------------------------

def find_confirmed_events(
    replay_root: str | Path,
    pg: pd.DataFrame,
    tag: str,
    trigger: str | set,
    outcome: str | None = "kill",
    window_frames: int = 300,
    character: str | None = None,
    min_opp_pct: float | None = None,
    as_attacker: bool = True,
) -> pd.DataFrame:
    """Find instances where a trigger event is (or isn't) followed by an outcome.

    Trigger types (resolved automatically from the trigger argument):
    - **Move trigger** (str alias like "stomp", "knee"):
      fires when a hit is attributed to that move (reactor percent increases
      and attacker's last_attack_landed == move_id). Correctly handles
      back-to-back hits with the same move (e.g. stomp → stomp).
    - **State trigger** (str matching an ACTION_STATE_CATEGORIES key, or a
      set[int] of raw action state IDs): fires on state *entry*. Useful for
      throw states (grab, dthrow, uthrow) where the action begins before the
      hit lands.

    Outcome types:
    - ``"kill"``  — reactor loses a stock within window_frames.
    - Move alias string — that move lands within window_frames.
    - ``None`` — no outcome filter; every trigger is returned as converted=True.

    All returned rows use the standard clip schema, so results can be passed
    directly to export_dolphin_json() for watchback.

    Args:
        replay_root: Root directory of replays.
        pg: Player-game DataFrame from player_games().
        tag: Player tag.
        trigger: Move alias, ACTION_STATE_CATEGORIES key, or set[int].
        outcome: "kill", move alias string, or None.
        window_frames: Max frames after trigger to look for outcome (default 300 = 5 sec).
        character: Optional character filter (supports aliases).
        min_opp_pct: Only include triggers where reactor's percent >= this value.
        as_attacker: If True, this player performs the trigger. If False,
            the opponent performs the trigger and this player is the reactor.

    Returns:
        Clip DataFrame with standardized schema. Each row also has a top-level
        ``converted`` column (bool) for easy filtering.
        metadata includes: trigger_type, trigger_label, trigger_frame,
        outcome_type, outcome_frame, converted, opp_pct_at_trigger.

    Examples:
        # D-throw kill confirm rate (Sheik, opponent at kill %)
        clips = find_confirmed_events(
            root, pg, TAG, trigger="throw_down", outcome="kill",
            character="sheik", min_opp_pct=80,
        )
        print(clips["converted"].mean())

        # Stomp → stomp (Falcon Dair → Dair within 1.5 sec)
        clips = find_confirmed_events(
            root, pg, TAG, trigger="stomp", outcome="stomp",
            window_frames=90, character="falcon",
        )

        # All knees that connected, exported for Dolphin watchback
        clips = find_confirmed_events(
            root, pg, TAG, trigger="knee", outcome=None, character="falcon",
        )
        export_dolphin_json(clips, "all_knees.json")

        # Moves that kill me (opponent as attacker)
        clips = find_confirmed_events(
            root, pg, TAG, trigger="fair", outcome="kill", as_attacker=False,
        )
    """
    from melee_tools.action_states import ACTION_STATE_CATEGORIES
    from melee_tools.aliases import resolve_character, resolve_move
    from melee_tools.moves import move_name as _move_name

    # --- Resolve character ---
    char_filter = None
    if character:
        try:
            chars = resolve_character(character)
            char_filter = chars[0] if len(chars) == 1 else None
        except ValueError:
            char_filter = character

    # --- Resolve trigger ---
    trigger_move_id = None
    trigger_states = None
    trigger_type = None

    if isinstance(trigger, set):
        trigger_states = trigger
        trigger_type = "state"
        trigger_label = f"state({len(trigger)} ids)"
    else:
        resolved = resolve_move(trigger, character=char_filter)
        if resolved is not None:
            trigger_move_id = resolved
            trigger_type = "move"
            trigger_label = _move_name(trigger_move_id)
        else:
            cat_states = ACTION_STATE_CATEGORIES.get(trigger)
            if cat_states:
                trigger_states = cat_states
                trigger_type = "state"
                trigger_label = trigger
            else:
                raise ValueError(
                    f"Cannot resolve trigger {trigger!r}: not a known move alias "
                    f"or ACTION_STATE_CATEGORIES key. "
                    f"Available state categories: {sorted(ACTION_STATE_CATEGORIES.keys())}"
                )

    # --- Resolve outcome ---
    outcome_move_id = None
    if outcome is not None and outcome != "kill":
        outcome_move_id = resolve_move(outcome, character=char_filter)
        if outcome_move_id is None:
            raise ValueError(f"Cannot resolve outcome move: {outcome!r}")
        outcome_label = _move_name(outcome_move_id)
    elif outcome == "kill":
        outcome_label = "kill"
    else:
        outcome_label = "any"

    rows = []
    for gi, my_df, opp_df, char_name in _iter_1v1_games(replay_root, pg, tag, char_filter):
        opp_char = opp_df["character_name"].iloc[0]
        filepath = gi["filepath"]

        actor_df   = my_df  if as_attacker else opp_df
        reactor_df = opp_df if as_attacker else my_df

        actor_frames_arr  = actor_df["frame"].values.astype(int)
        actor_lal_arr     = actor_df["last_attack_landed"].values
        actor_states_arr  = actor_df["state"].values
        actor_lal_map     = dict(zip(actor_frames_arr, actor_lal_arr))

        reactor_pct_arr    = reactor_df["percent"].values.astype(float)
        reactor_stocks_arr = reactor_df["stocks"].values.astype(float)
        reactor_frames_arr = reactor_df["frame"].values.astype(int)

        # --- Find trigger events: list of (index, trigger_frame) ---
        trigger_events = []

        if trigger_type == "move":
            # Hit-based: reactor percent increases attributed to trigger_move_id
            for j in range(1, len(reactor_pct_arr)):
                if (not np.isnan(reactor_pct_arr[j])
                        and not np.isnan(reactor_pct_arr[j - 1])
                        and reactor_pct_arr[j] > reactor_pct_arr[j - 1]
                        and not np.isnan(reactor_stocks_arr[j])
                        and reactor_stocks_arr[j] == reactor_stocks_arr[j - 1]):
                    frame = int(reactor_frames_arr[j])
                    lal_val = actor_lal_map.get(frame)
                    mid = int(lal_val) if lal_val is not None and not pd.isna(lal_val) else 0
                    if mid == trigger_move_id:
                        trigger_events.append((j, frame))

        elif trigger_type == "state":
            # State entry-based: actor enters one of trigger_states
            for i in range(1, len(actor_states_arr)):
                s    = int(actor_states_arr[i])     if not pd.isna(actor_states_arr[i])     else 0
                prev = int(actor_states_arr[i - 1]) if not pd.isna(actor_states_arr[i - 1]) else 0
                if s in trigger_states and prev not in trigger_states:
                    trigger_events.append((i, int(actor_frames_arr[i])))

        # --- For each trigger, check outcome ---
        for _, trigger_frame in trigger_events:
            r_idx = int(np.searchsorted(reactor_frames_arr, trigger_frame))
            if r_idx >= len(reactor_frames_arr):
                continue

            # For move triggers the reactor pct has already increased; use r_idx-1 for pre-hit pct
            pct_ref = max(0, r_idx - 1) if trigger_type == "move" else r_idx
            opp_pct_at = float(reactor_pct_arr[pct_ref]) if not np.isnan(reactor_pct_arr[pct_ref]) else 0.0
            opp_stock_at = float(reactor_stocks_arr[r_idx]) if not np.isnan(reactor_stocks_arr[r_idx]) else 4.0

            if min_opp_pct is not None and opp_pct_at < min_opp_pct:
                continue

            converted = False
            outcome_frame = None

            if outcome is None:
                converted = True

            elif outcome == "kill":
                start_r = int(np.searchsorted(reactor_frames_arr, trigger_frame + 1))
                for k in range(start_r, len(reactor_frames_arr)):
                    if reactor_frames_arr[k] > trigger_frame + window_frames:
                        break
                    if (not np.isnan(reactor_stocks_arr[k])
                            and reactor_stocks_arr[k] < opp_stock_at):
                        converted = True
                        outcome_frame = int(reactor_frames_arr[k])
                        break

            else:
                # outcome_move_id: look for that move hitting the reactor within window
                start_r = int(np.searchsorted(reactor_frames_arr, trigger_frame + 1))
                for k in range(start_r, len(reactor_pct_arr)):
                    rf = int(reactor_frames_arr[k])
                    if rf > trigger_frame + window_frames:
                        break
                    if (not np.isnan(reactor_pct_arr[k])
                            and not np.isnan(reactor_pct_arr[k - 1])
                            and reactor_pct_arr[k] > reactor_pct_arr[k - 1]
                            and not np.isnan(reactor_stocks_arr[k])
                            and reactor_stocks_arr[k] == reactor_stocks_arr[k - 1]):
                        lal_val = actor_lal_map.get(rf)
                        mid = int(lal_val) if lal_val is not None and not pd.isna(lal_val) else 0
                        if mid == outcome_move_id:
                            converted = True
                            outcome_frame = rf
                            break

            desc = (
                f"{trigger_label} → {outcome_label}"
                f" {'✓' if converted else '✗'}"
                f" (opp {opp_pct_at:.0f}%)"
            )

            row = _clip_row(
                filepath=filepath,
                start_frame=trigger_frame,
                end_frame=outcome_frame if outcome_frame is not None else trigger_frame + min(window_frames, 120),
                character=char_name,
                opp_character=opp_char,
                pattern_type="confirmed_event",
                description=desc,
                metadata={
                    "trigger_type": trigger_type,
                    "trigger_label": trigger_label,
                    "trigger_frame": trigger_frame,
                    "outcome_type": outcome_label,
                    "outcome_frame": outcome_frame,
                    "converted": converted,
                    "opp_pct_at_trigger": opp_pct_at,
                },
            )
            row["converted"] = converted
            rows.append(row)

    return pd.DataFrame(rows)
