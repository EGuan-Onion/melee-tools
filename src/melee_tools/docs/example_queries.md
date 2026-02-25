# Example Research Questions for Melee Replay Analysis

These questions can be answered with the melee-tools library against a
directory of `.slp` replay files.  They are grouped by analysis domain.

---

## Batch 1 — Skill / Technique Execution

**Q1: L-cancel rate by aerial move**
Which aerial do I miss L-cancels on most?  Does it vary by character?

```python
from melee_tools import aerial_stats, parse_replays, player_games

games = parse_replays("replays")
pg = player_games(games)

aerials = aerial_stats("replays", pg, "EG＃0")
aerials.groupby(["character", "aerial"]).agg(
    attempts=("lc_success", "count"),
    rate=("lc_success", "mean"),
).round(3)
```

*Finding:* Sheik fair 87% vs uair/dair ~70–73%. Falcon dair notably weak (64%).

---

**Q2: SHFFL rate**
Of all aerial attacks, how many are executed as full SHFFLs (short hop + fast
fall + L-cancel)?

```python
aerials = aerial_stats("replays", pg, "EG＃0")
aerials.groupby("character").agg(
    aerials=("shffl", "count"),
    shffl_rate=("shffl", "mean"),
    sh_rate=("short_hop", "mean"),
    ff_rate=("fastfall", "mean"),
    lc_rate=("lc_success", "mean"),
).round(3)
```

*Finding:* Falcon 45% SHFFL rate; Sheik 23%.

---

**Q3: Wavedash frequency per minute**
How often do I wavedash, and does it differ by character/stage?

```python
from melee_tools import wavedash_stats

wds = wavedash_stats("replays", pg, "EG＃0")
wds.groupby("character").agg(
    total=("slide_vel", "count"),
    avg_per_min=("duration_min", lambda x: len(x) / x.sum()),
)
```

*Finding:* Sheik ~10.9 WD/min, Falcon ~5.0 WD/min.

---

**Q4: Ledge option distribution + ledgedash rate**
From ledge, do I vary my options or are they predictable?

```python
from melee_tools import ledge_options

ledge = ledge_options("replays", pg, "EG＃0")
ledge.groupby(["character", "option"]).size().unstack(fill_value=0)
```

*Finding:* Nearly all exits are "drop_jump" (drop + double jump). Ledgedash
rate: 0%.

---

**Q5: Crouch cancel rate**
How often do I absorb hits while crouching?  Am I using crouch cancel actively?

```python
from melee_tools import crouch_cancel_stats

cc = crouch_cancel_stats("replays", pg, "EG＃0")
cc.groupby(["character", "was_crouching"]).size()
```

*Finding:* Only 1–3% of hits absorbed while crouching — very low, room for
improvement at low % vs heavy-hitting characters.

---

## Batch 2 — Neutral Game

**Q6: How does neutral end?**
What move do I use to win neutral most often?  Grab vs aerial vs projectile?

```python
from melee_tools import find_neutral_openings

openings = find_neutral_openings("replays", pg, "EG＃0")
won = openings[openings["outcome"] == "won"]
won.groupby(["character", "opener_group"]).size().unstack(fill_value=0)
```

*Finding:* Sheik: grab (214x), aerials (393x combined), needles (110x).
Falcon: aerials (440x), grabs (164x).

---

**Q7: Neutral length**
How many frames does neutral typically last before someone gets hit?

```python
openings.groupby(["character", "outcome"])["neutral_frames"].describe()
```

*Finding:* Median neutral ~64 frames (~1 sec) when I win, ~79 frames when
I lose — I'm slightly quicker to find my opening.

---

**Q8: Projectile conversion rate (Sheik needles)**
When needles land in neutral, do they lead to a punish?

```python
# Filter to projectile neutral openers for Sheik
sheik_opens = openings[
    (openings["character"] == "Sheik") &
    (openings["outcome"] == "won") &
    (openings["opener_group"] == "projectile")
]
# These ARE the conversions — the neutral window ended with a projectile hit.
print(f"Needle-started openings: {len(sheik_opens)}")
```

*Note:* 110 needle-started neutral wins out of ~1000 Sheik neutral wins.

---

**Q9: Approach option distribution**
What mix of approaches do I use?

```python
won = openings[openings["outcome"] == "won"]
won.groupby(["character", "opener_group"]).size().unstack(fill_value=0)
```

---

**Q10: Stage control bias**
Where on stage am I during neutral?  Do I get pushed toward edges?

```python
from melee_tools import stage_positions

pos = stage_positions("replays", pg, "EG＃0", sample_every=10)
pos.groupby("character")["pos_x"].describe()
```

*Finding:* Average x ≈ 6–9 (slightly right-of-center). Std ~50 — wide range.
Both Sheik and Falcon spend neutral near center.

---

## Batch 3 — Punish Game / Combos

**Q11: Damage per opening**
How much damage do I deal per punish sequence on average?

```python
from melee_tools import analyze_combos

combos = analyze_combos("replays", pg, "EG＃0")
combos.groupby("character")["damage"].describe()
```

---

**Q12: Conversion rate (opening → stock)**
What fraction of punish sequences end in a kill?

```python
combos.groupby("character")["killed"].mean()
```

---

**Q13: Kill move distribution**
What move do I kill with most often, by character?

```python
from melee_tools import find_kills, player_games

# Use analyze_combos kill_finishers helper
from melee_tools import kill_finishers
combos = analyze_combos("replays", pg, "EG＃0")
kf = kill_finishers(combos)
kf.value_counts()
```

---

**Q14: Kill % distribution**
At what percent does my opponent typically die?

```python
killed_combos = combos[combos["killed"]]
killed_combos.groupby("character")["end_pct"].describe()
```

