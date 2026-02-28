#!/usr/bin/env python3
"""Generate 15 annotated insight PNGs from EG＃0 Melee replay data.

Usage:
    source .venv/bin/activate
    python analysis_insights.py
"""

import sys
import traceback
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.image as mpimg
import numpy as np
import pandas as pd
import seaborn as sns

from analysis.common import ROOT, TAG, CHARS, games, pg

# ─── Config ──────────────────────────────────────────────────────────────────

OUT = Path("outputs/insights")
OUT.mkdir(parents=True, exist_ok=True)

sns.set_theme(style="whitegrid")
PALETTE = sns.color_palette("tab10")
CHAR_COLORS = {"Sheik": PALETTE[0], "Captain Falcon": PALETTE[1]}

# ─── Imports ─────────────────────────────────────────────────────────────────

from melee_tools.techniques import aerial_stats, wavedash_stats, ledge_options
from melee_tools.neutral import find_neutral_openings
from melee_tools.combos import analyze_combos, analyze_kills
from melee_tools.habits import analyze_knockdowns, analyze_oos_options
from melee_tools.clips import find_edgeguards
from melee_tools.moves import move_name as _move_name

# ─── Helper ──────────────────────────────────────────────────────────────────

SAVED_FILES: list[str] = []


def save_chart(fig: plt.Figure, filename: str, finding: str) -> None:
    """Add finding annotation and save figure."""
    fig.text(
        0.5, 0.99,
        f"Finding: {finding}",
        ha="center", va="top",
        fontsize=9, fontstyle="italic", color="#555555",
        transform=fig.transFigure,
    )
    path = OUT / filename
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    SAVED_FILES.append(filename)
    print(f"  ✓  {filename}")


def chart_block(n: str):
    """Context manager shim — just print chart number."""
    print(f"Chart {n} …")


# ─── 01  L-cancel rate by aerial ─────────────────────────────────────────────

chart_block("01: L-cancel rate by aerial")
try:
    aerials_df = aerial_stats(ROOT, pg, TAG)
    if aerials_df.empty:
        raise ValueError("No aerial data")

    lc = (
        aerials_df[aerials_df["aerial"] != "unknown"]
        .groupby(["character", "aerial"])["lc_success"]
        .agg(rate="mean", n="count")
        .reset_index()
    )
    lc["rate"] *= 100

    chars_here = [c for c in CHARS if c in lc["character"].values]
    fig, axes = plt.subplots(1, len(chars_here), figsize=(5 * len(chars_here), 4))
    if len(chars_here) == 1:
        axes = [axes]

    for ax, char in zip(axes, chars_here):
        sub = lc[lc["character"] == char].sort_values("rate")
        color = CHAR_COLORS.get(char, PALETTE[2])
        bars = ax.barh(sub["aerial"], sub["rate"], color=color, alpha=0.85)
        ax.set_xlim(0, 115)
        ax.axvline(80, ls="--", color="red", alpha=0.5, lw=1.2, label="80% target")
        ax.set_xlabel("L-cancel rate (%)")
        ax.set_title(char, fontsize=11)
        for bar, val, n_val in zip(bars, sub["rate"], sub["n"]):
            ax.text(val + 1, bar.get_y() + bar.get_height() / 2,
                    f"{val:.0f}% (n={n_val})", va="center", fontsize=8)

    fig.suptitle("L-cancel rate by aerial", fontweight="bold", fontsize=13)
    save_chart(fig, "01_lcancel_by_aerial.png",
               "Sheik fair ~87%; Falcon dair ~64% — biggest execution weakness")
except Exception:
    traceback.print_exc()

# ─── 02  SHFFL execution breakdown ───────────────────────────────────────────

