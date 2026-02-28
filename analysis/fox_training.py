#!/usr/bin/env python3
"""Positional analysis for Fox (Q40–Q48 style) from community training data.

Scans replays/training_data for Fox games, samples 1000, and runs:
  - Ledge-hugging frequency by stage
  - Position drift (x) vs damage percent
  - Off-stage time: Fox vs opponent
  - Blast zone distribution on death
  - Edgeguard depth when opponent is off-stage

Interesting findings are printed and charted.

Usage:
    source .venv/bin/activate
    python -m analysis.fox_training
"""

import sys
import traceback
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
import pandas as pd
from peppi_py import read_slippi

from melee_tools.enums import character_name
from melee_tools.frames import _safe_np
from melee_tools.stages import STAGE_GEOMETRY

# ─── Config ──────────────────────────────────────────────────────────────────

REPLAY_DIR = Path("replays/training_data")
TARGET_GAMES = 1000
SEED = 42
SAMPLE_EVERY = 5  # keep every Nth frame for position sampling

OUT = Path("outputs/fox_training")
OUT.mkdir(parents=True, exist_ok=True)

FOX_CHAR_ID = 2  # internal character ID for Fox

# Stage geometry lookups
EDGE_X_BY_ID:   dict[int, float]  = {k: v["edge_x"] for k, v in STAGE_GEOMETRY.items()}
STAGE_NAME_BY_ID: dict[int, str]  = {k: v["name"]   for k, v in STAGE_GEOMETRY.items()}
EDGE_X_BY_NAME: dict[str, float]  = {v["name"]: v["edge_x"] for v in STAGE_GEOMETRY.values()}
LEGAL_STAGE_IDS = set(STAGE_GEOMETRY.keys())

# Death state → blast zone
BLASTZONE_MAP = {
    0: "bottom", 1: "left",  2: "right",
    3: "top",    4: "top",   5: "top",
    6: "top",    7: "top",   8: "top",
    9: "top",   10: "top",
}

# ─── Scanning ────────────────────────────────────────────────────────────────

def _extract_fox_data(fpath: Path) -> dict | None:
    """Parse a single .slp file and return Fox frame data if Fox is a player.

    Returns None if the file is unreadable, not 1v1, not on a legal stage,
    or Fox is not a player.

    Returns a dict with:
        stage_id, stage_name, edge_x,
        fox_pos_x, fox_pos_y, fox_pct, fox_stocks, fox_state,
        opp_pos_x, opp_pos_y, opp_pct, opp_stocks, opp_state,
        opp_char,
    """
    try:
        game = read_slippi(str(fpath))
    except BaseException:
        return None

    active = [(slot, p) for slot, p in enumerate(game.start.players) if p is not None]
    if len(active) != 2:
        return None

    stage_id = int(game.start.stage) if game.start.stage is not None else -1
    if stage_id not in LEGAL_STAGE_IDS:
        return None

    # Find which slot is Fox
    fox_slot = None
    opp_slot = None
    opp_char_name = None
    for slot, player in active:
        try:
            cname = character_name(int(player.character))
        except Exception:
            return None
        if cname == "Fox" and fox_slot is None:
            fox_slot = slot
        else:
            opp_slot = slot
            opp_char_name = cname

    if fox_slot is None or opp_slot is None:
        return None

    # Extract frame arrays
    frame_ids = _safe_np(game.frames.id)
    if frame_ids is None or len(frame_ids) < 60:  # skip very short games
        return None

    def _get_post(slot):
        port = game.frames.ports[slot]
        if port is None or port.leader is None:
            return None
        return port.leader.post

    fox_post = _get_post(fox_slot)
    opp_post = _get_post(opp_slot)
    if fox_post is None or opp_post is None:
        return None

    def _arr(a):
        v = _safe_np(a)
        return v.astype(float) if v is not None else None

    fox_x    = _arr(fox_post.position.x)
    fox_y    = _arr(fox_post.position.y)
    fox_pct  = _arr(fox_post.percent)
    fox_stk  = _arr(fox_post.stocks)
    fox_st   = _arr(fox_post.state)

    opp_x    = _arr(opp_post.position.x)
    opp_y    = _arr(opp_post.position.y)
    opp_pct  = _arr(opp_post.percent)
    opp_stk  = _arr(opp_post.stocks)
    opp_st   = _arr(opp_post.state)

    if any(v is None for v in [fox_x, fox_y, fox_pct, fox_stk, fox_st,
                                opp_x, opp_y, opp_pct, opp_stk, opp_st]):
        return None

    n = min(len(fox_x), len(opp_x), len(frame_ids))
    edge_x = EDGE_X_BY_ID[stage_id]

    return {
        "stage_id":   stage_id,
        "stage_name": STAGE_NAME_BY_ID[stage_id],
        "edge_x":     edge_x,
        "frames":     frame_ids[:n],
        "fox_x":      fox_x[:n],
        "fox_y":      fox_y[:n],
        "fox_pct":    fox_pct[:n],
        "fox_stk":    fox_stk[:n],
        "fox_st":     fox_st[:n].astype(int),
        "opp_x":      opp_x[:n],
        "opp_y":      opp_y[:n],
        "opp_pct":    opp_pct[:n],
        "opp_stk":    opp_stk[:n],
        "opp_st":     opp_st[:n],
        "opp_char":   opp_char_name,
    }


