"""Tech chase analysis: Fox's tech option distribution and attacker response.

Scans ALL knockdown situations (both missed techs AND successful techs) from
any game where Fox is knocked down. Uses a random sample of replays from
the training_data folder.

Produces:
  1. Fox's tech option frequency bar chart
  2. Attacker response × tech option heatmap
  3. Conversion rate by knockdown % bucket
  4. Summary stats to console

Output: outputs/insights/tech_chases_*.png
"""

import random
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from peppi_py import read_slippi

from melee_tools.enums import character_name
from melee_tools.frames import _safe_np
from melee_tools.habits import classify_attacker_response
from melee_tools.iteration import classify_direction
from melee_tools.moves import move_name

# ─── Config ──────────────────────────────────────────────────────────────────

REPLAY_DIR = Path("replays/training_data")
SAMPLE_N = 1000
SEED = 42

OUT_DIR = Path("outputs/insights")
OUT_DIR.mkdir(parents=True, exist_ok=True)

# Action states for knockdown detection on the OPPONENT
_MISSED_BOUND = {183, 191}
_MISSED_WAIT = {184, 192}
_HIT_DOWN = {185, 193}

_TECH_IN_PLACE = 199
_TECH_ROLL_F = 200
_TECH_ROLL_B = 201

_GETUP = {186, 194}
_GETUP_ATTACK = {187, 195}
_DOWN_ROLL_F = {188, 196}
_DOWN_ROLL_B = {189, 197}




