# Query Cookbook

Worked examples translating natural language questions into melee-tools code.
For background on Melee concepts and terminology, see `melee_guide.md`. For
term-to-data mappings, see `glossary.md`.

## Setup (common imports)

```python
import pandas as pd

from melee_tools import (
    parse_replays, player_games,
    find_kills, find_state_entries, find_state_exits, next_action_after,
    analyze_kills, analyze_combos,
    game_stats, game_stats_directory,
)
from melee_tools.frames import extract_frames, extract_all_players_frames
from melee_tools.action_states import ACTION_STATE_CATEGORIES, ACTION_STATES, FRIENDLY_NAMES
from melee_tools.moves import MOVE_NAMES, move_name
from melee_tools.enums import character_name

REPLAY_DIR = '../replays'
TAG = "EG＃0"

games = parse_replays(REPLAY_DIR)
pg = player_games(games)
```

---

## Pattern 1: "What attack does [character] kill with most?"

**Approach:** Use `analyze_kills()` to find all kills by a character across
replays, then group by `killing_move`.

```python
kills = analyze_kills(REPLAY_DIR, pg, TAG, character="Captain Falcon")
print(kills['killing_move'].value_counts())
```

**Variations:**
- Average kill percent: `kills.groupby('killing_move')['death_percent'].mean()`
- By opponent: `kills.groupby('opp_character')['killing_move'].value_counts()`

---

## Pattern 2: "Which blastzone does [character] die off of most?"

**Approach:** Use `analyze_kills()` with `as_attacker=False` to find deaths,
then group by `blastzone`.

```python
deaths = analyze_kills(REPLAY_DIR, pg, TAG, character="Sheik", as_attacker=False)
print(deaths['blastzone'].value_counts())
```

**Variations:**
- By attacker: `deaths.groupby('opp_character')['blastzone'].value_counts()`
- By killing move per blastzone: `deaths.groupby('blastzone')['killing_move'].value_counts()`

---

## Pattern 3: "After [event], what does [character] do?"

**Approach:** Use `find_state_exits()` + `next_action_after()` on per-game
DataFrames via `_iter_1v1_games()`.

```python
from melee_tools.iteration import _iter_1v1_games

damage_states = ACTION_STATE_CATEGORIES['damage']
all_actions = set(ACTION_STATES.keys()) - damage_states

results = []
for gi, my_df, opp_df, char_name in _iter_1v1_games(REPLAY_DIR, pg, TAG, character="Fox"):
    exits = find_state_exits(my_df, damage_states)
    actions = next_action_after(my_df, exits.index, all_actions, window_frames=60)
    results.extend(actions)

pd.DataFrame(results)['state_name'].value_counts()
```

**Common trigger categories:** `"damage"`, `"spawn"`, `"shield_stun"`,
`"grabbed"`, `"ledge_hang"`, `"tech"`, `"missed_tech_down"`, `"missed_tech_up"`

---

## Pattern 4: "What's the first attack after respawn?"

**Approach:** Find spawn exits, look for the first attack state within a window.

```python
all_attacks = ACTION_STATE_CATEGORIES['ground_attack'] | ACTION_STATE_CATEGORIES['aerial'] | ACTION_STATE_CATEGORIES['grab']
spawn_states = ACTION_STATE_CATEGORIES['spawn']

first_attacks = []
for f in sorted(os.listdir(REPLAY_DIR)):
    if not f.endswith('.slp'): continue
    result = extract_frames(os.path.join(REPLAY_DIR, f), include_inputs=False)
    for idx, df in result['players'].items():
        if df['character_name'].iloc[0] != 'Jigglypuff': continue
        exits = find_state_exits(df, spawn_states)
        actions = next_action_after(df, exits.index, all_attacks, window_frames=300)
        first_attacks.extend(actions)

pd.Series([a['state_name'] for a in first_attacks]).value_counts()
```

---

## Pattern 5: "What tech option does [character] choose after [move]?"

**Approach:** Find frames where the victim enters knockdown after being hit by
a specific move, then look for tech/missed-tech states.

