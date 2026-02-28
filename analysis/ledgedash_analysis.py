"""Sheik ledgedash analysis: GALINT options + post-ledgedash moves from replays.

Generates two charts:
1. Sheik's fully invulnerable options at max GALINT (11 frames)
2. Most commonly used Sheik moves out of ledgedash (from replay data)
"""

import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
import pandas as pd

# ─── Add project root to path ────────────────────────────────────────────────
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from analysis.common import ROOT, TAG, games, pg
from melee_tools import find_ledgedashes
from melee_tools.iteration import _iter_1v1_games
from melee_tools.action_states import ACTION_STATES, ACTION_STATE_CATEGORIES

# ═══════════════════════════════════════════════════════════════════════════════
# Q1: Sheik's fully invulnerable ledgedash options at max GALINT
# ═══════════════════════════════════════════════════════════════════════════════

SHEIK_MAX_GALINT = 11  # standard max GALINT
GALINT_BATTLEFIELD = 13  # with regrab method on Battlefield

# Sheik's grounded move startup frames (frame the hitbox becomes active)
# Source: fightcore.gg/meleeframedata.com
SHEIK_MOVES = {
    "Jab":          2,
    "Needles":      4,
    "F-tilt":       5,
    "Up tilt":      5,
    "Down tilt":    5,
    "Down smash":   5,
    "Dash attack":  6,
    "Grab":         6,
    "Dash grab":    8,
    "F-smash":     12,
    "Up smash":    12,
}

# Classify each move
move_names = []
startup_frames = []
covered_standard = []  # fully covered at 11 GALINT
covered_bf = []        # fully covered at 13 GALINT (Battlefield regrab)

for move, startup in sorted(SHEIK_MOVES.items(), key=lambda x: x[1]):
    move_names.append(move)
    startup_frames.append(startup)
    covered_standard.append(startup <= SHEIK_MAX_GALINT)
    covered_bf.append(startup <= GALINT_BATTLEFIELD)

galint_df = pd.DataFrame({
    "move": move_names,
    "startup": startup_frames,
    "covered_11": covered_standard,
    "covered_13": covered_bf,
})

print("=" * 60)
print("Q1: Sheik's Fully Invulnerable Ledgedash Options")
print("=" * 60)
print(f"\nMax GALINT (standard): {SHEIK_MAX_GALINT} frames")
print(f"Max GALINT (Battlefield regrab): {GALINT_BATTLEFIELD} frames")
print(f"\nMoves with hitbox out during invincibility (standard {SHEIK_MAX_GALINT}f):")
for _, row in galint_df[galint_df.covered_11].iterrows():
    remaining = SHEIK_MAX_GALINT - row.startup
    print(f"  {row.move:15s}  startup f{row.startup:2d}  →  {remaining}f invincible after hitbox")
print(f"\nAdditional moves at {GALINT_BATTLEFIELD}f GALINT (Battlefield regrab):")
for _, row in galint_df[~galint_df.covered_11 & galint_df.covered_13].iterrows():
    remaining = GALINT_BATTLEFIELD - row.startup
    print(f"  {row.move:15s}  startup f{row.startup:2d}  →  {remaining}f invincible after hitbox")
not_covered = galint_df[~galint_df.covered_13]
if len(not_covered):
    print(f"\nNever fully covered:")
    for _, row in not_covered.iterrows():
        print(f"  {row.move:15s}  startup f{row.startup:2d}  →  {row.startup - GALINT_BATTLEFIELD}f short")

# ─── Chart 1: GALINT coverage ────────────────────────────────────────────────

fig, ax = plt.subplots(figsize=(14, 6))

y_pos = np.arange(len(galint_df))
bars = ax.barh(y_pos, galint_df.startup, color="steelblue", height=0.6, zorder=3)

# Color bars by coverage
for i, (bar, cov11, cov13) in enumerate(zip(bars, covered_standard, covered_bf)):
    if cov11:
        bar.set_color("#2ecc71")  # green — covered at standard GALINT
    elif cov13:
        bar.set_color("#f39c12")  # orange — only covered at BF GALINT
    else:
        bar.set_color("#e74c3c")  # red — never covered

