# Query Cookbook

Worked examples translating natural language questions into melee-tools code.

## Setup (common imports)

```python
import sys
sys.path.insert(0, '../src')  # if running from notebooks/

from melee_tools.frames import extract_frames
from melee_tools.query import (
    find_kills, find_kills_for_character, find_state_entries,
    find_state_exits, next_action_after, post_state_actions,
)
from melee_tools.action_states import ACTION_STATE_CATEGORIES, ACTION_STATES, FRIENDLY_NAMES
from melee_tools.moves import MOVE_NAMES, move_name
from melee_tools.enums import character_name

REPLAY_DIR = '../replays'
```

---

## Pattern 1: "What attack does [character] kill with most?"

**Approach:** Find all kills by the character across replays, group by
`killing_move`.

```python
kills = find_kills_for_character(REPLAY_DIR, "Captain Falcon", as_attacker=True)
print(kills['killing_move'].value_counts())
```

**Variations:**
- Filter by stage: `kills[kills['stage'] == 'Dream Land N64']`
- Filter by victim: `kills[kills['victim_character'] == 'Fox']`
- Average kill percent: `kills.groupby('killing_move')['death_percent'].mean()`

---

## Pattern 2: "Which blastzone does [character] die off of most on [stage]?"

**Approach:** Find all deaths of the character, filter by stage, group by
`blastzone`.

```python
deaths = find_kills_for_character(REPLAY_DIR, "Jigglypuff", as_attacker=False)
dreamland = deaths[deaths['stage'] == 'Dream Land N64']
print(dreamland['blastzone'].value_counts())
```

**Variations:**
- By attacker: `dreamland.groupby('attacker_character')['blastzone'].value_counts()`
- By killing move per blastzone: `dreamland.groupby('blastzone')['killing_move'].value_counts()`

---

## Pattern 3: "After [event], what does [character] do?"

**Approach:** Find exits from the trigger state category, then look for the
next action within a time window.

```python
# After getting hit (leaving hitstun), what does Fox do?
actions = post_state_actions(REPLAY_DIR, "Fox", "damage", "any", window_frames=60)
print(actions['state_name'].value_counts())
```

**Common trigger categories:** `"damage"`, `"spawn"`, `"shield_stun"`,
`"grabbed"`, `"ledge_hang"`, `"tech"`, `"missed_tech_down"`, `"missed_tech_up"`

**Common target categories:** `"any"`, `"aerial"`, `"ground_attack"`,
`"dodge"`, `"grab"`, `"shield"`, `"jump"`

---

## Pattern 4: "What's the first attack after respawn?"

**Approach:** Find spawn exits, look for the first attack state within a window.

```python
from melee_tools.frames import extract_frames
import os, pandas as pd

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
# Step 1: Find frames where Fox enters knockdown states (missed tech face up/down)
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
        # Find knockdown entries where last attack was down-throw
        entries = find_state_entries(df, knockdown_states)
        dthrow_knockdowns = entries[entries['last_attack_landed'] == 56]
        # Then look at what tech they chose
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
from melee_tools.stats import game_stats_directory
df = game_stats_directory(REPLAY_DIR)
games = df[df['end_method'].isin(['RESOLVED', 'GAME'])]

# Build player rows
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

## Composing New Queries

Most questions decompose into:

1. **Select games** — filter by stage, character, end_method, etc.
2. **Select player** — filter by character name, name tag, or port
3. **Find trigger event** — use `find_state_entries()`, `find_state_exits()`,
   `find_kills()`, or stock/percent thresholds
4. **Find response** — use `next_action_after()` with a target state set
5. **Aggregate** — value_counts(), mean(), groupby()

If a query doesn't fit these patterns, you can always work directly with the
frame DataFrame — it has all the raw data per frame.