def _scan_game_knockdowns(fpath):
    """Scan a single game for all knockdown situations involving Fox."""
    try:
        game = read_slippi(str(fpath))
    except BaseException:
        return []

    active_players = [(i, p) for i, p in enumerate(game.start.players) if p is not None]
    if len(active_players) != 2:
        return []

    frame_ids = _safe_np(game.frames.id)
    if frame_ids is None:
        return []

    rows = []

    # Check each player — if their opponent is Fox, scan Fox's knockdowns
    for fox_slot_idx, (fox_slot, fox_player) in enumerate(active_players):
        try:
            fox_char = character_name(int(fox_player.character))
        except Exception:
            continue
        if fox_char != "Fox":
            continue

        att_slot_idx = 1 - fox_slot_idx
        att_slot, att_player = active_players[att_slot_idx]
        try:
            att_char = character_name(int(att_player.character))
        except Exception:
            continue

        # Extract minimal fields from peppi_py raw data
        fox_port = game.frames.ports[fox_slot]
        att_port = game.frames.ports[att_slot]
        if fox_port is None or fox_port.leader is None:
            continue
        if att_port is None or att_port.leader is None:
            continue

        opp_states = _safe_np(fox_port.leader.post.state)
        opp_pct = _safe_np(fox_port.leader.post.percent)
        opp_x = _safe_np(fox_port.leader.post.position.x)
        opp_dir = _safe_np(fox_port.leader.post.direction)
        opp_stocks = _safe_np(fox_port.leader.post.stocks)
        opp_lal = _safe_np(fox_port.leader.post.last_attack_landed)

        att_states_raw = _safe_np(att_port.leader.post.state)
        att_x = _safe_np(att_port.leader.post.position.x)

        if any(x is None for x in [opp_states, opp_pct, opp_x, opp_dir, opp_stocks, att_states_raw, att_x]):
            continue

        opp_frames = frame_ids.astype(int)
        opp_pct = opp_pct.astype(float)
        opp_x = opp_x.astype(float)
        opp_dir = opp_dir.astype(float)
        att_frames = frame_ids.astype(int)
        att_states = att_states_raw.astype(float)

        def _get_att_x(frame):
            idx = np.searchsorted(att_frames, frame)
            if idx < len(att_frames) and att_frames[idx] == frame:
                return float(att_x[idx])
            return None

        seen_frames = set()

        # ── Path A: Successful techs (199, 200, 201) ────────────────
        for i in range(1, len(opp_states)):
            s = int(opp_states[i]) if not pd.isna(opp_states[i]) else 0
            prev_s = int(opp_states[i - 1]) if not pd.isna(opp_states[i - 1]) else 0

            if s == _TECH_IN_PLACE and prev_s != _TECH_IN_PLACE:
                option_name = "tech in place"
            elif s in {_TECH_ROLL_F, _TECH_ROLL_B} and prev_s not in {_TECH_ROLL_F, _TECH_ROLL_B}:
                ax_val = _get_att_x(int(opp_frames[i]))
                if ax_val is not None:
                    d = classify_direction(float(opp_x[i]), ax_val,
                                           float(opp_dir[i]), s == _TECH_ROLL_F)
                    option_name = f"tech {d}"
                else:
                    option_name = "tech roll"
            else:
                continue

            kd_frame = int(opp_frames[i])
            if kd_frame in seen_frames:
                continue
            seen_frames.add(kd_frame)
            kd_pct = float(opp_pct[i]) if not np.isnan(opp_pct[i]) else 0.0

            # Check followup hit
            followup_hit, followup_move = _check_followup(
                opp_pct, opp_frames, opp_lal, i, kd_frame, 90)

            att_resp = classify_attacker_response(att_states, att_frames, kd_frame)

            rows.append({
                "attacker_character": att_char,
                "tech_option": option_name,
                "knockdown_pct": kd_pct,
                "followup_hit": followup_hit,
                "followup_move": followup_move,
                "attacker_response": att_resp,
                "filename": fpath.name,
                "frame": kd_frame,
            })

        # ── Path B: Missed tech bounces (183, 191) ──────────────────
        for i in range(1, len(opp_states)):
            s = int(opp_states[i]) if not pd.isna(opp_states[i]) else 0
            prev_s = int(opp_states[i - 1]) if not pd.isna(opp_states[i - 1]) else 0

            if s not in _MISSED_BOUND or prev_s in _MISSED_BOUND:
                continue

            kd_frame = int(opp_frames[i])
            if kd_frame in seen_frames:
                continue
            seen_frames.add(kd_frame)

            kd_pct = float(opp_pct[i]) if not np.isnan(opp_pct[i]) else 0.0
            kd_stocks = int(opp_stocks[i]) if not pd.isna(opp_stocks[i]) else 0

            option_name = None
            option_frame = kd_frame

            for j in range(i + 1, min(i + 300, len(opp_states))):
                sj = int(opp_states[j]) if not pd.isna(opp_states[j]) else 0

                if sj in _MISSED_BOUND or sj in _MISSED_WAIT:
                    continue

                sj_stocks = int(opp_stocks[j]) if not pd.isna(opp_stocks[j]) else 0
                if sj_stocks < kd_stocks:
                    option_name = "died"
                    break

                if sj in _HIT_DOWN:
                    option_name = "hit while down"
                    option_frame = int(opp_frames[j])
                elif sj in _GETUP:
                    option_name = "getup"
                    option_frame = int(opp_frames[j])
                elif sj in _GETUP_ATTACK:
                    option_name = "getup attack"
                    option_frame = int(opp_frames[j])
                elif sj in _DOWN_ROLL_F or sj in _DOWN_ROLL_B:
                    ax_val = _get_att_x(int(opp_frames[j]))
                    if ax_val is not None:
                        d = classify_direction(float(opp_x[j]), ax_val,
                                               float(opp_dir[j]), sj in _DOWN_ROLL_F)
                        option_name = f"roll {d}"
                    else:
                        option_name = "roll"
                    option_frame = int(opp_frames[j])
                else:
                    option_name = "missed tech (other)"
                    option_frame = int(opp_frames[j])
                break

            if option_name is None or option_name == "died":
                continue

            followup_hit, followup_move = _check_followup(
                opp_pct, opp_frames, opp_lal, i, option_frame, 90)

            att_resp = classify_attacker_response(att_states, att_frames, kd_frame)

            rows.append({
                "attacker_character": att_char,
                "tech_option": option_name,
                "knockdown_pct": kd_pct,
                "followup_hit": followup_hit,
                "followup_move": followup_move,
                "attacker_response": att_resp,
                "filename": fpath.name,
                "frame": kd_frame,
            })

    return rows