```python
# After being hit by Sheik's down-throw, what does Fox do?
# Step 1: Find frames where Fox enters knockdown states
# Step 2: Check if last_attack_landed == 56 (down-throw)
# Step 3: Look for next tech state

tech_states = (
    ACTION_STATE_CATEGORIES['tech'] |
    ACTION_STATE_CATEGORIES['missed_tech_up'] |
    ACTION_STATE_CATEGORIES['missed_tech_down'] |
    ACTION_STATE_CATEGORIES['getup_attack']
)
knockdown_states = ACTION_STATE_CATEGORIES['missed_tech_up'] | ACTION_STATE_CATEGORIES['missed_tech_down']

for f in sorted(os.listdir(REPLAY_DIR)):
    if not f.endswith('.slp'): continue
    result = extract_frames(os.path.join(REPLAY_DIR, f), include_inputs=False)
    for idx, df in result['players'].items():
        if df['character_name'].iloc[0] != 'Fox': continue
        entries = find_state_entries(df, knockdown_states)
        dthrow_knockdowns = entries[entries['last_attack_landed'] == 56]
        actions = next_action_after(df, dthrow_knockdowns.index, tech_states, window_frames=120)
        for a in actions:
            print(a['state_name'])
```

---

## Pattern 6: "How often does [character] L-cancel?"

**Approach:** The `l_cancel` field in post-frame data: 1 = success, 2 = miss.

```python
result = extract_frames('path/to/game.slp', include_inputs=False)
df = result['players'][0]
lc = df['l_cancel'].dropna()
success = (lc == 1).sum()
fail = (lc == 2).sum()
rate = success / (success + fail) if (success + fail) > 0 else None
print(f"L-cancel rate: {rate:.1%} ({success}/{success+fail})")
```

Or use the stats module: `game_stats(filepath)` includes `pN_l_cancel_rate`.

---

## Pattern 7: "Compare player X vs player Y"

**Approach:** Use name tags to identify players, filter game stats.

```python
df = game_stats_directory(REPLAY_DIR)
games = df[df['end_method'].isin(['RESOLVED', 'GAME'])]

player_rows = []
for _, row in games.iterrows():
    for i in range(int(row['num_players'])):
        p = f'p{i}'
        player_rows.append({
            'tag': row.get(f'{p}_name_tag') or 'Unknown',
            'character': row[f'{p}_character'],
            'damage_dealt': row.get(f'{p}_damage_dealt', 0),
            'stocks_lost': row.get(f'{p}_stocks_lost', 0),
            'l_cancel_rate': row.get(f'{p}_l_cancel_rate'),
            'won': row.get(f'{p}_placement') == 0,
        })

players = pd.DataFrame(player_rows)
players.groupby('tag').agg(
    games=('won', 'count'),
    wins=('won', 'sum'),
    avg_damage=('damage_dealt', 'mean'),
    avg_lcancel=('l_cancel_rate', 'mean'),
).round(2)
```

---

## Pattern 8: "How does [character] use their grab game?"

**Approach:** Find all grabs by the character, then look at which throw they
chose and what follow-up came next.

```python
grab_states = ACTION_STATE_CATEGORIES['grab']
throw_states = {219, 220, 221, 222}  # fthrow, bthrow, uthrow, dthrow
THROW_NAMES = {219: 'fthrow', 220: 'bthrow', 221: 'uthrow', 222: 'dthrow'}

throw_data = []
for f in sorted(os.listdir(REPLAY_DIR)):
    if not f.endswith('.slp'): continue
    result = extract_frames(os.path.join(REPLAY_DIR, f), include_inputs=False)
    for idx, df in result['players'].items():
        if df['character_name'].iloc[0] != 'Sheik': continue
        entries = find_state_entries(df, throw_states)
        for frame_idx, row in entries.iterrows():
            throw_name = THROW_NAMES.get(row['action_state'], 'unknown')
            # Find what happened after the throw within 60 frames
            all_action_states = set(range(14, 400)) - throw_states - grab_states
            followups = next_action_after(df, [frame_idx], all_action_states, window_frames=60)
            followup_name = followups[0]['state_name'] if followups else 'none'
            throw_data.append({
                'throw': throw_name,
                'followup': followup_name,
                'percent': row['percent'],
            })

throws = pd.DataFrame(throw_data)
print(throws['throw'].value_counts())
print(throws.groupby('throw')['followup'].value_counts())
```

