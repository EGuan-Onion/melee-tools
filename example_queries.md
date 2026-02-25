# Example Queries — melee-tools

Code snippets for common competitive analysis questions.
All examples assume replays are in `"replays/"` and your tag is `"EG＃0"`.

```python
from melee_tools import *
games = parse_replays("replays")
pg = player_games(games)
TAG = "EG＃0"
```

---

## Q1 — Average combo damage by opening move

```python
combos = analyze_combos("replays", pg, TAG, character="Sheik")
combos.groupby("started_by")["damage"].agg(["mean", "count", "median"]).query("count >= 5").sort_values("mean", ascending=False)
```

---

## Q2 — At what % do I kill, by move?

```python
from melee_tools.habits import _iter_1v1_games

rows = []
for gi, my_df, opp_df, char_name in _iter_1v1_games("replays", pg, TAG):
    kills = find_kills(opp_df, attacker_df=my_df)
    kills["character"] = char_name
    rows.append(kills)

kills_df = pd.concat(rows, ignore_index=True)
kills_df.groupby(["character", "killing_move"])["death_percent"].agg(["median", "count"]).sort_values("count", ascending=False)
```

---

## Q3 — Sweetspot / sourspot rate (Captain Falcon knee)

```python
hits = find_move_hits("replays", pg, TAG, move="knee", character="falcon")
hits["label"].value_counts(normalize=True).mul(100).round(1)
```

All moves with classification data for Falcon:
```python
hits = find_move_hits("replays", pg, TAG, character="Captain Falcon")
hits[hits.has_data].groupby(["move_name", "label"]).size().unstack(fill_value=0)
```

---

## Q4 — Move usage and hit rate in neutral

```python
attacks = analyze_neutral_attacks("replays", pg, TAG, character="Sheik")
attacks.groupby("move").agg(uses=("hit", "count"), hits=("hit", "sum")).assign(
    hit_rate=lambda d: d.hits / d.uses
).sort_values("uses", ascending=False)
```

---

## Q5 — What moves does the opponent land on me most?

```python
from melee_tools.moves import move_name

rows = []
for gi, my_df, opp_df, char_name in _iter_1v1_games("replays", pg, TAG):
    my_pct = my_df["percent"].values.astype(float)
    my_stocks = my_df["stocks"].values.astype(float)
    opp_lal_map = dict(zip(opp_df["frame"].values.astype(int), opp_df["last_attack_landed"].values))

    for j in range(1, len(my_pct)):
        if my_pct[j] > my_pct[j-1] and my_stocks[j] == my_stocks[j-1]:
            frame = int(my_df["frame"].values[j])
            mid = int(opp_lal_map.get(frame, 0))
            if mid == 0: continue
            rows.append({"my_char": char_name, "move": move_name(mid),
                         "damage": round(round(my_pct[j],1) - round(my_pct[j-1],1), 1)})

opp_hits = pd.DataFrame(rows)
opp_hits.groupby(["my_char", "move"]).agg(count=("damage","count"), avg_dmg=("damage","mean")).sort_values("count", ascending=False)
```

---

## Q6 — Combo damage distribution (neutral win value)

```python
combos = analyze_combos("replays", pg, TAG, character="Sheik")
print(f"Mean: {combos.damage.mean():.1f}%  Median: {combos.damage.median():.1f}%")
print(f"Kill combos: {combos.killed.mean()*100:.0f}%")
combos["damage"].hist(bins=range(0, 100, 5))
```

---

## Q7 — Knockdown option distribution

```python
kd = analyze_knockdowns("replays", pg, TAG, character="Sheik")
kd["option"].value_counts(normalize=True).mul(100).round(1)

# By percent bucket
kd = add_pct_buckets(kd, pct_col="percent")
kd.groupby(["bucket", "option"]).size().unstack(fill_value=0)
```

---

## Q8 — Where am I dying? (blastzone + position)

```python
rows = []
for gi, my_df, opp_df, char_name in _iter_1v1_games("replays", pg, TAG):
    deaths = find_kills(my_df, attacker_df=opp_df)
    deaths["character"] = char_name
    rows.append(deaths)

deaths_df = pd.concat(rows, ignore_index=True)
deaths_df["blastzone"].value_counts()
# scatter: deaths_df.plot.scatter("death_x", "death_y", c=deaths_df.blastzone.map({...}))
```

---

## Q9 — D-throw kill conversion (Sheik)

