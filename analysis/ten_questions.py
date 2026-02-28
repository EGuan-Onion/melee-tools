"""
10 Competitive Questions — Analysis Script
Generates one figure per question and saves to outputs/10q/
"""

import warnings
warnings.filterwarnings("ignore")

import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

from analysis.common import ROOT, TAG, games, pg

from melee_tools import (
    analyze_combos, analyze_knockdowns, analyze_neutral_attacks,
    find_move_hits,
)
from melee_tools.combos import analyze_kills
from melee_tools.clips import find_confirmed_events
from melee_tools.habits import analyze_hits_taken

OUT = "outputs/10q"
os.makedirs(OUT, exist_ok=True)

STYLE = {
    "figure.facecolor": "#1a1a2e",
    "axes.facecolor":   "#16213e",
    "axes.edgecolor":   "#4a4a6a",
    "axes.labelcolor":  "#e0e0e0",
    "xtick.color":      "#c0c0c0",
    "ytick.color":      "#c0c0c0",
    "text.color":       "#e0e0e0",
    "grid.color":       "#2a2a4a",
    "grid.linestyle":   "--",
    "grid.alpha":       0.5,
    "axes.titlecolor":  "#ffffff",
    "font.family":      "monospace",
}
plt.rcParams.update(STYLE)

ACCENT = ["#e94560", "#0f3460", "#533483", "#e94560", "#06b6d4",
          "#f59e0b", "#10b981", "#8b5cf6", "#f97316", "#ec4899"]

# ─────────────────────────────────────────────────────────────
# Q1 — Average combo damage by opening move (Sheik + Falcon)
# ─────────────────────────────────────────────────────────────
print("Q1: Combo damage by opening move...")

combos_s = analyze_combos(ROOT, pg, TAG, character="Sheik")
combos_f = analyze_combos(ROOT, pg, TAG, character="Captain Falcon")

fig, axes = plt.subplots(1, 2, figsize=(14, 5))
fig.suptitle("Q1 — Average Combo Damage by Opening Move", fontsize=13, fontweight="bold", y=1.01)

for ax, combos, char, color in zip(
    axes, [combos_s, combos_f], ["Sheik", "Falcon"], [ACCENT[0], ACCENT[4]]
):
    if len(combos) == 0:
        ax.set_title(f"{char} (no data)")
        continue
    grp = (
        combos.groupby("started_by")["damage"]
        .agg(["mean", "count", "median"])
        .rename(columns={"mean": "avg", "count": "n", "median": "med"})
        .query("n >= 5")
        .sort_values("avg", ascending=True)
        .tail(15)
    )
    bars = ax.barh(grp.index, grp["avg"], color=color, alpha=0.85)
    ax.barh(grp.index, grp["med"], color=color, alpha=0.35, label="median")
    for i, (_, row) in enumerate(grp.iterrows()):
        ax.text(row["avg"] + 0.5, i, f'{row["avg"]:.0f}% (n={row["n"]})',
                va="center", fontsize=8)
    ax.set_title(char, fontsize=11, fontweight="bold")
    ax.set_xlabel("Damage (%)")
    ax.set_xlim(0, grp["avg"].max() * 1.35)
    ax.grid(axis="x")
    ax.legend(fontsize=8)

fig.tight_layout()
fig.savefig(f"{OUT}/q1_combo_damage_by_opener.png", dpi=130, bbox_inches="tight")
plt.close()
print("  saved q1")

# ─────────────────────────────────────────────────────────────
# Q2 — At what % do I actually kill? Distribution by move
# ─────────────────────────────────────────────────────────────
print("Q2: Kill percent distribution...")

kills_df = analyze_kills(ROOT, pg, TAG).dropna(subset=["death_percent", "killing_move"])

fig, axes = plt.subplots(1, 2, figsize=(14, 5))
fig.suptitle("Q2 — Kill Percent Distribution by Move (my kills)", fontsize=13, fontweight="bold")

