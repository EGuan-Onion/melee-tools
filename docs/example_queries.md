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
from melee_tools import find_state_exits, next_action_after, ACTION_STATE_CATEGORIES
from melee_tools.iteration import _iter_1v1_games

shield_states = ACTION_STATE_CATEGORIES['shield']
all_states = set(range(0, 400)) - shield_states

results = []
for gi, my_df, opp_df, char_name in _iter_1v1_games("replays", pg, "EG＃0", character="Sheik"):
    exits = find_state_exits(my_df, shield_states)
    actions = next_action_after(my_df, exits.index, all_states, window_frames=30)
    results.extend(actions)

pd.DataFrame(results)['state_name'].value_counts()
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

---

## Batch 8 — Population-Level Analysis (training_data)

These questions use the `replays/training_data/` community dataset (95k files) rather than personal
replays. Always sample randomly (1000 games, seed=42) and scan with raw peppi_py — `extract_frames()`
fails on older Slippi formats in this folder.

**Q36: Fox tech option distribution across all matchups**
When Fox gets knocked down, what does he do? How often does he tech vs miss?

```python
# See analysis/tech_chases.py for full implementation.
# Key findings from 1000-game sample (n=6150 knockdowns):
#   tech in place:     22.0%  — most common single option
#   missed tech:       20.2%  — second most (many mid-level players don't tech)
#   tech toward:       11.3%
#   tech away:         10.5%
#   getup:             10.2%
#   roll away:          8.1%
#   getup attack:       7.1%
#   roll toward:        6.8%
#   hit while down:     3.6%
#
# Conversion rates are flat across options (~46-54%) except:
#   hit while down: 100% (trivially)
#   missed tech (other): 58% (easiest to punish)
#   roll away / tech in place: lowest at ~46%
```

---

**Q37: Fox tech options in the Peach matchup vs overall**
Does Fox behave differently on knockdown when facing Peach?

```python
# Filter the tech_chases DataFrame:
peach_df = df[df["attacker_character"] == "Peach"]

# Key differences vs overall (n=278 Peach vs Fox situations):
#   missed tech:      +4.6pp higher vs Peach (24.8% vs 20.2%)  — Fox misses tech more
#   tech away:        +2.8pp higher vs Peach (13.3% vs 10.5%)  — Fox tries to escape more
#   getup attack:     -4.2pp lower  vs Peach (2.9% vs 7.1%)    — Fox avoids getup attack (Peach punishes it)
#
# Peach's conversion rate (44%) is below dataset average (52%) despite Fox making it
# easier by missing tech more — suggests Peach players react more slowly or choose
# suboptimal punishes.
```

---

**Q38: Attacker response by tech option (population level)**
What do attackers actually throw out when Fox techs? How does it vary by tech choice?

```python
# From analysis/tech_chases.py heatmap chart.
# Top attacker responses overall:
#   Other/None (2243) — no clear committed move
#   Dair  (505, 59% hit rate)
#   Fair  (386, 54%)
#   Grab  (372, 66% — highest hit rate)
#   Dash attack (333, 62%)
#   Uair  (318, 63%)
#   Wavedash (282, 49%) — repositioning
#   Nair  (245, 44%)
#   Dsmash (223, 45%)
#
# Grab has the highest hit rate (66%) — players who commit to grab after knockdown
# are converting well, especially off getup and tech in place.
```

---

---

## Batch 9 — Stage & Positional Analysis

For positional charts, draw the stage geometry as a backdrop using `STAGE_GEOMETRY` edge_x values
and hardcoded platform coordinates before plotting scatter points.

**Q40: Ledge-hugging frequency**
What fraction of my in-game frames am I within 20 units of the blast zone edge?
Measures whether I'm ceding center stage and backing myself into bad positions.

```python
from melee_tools import stage_positions, STAGE_GEOMETRY, parse_replays, player_games

games = parse_replays("replays")
pg = player_games(games)
pos = stage_positions("replays", pg, "EG＃0", sample_every=5)

edge_map = {s: v["edge_x"] for s, v in STAGE_GEOMETRY.items()}
pos["edge_x"] = pos["stage"].map(edge_map)
pos["near_ledge"] = pos["pos_x"].abs() > (pos["edge_x"] - 20)
pos.groupby("character")["near_ledge"].mean().round(3)
```