```python
from melee_tools.action_states import ACTION_STATE_CATEGORIES

DTHROW_STATES = ACTION_STATE_CATEGORIES.get("throw_down", set()) | {60}
KILL_PCT_THRESHOLD = 80
CONVERSION_WINDOW = 300

rows = []
for gi, my_df, opp_df, char_name in _iter_1v1_games("replays", pg, TAG, character="Sheik"):
    opp_pct_map = dict(zip(opp_df["frame"].values.astype(int), opp_df["percent"].values.astype(float)))
    opp_stocks_map = dict(zip(opp_df["frame"].values.astype(int), opp_df["stocks"].values.astype(float)))
    my_states = my_df["state"].values
    my_frames = my_df["frame"].values.astype(int)

    for i in range(1, len(my_states)):
        s = int(my_states[i]) if not pd.isna(my_states[i]) else 0
        prev_s = int(my_states[i-1]) if not pd.isna(my_states[i-1]) else 0
        if s not in DTHROW_STATES or prev_s in DTHROW_STATES: continue
        frame = int(my_frames[i])
        opp_pct = opp_pct_map.get(frame, 0)
        opp_stock = opp_stocks_map.get(frame, 4)
        if opp_pct < KILL_PCT_THRESHOLD: continue
        converted = any(
            opp_stocks_map.get(int(my_frames[j]), opp_stock) < opp_stock
            for j in range(i+1, min(i+CONVERSION_WINDOW, len(my_frames)))
        )
        rows.append({"opp_pct": opp_pct, "converted": converted})

df = pd.DataFrame(rows)
print(f"Kill-% d-throws: {len(df)}, Converted: {df.converted.mean()*100:.0f}%")
```

---

## Q10 — How do I die?

```python
# deaths_df from Q8 above
deaths_df.groupby(["character", "killing_move"]).agg(
    count=("death_percent", "count"),
    avg_pct=("death_percent", "mean"),
).sort_values("count", ascending=False).head(15)
```

---

---

## Q — analyze_hits_taken: what does the opponent land on me?

```python
hits = analyze_hits_taken("replays", pg, TAG, character="Sheik")
hits.groupby(["opp_character", "move"]).agg(
    count=("damage", "count"), avg_dmg=("damage", "mean")
).sort_values("count", ascending=False).head(15)
```

---

## Q — analyze_kills: multi-game kill/death with tag filtering

```python
# Kills I dealt as Falcon
kills = analyze_kills("replays", pg, TAG, character="Captain Falcon")
kills.groupby("killing_move")["death_percent"].describe()

# How I die as Sheik
deaths = analyze_kills("replays", pg, TAG, character="Sheik", as_attacker=False)
deaths["killing_move"].value_counts()
```

---

## Q — find_confirmed_events: general trigger → outcome confirm detector

```python
# Knee → kill rate (Falcon)
clips = find_confirmed_events("replays", pg, TAG, trigger="knee", outcome="kill", character="falcon")
print(f"Knee→kill: {clips['converted'].mean()*100:.0f}% ({clips['converted'].sum()}/{len(clips)})")

# Throw → kill rate (Sheik, opponent at kill %)
clips = find_confirmed_events(
    "replays", pg, TAG, trigger="throw", outcome="kill",
    character="sheik", min_opp_pct=80,
)
print(f"Throw→kill at 80%+: {clips['converted'].mean()*100:.0f}%")

# Stomp → stomp (Falcon Dair → Dair within 1.5 sec)
clips = find_confirmed_events(
    "replays", pg, TAG, trigger="stomp", outcome="stomp",
    window_frames=90, character="falcon",
)

# All knees that landed → export for Dolphin watchback
clips = find_confirmed_events("replays", pg, TAG, trigger="knee", outcome=None, character="falcon")
export_dolphin_json(clips, "replays/outputs/all_knees.json")

# What opponent move kills me (as_attacker=False)
clips = find_confirmed_events("replays", pg, TAG, trigger="fair", outcome="kill", as_attacker=False)
print(f"Opp fair→my death: {clips['converted'].sum()} kills")
```

**Trigger resolution:**
- Move alias string → fires on hit (lal-based, handles back-to-back same move)
- `ACTION_STATE_CATEGORIES` key string (e.g. `"throw"`, `"grab"`) → fires on state entry
- `set[int]` of raw action state IDs → fires on state entry

---

## Bonus — Clip export

```python
clips = find_move_sequences("replays", pg, TAG, moves=["ftilt", "fair"], character="sheik")
export_dolphin_json(clips, "replays/outputs/clips.json")
```

## Bonus — Hitbox coverage for a character

```python
from melee_tools import hitbox_coverage
hitbox_coverage("falcon")
```