for ax, char in zip(axes, ["Sheik", "Captain Falcon"]):
    sub = kills_df[kills_df.character == char]
    if len(sub) == 0:
        ax.set_title(f"{char} (no data)")
        continue
    top_moves = sub["killing_move"].value_counts().head(6).index
    sub = sub[sub["killing_move"].isin(top_moves)]

    for i, move in enumerate(top_moves):
        pcts = sub[sub.killing_move == move]["death_percent"].dropna()
        if len(pcts) < 3:
            continue
        ax.scatter(pcts, [move] * len(pcts), alpha=0.5, s=25, color=ACCENT[i])
        ax.axvline(pcts.median(), color=ACCENT[i], lw=0.8, alpha=0.5)
        ax.text(pcts.median() + 1, i, f'{pcts.median():.0f}%', va="center", fontsize=8, color=ACCENT[i])

    ax.set_title(f"{char} ({len(sub)} kills)", fontsize=11, fontweight="bold")
    ax.set_xlabel("Opponent % when killed")
    ax.grid(axis="x")

fig.tight_layout()
fig.savefig(f"{OUT}/q2_kill_percent_by_move.png", dpi=130, bbox_inches="tight")
plt.close()
print("  saved q2")

# ─────────────────────────────────────────────────────────────
# Q3 — Sweetspot / sourspot rate (Falcon Knee + moves w/ data)
# ─────────────────────────────────────────────────────────────
print("Q3: Sweetspot rates...")

hits_f = find_move_hits(ROOT, pg, TAG, character="Captain Falcon")

fig, ax = plt.subplots(figsize=(9, 5))
fig.suptitle("Q3 — Sweetspot vs Sourspot Rate (Captain Falcon)", fontsize=13, fontweight="bold")

if len(hits_f) > 0:
    # Only moves with hitbox data
    has_data = hits_f[hits_f.has_data]
    if len(has_data) > 0:
        grp = has_data.groupby(["move_name", "label"]).size().unstack(fill_value=0)
        grp_pct = grp.div(grp.sum(axis=1), axis=0) * 100
        grp_pct = grp_pct.loc[grp.sum(axis=1).sort_values(ascending=False).index]

        bottom = np.zeros(len(grp_pct))
        for i, col in enumerate(grp_pct.columns):
            bars = ax.bar(grp_pct.index, grp_pct[col], bottom=bottom,
                          label=col, color=ACCENT[i], alpha=0.85)
            for j, (val, b) in enumerate(zip(grp_pct[col], bottom)):
                if val > 5:
                    n = int(grp[col].iloc[j])
                    ax.text(j, b + val/2, f'{val:.0f}%\n(n={n})',
                            ha="center", va="center", fontsize=8)
            bottom += grp_pct[col].values

        ax.set_ylabel("% of hits")
        ax.set_ylim(0, 115)
        ax.legend(loc="upper right")
        ax.grid(axis="y")
    else:
        ax.text(0.5, 0.5, "No hits with classification data", transform=ax.transAxes, ha="center")

fig.tight_layout()
fig.savefig(f"{OUT}/q3_sweetspot_rates.png", dpi=130, bbox_inches="tight")
plt.close()
print("  saved q3")

# ─────────────────────────────────────────────────────────────
# Q4 — Neutral hit rate by move (Sheik + Falcon)
# ─────────────────────────────────────────────────────────────
print("Q4: Neutral hit rates...")

na_s = analyze_neutral_attacks(ROOT, pg, TAG, character="Sheik")
na_f = analyze_neutral_attacks(ROOT, pg, TAG, character="Captain Falcon")

fig, axes = plt.subplots(1, 2, figsize=(14, 6))
fig.suptitle("Q4 — Move Usage and Hit Rate in Neutral", fontsize=13, fontweight="bold")

for ax, na, char in zip(axes, [na_s, na_f], ["Sheik", "Captain Falcon"]):
    if len(na) == 0:
        ax.set_title(f"{char} (no data)")
        continue
    grp = na.groupby("move").agg(
        uses=("hit", "count"),
        hits=("hit", "sum"),
    )
    grp["hit_rate"] = grp["hits"] / grp["uses"] * 100
    grp = grp.sort_values("uses", ascending=True)

    bars = ax.barh(grp.index, grp["uses"], color="#334155", alpha=0.9, label="Uses")
    hit_bars = ax.barh(grp.index, grp["hits"], color=ACCENT[0], alpha=0.9, label="Hits")
    for i, (_, row) in enumerate(grp.iterrows()):
        ax.text(row["uses"] + 1, i, f'{row["hit_rate"]:.0f}% hit', va="center", fontsize=8)

    ax.set_title(f"{char}", fontsize=11, fontweight="bold")
    ax.set_xlabel("Count")
    ax.legend(fontsize=8)
    ax.grid(axis="x")