---

## Pattern 9: "What does [character] do from ledge?"

**Approach:** Find ledge hang exits, look for the next action.

```python
ledge_hang = ACTION_STATE_CATEGORIES['ledge_hang']
ledge_options = {254, 255, 256, 257, 258, 259, 260, 261, 262, 263}
# 254-255: getup, 256-257: attack, 258-259: roll, 260-263: jump

LEDGE_OPTION_NAMES = {
    254: 'getup', 255: 'getup_slow',
    256: 'attack', 257: 'attack_slow',
    258: 'roll', 259: 'roll_slow',
    260: 'jump', 261: 'jump', 262: 'jump', 263: 'jump',
}

ledge_choices = []
for f in sorted(os.listdir(REPLAY_DIR)):
    if not f.endswith('.slp'): continue
    result = extract_frames(os.path.join(REPLAY_DIR, f), include_inputs=False)
    for idx, df in result['players'].items():
        if df['character_name'].iloc[0] != 'Fox': continue
        exits = find_state_exits(df, ledge_hang)
        for frame_idx in exits.index:
            if frame_idx + 1 >= len(df): continue
            next_state = df.iloc[frame_idx + 1]['action_state']
            if next_state in LEDGE_OPTION_NAMES:
                ledge_choices.append(LEDGE_OPTION_NAMES[next_state])
            elif next_state == 30 or next_state == 31:
                ledge_choices.append('drop')  # dropped from ledge
            else:
                ledge_choices.append(f'other_{int(next_state)}')

pd.Series(ledge_choices).value_counts()
```

**Why this matters:** Ledge option habits are a key part of a player's
defensive tendencies. Predictable ledge behavior is exploitable.

---

## Pattern 10: "Detect wavedashes"

**Approach:** Look for the sequence: jumpsquat (24) → ESCAPE_AIR (236) within
a few frames, followed by a grounded state.

```python
result = extract_frames('path/to/game.slp', include_inputs=False)
df = result['players'][0]

wavedash_count = 0
states = df['action_state'].values
for i in range(len(states) - 3):
    if states[i] == 24:  # jumpsquat
        # Look ahead for airdodge within jumpsquat duration (up to 6 frames)
        for j in range(i + 1, min(i + 7, len(states))):
            if states[j] == 236:  # ESCAPE_AIR
                # Check if they land on ground within a few frames
                for k in range(j + 1, min(j + 10, len(states))):
                    if states[k] in {23, 14, 20, 21, 39, 40, 41}:  # grounded states
                        wavedash_count += 1
                        break
                break
print(f"Wavedashes: {wavedash_count}")
```

---

## Pattern 11: "What is [character]'s damage per opening / conversion rate?"

**Approach:** Identify "openings" as transitions from neutral to advantage
(opponent enters hitstun from a non-hitstun state), then track total damage
dealt before returning to neutral.

```python
damage_states = ACTION_STATE_CATEGORIES['damage']

result = extract_frames('path/to/game.slp', include_inputs=False)
# Assume player 0 is attacker, player 1 is defender
attacker_df = result['players'][0]
defender_df = result['players'][1]

conversions = []
in_conversion = False
conversion_start_pct = 0

for i in range(1, len(defender_df)):
    state = defender_df.iloc[i]['action_state']
    prev_state = defender_df.iloc[i - 1]['action_state']
    pct = defender_df.iloc[i]['percent']

    # Detect opening: opponent enters hitstun from non-hitstun
    if state in damage_states and prev_state not in damage_states:
        if not in_conversion:
            in_conversion = True
            conversion_start_pct = defender_df.iloc[i - 1]['percent'] or 0

    # Detect reset to neutral: opponent in actionable state for 60+ frames
    # (simplified: just check if they leave hitstun for 30+ frames)
    if in_conversion and state not in damage_states:
        # Count consecutive non-hitstun frames
        non_hitstun_run = 0
        for j in range(i, min(i + 30, len(defender_df))):
            if defender_df.iloc[j]['action_state'] not in damage_states:
                non_hitstun_run += 1
            else:
                break
        if non_hitstun_run >= 30:
            damage_done = (pct or 0) - conversion_start_pct
            conversions.append({'damage': damage_done, 'start_pct': conversion_start_pct})
            in_conversion = False

avg_damage = pd.DataFrame(conversions)['damage'].mean()
print(f"Average damage per opening: {avg_damage:.1f}%")
```