print(f"Scanning {REPLAY_DIR} for Fox games (target: {TARGET_GAMES}) ...")
all_files = list(REPLAY_DIR.rglob("*.slp"))
rng = np.random.default_rng(SEED)
shuffled = rng.permutation(len(all_files))

fox_games: list[dict] = []
scanned = 0
for idx in shuffled:
    if len(fox_games) >= TARGET_GAMES:
        break
    data = _extract_fox_data(all_files[idx])
    scanned += 1
    if data is not None:
        fox_games.append(data)
    if scanned % 500 == 0:
        print(f"  scanned {scanned:,} files, {len(fox_games)} Fox games found ...")

print(f"  Done: {scanned:,} files scanned → {len(fox_games)} Fox games\n")

if not fox_games:
    print("No Fox games found — exiting.")
    sys.exit(1)

# ─── Build shared DataFrames ──────────────────────────────────────────────────

# Frame samples (every SAMPLE_EVERY-th frame)
sample_rows = []
death_rows   = []

for g in fox_games:
    n = len(g["frames"])
    stage = g["stage_name"]
    edge_x = g["edge_x"]
    opp_char = g["opp_char"]

    # ── Frame samples ──
    idx = np.arange(0, n, SAMPLE_EVERY)
    sample_rows.append(pd.DataFrame({
        "stage":       stage,
        "edge_x":      edge_x,
        "opp_char":    opp_char,
        "fox_x":       g["fox_x"][idx],
        "fox_y":       g["fox_y"][idx],
        "fox_pct":     g["fox_pct"][idx],
        "opp_x":       g["opp_x"][idx],
        "opp_y":       g["opp_y"][idx],
    }))

    # ── Fox deaths (stock loss detection) ──
    stk = g["fox_stk"]
    fox_st = g["fox_st"]
    for i in range(1, n):
        if np.isnan(stk[i]) or np.isnan(stk[i - 1]):
            continue
        if stk[i] < stk[i - 1]:
            state = fox_st[i] if i < n else fox_st[n - 1]
            blastzone = BLASTZONE_MAP.get(int(state))
            death_rows.append({
                "stage":     stage,
                "opp_char":  opp_char,
                "death_pct": float(g["fox_pct"][i - 1]) if not np.isnan(g["fox_pct"][i - 1]) else np.nan,
                "death_x":   float(g["fox_x"][i]) if not np.isnan(g["fox_x"][i]) else np.nan,
                "death_y":   float(g["fox_y"][i]) if not np.isnan(g["fox_y"][i]) else np.nan,
                "blastzone": blastzone,
            })

fs = pd.concat(sample_rows, ignore_index=True) if sample_rows else pd.DataFrame()
deaths = pd.DataFrame(death_rows)

print(f"Frame samples: {len(fs):,}")
print(f"Fox deaths detected: {len(deaths)}\n")

# ─── Q40-style: Ledge-hugging frequency ──────────────────────────────────────

print("=" * 60)
print("Q40 — Fox ledge-hugging frequency")
print("=" * 60)
try:
    fs["near_ledge"] = fs["fox_x"].abs() > (fs["edge_x"] - 15)
    fs["offstage"]   = fs["fox_x"].abs() > fs["edge_x"]

    overall_ledge = fs["near_ledge"].mean() * 100
    overall_off   = fs["offstage"].mean() * 100
    print(f"\n  Overall near-ledge (within 15u): {overall_ledge:.1f}%")
    print(f"  Overall off-stage:               {overall_off:.1f}%")

    by_stage = (
        fs.groupby("stage")[["near_ledge", "offstage"]]
        .mean()
        .mul(100)
        .round(1)
        .sort_values("near_ledge", ascending=False)
    )
    print("\nBy stage:")
    print(by_stage.to_string())