fig.tight_layout()
fig.savefig(f"{OUT}/q4_neutral_hit_rates.png", dpi=130, bbox_inches="tight")
plt.close()
print("  saved q4")

# ─────────────────────────────────────────────────────────────
# Q5 — What moves does the opponent land on ME most?
# ─────────────────────────────────────────────────────────────
print("Q5: Moves landed on me...")

opp_hits = pd.concat([
    analyze_hits_taken(ROOT, pg, TAG, character="Sheik"),
    analyze_hits_taken(ROOT, pg, TAG, character="Captain Falcon"),
], ignore_index=True).rename(columns={"character": "my_char", "opp_character": "opp_char", "my_pct": "my_pct_before"})

fig, axes = plt.subplots(1, 2, figsize=(14, 6))
fig.suptitle("Q5 — Moves Opponent Lands on Me (top 12)", fontsize=13, fontweight="bold")

for ax, char in zip(axes, ["Sheik", "Captain Falcon"]):
    sub = opp_hits[opp_hits.my_char == char]
    if len(sub) == 0:
        ax.set_title(f"vs {char} (no data)")
        continue
    grp = sub.groupby("move").agg(count=("damage", "count"), avg_dmg=("damage", "mean"))
    grp = grp.sort_values("count", ascending=True).tail(12)

    cmap = plt.cm.get_cmap("RdYlGn_r", len(grp))
    colors = [cmap(i / len(grp)) for i in range(len(grp))]
    bars = ax.barh(grp.index, grp["count"], color=colors, alpha=0.85)
    for i, (_, row) in enumerate(grp.iterrows()):
        ax.text(row["count"] + 0.3, i, f'avg {row["avg_dmg"]:.1f}%', va="center", fontsize=8)

    ax.set_title(f"Playing {char} ({len(sub)} hits taken)", fontsize=11, fontweight="bold")
    ax.set_xlabel("Times hit")
    ax.grid(axis="x")

fig.tight_layout()
fig.savefig(f"{OUT}/q5_moves_opponent_lands.png", dpi=130, bbox_inches="tight")
plt.close()
print("  saved q5")

# ─────────────────────────────────────────────────────────────
# Q6 — Neutral win value: combo damage distribution
# ─────────────────────────────────────────────────────────────
print("Q6: Neutral win damage distribution...")

all_combos = pd.concat([combos_s, combos_f], ignore_index=True) if (len(combos_s) + len(combos_f)) > 0 else pd.DataFrame()

fig, axes = plt.subplots(1, 2, figsize=(14, 5))
fig.suptitle("Q6 — Damage per Neutral Win (combo damage distribution)", fontsize=13, fontweight="bold")

for ax, char, combos, color in zip(
    axes, ["Sheik", "Captain Falcon"], [combos_s, combos_f], [ACCENT[0], ACCENT[4]]
):
    if len(combos) == 0:
        ax.set_title(f"{char} (no data)")
        continue
    dmg = combos["damage"].clip(upper=100)
    bins = list(range(0, 105, 5))
    ax.hist(dmg, bins=bins, color=color, alpha=0.85, edgecolor="#ffffff20")
    ax.axvline(dmg.mean(), color="white", lw=1.5, linestyle="--", label=f'Mean: {dmg.mean():.1f}%')
    ax.axvline(dmg.median(), color=ACCENT[5], lw=1.5, linestyle=":", label=f'Median: {dmg.median():.1f}%')

    kill_pct = combos["killed"].mean() * 100
    ax.set_title(f"{char}  (n={len(combos)}, {kill_pct:.0f}% kill combos)", fontsize=11, fontweight="bold")
    ax.set_xlabel("Combo damage (%)")
    ax.set_ylabel("Combos")
    ax.legend(fontsize=8)
    ax.grid(axis="y")

fig.tight_layout()
fig.savefig(f"{OUT}/q6_combo_damage_distribution.png", dpi=130, bbox_inches="tight")
plt.close()
print("  saved q6")