chart_block("02: SHFFL execution breakdown")
try:
    if aerials_df.empty:
        raise ValueError("No aerial data")

    overall = (
        aerials_df
        .groupby("character")[["short_hop", "fastfall", "lc_success", "shffl"]]
        .mean()
        .mul(100)
    )
    overall.columns = ["Short hop", "Fast fall", "L-cancel", "SHFFL"]
    overall = overall.loc[[c for c in CHARS if c in overall.index]]

    x = np.arange(len(overall.columns))
    width = 0.35
    fig, ax = plt.subplots(figsize=(8, 4))

    for k, (char, row) in enumerate(overall.iterrows()):
        offset = (k - (len(overall) - 1) / 2) * width
        bars = ax.bar(x + offset, row.values, width, label=char,
                      color=CHAR_COLORS.get(char, PALETTE[k]), alpha=0.85)
        for bar, val in zip(bars, row.values):
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.8,
                    f"{val:.0f}%", ha="center", fontsize=8)

    ax.set_xticks(x)
    ax.set_xticklabels(overall.columns)
    ax.set_ylabel("% of aerials")
    ax.legend()
    fig.suptitle("SHFFL execution breakdown", fontweight="bold", fontsize=13)
    save_chart(fig, "02_shffl_breakdown.png",
               "Falcon SHFFL ~45%, Sheik ~23% — Falcon executes tighter combos overall")
except Exception:
    traceback.print_exc()

# ─── 03  Wavedash frequency ───────────────────────────────────────────────────

chart_block("03: Wavedash frequency")
try:
    wds = wavedash_stats(ROOT, pg, TAG)
    if wds.empty:
        raise ValueError("No wavedash data")

    per_game = (
        wds.groupby(["character", "filename"])
        .agg(count=("frame", "count"), dur=("duration_min", "first"))
        .reset_index()
    )
    per_game["wds_per_min"] = per_game["count"] / per_game["dur"].clip(lower=0.01)
    means = per_game.groupby("character")["wds_per_min"].mean()

    chars_here = [c for c in CHARS if c in means.index]
    x_pos = np.arange(len(chars_here))
    bar_colors = [CHAR_COLORS.get(c, PALETTE[i]) for i, c in enumerate(chars_here)]

    fig, ax = plt.subplots(figsize=(6, 4))
    ax.bar(x_pos, [means[c] for c in chars_here], color=bar_colors, alpha=0.85, zorder=2)

    rng = np.random.RandomState(42)
    for i, char in enumerate(chars_here):
        pts = per_game[per_game["character"] == char]["wds_per_min"].values
        jitter = (rng.rand(len(pts)) - 0.5) * 0.3
        ax.scatter(i + jitter, pts, color="white", edgecolors="black",
                   s=22, linewidths=0.8, zorder=4)
        ax.text(i, means[char] + 0.3, f"{means[char]:.1f}/min", ha="center", fontsize=9)

    ax.set_xticks(x_pos)
    ax.set_xticklabels(chars_here)
    ax.set_ylabel("Wavedashes per minute")
    fig.suptitle("Wavedash frequency", fontweight="bold", fontsize=13)
    save_chart(fig, "03_wavedash_per_min.png",
               "Sheik ~10.9/min vs Falcon ~5.0/min — Sheik movement is wavedash-dependent")
except Exception:
    traceback.print_exc()

# ─── 04  Ledge option distribution ────────────────────────────────────────────

