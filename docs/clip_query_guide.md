# Clip Query Guide

LLM reference for translating natural-language Melee replay queries into Python API calls.

## Quick Start

```python
from melee_tools import parse_replays, player_games
from melee_tools.clips import find_move_sequences, export_dolphin_json

games = parse_replays("replays")
pg = player_games(games)
clips = find_move_sequences("replays", pg, "EG＃0", moves=["dair", "fair"], character="Falcon")
export_dolphin_json(clips, "stomp_knee.json")
# Run: dolphin -i stomp_knee.json
```

## Setup

Every pattern finder requires a `pg` (player-games) DataFrame:

```python
from melee_tools import parse_replays, player_games

games = parse_replays("replays")  # or parse_directory("replays/2025-01")
pg = player_games(games)
```

Common args across all finders:
- `replay_root` — root directory containing .slp files (searched recursively)
- `pg` — player-games DataFrame from `player_games()`
- `tag` — player's netplay tag (e.g. `"EG＃0"`)
- `character` — optional character filter, supports aliases (e.g. `"falcon"`, `"spacies"`)

## Pattern Finders

### `find_move_sequences()`

Find combos containing a specific sequence of moves.

```python
find_move_sequences(
    replay_root,
    pg,
    tag,
    moves: list[str],           # move names/aliases or named combo
    character: str | None,      # player character filter
    gap_frames: int = 45,       # combo gap tolerance
    as_attacker: bool = True,   # True = combos performed, False = combos received
    killed: bool | None = None, # None=any, True=only kills, False=no kills
    min_damage: float | None = None,
)
```

### `find_kills_by_move()`

Find kills with a specific move.

```python
find_kills_by_move(
    replay_root,
    pg,
    tag,
    move: str,                  # move name/alias
    character: str | None,
    as_attacker: bool = True,
)
```

### `find_edgeguards()`

Find edgeguard sequences (hitting opponents offstage).

```python
find_edgeguards(
    replay_root,
    pg,
    tag,
    character: str | None,
    killed: bool | None = None,
)
```

### `find_tech_chases()`

Find tech chase situations (knockdown followups).

```python
find_tech_chases(
    replay_root,
    pg,
    tag,
    character: str | None,
    followup_window: int = 90,
    tech_option: str | None,    # "tech in place", "tech toward", "tech away",
                                # "missed tech", "getup", "getup attack",
                                # "roll toward", "roll away"
)
```

## Alias System

### Character Aliases

| Alias | Resolves to |
|-------|-------------|
| `falcon`, `cf` | Captain Falcon |
| `spacies`, `spacie` | Fox, Falco |
| `puff`, `jiggs` | Jigglypuff |
| `doc` | Dr. Mario |
| `ganon` | Ganondorf |
| `ics`, `icies`, `ic` | Ice Climbers |
| `pika` | Pikachu |
| `yl` | Young Link |
| `dk` | Donkey Kong |
| `m2` | Mewtwo |
| `gnw`, `g&w` | Mr. Game & Watch |

All canonical names also work (case-insensitive): `"fox"`, `"marth"`, `"sheik"`, etc.

### Move Aliases

Character-specific:

| Alias | Character(s) | Move |
|-------|-------------|------|
| `stomp` | Captain Falcon, Ganondorf | Dair (17) |
| `knee`, `knee of justice` | Captain Falcon | Fair (14) |
| `falcon punch` | Captain Falcon | Neutral B (18) |
| `falcon kick` | Captain Falcon | Down B (21) |
| `shine`, `reflector` | Fox, Falco | Down B (21) |
| `laser` | Fox, Falco | Neutral B (18) |
| `rest` | Jigglypuff | Down B (21) |
| `needles` | Sheik | Neutral B (18) |
| `tipper` | Marth | F-smash (10) |
| `shield breaker` | Marth, Roy | Neutral B (18) |
| `counter` | Marth, Roy | Down B (21) |
| `turnip` | Peach | Down B (21) |
| `warlock punch` | Ganondorf | Neutral B (18) |
| `charge shot` | Samus | Neutral B (18) |
| `thunder` | Pikachu, Pichu | Down B (21) |

Generic (work for any character):