def _check_followup(opp_pct, opp_frames, opp_lal, start_i, search_start, window):
    """Check if the attacker landed a followup hit within window frames."""
    followup_hit = False
    followup_move = None
    for j in range(start_i, min(start_i + 400, len(opp_pct))):
        if int(opp_frames[j]) < search_start:
            continue
        if int(opp_frames[j]) > search_start + window:
            break
        if j > 0 and not np.isnan(opp_pct[j]) and not np.isnan(opp_pct[j - 1]):
            if opp_pct[j] > opp_pct[j - 1]:
                followup_hit = True
                if opp_lal is not None:
                    last_atk = opp_lal[j]
                    if not pd.isna(last_atk):
                        followup_move = move_name(int(last_atk))
                break
    return followup_hit, followup_move


# ─── Sample and scan ─────────────────────────────────────────────────────────

print(f"Finding .slp files in {REPLAY_DIR} ...")
all_slps = list(REPLAY_DIR.glob("*.slp"))
print(f"  Found {len(all_slps)} replay files")

random.seed(SEED)
sample = random.sample(all_slps, min(SAMPLE_N, len(all_slps)))
print(f"  Sampled {len(sample)} replays")

print("Scanning for Fox knockdowns ...")
all_rows = []
games_with_fox = 0
for idx, fpath in enumerate(sample):
    if (idx + 1) % 100 == 0:
        print(f"  ... {idx + 1}/{len(sample)} replays processed ({len(all_rows)} knockdowns so far)")
    game_rows = _scan_game_knockdowns(fpath)
    if game_rows:
        games_with_fox += 1
    all_rows.extend(game_rows)

df = pd.DataFrame(all_rows)

if df.empty:
    print("No Fox knockdown situations found!")
    sys.exit(0)

print(f"\nGames scanned: {len(sample)}")
print(f"Games with Fox: {games_with_fox}")
print(f"Total Fox knockdown situations: {len(df)}")


# ─── Summary stats ───────────────────────────────────────────────────────────

TECH_ORDER = [
    "tech away", "tech roll", "roll away",
    "tech in place",
    "tech toward", "roll toward",
    "getup", "getup attack",
    "hit while down", "missed tech (other)",
]

def _ordered(counts):
    ordered = [o for o in TECH_ORDER if o in counts.index]
    extras = [o for o in counts.index if o not in TECH_ORDER]
    return counts.reindex(ordered + extras)


print(f"\n{'='*60}")
print(f"FOX TECH OPTION DISTRIBUTION (n={len(df)})")
print(f"{'='*60}")

tech_counts = _ordered(df["tech_option"].value_counts())
tech_pcts = (tech_counts / len(df) * 100).round(1)

for opt, cnt in tech_counts.items():
    print(f"  {opt:<25s}  {cnt:4d}  ({tech_pcts[opt]:.1f}%)")


print(f"\n{'='*60}")
print(f"CONVERSION RATE BY TECH OPTION")
print(f"{'='*60}")

conv = df.groupby("tech_option").agg(
    total=("followup_hit", "count"),
    converted=("followup_hit", "sum"),
)
conv_order = [o for o in TECH_ORDER + list(conv.index) if o in conv.index]
conv = conv.reindex(conv_order)
conv = conv[~conv.index.duplicated()]
conv["rate"] = (conv["converted"] / conv["total"] * 100).round(1)

for opt in conv.index:
    r = conv.loc[opt]
    print(f"  {opt:<25s}  {int(r['converted']):3d}/{int(r['total']):3d}  ({r['rate']:.1f}%)")


print(f"\n{'='*60}")
print(f"ATTACKER RESPONSE (what the opponent did)")
print(f"{'='*60}")

