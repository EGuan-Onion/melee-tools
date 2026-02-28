#!/usr/bin/env python3
"""Stage and positional analysis (Q40–Q48).

Q40 — Ledge-hugging frequency
Q41 — Position drift vs percent
Q42 — Off-stage time comparison
Q43 — Kill position scatter (where I kill opponents)
Q44 — Which blast zone kills me
Q45 — Where I stand when I die
Q46 — Where combos start on stage
Q47 — Combo displacement
Q48 — Edgeguard depth off-stage

Usage:
    source .venv/bin/activate
    python -m analysis.positions
"""

import traceback
from pathlib import Path

import numpy as np
import pandas as pd

from analysis.common import ROOT, TAG, CHARS, pg

from melee_tools.iteration import _iter_1v1_games
from melee_tools.combos import analyze_kills, detect_combos
from melee_tools.stages import STAGE_GEOMETRY

# ─── Config ──────────────────────────────────────────────────────────────────

OUT = Path("outputs/positions")
OUT.mkdir(parents=True, exist_ok=True)

# Stage name → edge_x lookup (for gi["stage_name"] joins)
EDGE_X_BY_NAME: dict[str, float] = {v["name"]: v["edge_x"] for v in STAGE_GEOMETRY.values()}

# Stage mapping from pg (one row per filename for tag; used to add stage to analyze_kills output)
_STAGE_BY_FILE = (
    pg[pg.tag == TAG][["filename", "stage"]]
    .drop_duplicates("filename")
    .set_index("filename")["stage"]
)


def _add_stage(df: pd.DataFrame) -> pd.DataFrame:
    """Add a 'stage' column to a DataFrame that has a 'filename' column."""
    df = df.copy()
    df["stage"] = df["filename"].map(_STAGE_BY_FILE)
    return df


# ─── Shared Collectors ───────────────────────────────────────────────────────

def collect_frame_samples(root: str, pg_df: pd.DataFrame, tag: str, sample_every: int = 5) -> pd.DataFrame:
    """Sample frames from every 1v1 game.

    Returns one row per sampled frame with both players' positions and percents.

    Columns: character, opp_character, stage, filename, frame,
             my_x, my_y, my_pct, opp_x, opp_y, opp_pct
    """
    batches = []
    for gi, my_df, opp_df, char_name in _iter_1v1_games(root, pg_df, tag):
        if len(my_df) < sample_every or len(opp_df) < sample_every:
            continue

        my_s = my_df.iloc[::sample_every].reset_index(drop=True)
        opp_s = opp_df.iloc[::sample_every].reset_index(drop=True)
        n = min(len(my_s), len(opp_s))
        my_s = my_s.iloc[:n]
        opp_s = opp_s.iloc[:n]

        opp_char = opp_df["character_name"].iloc[0]
        stage = gi.get("stage_name", "Unknown")
        filename = gi["filename"]

        batch = pd.DataFrame({
            "character":     char_name,
            "opp_character": opp_char,
            "stage":         stage,
            "filename":      filename,
            "frame":         my_s["frame"].values.astype(int),
            "my_x":          my_s["position_x"].values.astype(float),
            "my_y":          my_s["position_y"].values.astype(float),
            "my_pct":        my_s["percent"].values.astype(float),
            "opp_x":         opp_s["position_x"].values.astype(float),
            "opp_y":         opp_s["position_y"].values.astype(float),
            "opp_pct":       opp_s["percent"].values.astype(float),
        })
        batches.append(batch)

    if not batches:
        return pd.DataFrame()
    return pd.concat(batches, ignore_index=True)