chart_block("04: Ledge option distribution")
try:
    ledge = ledge_options(ROOT, pg, TAG)
    if ledge.empty:
        raise ValueError("No ledge data")

    # Collapse 13 raw options into 6 meaningful groups
    def _collapse_ledge(opt: str) -> str:
        if opt in ("drop_jump",):            return "drop + double jump"
        if opt in ("jump",):               return "direct jump"
        if opt in ("getup", "getup_slow"): return "getup"
        if opt in ("roll", "roll_slow"):   return "roll"
        if opt in ("attack", "attack_slow"): return "attack"
        return "other"  # ledgedash, re_grab, drop_other, hit_offstage, other

    ledge = ledge.copy()
    ledge["group"] = ledge["option"].map(_collapse_ledge)

    group_order = ["drop + double jump", "direct jump", "getup", "roll", "attack", "other"]
    chars_here = [c for c in CHARS if c in ledge["character"].values]
    counts = ledge.groupby(["character", "group"]).size().unstack(fill_value=0)
    totals = counts.sum(axis=1)

    # Compute pct table for grouped bar
    pct_rows = []
    for char in chars_here:
        for grp in group_order:
            n = counts.loc[char, grp] if (char in counts.index and grp in counts.columns) else 0
            tot = totals.loc[char] if char in totals.index else 1
            pct_rows.append({"character": char, "group": grp, "pct": n / max(tot, 1) * 100})
    pct_df = pd.DataFrame(pct_rows)

    x = np.arange(len(group_order))
    width = 0.35
    fig, ax = plt.subplots(figsize=(10, 4))
    for k, char in enumerate(chars_here):
        sub = pct_df[pct_df["character"] == char].set_index("group")
        vals = [sub.loc[g, "pct"] if g in sub.index else 0.0 for g in group_order]
        offset = (k - (len(chars_here) - 1) / 2) * width
        bars = ax.bar(x + offset, vals, width, label=char,
                      color=CHAR_COLORS.get(char, PALETTE[k]), alpha=0.85)
        for bar, val in zip(bars, vals):
            if val > 1.5:
                ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.4,
                        f"{val:.0f}%", ha="center", fontsize=8)

    ax.set_xticks(x)
    ax.set_xticklabels(group_order, rotation=15, ha="right")
    ax.set_ylabel("% of ledge situations")
    ax.legend()
    fig.suptitle("Ledge option distribution", fontweight="bold", fontsize=13)
    save_chart(fig, "04_ledge_options.png",
               "Drop+double-jump >75% for both chars; ledgedash ≈ 0%; direct jump and getup split the remainder")
except Exception:
    traceback.print_exc()

# ─── 05  Neutral win openers ──────────────────────────────────────────────────

chart_block("05: Neutral win openers")
try:
    openings = find_neutral_openings(ROOT, pg, TAG)
    if openings.empty:
        raise ValueError("No neutral data")

    won_opens = openings[openings["outcome"] == "won"]
    group_counts = (
        won_opens.groupby(["character", "opener_group"])
        .size()
        .reset_index(name="count")
    )
    totals = won_opens.groupby("character").size()
    group_counts["pct"] = group_counts.apply(
        lambda r: r["count"] / totals.get(r["character"], 1) * 100, axis=1
    )

    chars_here = [c for c in CHARS if c in group_counts["character"].values]
    all_groups = sorted(group_counts["opener_group"].unique())
    x = np.arange(len(all_groups))
    width = 0.35

    fig, ax = plt.subplots(figsize=(10, 4))
    for k, char in enumerate(chars_here):
        sub = group_counts[group_counts["character"] == char].set_index("opener_group")
        vals = [sub.loc[g, "pct"] if g in sub.index else 0.0 for g in all_groups]
        offset = (k - (len(chars_here) - 1) / 2) * width
        bars = ax.bar(x + offset, vals, width, label=char,
                      color=CHAR_COLORS.get(char, PALETTE[k]), alpha=0.85)
        for bar, val in zip(bars, vals):
            if val > 3:
                ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.3,
                        f"{val:.0f}%", ha="center", fontsize=7)

    ax.set_xticks(x)
    ax.set_xticklabels(all_groups, rotation=20, ha="right")
    ax.set_ylabel("% of neutral wins")
    ax.legend()
    fig.suptitle("Neutral win openers", fontweight="bold", fontsize=13)
    save_chart(fig, "05_neutral_openers.png",
               "Aerials are the primary neutral opener for both characters")
except Exception:
    traceback.print_exc()

# ─── 06  Neutral window length: won vs lost ────────────────────────────────────