resp_counts = df["attacker_response"].value_counts()
for resp, cnt in resp_counts.items():
    sub = df[df["attacker_response"] == resp]
    hit_rate = sub["followup_hit"].mean() * 100
    print(f"  {resp:<20s}  {cnt:4d} used  ({hit_rate:.0f}% hit rate)")


print(f"\n{'='*60}")
print(f"FOLLOWUP MOVES THAT HIT")
print(f"{'='*60}")

converted = df[df["followup_hit"]].copy()
if len(converted) > 0:
    move_counts = converted["followup_move"].value_counts()
    for mv, cnt in move_counts.head(15).items():
        print(f"  {mv:<20s}  {cnt:3d}  ({cnt/len(converted)*100:.1f}%)")


print(f"\n{'='*60}")
print(f"BY ATTACKER CHARACTER (top 10)")
print(f"{'='*60}")

for char_name, char_df in df.groupby("attacker_character"):
    n = len(char_df)
    if n < 10:
        continue
    n_conv = char_df["followup_hit"].sum()
    print(f"\n  {char_name} vs Fox (n={n}, converted={int(n_conv)}, rate={n_conv/n*100:.1f}%)")
    char_tech = _ordered(char_df["tech_option"].value_counts())
    for opt, cnt in char_tech.head(8).items():
        n_hit = char_df[char_df["tech_option"] == opt]["followup_hit"].sum()
        print(f"    {opt:<25s}  {cnt:3d}  ({cnt/n*100:.1f}%)  conv: {int(n_hit)}/{cnt}")


# ─── Chart 1: Tech option distribution + conversion rate ────────────────────

ordered_options = list(tech_counts.index)

fig, axes = plt.subplots(1, 2, figsize=(16, 7), gridspec_kw={"width_ratios": [1.2, 1]})

colors_map = {
    "tech away": "#e74c3c",
    "roll away": "#e67e22",
    "tech in place": "#3498db",
    "tech toward": "#2ecc71",
    "roll toward": "#27ae60",
    "getup": "#95a5a6",
    "getup attack": "#7f8c8d",
    "hit while down": "#c0392b",
    "missed tech (other)": "#bdc3c7",
    "tech roll": "#f39c12",
}

ax = axes[0]
bar_colors = [colors_map.get(o, "#95a5a6") for o in reversed(ordered_options)]
y_pos = range(len(ordered_options))
vals = [float(tech_pcts[o]) for o in reversed(ordered_options)]
labels = list(reversed(ordered_options))

bars = ax.barh(y_pos, vals, color=bar_colors, edgecolor="white", height=0.7)
ax.set_yticks(y_pos)
ax.set_yticklabels(labels, fontsize=12)
ax.set_xlabel("% of knockdowns", fontsize=12)
ax.set_title(f"Fox Tech Options (n={len(df)} knockdowns, {len(sample)} games sampled)",
             fontsize=13, fontweight="bold")

for bar, val in zip(bars, vals):
    if not np.isnan(val) and val > 0:
        ax.text(bar.get_width() + 0.3, bar.get_y() + bar.get_height()/2,
                f"{val:.1f}%", va="center", fontsize=11, fontweight="bold")

ax.set_xlim(0, max(v for v in vals if not np.isnan(v)) * 1.25 if vals else 10)
ax.spines["top"].set_visible(False)
ax.spines["right"].set_visible(False)

ax2 = axes[1]
conv_opts = [o for o in ordered_options if o in conv.index]
conv_rates = [float(conv.loc[o, "rate"]) for o in reversed(conv_opts)]
conv_labels = list(reversed(conv_opts))
conv_n = [f"({int(conv.loc[o, 'converted'])}/{int(conv.loc[o, 'total'])})" for o in reversed(conv_opts)]
bar_colors2 = [colors_map.get(o, "#95a5a6") for o in reversed(conv_opts)]

