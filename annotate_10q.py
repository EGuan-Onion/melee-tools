"""
Annotate the 10Q charts as PowerPoint-style slides with insight callouts.
Saves annotated versions to replays/outputs/10q/slides/
"""

import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.image import imread
from pathlib import Path

SRC  = "replays/outputs/10q"
OUT  = "replays/outputs/10q/slides"
os.makedirs(OUT, exist_ok=True)

BG       = "#0d0d1a"
PANEL_BG = "#12122a"
TITLE_BG = "#1a1a3e"
ACCENT   = "#e94560"
CYAN     = "#06b6d4"
GOLD     = "#f59e0b"
GREEN    = "#10b981"
WHITE    = "#f0f0f0"
MUTED    = "#9090b0"

SLIDES = [
    {
        "file": "q1_combo_damage_by_opener.png",
        "title": "What opening move leads to the most damage?",
        "tag": "PUNISH GAME",
        "tag_color": ACCENT,
        "insights": [
            ("[KEY]",
             "Fair (n=170) and D-throw (n=176) are Sheik's most-used openers,\n"
             "but both only average 11-12% — very consistent, not explosive."),
            ("[+] Falcon standout",
             "Dair and Fair lead at 15% avg for Falcon. Uair is the most-used\n"
             "(n=197) at 12% — bread-and-butter but not a big conversion starter."),
            ("[!] Watch out",
             "The tight clustering at 10-15% across all moves suggests\n"
             "most 'combos' are just 1-2 hits. Real damage comes from extensions."),
            ("[>] Action item",
             "Sheik should look to convert Usmash (19% avg) more — small sample\n"
             "but clearly the highest-upside opener when it lands."),
        ]
    },
    {
        "file": "q2_kill_percent_by_move.png",
        "title": "Am I killing efficiently, or leaving percent on the table?",
        "tag": "KILL CONFIRMS",
        "tag_color": GOLD,
        "insights": [
            ("[KEY]",
             "Sheik's Neutral B kills at a median of 96%. It has kill power\n"
             "well before 100% — this should be the primary confirm tool."),
            ("[+] Wide spread on Fair",
             "Sheik Fair kills from 20% to 160+ % — that range shows a mix\n"
             "of early edgeguards and late desperate hits. Very different situations."),
            ("[!] Bair killing at 137%",
             "Sheik Bair median kill % of 137 is very late. Likely landing\n"
             "it as a stray hit, not as a confirm. Use it earlier offstage."),
            ("[>] Falcon efficiency",
             "Falcon D-smash killing at 97% median is solid — confirms it's\n"
             "being used as an edgeguard, not a panic option."),
        ]
    },
    {
        "file": "q3_sweetspot_rates.png",
        "title": "How often am I hitting the sweet hitbox?",
        "tag": "EXECUTION",
        "tag_color": CYAN,
        "insights": [
            ("[KEY]",
             "Falcon Fair sweetspot rate is 76% — decent, but 1 in 4 fairs\n"
             "is a sourspot, which deals 9% instead of 13%. That gap matters."),
            ("[+] Uair clean rate",
             "Uair (bair in position) hits clean only 54% of the time.\n"
             "Late hits do less damage and less knockback."),
            ("[!] Small sample caveat",
             "Sweetspot classification only covers moves in MOVE_HITBOXES.\n"
             "Add more characters/moves to get broader coverage."),
            ("[>] Target",
             "85%+ sweetspot rate on knee is a reasonable goal for a\n"
             "top-level Falcon. 76% on fair is a realistic improvement area."),
        ]
    },
    {
        "file": "q4_neutral_hit_rates.png",
        "title": "Which moves am I spamming vs. which ones actually connect?",
        "tag": "NEUTRAL GAME",
        "tag_color": GREEN,
        "insights": [
            ("[KEY]",
             "Sheik Fair: 500+ uses, only 36% hit rate — the most-used\n"
             "move with the worst accuracy. Classic telegraphed spacing tool."),
            ("[+] Underused efficiency",
             "Sheik D-tilt hits 55% and D-smash 54% — both used infrequently\n"
             "but connecting at far higher rates than Fair."),
            ("[!] Falcon Dash Attack",
             "57% hit rate is the best on the chart. Suggests opponents\n"
             "aren't expecting it — lean into this more in neutral."),
            ("[>] Action item",
             "Reduce Fair spam, increase D-tilt and Jab (45%). The data\n"
             "shows Falcon Jab at 50% hit rate is an underutilized neutral tool."),
        ]
    },
    {
        "file": "q5_moves_opponent_lands.png",
        "title": "What is the opponent hitting me with most?",
        "tag": "DEFENSIVE AWARENESS",
        "tag_color": ACCENT,
        "insights": [
            ("[KEY]",
             "Playing Sheik: opponent Dair lands 175+ times (avg 8.9% dmg).\n"
             "This is the Falco matchup — Falco Dair is the dominant threat."),
            ("[+] Falcon getting Baired",
             "Bair lands 200 times on Falcon at avg 11.7% — the highest\n"
             "damage-per-hit of any frequent move. Falco/Fox bair pressure."),
            ("[!] Neutral B volume",
             "Shine (Neutral B) landing 170+ times on Falcon is notable.\n"
             "Getting shine-grabbed repeatedly — need better DI out of shine."),
            ("[>] Matchup insight",
             "Both characters are dominated by the spacie matchup (Falco/Fox).\n"
             "Improving SDI on Falco Dair would have the biggest impact."),
        ]
    },
    {
        "file": "q6_combo_damage_distribution.png",
        "title": "How much damage do I deal per neutral win?",
        "tag": "PUNISH VALUE",
        "tag_color": GOLD,
        "insights": [
            ("[KEY]",
             "Sheik median: 9% per combo. Falcon median: 11%.\n"
             "Both are low — the majority of 'combos' are single-hit confirms."),
            ("[+] The important tail",
             "The 20-60% conversions are game-deciding. Sheik has ~50 combos\n"
             "in that range. These are the sequences worth reviewing on film."),
            ("[!] Kill combo rate",
             "Only 6% (Sheik) and 8% (Falcon) of combos end in a kill.\n"
             "Most kill attempts are happening outside of tracked combo windows."),
            ("[>] Benchmark",
             "Top-level Sheik averages 25-30% per conversion vs good opponents.\n"
             "There's significant room to extend combos past the first hit."),
        ]
    },
    {
        "file": "q7_knockdown_options.png",
        "title": "Are my knockdown options predictable?",
        "tag": "HABITS / DEFENSE",
        "tag_color": CYAN,
        "insights": [
            ("[KEY]",
             "Tech toward is the single most common option for both chars\n"
             "(Sheik 25%, Falcon 23%). Any opponent watching film will read this."),
            ("[+] Falcon more balanced",
             "Falcon's distribution is more even (tech in place 16%, tech away 16%,\n"
             "getup 15%) — harder to read, which is good."),
            ("[!] Sheik tech toward spike",
             "25% on a single option is exploitable. A smart opponent will\n"
             "camp the 'toward' tech and punish it for free damage every time."),
            ("[>] Target",
             "Aim for no single option above 20%. Add conscious getup attack\n"
             "and tech in place reps — currently only 14% each for Sheik."),
        ]
    },
    {
        "file": "q8_death_positions.png",
        "title": "Where and how am I dying?",
        "tag": "SURVIVAL",
        "tag_color": GREEN,
        "insights": [
            ("[KEY]",
             "Bottom blastzone is #1 for both chars: 50 of 98 Sheik deaths,\n"
             "48 of 88 Falcon deaths. Dying offstage > dying to KO moves."),
            ("[+] Right side bias",
             "Both characters die through the right blastzone more than left\n"
             "(26 vs 14 for Sheik, 24 vs 15 for Falcon). Stage position habit?"),
            ("[!] Getting edgeguarded",
             "Bottom deaths mean recovery is being intercepted. These aren't\n"
             "SD — they're opponents winning the edgeguard battle consistently."),
            ("[>] Priority",
             "Recovery mixups and DI on killing moves would reduce bottom deaths\n"
             "the most. Mixing up recovery timing and angles is the highest-value fix."),
        ]
    },
    {
        "file": "q9_dthrow_kill_conversion.png",
        "title": "Do I convert throws into kills at kill percent?",
        "tag": "KILL CONFIRMS",
        "tag_color": GOLD,
        "insights": [
            ("[KEY]",
             "Only 2 d-throw opportunities detected at 80%+ for Sheik.\n"
             "0% conversion rate — but the n=2 is the real issue here."),
            ("[+] Why so few d-throws?",
             "At kill percent vs Falco/Fox/Marth, Sheik rarely d-throws —\n"
             "she uses Fsmash, Usmash, or Bair/Fair edgeguards instead."),
            ("[!] Detection note",
             "Trigger uses the 'throw' action state category, which catches\n"
             "all throw directions. Sheik likely grabs but chooses U-throw or F-throw."),
            ("[>] Better question",
             "Reframe as: 'grab → kill' (any throw direction) to get a\n"
             "meaningful sample. Use find_confirmed_events(trigger='grab')."),
        ]
    },
    {
        "file": "q10_how_i_die.png",
        "title": "What move kills me most, and at what percent?",
        "tag": "WEAKNESSES",
        "tag_color": ACCENT,
        "insights": [
            ("[KEY]",
             "Playing Sheik: F-smash kills me 22 times at avg 92%.\n"
             "Opponents are landing Fsmash efficiently — I'm getting hit by it early."),
            ("[+] Falcon: Bair dominates",
             "Bair kills Falcon 30 times (most frequent) at avg 123%.\n"
             "This is the Falco bair out-of-shield / edgeguard pattern."),
            ("[!] Unknown(0) at 58%",
             "Falcon dying to 'Unknown' move at avg 58% suggests early deaths\n"
             "with move attribution errors — possibly chain grabs or zero-deaths."),
            ("[>] Film review targets",
             "Watch the 22 Fsmash deaths (Sheik) — are they punishing\n"
             "whiffed fairs? Landing lag? Identify the setup and patch it."),
        ]
    },
]