def collect_combo_positions(root: str, pg_df: pd.DataFrame, tag: str) -> pd.DataFrame:
    """Detect combos and attach start/end positions of the defender.

    Returns all detect_combos() columns plus:
    character, opp_character, stage, filename, start_x, start_y, end_x, end_y
    """
    batches = []
    for gi, my_df, opp_df, char_name in _iter_1v1_games(root, pg_df, tag):
        combos = detect_combos(my_df, opp_df)
        if combos.empty:
            continue

        opp_char = opp_df["character_name"].iloc[0]
        stage = gi.get("stage_name", "Unknown")
        filename = gi["filename"]

        # Frame-indexed position lookup for the defender (opp_df)
        opp_pos = opp_df.drop_duplicates("frame").set_index("frame")[["position_x", "position_y"]]

        combos = combos.copy()
        combos["character"] = char_name
        combos["opp_character"] = opp_char
        combos["stage"] = stage
        combos["filename"] = filename

        start_x, start_y, end_x, end_y = [], [], [], []
        for _, row in combos.iterrows():
            sf, ef = row["start_frame"], row["end_frame"]
            if sf in opp_pos.index:
                start_x.append(float(opp_pos.loc[sf, "position_x"]))
                start_y.append(float(opp_pos.loc[sf, "position_y"]))
            else:
                start_x.append(np.nan)
                start_y.append(np.nan)
            if ef in opp_pos.index:
                end_x.append(float(opp_pos.loc[ef, "position_x"]))
                end_y.append(float(opp_pos.loc[ef, "position_y"]))
            else:
                end_x.append(np.nan)
                end_y.append(np.nan)

        combos["start_x"] = start_x
        combos["start_y"] = start_y
        combos["end_x"] = end_x
        combos["end_y"] = end_y
        batches.append(combos)

    if not batches:
        return pd.DataFrame()
    return pd.concat(batches, ignore_index=True)


# ─── Collect shared data ─────────────────────────────────────────────────────

print("Collecting frame samples (Q40/41/42/48) ...")
frame_samples = collect_frame_samples(ROOT, pg, TAG)
print(f"  {len(frame_samples):,} sampled frames from {frame_samples['filename'].nunique() if not frame_samples.empty else 0} games\n")

print("Collecting combo positions (Q46/47) ...")
combo_positions = collect_combo_positions(ROOT, pg, TAG)
print(f"  {len(combo_positions):,} combos\n")

# ─── Q40 — Ledge-hugging frequency ───────────────────────────────────────────

print("=" * 60)
print("Q40 — Ledge-hugging frequency (% of frames near ledge)")
print("=" * 60)
try:
    fs = frame_samples.dropna(subset=["my_x", "stage"]).copy()
    fs["edge_x"] = fs["stage"].map(EDGE_X_BY_NAME).fillna(80.0)
    fs["near_ledge"] = fs["my_x"].abs() > (fs["edge_x"] - 15)

    print("\nOverall by character:")
    print(
        fs.groupby("character")["near_ledge"].mean()
        .mul(100).round(1).rename("near_ledge_%")
        .to_string()
    )

    print("\nBy character × stage:")
    tbl = (
        fs.groupby(["character", "stage"])["near_ledge"]
        .agg(near_ledge_pct=("mean"), n="count")
        .assign(near_ledge_pct=lambda d: (d["near_ledge_pct"] * 100).round(1))
        .sort_values(["character", "near_ledge_pct"], ascending=[True, False])
    )
    print(tbl.to_string())

    out = OUT / "q40_ledge_hugging.csv"
    tbl.reset_index().to_csv(out, index=False)
    print(f"\n  Saved → {out}")
except Exception:
    traceback.print_exc()

# ─── Q41 — Position drift vs percent ─────────────────────────────────────────

print("\n" + "=" * 60)
print("Q41 — Position drift vs percent (where do I stand at each % range)")
print("=" * 60)
try:
    fs = frame_samples.dropna(subset=["my_x", "my_pct"]).copy()
    fs["pct_bin"] = pd.cut(
        fs["my_pct"],
        bins=[0, 30, 60, 90, 120, 999],
        labels=["0–30", "30–60", "60–90", "90–120", "120+"],
        right=True,
    )

    print("\nMean |my_x| by character × pct_bin (positive = further from center):")
    tbl = (
        fs.groupby(["character", "pct_bin"], observed=True)["my_x"]
        .agg(mean_x="mean", median_x="median", n="count")
        .round(2)
    )
    print(tbl.to_string())

    out = OUT / "q41_position_drift.csv"
    tbl.reset_index().to_csv(out, index=False)
    print(f"\n  Saved → {out}")
except Exception:
    traceback.print_exc()

# ─── Q42 — Off-stage time comparison ─────────────────────────────────────────