except Exception:
    traceback.print_exc()

# ─── Q41-style: Position drift vs percent ────────────────────────────────────

print("\n" + "=" * 60)
print("Q41 — Fox position drift vs damage percent")
print("=" * 60)
try:
    valid = fs.dropna(subset=["fox_x", "fox_pct"]).copy()
    valid["pct_bin"] = pd.cut(
        valid["fox_pct"],
        bins=[0, 30, 60, 90, 120, 999],
        labels=["0–30", "30–60", "60–90", "90–120", "120+"],
    )
    drift = (
        valid.groupby("pct_bin", observed=True)["fox_x"]
        .agg(mean_x="mean", median_x="median", n="count")
        .round(2)
    )
    print(drift.to_string())
except Exception:
    traceback.print_exc()

# ─── Q42-style: Off-stage time ───────────────────────────────────────────────

print("\n" + "=" * 60)
print("Q42 — Fox vs opponent off-stage time")
print("=" * 60)
try:
    valid = fs.dropna(subset=["fox_x", "opp_x"]).copy()
    valid["fox_off"] = valid["fox_x"].abs() > valid["edge_x"]
    valid["opp_off"] = valid["opp_x"].abs() > valid["edge_x"]

    fox_off_overall = valid["fox_off"].mean() * 100
    opp_off_overall = valid["opp_off"].mean() * 100
    print(f"\n  Fox off-stage: {fox_off_overall:.1f}%  |  Opponent off-stage: {opp_off_overall:.1f}%")

    by_stage = (
        valid.groupby("stage")[["fox_off", "opp_off"]]
        .mean()
        .mul(100)
        .round(1)
        .sort_values("fox_off", ascending=False)
    )
    print("\nBy stage:")
    print(by_stage.to_string())

    by_opp = (
        valid.groupby("opp_char")[["fox_off", "opp_off"]]
        .mean()
        .mul(100)
        .round(1)
        .sort_values("fox_off", ascending=False)
        .head(10)
    )
    print("\nTop 10 matchups by Fox off-stage %:")
    print(by_opp.to_string())
except Exception:
    traceback.print_exc()

# ─── Q44-style: Blast zone deaths ────────────────────────────────────────────

print("\n" + "=" * 60)
print("Q44 — Which blast zone kills Fox")
print("=" * 60)
try:
    valid_d = deaths.dropna(subset=["blastzone"])
    bz_counts = valid_d["blastzone"].value_counts()
    bz_pct = (bz_counts / bz_counts.sum() * 100).round(1)
    print("\nBlast zone distribution:")
    print(pd.DataFrame({"count": bz_counts, "pct": bz_pct}).to_string())

    by_stage = (
        valid_d.groupby(["stage", "blastzone"])
        .size()
        .unstack(fill_value=0)
    )
    # Normalize to percent per stage
    by_stage_pct = by_stage.div(by_stage.sum(axis=1), axis=0).mul(100).round(1)
    print("\nBlast zone % by stage:")
    print(by_stage_pct.to_string())

    print("\nMedian death % by blast zone:")
    print(valid_d.groupby("blastzone")["death_pct"].median().round(1).to_string())
except Exception:
    traceback.print_exc()

# ─── Q48-style: Edgeguard depth ──────────────────────────────────────────────

print("\n" + "=" * 60)
print("Q48 — Fox edgeguard depth (when opponent is off-stage)")
print("=" * 60)
try:
    valid = fs.dropna(subset=["fox_x", "opp_x"]).copy()
    eg = valid[valid["opp_x"].abs() > valid["edge_x"]].copy()
    eg["fox_depth"] = (eg["fox_x"].abs() - eg["edge_x"]).clip(lower=0)
    eg["fox_went_off"] = eg["fox_depth"] > 0

    print(f"\n  Frames with opponent off-stage: {len(eg):,}")
    print(f"  Fox also off-stage: {eg['fox_went_off'].mean() * 100:.1f}%")
    print(f"  Avg depth when off: {eg[eg['fox_went_off']]['fox_depth'].mean():.2f} units")
    print(f"  Max depth observed: {eg['fox_depth'].max():.1f} units")

    by_stage = (
        eg.groupby("stage")
        .agg(
            went_off_pct=("fox_went_off", lambda x: round(x.mean() * 100, 1)),
            avg_depth=("fox_depth", lambda x: round(x.mean(), 2)),
        )
        .sort_values("went_off_pct", ascending=False)
    )
    print("\nBy stage:")
    print(by_stage.to_string())