y_pos2 = range(len(conv_opts))
bars2 = ax2.barh(y_pos2, conv_rates, color=bar_colors2, edgecolor="white", height=0.7, alpha=0.8)
ax2.set_yticks(y_pos2)
ax2.set_yticklabels(conv_labels, fontsize=12)
ax2.set_xlabel("Conversion rate %", fontsize=12)
ax2.set_title("Opponent Conversion Rate per Tech Option", fontsize=13, fontweight="bold")

for bar, rate, n_label in zip(bars2, conv_rates, conv_n):
    if not np.isnan(rate):
        ax2.text(bar.get_width() + 0.5, bar.get_y() + bar.get_height()/2,
                f"{rate:.0f}% {n_label}", va="center", fontsize=10)

ax2.set_xlim(0, 100)
ax2.spines["top"].set_visible(False)
ax2.spines["right"].set_visible(False)

plt.tight_layout()
fig.savefig(OUT_DIR / "tech_chases_options.png", dpi=150, bbox_inches="tight")
print(f"\nSaved: {OUT_DIR / 'tech_chases_options.png'}")
plt.close()


# ─── Chart 2: Attacker response × tech option heatmap ───────────────────────

cross = pd.crosstab(df["tech_option"], df["attacker_response"])
if "Other/None" in cross.columns and cross.shape[1] > 2:
    cross = cross.drop(columns=["Other/None"])
cross = cross.loc[cross.sum(axis=1) >= 5, cross.sum(axis=0) >= 5]
cross = cross.reindex([o for o in TECH_ORDER if o in cross.index])

if cross.shape[0] >= 2 and cross.shape[1] >= 2:
    cross_pct = cross.div(cross.sum(axis=1), axis=0) * 100

    fig, ax = plt.subplots(figsize=(max(12, cross.shape[1] * 1.3), max(5, cross.shape[0] * 0.9)))
    im = ax.imshow(cross_pct.values, cmap="YlOrRd", aspect="auto", vmin=0, vmax=60)

    ax.set_xticks(range(cross_pct.shape[1]))
    ax.set_xticklabels(cross_pct.columns, fontsize=11, rotation=45, ha="right")
    ax.set_yticks(range(cross_pct.shape[0]))
    ax.set_yticklabels(cross_pct.index, fontsize=11)

    for i in range(cross_pct.shape[0]):
        for j in range(cross_pct.shape[1]):
            count = cross.iloc[i, j]
            pct = cross_pct.iloc[i, j]
            if count > 0:
                text_color = "white" if pct > 35 else "black"
                ax.text(j, i, f"{count}\n({pct:.0f}%)",
                        ha="center", va="center", fontsize=8,
                        color=text_color, fontweight="bold")

    ax.set_title(f"Opponent Response by Fox Tech Option (all attempts, n={len(df)})",
                 fontsize=13, fontweight="bold")
    ax.set_xlabel("Opponent's Move Choice", fontsize=12)
    ax.set_ylabel("Fox's Tech Option", fontsize=12)

    plt.colorbar(im, ax=ax, label="% of responses", shrink=0.8)
    plt.tight_layout()
    fig.savefig(OUT_DIR / "tech_chases_heatmap.png", dpi=150, bbox_inches="tight")
    print(f"Saved: {OUT_DIR / 'tech_chases_heatmap.png'}")
    plt.close()


# ─── Chart 3: Conversion rate by knockdown % bucket ─────────────────────────

df["pct_bucket"] = pd.cut(
    df["knockdown_pct"],
    bins=[0, 30, 60, 90, 120, 999],
    labels=["0-30%", "30-60%", "60-90%", "90-120%", "120%+"],
    right=False,
)
bucket_conv = df.groupby("pct_bucket", observed=True).agg(
    total=("followup_hit", "count"),
    converted=("followup_hit", "sum"),
)
bucket_conv["rate"] = (bucket_conv["converted"] / bucket_conv["total"] * 100).round(1)