---

**Q41: Do I drift toward the ledge as my percent rises?**
At low percent I should hold center; defensive drift at high percent is a diagnosable habit.

```python
from melee_tools import STAGE_GEOMETRY
from melee_tools.iteration import _iter_1v1_games
import pandas as pd

rows = []
for gi, my_df, opp_df, char in _iter_1v1_games("replays", pg, "EG＃0"):
    sampled = my_df[::5][["position_x", "percent"]].copy()
    sampled["character"] = char
    rows.append(sampled)

df = pd.concat(rows)
df["pct_bin"] = pd.cut(df["percent"], bins=[0, 30, 60, 90, 120, 999],
                        labels=["0–30", "30–60", "60–90", "90–120", "120+"])
df.groupby(["character", "pct_bin"])["position_x"].mean().round(1)
# Negative drift (lower mean x at high %) = backing toward left ledge
```

---

**Q42: Off-stage time — me vs my opponent**
Who spends more time off-stage per game? High personal off-stage % = aggressive edgeguard style
or poor recovery choices. High opponent off-stage % = I'm forcing them out.

```python
from melee_tools import STAGE_GEOMETRY
from melee_tools.iteration import _iter_1v1_games
import pandas as pd

rows = []
for gi, my_df, opp_df, char in _iter_1v1_games("replays", pg, "EG＃0"):
    edge_x = STAGE_GEOMETRY.get(gi.get("stage"), {}).get("edge_x", 80)
    my_off = (my_df["position_x"].abs() > edge_x).mean()
    opp_off = (opp_df["position_x"].abs() > edge_x).mean()
    rows.append({"character": char, "my_off_pct": my_off, "opp_off_pct": opp_off})

pd.DataFrame(rows).groupby("character")[["my_off_pct", "opp_off_pct"]].mean().round(3)
```

---

**Q43: Kill position scatter — where on stage do my kills happen?**
Scatter of opponent position at stock loss, overlaid on stage geometry. Reveals off-stage gimps
vs center-stage kills vs ledge traps by character.

```python
from melee_tools import STAGE_GEOMETRY
from melee_tools.iteration import _iter_1v1_games
from melee_tools.query import find_kills
import pandas as pd

kill_positions = []
for gi, my_df, opp_df, char in _iter_1v1_games("replays", pg, "EG＃0"):
    for frame in find_kills(my_df, opp_df):     # frames where opp loses a stock
        kill_positions.append({
            "character": char,
            "stage": gi.get("stage"),
            "x": opp_df.loc[frame, "position_x"],
            "y": opp_df.loc[frame, "position_y"],
        })

kp = pd.DataFrame(kill_positions)
# Visualize: scatter(x, y) per character with STAGE_GEOMETRY stage outline backdrop
```

---

**Q44: Which blast zone kills me most?**
Diagnose DI habits — dying left/right more than up at mid percent suggests missed survival DI.

```python
from melee_tools import STAGE_GEOMETRY
from melee_tools.iteration import _iter_1v1_games
from melee_tools.query import find_kills
import pandas as pd

rows = []
for gi, my_df, opp_df, char in _iter_1v1_games("replays", pg, "EG＃0"):
    edge_x = STAGE_GEOMETRY.get(gi.get("stage"), {}).get("edge_x", 80)
    for frame in find_kills(opp_df, my_df):     # frames where I lose a stock
        x = my_df.loc[frame, "position_x"]
        y = my_df.loc[frame, "position_y"]
        if y > 180:
            zone = "top"
        elif y < -120:
            zone = "bottom"
        elif x > 0:
            zone = "right"
        else:
            zone = "left"
        rows.append({"character": char, "zone": zone})

pd.DataFrame(rows).groupby(["character", "zone"]).size().unstack(fill_value=0)
```

---

**Q45: Where am I standing when I die?**
My position at the stock loss frame. Dying from center stage (x ≈ 0) vs near edge (|x| large)
are very different tactical problems.