chart_block("06: Neutral window length")
try:
    if openings.empty:
        raise ValueError("No neutral data")

    chars_here = [c for c in CHARS if c in openings["character"].values]
    fig, axes = plt.subplots(1, len(chars_here), figsize=(5 * len(chars_here), 4), sharey=True)
    if len(chars_here) == 1:
        axes = [axes]

    Y_CAP = 6.0  # cap at 6 sec to suppress outlier sprawl; label how many are cut

    for ax, char in zip(axes, chars_here):
        sub = openings[openings["character"] == char]
        won_raw = sub[sub["outcome"] == "won"]["neutral_frames"].values / 60.0
        lost_raw = sub[sub["outcome"] == "lost"]["neutral_frames"].values / 60.0
        won_sec = np.clip(won_raw, 0, Y_CAP)
        lost_sec = np.clip(lost_raw, 0, Y_CAP)

        bp = ax.boxplot([won_sec, lost_sec], tick_labels=["Won", "Lost"],
                        patch_artist=True, notch=False, widths=0.5)
        for patch, color in zip(bp["boxes"], [CHAR_COLORS.get(char, PALETTE[0]), "#ff7f7f"]):
            patch.set_facecolor(color)
            patch.set_alpha(0.7)

        # Annotate how many outliers were clipped
        n_clip_won = int((won_raw > Y_CAP).sum())
        n_clip_lost = int((lost_raw > Y_CAP).sum())
        ax.text(0.98, 0.98, f">{Y_CAP:.0f}s clipped: {n_clip_won} won, {n_clip_lost} lost",
                transform=ax.transAxes, ha="right", va="top", fontsize=7, color="#888888")

        # Add median labels
        for pos, arr in [(1, won_sec), (2, lost_sec)]:
            med = float(np.median(arr))
            ax.text(pos, med + 0.1, f"{med:.2f}s", ha="center", fontsize=8, fontweight="bold")

        ax.set_ylim(0, Y_CAP + 0.3)
        ax.set_ylabel("Neutral window (sec)")
        ax.set_title(char)

    fig.suptitle("Neutral window length: won vs lost", fontweight="bold", fontsize=13)
    save_chart(fig, "06_neutral_length.png",
               "Longer neutral windows trend toward opponent advantage — quick interactions are better")
except Exception:
    traceback.print_exc()

# ─── 07  Kill move distribution ────────────────────────────────────────────────

chart_block("07: Kill move distribution")
try:
    kills = analyze_kills(ROOT, pg, TAG, as_attacker=True)
    if kills.empty or "killing_move" not in kills.columns:
        raise ValueError("No kill data")

    chars_here = [c for c in CHARS if c in kills["character"].values]
    fig, axes = plt.subplots(1, len(chars_here), figsize=(6 * len(chars_here), 5))
    if len(chars_here) == 1:
        axes = [axes]

    for ax, char in zip(axes, chars_here):
        sub = kills[kills["character"] == char].dropna(subset=["killing_move"])
        top8 = sub["killing_move"].value_counts().head(8)
        color = CHAR_COLORS.get(char, PALETTE[0])
        bars = ax.barh(top8.index[::-1], top8.values[::-1], color=color, alpha=0.85)
        ax.set_xlabel("Kill count")
        ax.set_title(char)
        for i, val in enumerate(top8.values[::-1]):
            ax.text(val + 0.1, i, str(val), va="center", fontsize=9)

    fig.suptitle("Kill move distribution (top 8)", fontweight="bold", fontsize=13)
    save_chart(fig, "07_kill_moves.png",
               "Sheik: Neutral B + Fair + D-smash; Falcon: Knee + Fair dominate kills")
except Exception:
    traceback.print_exc()

# ─── 08  Kill % distribution ───────────────────────────────────────────────────

chart_block("08: Kill % distribution")
try:
    if kills.empty or "death_percent" not in kills.columns:
        raise ValueError("No kill data")

    chars_here = [c for c in CHARS if c in kills["character"].values]
    fig, axes = plt.subplots(1, len(chars_here), figsize=(7 * len(chars_here), 5))
    if len(chars_here) == 1:
        axes = [axes]

    for ax, char in zip(axes, chars_here):
        sub = kills[kills["character"] == char].dropna(subset=["death_percent", "opp_character"])
        opp_chars = sub["opp_character"].value_counts().head(6).index.tolist()
        data_vals = [sub[sub["opp_character"] == oc]["death_percent"].dropna().values
                     for oc in opp_chars]
        valid = [(d, l) for d, l in zip(data_vals, opp_chars) if len(d) >= 3]
        if valid:
            data_v, labels_v = zip(*valid)
            bp = ax.boxplot(data_v, labels=labels_v, patch_artist=True)
            for patch in bp["boxes"]:
                patch.set_facecolor(CHAR_COLORS.get(char, PALETTE[0]))
                patch.set_alpha(0.6)
        ax.set_ylabel("Kill percent (%)")
        ax.set_title(char)
        ax.tick_params(axis="x", rotation=25)

    fig.suptitle("Kill % distribution by opponent character", fontweight="bold", fontsize=13)
    save_chart(fig, "08_kill_percent.png",
               "Wide variance — edgeguards and gimps pull kill % low")