print("\n" + "=" * 60)
print("Q42 — Off-stage time comparison (me vs opponent)")
print("=" * 60)
try:
    fs = frame_samples.dropna(subset=["my_x", "opp_x", "stage"]).copy()
    fs["edge_x"] = fs["stage"].map(EDGE_X_BY_NAME).fillna(80.0)
    fs["me_offstage"] = fs["my_x"].abs() > fs["edge_x"]
    fs["opp_offstage"] = fs["opp_x"].abs() > fs["edge_x"]

    print("\nOff-stage % by character × opponent character:")
    tbl = (
        fs.groupby(["character", "opp_character"])[["me_offstage", "opp_offstage"]]
        .mean()
        .mul(100)
        .round(1)
    )
    print(tbl.to_string())

    print("\nOff-stage % by character × stage:")
    tbl2 = (
        fs.groupby(["character", "stage"])[["me_offstage", "opp_offstage"]]
        .mean()
        .mul(100)
        .round(1)
    )
    print(tbl2.to_string())

    out = OUT / "q42_offstage_time.csv"
    tbl2.reset_index().to_csv(out, index=False)
    print(f"\n  Saved → {out}")
except Exception:
    traceback.print_exc()

# ─── Q43 — Kill position scatter ─────────────────────────────────────────────

print("\n" + "=" * 60)
print("Q43 — Kill positions (where do opponents die when I kill them)")
print("=" * 60)
try:
    kills = _add_stage(analyze_kills(ROOT, pg, TAG))
    if kills.empty:
        raise ValueError("No kill data")

    print(f"\n  {len(kills)} kills loaded")
    tbl = (
        kills.dropna(subset=["death_x", "death_y"])
        .groupby(["character", "opp_character", "stage"])[["death_x", "death_y"]]
        .agg(["mean", "median", "count"])
        .round(2)
    )
    print(tbl.to_string())

    out = OUT / "q43_kill_positions.csv"
    kills.dropna(subset=["death_x", "death_y"]).to_csv(out, index=False)
    print(f"\n  Saved → {out}")
except Exception:
    traceback.print_exc()

# ─── Q44 — Which blast zone kills me ─────────────────────────────────────────

print("\n" + "=" * 60)
print("Q44 — Which blast zone kills me")
print("=" * 60)
try:
    deaths = _add_stage(analyze_kills(ROOT, pg, TAG, as_attacker=False))
    if deaths.empty:
        raise ValueError("No death data")

    print(f"\n  {len(deaths)} deaths loaded")

    print("\nBlast zone breakdown by character:")
    tbl = (
        deaths.groupby(["character", "blastzone"])
        .size()
        .unstack(fill_value=0)
    )
    # Add pct columns
    tbl_pct = tbl.div(tbl.sum(axis=1), axis=0).mul(100).round(1)
    print("Counts:")
    print(tbl.to_string())
    print("\nPercent:")
    print(tbl_pct.to_string())

    print("\nBlast zone breakdown by character × opponent:")
    tbl2 = (
        deaths.groupby(["character", "opp_character", "blastzone"])
        .size()
        .unstack(fill_value=0)
    )
    print(tbl2.to_string())

    out = OUT / "q44_blast_zones.csv"
    tbl_pct.reset_index().to_csv(out, index=False)
    print(f"\n  Saved → {out}")
except Exception:
    traceback.print_exc()

# ─── Q45 — Where I stand when I die ─────────────────────────────────────────

print("\n" + "=" * 60)
print("Q45 — Where I stand when I die (death_x / death_y distribution)")
print("=" * 60)
try:
    # Reuse deaths from Q44 if still in scope
    if "deaths" not in dir() or deaths.empty:
        deaths = _add_stage(analyze_kills(ROOT, pg, TAG, as_attacker=False))

    tbl = (
        deaths.dropna(subset=["death_x", "death_y"])
        .groupby(["character", "stage"])[["death_x", "death_y"]]
        .agg(["mean", "median", "std", "count"])
        .round(2)
    )
    print(tbl.to_string())

    out = OUT / "q45_death_positions.csv"
    deaths.dropna(subset=["death_x", "death_y"]).to_csv(out, index=False)
    print(f"\n  Saved → {out}")
except Exception:
    traceback.print_exc()

# ─── Q46 — Where combos start on stage ───────────────────────────────────────