# ─────────────────────────────────────────────────────────────
# Q7 — Knockdown option distribution by percent bucket
# ─────────────────────────────────────────────────────────────
print("Q7: Knockdown options...")

kd_s = analyze_knockdowns(ROOT, pg, TAG, character="Sheik")
kd_f = analyze_knockdowns(ROOT, pg, TAG, character="Captain Falcon")

fig, axes = plt.subplots(1, 2, figsize=(14, 6))
fig.suptitle("Q7 — My Knockdown Options by % (predictability check)", fontsize=13, fontweight="bold")

for ax, kd, char in zip(axes, [kd_s, kd_f], ["Sheik", "Captain Falcon"]):
    if len(kd) == 0:
        ax.set_title(f"{char} (no data)")
        continue

    # Overall option distribution
    grp = kd["option"].value_counts(normalize=True) * 100
    colors_map = {
        "tech in place": ACCENT[6], "tech toward": ACCENT[4], "tech away": ACCENT[3],
        "getup": ACCENT[5], "getup attack": ACCENT[0], "roll toward": ACCENT[2],
        "roll away": ACCENT[1], "slideoff": "#888", "hit while down": "#444",
    }
    colors_list = [colors_map.get(o, "#999") for o in grp.index]
    bars = ax.bar(grp.index, grp.values, color=colors_list, alpha=0.85)
    for bar, val in zip(bars, grp.values):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5,
                f'{val:.0f}%', ha="center", fontsize=8)

    ax.set_title(f"{char} (n={len(kd)})", fontsize=11, fontweight="bold")
    ax.set_ylabel("% of knockdowns")
    ax.set_ylim(0, grp.max() * 1.2)
    ax.tick_params(axis="x", rotation=35)
    ax.grid(axis="y")

fig.tight_layout()
fig.savefig(f"{OUT}/q7_knockdown_options.png", dpi=130, bbox_inches="tight")
plt.close()
print("  saved q7")

# ─────────────────────────────────────────────────────────────
# Q8 — Where am I dying? Blastzone + position scatter
# ─────────────────────────────────────────────────────────────
print("Q8: Death positions...")

deaths_df = analyze_kills(ROOT, pg, TAG, as_attacker=False).dropna(subset=["death_x", "death_y"])

bz_colors = {"top": ACCENT[0], "left": ACCENT[4], "right": ACCENT[6], "bottom": ACCENT[5]}

fig, axes = plt.subplots(1, 2, figsize=(14, 6))
fig.suptitle("Q8 — My Deaths: Position & Blastzone", fontsize=13, fontweight="bold")

for ax, char in zip(axes, ["Sheik", "Captain Falcon"]):
    sub = deaths_df[deaths_df.character == char]
    if len(sub) == 0:
        ax.set_title(f"{char} (no data)")
        continue
    for bz, color in bz_colors.items():
        pts = sub[sub.blastzone == bz]
        if len(pts):
            ax.scatter(pts["death_x"], pts["death_y"], c=color, alpha=0.65, s=40,
                       label=f"{bz} ({len(pts)})", edgecolors="none")

    ax.axhline(0, color="#ffffff20", lw=0.5)
    ax.axvline(0, color="#ffffff20", lw=0.5)
    ax.set_title(f"{char} ({len(sub)} deaths)", fontsize=11, fontweight="bold")
    ax.set_xlabel("X position")
    ax.set_ylabel("Y position")
    ax.legend(fontsize=8, title="Blastzone")
    ax.grid()

fig.tight_layout()
fig.savefig(f"{OUT}/q8_death_positions.png", dpi=130, bbox_inches="tight")
plt.close()
print("  saved q8")

# ─────────────────────────────────────────────────────────────
# Q9 — D-throw → kill conversion (Sheik)
# ─────────────────────────────────────────────────────────────
print("Q9: D-throw kill conversion...")

# THROW_LW (state 222) = down throw; min_opp_pct filters to kill-% situations
KILL_PCT_THRESHOLD = 80   # only count as "kill opportunity" if opp is >= this %

q9_opp = find_confirmed_events(
    ROOT, pg, TAG, trigger={222}, outcome="kill",
    character="Sheik", min_opp_pct=KILL_PCT_THRESHOLD,
)