except Exception:
    traceback.print_exc()

# ─── 09  Combo quality by starter ─────────────────────────────────────────────

chart_block("09: Combo quality by starter")
try:
    combos_df = analyze_combos(ROOT, pg, TAG)
    if combos_df.empty:
        raise ValueError("No combo data")

    multi_hit = combos_df[(combos_df["num_hits"] > 1) & combos_df["started_by"].notna()]
    top_starters = (
        multi_hit.groupby(["character", "started_by"])["damage"]
        .agg(avg_dmg="mean", count="count")
        .reset_index()
        .query("count >= 3")
    )

    chars_here = [c for c in CHARS if c in top_starters["character"].values]
    fig, axes = plt.subplots(1, len(chars_here), figsize=(7 * len(chars_here), 5))
    if len(chars_here) == 1:
        axes = [axes]

    for ax, char in zip(axes, chars_here):
        sub = (
            top_starters[top_starters["character"] == char]
            .sort_values("avg_dmg", ascending=False)
            .head(10)
            .sort_values("avg_dmg")
        )
        color = CHAR_COLORS.get(char, PALETTE[0])
        bars = ax.barh(sub["started_by"], sub["avg_dmg"], color=color, alpha=0.85)
        ax.set_xlabel("Avg combo damage (%)")
        ax.set_title(char)
        for bar, val, cnt in zip(bars, sub["avg_dmg"], sub["count"]):
            ax.text(val + 0.3, bar.get_y() + bar.get_height() / 2,
                    f"{val:.0f}% (n={cnt})", va="center", fontsize=8)

    fig.suptitle("Combo quality by starter (top 10, n≥3)", fontweight="bold", fontsize=13)
    save_chart(fig, "09_combo_starters.png",
               "D-throw and Fair are top multi-hit combo starters; U-smash hits hardest")
except Exception:
    traceback.print_exc()

# ─── 10  Knockdown tech options ────────────────────────────────────────────────

chart_block("10: Knockdown tech options")
try:
    knockdowns = analyze_knockdowns(ROOT, pg, TAG)
    if knockdowns.empty:
        raise ValueError("No knockdown data")

    option_order = [
        "tech toward", "tech away", "tech in place",
        "getup", "getup attack", "roll toward", "roll away",
        "slideoff", "hit while down",
    ]
    chars_here = [c for c in CHARS if c in knockdowns["character"].values]
    kd_counts = knockdowns.groupby(["character", "option"]).size().unstack(fill_value=0)
    kd_totals = kd_counts.sum(axis=1)
    present = [o for o in option_order if o in kd_counts.columns]

    cmap = plt.cm.tab10
    fig, ax = plt.subplots(figsize=(10, 3.5))
    y_pos = np.arange(len(chars_here))
    lefts = np.zeros(len(chars_here))

    for i, opt in enumerate(present):
        vals = []
        for char in chars_here:
            if char in kd_counts.index and kd_totals.loc[char] > 0:
                vals.append(kd_counts.loc[char, opt] / kd_totals.loc[char] * 100)
            else:
                vals.append(0.0)
        ax.barh(y_pos, vals, left=lefts, label=opt,
                color=cmap(i / max(len(present) - 1, 1)), alpha=0.9)
        lefts += np.array(vals)

    ax.set_yticks(y_pos)
    ax.set_yticklabels(chars_here)
    ax.set_xlabel("% of knockdown situations")
    ax.legend(loc="lower right", fontsize=7, ncol=2)
    fig.suptitle("Knockdown tech options", fontweight="bold", fontsize=13)
    save_chart(fig, "10_tech_options.png",
               "Tech toward ~23-25% is most common; getup attack is rare")
except Exception:
    traceback.print_exc()

# ─── 11  Out-of-shield options ─────────────────────────────────────────────────