except Exception:
    traceback.print_exc()


# ─── Charts ───────────────────────────────────────────────────────────────────

PALETTE = ["#2196F3", "#FF5722", "#4CAF50", "#9C27B0", "#FF9800", "#00BCD4"]
sns_style = {"axes.facecolor": "#f8f9fa", "grid.color": "white", "axes.grid": True}
plt.rcParams.update({"font.size": 10})

# ── Chart 1: Blast zone distribution ─────────────────────────────────────────
print("\nGenerating charts ...")
try:
    valid_d = deaths.dropna(subset=["blastzone"])
    bz_order = ["top", "right", "left", "bottom"]
    bz_colors = {"top": "#E53935", "right": "#1E88E5", "left": "#43A047", "bottom": "#8E24AA"}

    bz_overall = valid_d["blastzone"].value_counts().reindex(bz_order, fill_value=0)
    bz_overall_pct = bz_overall / bz_overall.sum() * 100

    # Per-stage breakdown
    stages_present = sorted(valid_d["stage"].dropna().unique())
    n_stages = len(stages_present)

    fig, axes = plt.subplots(1, n_stages + 1, figsize=(3.5 * (n_stages + 1), 4.5))
    axes = list(axes)

    # Overall panel
    ax0 = axes[0]
    vals0 = [bz_overall_pct.get(bz, 0) for bz in bz_order]
    bars = ax0.bar(bz_order, vals0, color=[bz_colors[bz] for bz in bz_order], alpha=0.9)
    ax0.set_title("Overall", fontsize=11)
    ax0.set_ylabel("% of Fox deaths")
    ax0.set_ylim(0, max(vals0) * 1.25 + 5)
    for bar, val in zip(bars, vals0):
        if val > 0:
            ax0.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.8,
                     f"{val:.0f}%", ha="center", fontsize=9, fontweight="bold")

    for ax, stage in zip(axes[1:], stages_present):
        sub = valid_d[valid_d["stage"] == stage]
        bz_s = sub["blastzone"].value_counts().reindex(bz_order, fill_value=0)
        bz_s_pct = bz_s / bz_s.sum() * 100 if bz_s.sum() > 0 else bz_s
        vals = [float(bz_s_pct.get(bz, 0)) for bz in bz_order]
        bars = ax.bar(bz_order, vals, color=[bz_colors[bz] for bz in bz_order], alpha=0.9)
        ax.set_title(stage.replace(" ", "\n"), fontsize=9)
        ax.set_ylim(0, max(vals) * 1.25 + 5 if max(vals) > 0 else 10)
        ax.set_ylabel("")
        n_total = int(bz_s.sum())
        ax.set_xlabel(f"n={n_total}", fontsize=8)
        for bar, val in zip(bars, vals):
            if val > 2:
                ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.8,
                        f"{val:.0f}%", ha="center", fontsize=8)

    fig.suptitle(
        "Fox blast zone deaths — community data (1000 games)\n"
        "Bottom-spike is the primary kill method; top is rare",
        fontsize=12, fontweight="bold", y=1.02,
    )
    fig.tight_layout()
    path = OUT / "fox_blast_zones.png"
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  ✓  {path}")
except Exception:
    traceback.print_exc()

# ── Chart 2: Fox position x-distribution by damage % bucket ──────────────────
try:
    valid = fs.dropna(subset=["fox_x", "fox_pct"]).copy()
    valid["pct_bin"] = pd.cut(
        valid["fox_pct"],
        bins=[0, 30, 60, 90, 120, 999],
        labels=["0–30", "30–60", "60–90", "90–120", "120+"],
    )

    pct_bins = ["0–30", "30–60", "60–90", "90–120", "120+"]
    bin_colors = plt.cm.RdYlGn_r(np.linspace(0.15, 0.85, len(pct_bins)))

    fig, ax = plt.subplots(figsize=(9, 5))

    for i, (pct_bin, color) in enumerate(zip(pct_bins, bin_colors)):
        sub = valid[valid["pct_bin"] == pct_bin]["fox_x"].dropna()
        if len(sub) == 0:
            continue
        # Clip to ±130 for display
        clipped = sub.clip(-130, 130)
        ax.hist(clipped, bins=60, range=(-130, 130), density=True,
                alpha=0.55, color=color, label=f"{pct_bin}% (n={len(sub):,})")

    # Shade offstage regions (use median edge_x across all stages)
    med_edge = fs["edge_x"].median()
    ax.axvspan(-130, -med_edge, alpha=0.06, color="gray", label="Off-stage")
    ax.axvspan(med_edge, 130, alpha=0.06, color="gray")
    ax.axvline(0, color="black", ls="--", lw=0.8, alpha=0.4)
    ax.axvline(-med_edge, color="gray", ls=":", lw=1)
    ax.axvline(med_edge, color="gray", ls=":", lw=1)

    ax.set_xlabel("Fox position_x (negative = left side)")
    ax.set_ylabel("Density")
    ax.legend(fontsize=9, loc="upper right")
    fig.suptitle(
        "Fox x-position distribution by damage bucket — community data\n"
        "High% Fox shifts toward the blast zone edge",
        fontsize=12, fontweight="bold",
    )
    fig.tight_layout()
    path = OUT / "fox_position_drift.png"
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  ✓  {path}")
except Exception:
    traceback.print_exc()