fig, ax = plt.subplots(figsize=(10, 5))
x = range(len(bucket_conv))
bars = ax.bar(x, bucket_conv["rate"], color="#3498db", edgecolor="white", width=0.6)
ax.set_xticks(x)
ax.set_xticklabels(bucket_conv.index, fontsize=12)
ax.set_ylabel("Conversion Rate %", fontsize=12)
ax.set_xlabel("Fox's % at Knockdown", fontsize=12)
ax.set_title(f"Tech Chase Conversion Rate by Knockdown %\n(n={len(df)}, {len(sample)} games)",
             fontsize=13, fontweight="bold")
ax.set_ylim(0, 100)

for bar, (_, row) in zip(bars, bucket_conv.iterrows()):
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1,
            f"{row['rate']:.0f}%\n({int(row['converted'])}/{int(row['total'])})",
            ha="center", va="bottom", fontsize=10, fontweight="bold")

ax.spines["top"].set_visible(False)
ax.spines["right"].set_visible(False)
plt.tight_layout()
fig.savefig(OUT_DIR / "tech_chases_by_pct.png", dpi=150, bbox_inches="tight")
print(f"Saved: {OUT_DIR / 'tech_chases_by_pct.png'}")
plt.close()

# ─── Chart 4: Overall vs Peach matchup side-by-side comparison ───────────────

peach_df = df[df["attacker_character"] == "Peach"].copy()

if len(peach_df) >= 10:
    overall_counts = _ordered(df["tech_option"].value_counts())
    peach_counts = _ordered(peach_df["tech_option"].value_counts())

    # Align on the same options
    all_opts = list(overall_counts.index)
    overall_pcts = (overall_counts / len(df) * 100).reindex(all_opts).fillna(0)
    peach_pcts = (peach_counts / len(peach_df) * 100).reindex(all_opts).fillna(0)

    # Spatial order for display: away options at top, toward at bottom
    display_order = list(reversed(all_opts))

    x_overall = [float(overall_pcts[o]) for o in display_order]
    x_peach   = [float(peach_pcts[o])   for o in display_order]
    labels    = display_order
    n_opts    = len(labels)
    y         = np.arange(n_opts)
    height    = 0.35

    fig, ax = plt.subplots(figsize=(14, max(6, n_opts * 0.7)))

    bars_all   = ax.barh(y + height/2, x_overall, height=height,
                         label=f"All matchups (n={len(df)})",
                         color="#5b9bd5", edgecolor="white")
    bars_peach = ax.barh(y - height/2, x_peach, height=height,
                         label=f"vs Peach only (n={len(peach_df)})",
                         color="#ed7d31", edgecolor="white")

    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=12)
    ax.set_xlabel("% of Fox knockdowns", fontsize=12)
    ax.set_title("Fox Tech Options: All Matchups vs Peach Matchup", fontsize=14, fontweight="bold")
    ax.legend(fontsize=11, loc="lower right")

    max_val = max(max(x_overall), max(x_peach))
    ax.set_xlim(0, max_val * 1.3)

    for bar, val in zip(bars_all, x_overall):
        if val > 0.5:
            ax.text(bar.get_width() + 0.3, bar.get_y() + bar.get_height()/2,
                    f"{val:.1f}%", va="center", fontsize=9, color="#5b9bd5", fontweight="bold")

    for bar, val in zip(bars_peach, x_peach):
        if val > 0.5:
            ax.text(bar.get_width() + 0.3, bar.get_y() + bar.get_height()/2,
                    f"{val:.1f}%", va="center", fontsize=9, color="#ed7d31", fontweight="bold")

    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    plt.tight_layout()
    fig.savefig(OUT_DIR / "tech_chases_peach_comparison.png", dpi=150, bbox_inches="tight")
    print(f"Saved: {OUT_DIR / 'tech_chases_peach_comparison.png'}")
    plt.close()
else:
    print(f"Not enough Peach vs Fox data for comparison chart (n={len(peach_df)}).")

print("\nDone!")