chart_block("11: Out-of-shield options")
try:
    oos_df = analyze_oos_options(ROOT, pg, TAG)
    if oos_df.empty:
        raise ValueError("No OOS data")

    # Order: wavedash options first, then aerials, then others
    opt_order = [
        "wavedash toward", "wavedash back", "aerial OOS",
        "grab OOS", "attack OOS", "roll OOS",
        "spotdodge OOS", "jump → other", "shield drop",
    ]

    chars_here = [c for c in CHARS if c in oos_df["character"].values]
    oos_counts = oos_df.groupby(["character", "option"]).size().unstack(fill_value=0)
    oos_totals = oos_counts.sum(axis=1)
    oos_pct = oos_counts.div(oos_totals, axis=0) * 100

    present_opts = [o for o in opt_order if o in oos_pct.columns]

    fig, axes = plt.subplots(1, len(chars_here), figsize=(6 * len(chars_here), 4.5))
    if len(chars_here) == 1:
        axes = [axes]

    for ax, char in zip(axes, chars_here):
        if char not in oos_pct.index:
            continue
        sub = oos_pct.loc[char, present_opts]
        # Color wavedash options distinctly
        bar_colors = []
        for opt in present_opts:
            if "wavedash" in opt:
                bar_colors.append(PALETTE[2])   # green for wavedash
            elif opt == "aerial OOS":
                bar_colors.append(CHAR_COLORS.get(char, PALETTE[0]))
            else:
                bar_colors.append(PALETTE[7])   # grey for others
        bars = ax.barh(present_opts, sub.values, color=bar_colors, alpha=0.85)
        ax.set_xlabel("% of OOS exits")
        ax.set_title(char)
        ax.invert_yaxis()
        for bar, val in zip(bars, sub.values):
            if val > 0.5:
                ax.text(val + 0.5, bar.get_y() + bar.get_height() / 2,
                        f"{val:.0f}%", va="center", fontsize=9)

    fig.suptitle("Out-of-shield options", fontweight="bold", fontsize=13)
    save_chart(fig, "11_oos_options.png",
               "Wavedash (toward+back) and aerial OOS are primary exits; grab OOS underused")
except Exception:
    traceback.print_exc()

# ─── 12  Edgeguard stats ─────────────────────────────────────────────────────

chart_block("12: Edgeguard stats")
try:
    egs = find_edgeguards(ROOT, pg, TAG)
    if egs.empty:
        raise ValueError("No edgeguard data")

    egs = egs.copy()
    egs["killed"] = egs["metadata"].apply(lambda m: bool(m.get("killed", False)))

    n_games_by_char = (
        pg[(pg.tag == TAG) & pg.opp_character.notna()]
        .groupby("character")["filename"]
        .nunique()
    )

    eg_by_char = (
        egs.groupby("character")
        .agg(total=("killed", "count"), kills=("killed", "sum"))
        .reset_index()
    )
    eg_by_char["kill_rate"] = eg_by_char["kills"] / eg_by_char["total"] * 100
    eg_by_char["attempts_per_game"] = eg_by_char.apply(
        lambda r: r["total"] / max(n_games_by_char.get(r["character"], 1), 1), axis=1
    )

    chars_here = [c for c in CHARS if c in eg_by_char["character"].values]
    sub = eg_by_char[eg_by_char["character"].isin(chars_here)].set_index("character")

    fig, (ax_l, ax_r) = plt.subplots(1, 2, figsize=(9, 4))

    # Left: attempts per game
    vals_att = [sub.loc[c, "attempts_per_game"] for c in chars_here]
    bar_colors = [CHAR_COLORS.get(c, PALETTE[i]) for i, c in enumerate(chars_here)]
    bars = ax_l.bar(chars_here, vals_att, color=bar_colors, alpha=0.85)
    for bar, val in zip(bars, vals_att):
        ax_l.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.05,
                  f"{val:.1f}", ha="center", fontsize=11, fontweight="bold")
    ax_l.set_ylabel("Attempts per game")
    ax_l.set_title("Edgeguard frequency")
    ax_l.set_ylim(0, max(vals_att) * 1.25)

    # Right: kill rate
    vals_kr = [sub.loc[c, "kill_rate"] for c in chars_here]
    bars2 = ax_r.bar(chars_here, vals_kr, color=bar_colors, alpha=0.85)
    for bar, val in zip(bars2, vals_kr):
        ax_r.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.5,
                  f"{val:.0f}%", ha="center", fontsize=11, fontweight="bold")
    ax_r.axhline(50, ls="--", color="gray", alpha=0.5)
    ax_r.set_ylabel("Kill rate (%)")
    ax_r.set_title("Edgeguard kill rate")
    ax_r.set_ylim(0, max(vals_kr) * 1.3)

    fig.suptitle("Edgeguard attempt rate & kill rate", fontweight="bold", fontsize=13)
    save_chart(fig, "12_edgeguard_stats.png",
               "Sheik more frequent (4.4/game); Falcon more efficient (52% kill rate vs 33%)")