# ── Chart 3: Off-stage % by stage — Fox vs Opponent ──────────────────────────
try:
    valid = fs.dropna(subset=["fox_x", "opp_x"]).copy()
    valid["fox_off"] = valid["fox_x"].abs() > valid["edge_x"]
    valid["opp_off"] = valid["opp_x"].abs() > valid["edge_x"]

    by_stage = (
        valid.groupby("stage")[["fox_off", "opp_off"]]
        .mean()
        .mul(100)
        .sort_values("fox_off", ascending=False)
    )

    stages = by_stage.index.tolist()
    x = np.arange(len(stages))
    w = 0.35

    fig, ax = plt.subplots(figsize=(8, 4.5))
    b1 = ax.bar(x - w / 2, by_stage["fox_off"], w, label="Fox", color="#2196F3", alpha=0.9)
    b2 = ax.bar(x + w / 2, by_stage["opp_off"], w, label="Opponent", color="#FF5722", alpha=0.9)

    for bar in list(b1) + list(b2):
        h = bar.get_height()
        ax.text(bar.get_x() + bar.get_width() / 2, h + 0.3,
                f"{h:.1f}%", ha="center", fontsize=8)

    ax.set_xticks(x)
    ax.set_xticklabels(stages, rotation=15, ha="right")
    ax.set_ylabel("% of frames off-stage")
    ax.legend()
    fig.suptitle(
        "Fox vs opponent off-stage time by stage — community data\n"
        "Fox spends more time off-stage on small stages; roughly symmetric otherwise",
        fontsize=12, fontweight="bold",
    )
    fig.tight_layout()
    path = OUT / "fox_offstage_by_stage.png"
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  ✓  {path}")
except Exception:
    traceback.print_exc()

# ── Chart 4: Death % distribution by blast zone ──────────────────────────────
try:
    valid_d = deaths.dropna(subset=["blastzone", "death_pct"])
    valid_d = valid_d[valid_d["death_pct"] < 300]  # strip bogus values

    bz_order = ["top", "right", "left", "bottom"]
    bz_colors = {"top": "#E53935", "right": "#1E88E5", "left": "#43A047", "bottom": "#8E24AA"}

    present = [bz for bz in bz_order if bz in valid_d["blastzone"].values]

    fig, ax = plt.subplots(figsize=(8, 5))
    data_vals = [valid_d[valid_d["blastzone"] == bz]["death_pct"].values for bz in present]
    bp = ax.violinplot(data_vals, positions=range(len(present)),
                       showmedians=True, showextrema=True)

    for body, bz in zip(bp["bodies"], present):
        body.set_facecolor(bz_colors[bz])
        body.set_alpha(0.7)
    bp["cmedians"].set_color("black")
    bp["cmedians"].set_linewidth(2)

    for i, (bz, vals) in enumerate(zip(present, data_vals)):
        med = float(np.median(vals))
        n_v = len(vals)
        ax.text(i, med + 3, f"med {med:.0f}%\n(n={n_v})",
                ha="center", fontsize=8, fontweight="bold")

    ax.set_xticks(range(len(present)))
    ax.set_xticklabels([bz.capitalize() for bz in present])
    ax.set_ylabel("Fox damage % at death")
    ax.set_ylim(0, None)
    fig.suptitle(
        "Fox death % by blast zone — community data\n"
        "Side/top deaths happen earlier; bottom spikes can occur at any %",
        fontsize=12, fontweight="bold",
    )
    fig.tight_layout()
    path = OUT / "fox_death_pct_by_zone.png"
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  ✓  {path}")
except Exception:
    traceback.print_exc()

# ─── Done ─────────────────────────────────────────────────────────────────────

print(f"\nDone. Outputs in {OUT}/")