```python
from melee_tools import STAGE_GEOMETRY
from melee_tools.iteration import _iter_1v1_games
from melee_tools.query import find_kills
import pandas as pd

rows = []
for gi, my_df, opp_df, char in _iter_1v1_games("replays", pg, "EG＃0"):
    for frame in find_kills(opp_df, my_df):     # frames where I lose a stock
        rows.append({
            "character": char,
            "x": my_df.loc[frame, "position_x"],
            "y": my_df.loc[frame, "position_y"],
        })

dp = pd.DataFrame(rows)
dp.groupby("character")["x"].describe().round(1)
# Also useful: histogram of x, or scatter with stage geometry backdrop
```

---

**Q46: Where on stage do my combos start?**
Opponent position at the first hit of each punish sequence, visualized on stage. Shows whether
neutral is being won center stage or near the ledge.

```python
from melee_tools import detect_combos
from melee_tools.iteration import _iter_1v1_games
import pandas as pd

rows = []
for gi, my_df, opp_df, char in _iter_1v1_games("replays", pg, "EG＃0"):
    combos = detect_combos(my_df, opp_df)
    for _, combo in combos.iterrows():
        start_frame = combo["start_frame"]
        rows.append({
            "character": char,
            "stage": gi.get("stage"),
            "start_x": opp_df.loc[start_frame, "position_x"],
            "start_y": opp_df.loc[start_frame, "position_y"],
        })

combo_starts = pd.DataFrame(rows)
combo_starts.groupby("character")["start_x"].describe().round(1)
# Best as scatter(start_x, start_y) per character with stage geometry backdrop
```

---

**Q47: How far do my combos carry?**
Displacement from combo start to end frame. Lateral combos (high |dx|) carry toward the blast
zone; vertical combos (high dy) set up juggle kills. Differs sharply by character.

```python
rows = []
for gi, my_df, opp_df, char in _iter_1v1_games("replays", pg, "EG＃0"):
    combos = detect_combos(my_df, opp_df)
    for _, combo in combos.iterrows():
        s, e = combo["start_frame"], combo["end_frame"]
        rows.append({
            "character": char,
            "dx": opp_df.loc[e, "position_x"] - opp_df.loc[s, "position_x"],
            "dy": opp_df.loc[e, "position_y"] - opp_df.loc[s, "position_y"],
            "damage": combo["damage"],
        })

disp = pd.DataFrame(rows)
disp.groupby("character")[["dx", "dy"]].agg(["mean", "median"]).round(1)
```

---

**Q48: How deep off-stage do I go when edgeguarding?**
When my opponent is off-stage, how far past the edge do I venture? Measures edgeguard aggression
and risk tolerance. High max_depth = deep off-stage coverage; low = onstage passive edgeguarding.

```python
from melee_tools import STAGE_GEOMETRY
from melee_tools.iteration import _iter_1v1_games
import pandas as pd

rows = []
for gi, my_df, opp_df, char in _iter_1v1_games("replays", pg, "EG＃0"):
    edge_x = STAGE_GEOMETRY.get(gi.get("stage"), {}).get("edge_x", 80)
    opp_offstage = opp_df["position_x"].abs() > edge_x
    if not opp_offstage.any():
        continue
    my_x_during = my_df.loc[opp_offstage, "position_x"]
    depth = (my_x_during.abs() - edge_x).clip(lower=0)
    rows.append({
        "character": char,
        "went_offstage_pct": (depth > 0).mean(),   # fraction of opp-offstage frames I was off too
        "avg_depth": depth[depth > 0].mean() if (depth > 0).any() else 0,
        "max_depth": depth.max(),
    })

pd.DataFrame(rows).groupby("character").mean().round(2)
```

---

**Q39: Tech chase conversion rate by knockdown percent**
Is it easier to punish knockdowns at low percent or high percent?

```python
# From analysis/tech_chases.py bucket chart.
# Conversion rates are nearly flat with a slight downward trend at kill percent:
#   0-30%:    56%  (806/1446)
#   30-60%:   54%  (1085/2011)
#   60-90%:   52%  (830/1613)
#   90-120%:  48%  (373/785)   — lowest; opponents DI better / more careful
#   120%+:    44%  (130/295)   — may reflect edgeguard situations where Fox dies anyway
#
# The dip at 90-120% is meaningful: harder to land a clean punish at kill percent,
# likely because the knocked-down player is more cautious and the attacker is over-
# committing to kill moves.
```