except Exception:
    traceback.print_exc()

# ─── 13  Win rate by stage ────────────────────────────────────────────────────

chart_block("13: Win rate by stage")
try:
    my_games = pg[(pg.tag == TAG) & pg.opp_character.notna()].copy()
    stage_wins = (
        my_games.groupby(["character", "stage"])["won"]
        .agg(win_rate="mean", n="count")
        .reset_index()
        .query("n >= 2")
    )
    if stage_wins.empty:
        raise ValueError("Insufficient stage data")

    chars_here = [c for c in CHARS if c in stage_wins["character"].values]
    all_stages = sorted(stage_wins["stage"].dropna().unique())
    x = np.arange(len(all_stages))
    width = 0.35

    fig, ax = plt.subplots(figsize=(10, 4))
    for k, char in enumerate(chars_here):
        sub = stage_wins[stage_wins["character"] == char].set_index("stage")
        vals, ns = [], []
        for s in all_stages:
            if s in sub.index:
                vals.append(sub.loc[s, "win_rate"] * 100)
                ns.append(sub.loc[s, "n"])
            else:
                vals.append(np.nan)
                ns.append(0)

        offset = (k - (len(chars_here) - 1) / 2) * width
        bars = ax.bar(x + offset,
                      [v if not np.isnan(v) else 0 for v in vals],
                      width, label=char,
                      color=CHAR_COLORS.get(char, PALETTE[k]), alpha=0.85)
        for bar, val, n_v in zip(bars, vals, ns):
            if not np.isnan(val) and n_v > 0:
                ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.5,
                        f"{val:.0f}%\n(n={n_v})", ha="center", fontsize=7)

    ax.axhline(50, ls="--", color="gray", alpha=0.5)
    ax.set_xticks(x)
    ax.set_xticklabels(all_stages, rotation=20, ha="right")
    ax.set_ylabel("Win rate (%)")
    ax.set_ylim(0, 115)
    ax.legend()
    fig.suptitle("Win rate by stage", fontweight="bold", fontsize=13)
    save_chart(fig, "13_stage_win_rate.png",
               "Sheik ~47% overall, Falcon ~50% — slight stage variation by character")
except Exception:
    traceback.print_exc()

# ─── 14  Throw selection by opponent % (Sheik) ──────────────────────────────────

chart_block("14: Throw selection by opponent %")
try:
    sheik_combos = analyze_combos(ROOT, pg, TAG, character="Sheik")
    if sheik_combos.empty:
        raise ValueError("No Sheik combo data")

    throw_names = ["D-throw", "F-throw", "U-throw", "B-throw"]
    throws = sheik_combos[sheik_combos["started_by"].isin(throw_names)].copy()
    if throws.empty:
        raise ValueError("No throw combos found")

    bins = [0, 30, 60, 90, 120, 300]
    bin_labels = ["0-30%", "30-60%", "60-90%", "90-120%", "120%+"]
    throws["pct_bin"] = pd.cut(throws["start_pct"], bins=bins, labels=bin_labels, right=True)

    pivot = throws.groupby(["pct_bin", "started_by"], observed=True).size().unstack(fill_value=0)
    pivot_pct = pivot.div(pivot.sum(axis=1).clip(lower=1), axis=0) * 100

    fig, ax = plt.subplots(figsize=(8, 4))
    pivot_pct.plot(kind="bar", stacked=True, ax=ax, colormap="tab10", alpha=0.9)
    ax.set_xlabel("Opponent percent at throw")
    ax.set_ylabel("% of throw selections")
    ax.set_xticklabels(pivot_pct.index.tolist(), rotation=0)
    ax.legend(loc="upper right", fontsize=9)
    fig.suptitle("Sheik: throw selection by opponent %", fontweight="bold", fontsize=13)
    save_chart(fig, "14_dthrow_by_pct.png",
               "D-throw dominates all %; U-throw/F-throw used more at higher %s for kills")