def make_slide(slide: dict, idx: int):
    fig = plt.figure(figsize=(20, 10), facecolor=BG)

    # ── Layout: left 68% = chart, right 32% = insights panel ──────────────
    ax_chart = fig.add_axes([0.01, 0.08, 0.64, 0.82])   # [left, bottom, w, h]
    ax_panel = fig.add_axes([0.67, 0.08, 0.31, 0.82])

    # ── Chart image ─────────────────────────────────────────────────────────
    img = imread(f"{SRC}/{slide['file']}")
    ax_chart.imshow(img)
    ax_chart.axis("off")
    ax_chart.set_facecolor(BG)

    # ── Slide header ─────────────────────────────────────────────────────────
    fig.text(
        0.01, 0.97, f"Q{idx+1}  /  {slide['title']}",
        fontsize=14, fontweight="bold", color=WHITE,
        fontfamily="monospace", va="top",
    )
    # Tag pill
    fig.text(
        0.68, 0.97, slide["tag"],
        fontsize=9, fontweight="bold", color=BG,
        fontfamily="monospace", va="top",
        bbox=dict(facecolor=slide["tag_color"], boxstyle="round,pad=0.4", edgecolor="none"),
    )

    # ── Insights panel ───────────────────────────────────────────────────────
    ax_panel.set_facecolor(PANEL_BG)
    ax_panel.set_xlim(0, 1)
    ax_panel.set_ylim(0, 1)
    ax_panel.axis("off")

    # Panel title
    ax_panel.text(
        0.05, 0.96, "KEY INSIGHTS",
        fontsize=10, fontweight="bold", color=MUTED,
        fontfamily="monospace", va="top", transform=ax_panel.transAxes,
    )

    # Divider line
    ax_panel.axhline(0.93, color=MUTED, lw=0.5, alpha=0.4)

    n = len(slide["insights"])
    block_h = 0.88 / n

    for i, (header, body) in enumerate(slide["insights"]):
        y_top = 0.91 - i * block_h

        # Colored left bar
        bar_color = [ACCENT, CYAN, GOLD, GREEN][i % 4]
        ax_panel.add_patch(mpatches.FancyBboxPatch(
            (0.01, y_top - block_h + 0.01), 0.025, block_h - 0.02,
            boxstyle="round,pad=0.005",
            facecolor=bar_color, edgecolor="none",
            transform=ax_panel.transAxes,
        ))

        # Header
        ax_panel.text(
            0.07, y_top - 0.01, header,
            fontsize=9, fontweight="bold", color=WHITE,
            fontfamily="monospace", va="top", transform=ax_panel.transAxes,
        )
        # Body
        ax_panel.text(
            0.07, y_top - 0.055, body,
            fontsize=8, color="#c0c0d8",
            fontfamily="monospace", va="top", transform=ax_panel.transAxes,
            linespacing=1.4,
        )

        if i < n - 1:
            ax_panel.axhline(
                y_top - block_h + 0.005, color=MUTED, lw=0.3, alpha=0.25,
                xmin=0.04, xmax=0.96,
            )

    # ── Footer ───────────────────────────────────────────────────────────────
    fig.text(
        0.01, 0.02, "melee-tools  ·  EG＃0  ·  65 games",
        fontsize=7.5, color=MUTED, fontfamily="monospace",
    )
    fig.text(
        0.99, 0.02, f"{idx+1} / {len(SLIDES)}",
        fontsize=7.5, color=MUTED, fontfamily="monospace", ha="right",
    )

    out_path = f"{OUT}/slide_{idx+1:02d}_{slide['file']}"
    fig.savefig(out_path, dpi=130, bbox_inches="tight", facecolor=BG)
    plt.close(fig)
    print(f"  saved slide {idx+1}: {out_path}")
    return out_path


print("Generating annotated slides...")
for i, slide in enumerate(SLIDES):
    make_slide(slide, i)

print(f"\nDone. {len(SLIDES)} slides saved to {OUT}/")