print("\n" + "=" * 60)
print("Q46 — Where combos start on stage (start_x of the defender)")
print("=" * 60)
try:
    cp = combo_positions.dropna(subset=["start_x", "start_y"])
    if cp.empty:
        raise ValueError("No combo position data")

    print(f"\n  {len(cp)} combos with position data")

    print("\nCombo start positions by character × stage:")
    tbl = (
        cp.groupby(["character", "stage"])[["start_x", "start_y"]]
        .agg(["mean", "median", "count"])
        .round(2)
    )
    print(tbl.to_string())

    print("\nStart_x by combo starter move (top 10 by count):")
    by_starter = (
        cp.groupby(["character", "started_by"])
        .agg(
            mean_start_x=("start_x", "mean"),
            median_start_x=("start_x", "median"),
            n=("start_x", "count"),
        )
        .query("n >= 3")
        .sort_values(["character", "n"], ascending=[True, False])
        .round(2)
    )
    for char in CHARS:
        sub = by_starter.xs(char, level="character") if char in by_starter.index.get_level_values("character") else pd.DataFrame()
        if not sub.empty:
            print(f"\n  {char}:")
            print(sub.head(10).to_string())

    out = OUT / "q46_combo_starts.csv"
    cp[["character", "opp_character", "stage", "started_by", "start_x", "start_y", "num_hits", "damage"]].to_csv(out, index=False)
    print(f"\n  Saved → {out}")
except Exception:
    traceback.print_exc()

# ─── Q47 — Combo displacement ─────────────────────────────────────────────────

print("\n" + "=" * 60)
print("Q47 — Combo displacement (dx/dy from start to end of combo)")
print("=" * 60)
try:
    cp = combo_positions.dropna(subset=["start_x", "end_x"])
    if cp.empty:
        raise ValueError("No combo position data")

    cp = cp.copy()
    cp["dx"] = cp["end_x"] - cp["start_x"]
    cp["dy"] = cp["end_y"] - cp["start_y"]
    cp["dist"] = np.sqrt(cp["dx"] ** 2 + cp["dy"] ** 2)

    tbl = (
        cp.groupby(["character", "opp_character"])[["dx", "dy", "dist", "damage"]]
        .agg(["mean", "median"])
        .round(2)
    )
    print(tbl.to_string())

    print("\nDisplacement by stage:")
    tbl2b = (
        cp.groupby(["character", "stage"])
        .agg(
            mean_dx=("dx", "mean"),
            mean_dy=("dy", "mean"),
            mean_dist=("dist", "mean"),
            n=("dx", "count"),
        )
        .round(2)
    )
    print(tbl2b.to_string())

    out = OUT / "q47_combo_displacement.csv"
    cp[["character", "opp_character", "stage", "started_by", "dx", "dy", "dist", "damage", "num_hits"]].to_csv(out, index=False)
    print(f"\n  Saved → {out}")
except Exception:
    traceback.print_exc()

# ─── Q48 — Edgeguard depth off-stage ─────────────────────────────────────────

print("\n" + "=" * 60)
print("Q48 — Edgeguard depth (how far off-stage I go when opponent is off-stage)")
print("=" * 60)
try:
    fs = frame_samples.dropna(subset=["my_x", "opp_x", "stage"]).copy()
    fs["edge_x"] = fs["stage"].map(EDGE_X_BY_NAME).fillna(80.0)

    # Edgeguard windows = frames where opponent is off-stage
    eg = fs[fs["opp_x"].abs() > fs["edge_x"]].copy()
    if eg.empty:
        raise ValueError("No frames found with opponent off-stage")

    # How deep I go: positive = I'm also off-stage, 0 = I'm at/inside the ledge
    eg["my_depth"] = (eg["my_x"].abs() - eg["edge_x"]).clip(lower=0)
    eg["went_offstage"] = eg["my_depth"] > 0

    print(f"\n  {len(eg):,} frames with opponent off-stage")

    tbl = (
        eg.groupby(["character", "opp_character", "stage"])
        .agg(
            went_offstage_pct=("went_offstage", lambda x: round(x.mean() * 100, 1)),
            avg_depth=("my_depth", lambda x: round(x.mean(), 2)),
            max_depth=("my_depth", lambda x: round(x.max(), 2)),
            n_frames=("my_depth", "count"),
        )
        .sort_values(["character", "went_offstage_pct"], ascending=[True, False])
    )
    print(tbl.to_string())

    print("\nOverall by character:")
    print(
        eg.groupby("character")
        .agg(
            went_offstage_pct=("went_offstage", lambda x: round(x.mean() * 100, 1)),
            avg_depth=("my_depth", lambda x: round(x.mean(), 2)),
            max_depth=("my_depth", lambda x: round(x.max(), 2)),
        )
        .to_string()
    )

    out = OUT / "q48_edgeguard_depth.csv"
    tbl.reset_index().to_csv(out, index=False)
    print(f"\n  Saved → {out}")
except Exception:
    traceback.print_exc()

# ─── Done ─────────────────────────────────────────────────────────────────────

print(f"\nDone. Outputs in {OUT}/")