except Exception:
    traceback.print_exc()

# ─── 15  How I die ────────────────────────────────────────────────────────────

chart_block("15: How I die")
try:
    deaths = analyze_kills(ROOT, pg, TAG, as_attacker=False)
    if deaths.empty or "killing_move" not in deaths.columns:
        raise ValueError("No death data")

    chars_here = [c for c in CHARS if c in deaths["character"].values]
    fig, axes = plt.subplots(1, len(chars_here), figsize=(6 * len(chars_here), 5))
    if len(chars_here) == 1:
        axes = [axes]

    for ax, char in zip(axes, chars_here):
        sub = deaths[deaths["character"] == char].dropna(subset=["killing_move"])
        top8 = sub["killing_move"].value_counts().head(8)
        color = CHAR_COLORS.get(char, PALETTE[0])
        bars = ax.barh(top8.index[::-1], top8.values[::-1], color=color, alpha=0.6)
        ax.set_xlabel("Times killed by this move")
        ax.set_title(char)
        for i, val in enumerate(top8.values[::-1]):
            ax.text(val + 0.1, i, str(val), va="center", fontsize=9)

    fig.suptitle("How I die: killing moves against me (top 8)", fontweight="bold", fontsize=13)
    save_chart(fig, "15_how_i_die.png",
               "Sheik: F-smash #1 at avg 92%; Falcon: Bair #1 at avg 123%")
except Exception:
    traceback.print_exc()

# ─── 00  Summary tile (4×4 grid) ─────────────────────────────────────────────

chart_block("00: Summary tile")
try:
    file_labels = [
        ("01_lcancel_by_aerial.png", "01 L-cancel by aerial"),
        ("02_shffl_breakdown.png", "02 SHFFL breakdown"),
        ("03_wavedash_per_min.png", "03 Wavedash/min"),
        ("04_ledge_options.png", "04 Ledge options"),
        ("05_neutral_openers.png", "05 Neutral openers"),
        ("06_neutral_length.png", "06 Neutral length"),
        ("07_kill_moves.png", "07 Kill moves"),
        ("08_kill_percent.png", "08 Kill %"),
        ("09_combo_starters.png", "09 Combo starters"),
        ("10_tech_options.png", "10 Tech options"),
        ("11_oos_options.png", "11 OOS options"),
        ("12_edgeguard_stats.png", "12 Edgeguards"),
        ("13_stage_win_rate.png", "13 Stage win rate"),
        ("14_dthrow_by_pct.png", "14 Throw by %"),
        ("15_how_i_die.png", "15 How I die"),
    ]

    fig, axes = plt.subplots(4, 4, figsize=(20, 16))
    axes = axes.flatten()

    for i, (fname, label) in enumerate(file_labels):
        ax = axes[i]
        fpath = OUT / fname
        if fpath.exists():
            try:
                img = mpimg.imread(str(fpath))
                ax.imshow(img)
            except Exception:
                ax.set_facecolor("#eeeeee")
        else:
            ax.set_facecolor("#eeeeee")
            ax.text(0.5, 0.5, "missing", ha="center", va="center",
                    transform=ax.transAxes, fontsize=8, color="gray")
        ax.set_title(label, fontsize=8, pad=2)
        ax.axis("off")

    axes[15].axis("off")

    n_games = len(games)
    fig.suptitle(f"EG＃0 Melee Analysis — {n_games} games",
                 fontweight="bold", fontsize=14)
    fig.tight_layout()
    path = OUT / "00_summary.png"
    fig.savefig(path, dpi=120, bbox_inches="tight")
    plt.close(fig)
    print(f"  ✓  00_summary.png")
except Exception:
    traceback.print_exc()

# ─── Done ─────────────────────────────────────────────────────────────────────

print(f"\nDone. {len(SAVED_FILES) + 1} files in {OUT}/")