# GALINT lines
ax.axvline(x=SHEIK_MAX_GALINT, color="#2ecc71", linestyle="--", linewidth=2, alpha=0.8,
           label=f"Standard max GALINT ({SHEIK_MAX_GALINT}f)")
ax.axvline(x=GALINT_BATTLEFIELD, color="#f39c12", linestyle="--", linewidth=2, alpha=0.8,
           label=f"Battlefield regrab GALINT ({GALINT_BATTLEFIELD}f)")

# Labels on bars
for i, (move, startup) in enumerate(zip(galint_df.move, galint_df.startup)):
    ax.text(startup + 0.2, i, f"f{startup}", va="center", fontsize=11, fontweight="bold")

ax.set_yticks(y_pos)
ax.set_yticklabels(galint_df.move, fontsize=12)
ax.set_xlabel("Startup Frames", fontsize=12)
ax.set_title("Sheik Ledgedash: Move Startup vs GALINT Window", fontsize=15, fontweight="bold")
ax.legend(loc="lower right", fontsize=10)
ax.set_xlim(0, 16)
ax.invert_yaxis()
ax.grid(axis="x", alpha=0.3, zorder=0)

# Insight strip
insight = (
    f"At max GALINT ({SHEIK_MAX_GALINT}f): 9 options — jab, needles, all 3 tilts, dsmash, "
    f"dash attack, grab, dash grab\n"
    f"Battlefield regrab ({GALINT_BATTLEFIELD}f) adds: F-smash and Up smash"
)
fig.text(0.5, -0.02, insight, ha="center", fontsize=10, style="italic", color="#555")
fig.tight_layout()
fig.savefig("outputs/insights/ledgedash_galint.png", dpi=150, bbox_inches="tight")
print("\nSaved: outputs/insights/ledgedash_galint.png")

# ═══════════════════════════════════════════════════════════════════════════════
# Q2: Most commonly used Sheik moves out of ledgedash (from replays)
# ═══════════════════════════════════════════════════════════════════════════════

print("\n" + "=" * 60)
print("Q2: Sheik Post-Ledgedash Actions (from replays)")
print("=" * 60)

# Action classification: state ID → label
_JUMPSQUAT = 24  # used in action label setup below
ACTION_LABELS = {}
for cat_name in ["jab", "ftilt", "utilt", "dtilt", "fsmash", "usmash", "dsmash",
                  "dash_attack", "grab", "nair", "fair", "bair", "uair", "dair",
                  "roll", "spotdodge", "shield"]:
    if cat_name in ACTION_STATE_CATEGORIES:
        for s in ACTION_STATE_CATEGORIES[cat_name]:
            ACTION_LABELS[s] = cat_name

# Friendly display names
DISPLAY_NAMES = {
    "jab": "Jab", "ftilt": "F-tilt", "utilt": "Up tilt", "dtilt": "Down tilt",
    "fsmash": "F-smash", "usmash": "Up smash", "dsmash": "Down smash",
    "dash_attack": "Dash attack", "grab": "Grab",
    "nair": "Nair", "fair": "Fair", "bair": "Bair", "uair": "Up air", "dair": "Dair",
    "roll": "Roll", "spotdodge": "Spotdodge", "shield": "Shield",
    "dash_run": "Dash/Run", "jump": "Jump", "crouch": "Crouch",
    "idle": "Idle/Wait", "walk": "Walk",
}

# Add movement states
for s in ACTION_STATE_CATEGORIES.get("dash_run", set()):
    ACTION_LABELS[s] = "dash_run"
for s in ACTION_STATE_CATEGORIES.get("jump", set()) | {_JUMPSQUAT}:
    ACTION_LABELS[s] = "jump"
for s in ACTION_STATE_CATEGORIES.get("crouch", set()):
    ACTION_LABELS[s] = "crouch"
for s in ACTION_STATE_CATEGORIES.get("idle", set()):
    ACTION_LABELS[s] = "idle"
for s in ACTION_STATE_CATEGORIES.get("walk", set()):
    ACTION_LABELS[s] = "walk"

# Detect all ledgedashes using library function
all_lds = find_ledgedashes(ROOT, pg, TAG, "sheik")
print(f"\nTotal Sheik ledgedashes found: {len(all_lds)}")

# Classify post-ledgedash actions (requires per-game frame data for the state scan)
post_ld_rows = []