---

**Q15: Combo length vs starter**
Does dthrow lead to longer combos than dash attack at the same percent?

```python
combos.groupby(["character", "started_by"])["num_hits"].mean().sort_values(ascending=False)
```

---

**Q16: Dthrow follow-up rate by tech option**
When I hit with dthrow, what tech option does the opponent choose and
how often do I punish each?

```python
from melee_tools import find_state_entries, next_action_after
from melee_tools import ACTION_STATE_CATEGORIES

# See cookbook Pattern 5 for full implementation
```

---

## Batch 4 — Defense / Getting Comboed

**Q17: Tech rate**
How often do I successfully tech when knocked down?

```python
from melee_tools import analyze_knockdowns

kd = analyze_knockdowns("replays", pg, "EG＃0")
kd["option"].value_counts(normalize=True)
```

---

**Q18: Tech direction bias**
Do I roll toward or away from the opponent more?  Is it exploitable?

```python
tech_rolls = kd[kd["option"].str.startswith("tech")]
tech_rolls.groupby(["character", "option"]).size()
```

---

**Q19: DI choices during hitstun**
What direction do I hold during hitstun?  Am I DI-ing away?

```python
# Requires include_inputs=True — see custom analysis below
# Look at input_joystick_x during DAMAGE_STATES frames
```

---

**Q20: How long am I in combos?**
Average number of hits I take in a single combo string, by opponent.

```python
from melee_tools import analyze_combos

# Swap perspective: analyze_combos called from opponent's view
# Or: use detect_combos(opp_df, my_df) for each game
```

---

**Q21: OOS options from shield**
From shield, what do I do?  Roll, spotdodge, jump, grab?

```python
from melee_tools import post_state_actions

oos = post_state_actions("replays", "Sheik", "shield", "any", window_frames=30)
oos["state_name"].value_counts()
# Note: only works for character-level, not tag-level
```

---

## Batch 5 — Edgeguarding

**Q22: Edgeguard attempt rate**
When the opponent is offstage, how often do I go out to edgeguard vs reset?

```python
# See edgeguard_stats() in future implementation
```

---

**Q23: Edgeguard success rate**
Of edgeguard attempts, what % result in a stock?

```python
# Use find_kills() + classify by victim position at death
```

---

**Q24: Ledge option distribution (as the recovering player)**
How predictable is my ledge behavior when I'm hanging?

```python
from melee_tools import ledge_options

ledge = ledge_options("replays", pg, "EG＃0")
ledge.groupby(["character", "option"]).size()
```

---

**Q25: Ledge option success rate**
After each ledge option, do I get hit?

```python
# Extend ledge_options() to track whether a hit follows within N frames
```

---

**Q26: Gimp rate**
What fraction of stocks are taken at low % (edgeguard/gimp vs raw kill)?

```python
from melee_tools import analyze_combos

killed = analyze_combos("replays", pg, "EG＃0")[lambda d: d["killed"]]
gimp_threshold = 70  # percent
gimp_rate = (killed["end_pct"] < gimp_threshold).mean()
print(f"Gimp rate: {gimp_rate:.0%}")
```

---

## Batch 6 — Game Flow / Macro

**Q27: First-stock advantage**
How predictive is losing the first stock?

```python
from melee_tools import game_stats_directory
import pandas as pd

stats = game_stats_directory("replays")
# Identify which player lost first stock and whether they won
```

---

**Q28: Stock lead behavior**
Do I approach more aggressively when ahead?

```python
openings = find_neutral_openings("replays", pg, "EG＃0")
# Compare opener_group distribution when my_pct < opp_pct vs my_pct > opp_pct
openings["leading"] = openings["my_pct"] < openings["opp_pct"]
openings.groupby(["character", "leading", "opener_group"]).size()
```

---

**Q29: Performance by stage**
Win rate, damage per opening, kill % by stage.

```python
stats = game_stats_directory("replays")
openings = find_neutral_openings("replays", pg, "EG＃0")
openings.groupby(["character", "stage"]).agg(
    win_rate=("outcome", lambda x: (x == "won").mean()),
)
```

---

**Q30: Set adaptation**
Does my approach mix change game 2 vs game 1?

```python
# Tag each game with its position in its session/set
# Then compare opener distribution by game number
```

---

**Q31: Game length vs outcome**
Do I win more in long or short games?

```python
stats = game_stats_directory("replays")
# Use duration_minutes vs placement for EG#0 rows
```

---

## Batch 7 — Character-Specific (Sheik)

**Q32: Fair context (kill move vs combo ender vs edgeguard)**
How am I using fair — to kill, to extend combos, or to edgeguard?

```python
# Classify by opponent percent + position (y < 0 = offstage) at hit time
# and whether the hit leads to a stock loss
```

---

**Q33: Needle usage rate and hit rate**
How often are needles landing in neutral?

```python
openings_sheik = openings[openings["character"] == "Sheik"]
needle_rate = (openings_sheik["opener_group"] == "projectile").mean()
print(f"Needle neutral win rate: {needle_rate:.0%}")
```

---

**Q34: Grab rate and throw selection by percent**
When I grab, what throw do I choose at each percent range?

```python
# See cookbook Pattern 8 for Sheik throw analysis
# Use pct_bin analysis to see throw selection change by percent
```

---

**Q35: Fair kill % vs opponent character**
At what percent does fair actually kill by opponent character?

```python
from melee_tools import analyze_combos, kill_finishers

combos = analyze_combos("replays", pg, "EG＃0", character="Sheik")
fair_kills = combos[(combos["killed"]) & (combos["ended_by"] == "Fair")]
fair_kills.groupby("opp_character")["end_pct"].describe()
# Note: opp_character not yet in analyze_combos output — can add or cross-join
```