**Note:** This is a simplified conversion detector. A production version would
also track stock takes (kills) as conversion endpoints and handle edge cases
like self-destructs.

---

## Pattern 12: "How often does [character] crouch cancel?"

**Approach:** Find frames where the character is crouching (states 39-41) and
gets hit (enters hitstun), but stays grounded (no tumble/knockback fly).

```python
crouch_states = {39, 40, 41}
result = extract_frames('path/to/game.slp', include_inputs=False)
df = result['players'][0]

cc_count = 0
hit_while_standing_count = 0

for i in range(1, len(df)):
    state = df.iloc[i]['action_state']
    prev_state = df.iloc[i - 1]['action_state']
    pct = df.iloc[i]['percent']
    prev_pct = df.iloc[i - 1]['percent']

    # Was hit (percent increased)
    if pct and prev_pct and pct > prev_pct:
        if prev_state in crouch_states:
            cc_count += 1
        elif prev_state not in ACTION_STATE_CATEGORIES['damage']:
            hit_while_standing_count += 1

print(f"Crouch cancel hits: {cc_count}")
print(f"Non-CC hits taken: {hit_while_standing_count}")
```

---

## Pattern 13: "Edgeguard analysis — how does [player] get kills offstage?"

**Approach:** Use `analyze_kills()` and classify by blastzone as a proxy for
edgeguard vs onstage kills.

```python
kills = analyze_kills(REPLAY_DIR, pg, TAG, character="Marth")

# Blastzone as proxy:
# - Side (left/right) and bottom = likely edgeguard/gimp kills
# - Top = likely onstage kills (usmash, uair, uthrow combos)
edgeguard_kills = kills[kills['blastzone'].isin(['left', 'right', 'bottom'])]
onstage_kills = kills[kills['blastzone'] == 'top']
print(f"Edgeguard kills: {len(edgeguard_kills)} ({len(edgeguard_kills)/len(kills):.0%})")
print(f"Onstage kills: {len(onstage_kills)} ({len(onstage_kills)/len(kills):.0%})")
print(f"\nEdgeguard kill moves:\n{edgeguard_kills['killing_move'].value_counts()}")
```

---

## Composing New Queries

Most questions decompose into:

1. **Select games** — filter by stage, character, end_method, etc.
2. **Select player** — filter by character name, name tag, or port
3. **Find trigger event** — use `find_state_entries()`, `find_state_exits()`,
   `find_kills()`, or stock/percent thresholds
4. **Find response** — use `next_action_after()` with a target state set
5. **Aggregate** — value_counts(), mean(), groupby()

### Common trigger → response patterns

| Question Type | Trigger | Response | Window |
|--------------|---------|----------|--------|
| Post-hitstun action | Exit `damage` states | Any action | 60 frames |
| Tech option after throw | Enter knockdown states | Tech states | 120 frames |
| Post-respawn action | Exit `spawn` states | Any attack | 300 frames |
| Ledge option | Exit `ledge_hang` | Ledge action states | 30 frames |
| Post-shield option | Exit `shield` states | Any action | 30 frames |
| Recovery after being hit offstage | Exit `damage` with y < 0 | Up-B / airdodge / jump | 120 frames |
| Follow-up after landing a move | Attacker in attack end lag | Next attack or grab | 60 frames |

### Percent-range analysis

Many Melee interactions change based on damage %. To analyze by percent range:

```python
# Example: What throw does Sheik use at different % ranges?
throws['pct_bin'] = pd.cut(throws['percent'], bins=[0, 30, 60, 90, 120, 200],
                           labels=['0-30', '30-60', '60-90', '90-120', '120+'])
throws.groupby('pct_bin')['throw'].value_counts()
```

This is useful for detecting flowchart-style play: "at low %, character uses
dthrow for combos; at high %, switches to fthrow for stage positioning."

If a query doesn't fit these patterns, you can always work directly with the
frame DataFrame — it has all the raw data per frame.