for gi, my_df, opp_df, char_name in _iter_1v1_games(ROOT, pg, TAG, "sheik"):
    fname = gi["filename"]
    game_lds = all_lds[all_lds["filename"] == fname]
    if len(game_lds) == 0:
        continue

    states = my_df["state"].values
    frames = my_df["frame"].values.astype(int)

    for _, ld in game_lds.iterrows():
        land_frame = int(ld["land_frame"])
        land_idx = int(np.searchsorted(frames, land_frame))
        if land_idx >= len(states):
            continue

        # Find first meaningful action after landing, skipping landing lag (42, 43)
        action_label = None
        for k in range(land_idx, min(land_idx + 30, len(states))):
            sk = int(states[k]) if not pd.isna(states[k]) else 0
            if sk in {42, 43}:
                continue
            if sk in ACTION_LABELS:
                action_label = ACTION_LABELS[sk]
                break

        if action_label is None:
            land_s = int(states[land_idx]) if not pd.isna(states[land_idx]) else 0
            if land_s in ACTION_LABELS:
                action_label = ACTION_LABELS[land_s]
            else:
                action_label = f"other ({ACTION_STATES.get(land_s, land_s)})"

        post_ld_rows.append({
            "action": action_label,
            "frame": int(ld["frame"]),
            "filename": fname,
        })

post_ld_df = pd.DataFrame(post_ld_rows)

if len(post_ld_df) == 0:
    print("\nNo Sheik ledgedashes found in replay data.")
    print("(This is consistent with earlier findings: ledgedash rate = 0%)")
    # Still save chart 1
    plt.close("all")
    sys.exit(0)

# Aggregate
action_counts = post_ld_df["action"].value_counts()
total = len(post_ld_df)
print(f"\nTotal Sheik ledgedashes found: {total}")
print(f"\nPost-ledgedash actions:")
for action, count in action_counts.items():
    display = DISPLAY_NAMES.get(action, action)
    print(f"  {display:15s}  {count:3d}  ({count/total*100:.1f}%)")

# ─── Chart 2: Post-ledgedash actions ─────────────────────────────────────────

fig2, ax2 = plt.subplots(figsize=(12, max(5, len(action_counts) * 0.5 + 1)))

display_labels = [DISPLAY_NAMES.get(a, a) for a in action_counts.index]
colors = []
for a in action_counts.index:
    if a in {"jab", "ftilt", "utilt", "dtilt", "fsmash", "usmash", "dsmash",
             "dash_attack", "nair", "fair", "bair", "uair", "dair"}:
        colors.append("#e74c3c")  # attacks = red
    elif a == "grab":
        colors.append("#9b59b6")  # grab = purple
    elif a in {"shield", "spotdodge", "roll"}:
        colors.append("#3498db")  # defensive = blue
    else:
        colors.append("#95a5a6")  # movement/other = gray

y_pos2 = np.arange(len(action_counts))
bars2 = ax2.barh(y_pos2, action_counts.values, color=colors, height=0.6, zorder=3)

for i, (count, label) in enumerate(zip(action_counts.values, display_labels)):
    pct = count / total * 100
    ax2.text(count + 0.3, i, f"{count} ({pct:.0f}%)", va="center", fontsize=11)

ax2.set_yticks(y_pos2)
ax2.set_yticklabels(display_labels, fontsize=12)
ax2.set_xlabel("Count", fontsize=12)
ax2.set_title(f"Sheik Post-Ledgedash Actions (n={total})", fontsize=15, fontweight="bold")
ax2.invert_yaxis()
ax2.grid(axis="x", alpha=0.3, zorder=0)

# Legend
legend_patches = [
    mpatches.Patch(color="#e74c3c", label="Attack"),
    mpatches.Patch(color="#9b59b6", label="Grab"),
    mpatches.Patch(color="#3498db", label="Defensive"),
    mpatches.Patch(color="#95a5a6", label="Movement"),
]
ax2.legend(handles=legend_patches, loc="lower right", fontsize=10)

fig2.tight_layout()
fig2.savefig("outputs/insights/ledgedash_postmoves.png", dpi=150, bbox_inches="tight")
print(f"\nSaved: outputs/insights/ledgedash_postmoves.png")

plt.close("all")
print("\nDone.")