| Alias | Move |
|-------|------|
| `forward air`, `forward_air` | Fair (14) |
| `back air`, `back_air` | Bair (15) |
| `up air`, `up_air` | Uair (16) |
| `down air`, `down_air` | Dair (17) |
| `forward tilt`, etc. | Ftilt (7) |
| `forward smash`, etc. | Fsmash (10) |
| `forward throw`, etc. | Fthrow (53) |
| `neutral b`, `side b`, `up b`, `down b` | 18, 19, 20, 21 |

Short names always work directly: `fair`, `bair`, `dair`, `uair`, `nair`, `fsmash`, `dthrow`, etc.

### Named Combos

Pass as a single-element list to `moves` in `find_move_sequences()`:

| Name | Character(s) | Sequence |
|------|-------------|----------|
| `ken combo` | Marth | Fair → Dair |
| `pillar`, `pillars` | Fox, Falco | Dair → Down B |
| `stomp knee`, `stomp to knee`, `stomp into knee` | Captain Falcon | Dair → Fair |
| `upthrow rest` | Jigglypuff | Uthrow → Down B |
| `upthrow upair` | Fox | Uthrow → Uair |
| `chaingrab` | Marth, Sheik, ICs | Dthrow → Dthrow |
| `shine spike` | Fox, Falco | Down B |
| `waveshine` | Fox, Falco | Down B |

## Export

### `export_dolphin_json()`

```python
export_dolphin_json(
    clips,                      # DataFrame from any pattern finder
    output_path,                # e.g. "my_clips.json"
    pad_before: int = 120,      # context frames before (2 sec default)
    pad_after: int = 60,        # context frames after (1 sec default)
)
```

Writes Slippi Dolphin COMM_SPEC JSON:
```json
{
  "mode": "queue",
  "queue": [
    {"path": "/abs/path/game.slp", "startFrame": 880, "endFrame": 1560}
  ]
}
```

Run with: `dolphin -i output.json`

## Clip DataFrame Schema

Every pattern finder returns a DataFrame with these columns:

| Column | Type | Description |
|--------|------|-------------|
| `filepath` | str | Absolute path to .slp file |
| `filename` | str | Just the filename |
| `start_frame` | int | First frame of the moment |
| `end_frame` | int | Last frame of the moment |
| `character` | str | Player's character |
| `opp_character` | str | Opponent's character |
| `pattern_type` | str | `"move_sequence"`, `"kill"`, `"edgeguard"`, `"tech_chase"` |
| `description` | str | Human-readable summary |
| `metadata` | dict | Pattern-specific extras |

## Example Queries → Python

**"Falcon stomp into knee"**
```python
clips = find_move_sequences("replays", pg, tag, moves=["stomp", "knee"], character="falcon")
```

**"All my kills with knee"**
```python
clips = find_kills_by_move("replays", pg, tag, move="knee", character="falcon")
```

**"Edgeguards that killed"**
```python
clips = find_edgeguards("replays", pg, tag, killed=True)
```

**"Tech chases where they missed tech"**
```python
clips = find_tech_chases("replays", pg, tag, tech_option="missed tech")
```

**"Ken combos"**
```python
clips = find_move_sequences("replays", pg, tag, moves=["ken combo"])
```

**"Fox shine spikes"**
```python
clips = find_move_sequences("replays", pg, tag, moves=["shine spike"], character="fox")
```

**"Pillar combos that did 40+ damage"**
```python
clips = find_move_sequences("replays", pg, tag, moves=["pillar"], character="fox", min_damage=40)
```

**"All nair kills as Falcon"**
```python
clips = find_kills_by_move("replays", pg, tag, move="nair", character="falcon")
```

**"Edgeguards as Sheik"**
```python
clips = find_edgeguards("replays", pg, tag, character="sheik")
```

**"Upthrow rest clips"**
```python
clips = find_move_sequences("replays", pg, tag, moves=["upthrow rest"], character="puff")
```

**"Tech chases where opponent tech rolled away"**
```python
clips = find_tech_chases("replays", pg, tag, tech_option="tech away")
```

**"Stomp knee that killed"**
```python
clips = find_move_sequences("replays", pg, tag, moves=["stomp knee"], killed=True)
```

**"Dair into usmash combos"**
```python
clips = find_move_sequences("replays", pg, tag, moves=["dair", "usmash"])
```

**"Rest kills"**
```python
clips = find_kills_by_move("replays", pg, tag, move="rest", character="puff")
```

**"Edgeguard kills as Fox"**
```python
clips = find_edgeguards("replays", pg, tag, character="fox", killed=True)
```