fig, axes = plt.subplots(1, 2, figsize=(14, 5))
fig.suptitle(f"Q9 — Sheik D-throw Kill Conversion (opp ≥ {KILL_PCT_THRESHOLD}%)", fontsize=13, fontweight="bold")

ax = axes[0]
if len(q9_opp) > 0:
    conv_rate = q9_opp["converted"].mean() * 100
    bars = ax.bar(["Converted", "Dropped"], [q9_opp["converted"].sum(), (~q9_opp["converted"]).sum()],
                  color=[ACCENT[6], ACCENT[0]], alpha=0.85)
    for bar in bars:
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.3,
                str(int(bar.get_height())), ha="center", fontsize=12, fontweight="bold")
    ax.set_title(f"Overall conversion: {conv_rate:.0f}%  (n={len(q9_opp)})", fontsize=11)
    ax.set_ylabel("Count")
    ax.grid(axis="y")
else:
    ax.text(0.5, 0.5, "No kill-% d-throws found", transform=ax.transAxes, ha="center")

ax = axes[1]
if len(q9_opp) > 0:
    bins = list(range(int(q9_opp["opp_pct_at_trigger"].min()) // 10 * 10, 160, 10))
    conv_pts = q9_opp[q9_opp.converted]["opp_pct_at_trigger"]
    miss_pts = q9_opp[~q9_opp.converted]["opp_pct_at_trigger"]
    ax.hist(conv_pts, bins=bins, color=ACCENT[6], alpha=0.7, label="Converted")
    ax.hist(miss_pts, bins=bins, color=ACCENT[0], alpha=0.7, label="Dropped")
    ax.set_xlabel("Opponent % at d-throw")
    ax.set_ylabel("Count")
    ax.set_title("Conversion by Opponent %")
    ax.legend(fontsize=9)
    ax.grid(axis="y")

fig.tight_layout()
fig.savefig(f"{OUT}/q9_dthrow_kill_conversion.png", dpi=130, bbox_inches="tight")
plt.close()
print("  saved q9")

# ─────────────────────────────────────────────────────────────
# Q10 — How do I die? (killing move + percent distribution)
# ─────────────────────────────────────────────────────────────
print("Q10: How do I die...")

fig, axes = plt.subplots(1, 2, figsize=(14, 6))
fig.suptitle("Q10 — How Do I Die? (killing move distribution)", fontsize=13, fontweight="bold")

for ax, char in zip(axes, ["Sheik", "Captain Falcon"]):
    sub = deaths_df[deaths_df.character == char].dropna(subset=["killing_move"])
    if len(sub) == 0:
        ax.set_title(f"{char} (no data)")
        continue
    grp = sub.groupby("killing_move").agg(
        count=("death_percent", "count"),
        avg_pct=("death_percent", "mean"),
    ).sort_values("count", ascending=True).tail(12)

    cmap = plt.cm.get_cmap("YlOrRd", len(grp))
    colors = [cmap(i / max(len(grp) - 1, 1)) for i in range(len(grp))]
    bars = ax.barh(grp.index, grp["count"], color=colors, alpha=0.9)
    for i, (_, row) in enumerate(grp.iterrows()):
        ax.text(row["count"] + 0.2, i, f'avg {row["avg_pct"]:.0f}%', va="center", fontsize=8)

    ax.set_title(f"Playing {char} ({len(sub)} deaths)", fontsize=11, fontweight="bold")
    ax.set_xlabel("Times killed by")
    ax.grid(axis="x")

fig.tight_layout()
fig.savefig(f"{OUT}/q10_how_i_die.png", dpi=130, bbox_inches="tight")
plt.close()
print("  saved q10")

print("\nDone. All figures saved to", OUT)
print("\nSummary stats:")
print(f"  Total combos (Sheik):  {len(combos_s)}")
print(f"  Total combos (Falcon): {len(combos_f)}")
print(f"  Falcon hits logged:    {len(hits_f)}")
print(f"  My deaths:             {len(deaths_df)}")
print(f"  Opp hits on me:        {len(opp_hits)}")
if len(q9_opp) > 0:
    print(f"  D-throw kill opps:     {len(q9_opp)}  ({q9_opp['converted'].mean()*100:.0f}% converted)")
