"""Plotting utilities for habit analysis.

These functions take DataFrames produced by melee_tools.habits
(or any DataFrame with 'option' and 'percent' columns) and produce
frequency-by-damage-% charts.

Requires matplotlib and seaborn (optional dependencies).

Typical usage:
    from melee_tools import parse_replays, player_games, analyze_knockdowns
    from melee_tools.plotting import plot_options_by_percent

    games = parse_replays("replays")
    pg = player_games(games)
    kd = analyze_knockdowns("replays", pg, tag="EG＃0")

    # Group missed tech followups together
    kd["option"] = kd["option"].apply(
        lambda x: "missed tech" if x not in ("tech in place", "tech toward", "tech away") else x
    )

    plot_options_by_percent(kd, title="Knockdown Options (EG#0)")
"""

import numpy as np
import pandas as pd


def add_pct_buckets(
    df: pd.DataFrame,
    pct_col: str = "start_pct",
    cuts: list[float] | None = None,
) -> pd.DataFrame:
    """Add a 'bucket' column using custom cut points or auto-computed quartiles.

    Args:
        df: DataFrame with a percent column.
        pct_col: Column to bucket on.
        cuts: List of 3 cut points [Q1, Q2, Q3]. If None, uses the data's quartiles.

    Returns:
        Copy of df with 'bucket' (str label) and 'bucket_order' (int) columns.

    Example:
        combos = analyze_combos(...)
        combos = add_pct_buckets(combos, pct_col="start_pct")
        # or with manual cuts:
        combos = add_pct_buckets(combos, cuts=[40, 100, 150])
    """
    vals = df[pct_col].dropna().values
    if cuts is None:
        q1, q2, q3 = np.percentile(vals, [25, 50, 75])
    else:
        q1, q2, q3 = cuts

    labels = [
        f"Q1 (0-{q1:.0f}%)",
        f"Q2 ({q1:.0f}-{q2:.0f}%)",
        f"Q3 ({q2:.0f}-{q3:.0f}%)",
        f"Q4 ({q3:.0f}%+)",
    ]

    def _bucket(p):
        if p < q1:  return labels[0]
        if p < q2:  return labels[1]
        if p < q3:  return labels[2]
        return labels[3]

    def _order(p):
        if p < q1:  return 0
        if p < q2:  return 1
        if p < q3:  return 2
        return 3

    df = df.copy()
    df["bucket"] = df[pct_col].apply(_bucket)
    df["bucket_order"] = df[pct_col].apply(_order)
    return df


def plot_moves_by_bucket(
    df: pd.DataFrame,
    move_col: str = "move",
    bucket_col: str = "bucket",
    n_moves: int = 8,
    title: str = "Moves by % Bucket",
    save_path: str | None = None,
    figsize: tuple[float, float] = (12, 6),
):
    """Grouped bar chart showing move frequency broken down by percent bucket.

    Works with any DataFrame that has a move column and a bucket column,
    e.g. from analyze_combos() + add_pct_buckets(), or analyze_neutral_attacks()
    + add_pct_buckets().

    Args:
        df: DataFrame with move and bucket columns.
        move_col: Column containing move names.
        bucket_col: Column containing bucket labels (from add_pct_buckets).
        n_moves: Number of top moves to show.
        title: Chart title.
        save_path: If provided, saves the figure here.
        figsize: Figure size.

    Returns:
        (fig, ax) matplotlib figure and axes.

    Example:
        combos = analyze_combos("replays", pg, "EG＃0", character="Sheik")
        combos = add_pct_buckets(combos, pct_col="start_pct")
        # Rename started_by to move for compatibility
        combos["move"] = combos["started_by"]
        plot_moves_by_bucket(combos, title="Sheik Openers by %")
    """
    import matplotlib.pyplot as plt
    import matplotlib.ticker as mticker

    # Determine ordered bucket list
    if "bucket_order" in df.columns:
        bucket_order = (
            df[["bucket", "bucket_order"]]
            .drop_duplicates()
            .sort_values("bucket_order")["bucket"]
            .tolist()
        )
    else:
        bucket_order = sorted(df[bucket_col].unique())

    top_moves = (
        df[move_col].value_counts().head(n_moves).index.tolist()
    )

    data = {}
    for b in bucket_order:
        sub = df[df[bucket_col] == b]
        total = len(sub)
        counts = sub[move_col].value_counts()
        data[b] = [100 * counts.get(m, 0) / total for m in top_moves]

    x = np.arange(len(top_moves))
    n_buckets = len(bucket_order)
    width = 0.8 / n_buckets
    colors = ["#4e79a7", "#f28e2b", "#59a14f", "#e15759",
              "#76b7b2", "#edc948", "#b07aa1", "#ff9da7"]

    fig, ax = plt.subplots(figsize=figsize)
    for i, (b, color) in enumerate(zip(bucket_order, colors)):
        offset = (i - n_buckets / 2 + 0.5) * width
        ax.bar(x + offset, data[b], width, label=b, color=color, alpha=0.9)

    ax.set_xticks(x)
    ax.set_xticklabels(top_moves, fontsize=11)
    ax.set_ylabel("% of attacks", fontsize=11)
    ax.set_title(title, fontsize=13, fontweight="bold")
    ax.yaxis.set_major_formatter(mticker.FormatStrFormatter("%d%%"))
    ax.legend(fontsize=10)
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()

    if save_path:
        fig.savefig(save_path, dpi=150)

    return fig, ax


def bucket_percent(
    df: pd.DataFrame,
    percent_col: str = "percent",
    bucket_size: int = 20,
    cap: int = 140,
) -> pd.DataFrame:
    """Add pct_bucket and pct_sort columns to a DataFrame based on a percent column.

    Args:
        df: DataFrame with a percent column.
        percent_col: Name of the percent column.
        bucket_size: Width of each bucket in %.
        cap: Values >= cap are grouped into a single "{cap}+" bucket.

    Returns:
        Copy of df with 'pct_bucket' (str label) and 'pct_sort' (int) columns added.
    """
    df = df.copy()

    def _label(pct):
        if pct >= cap:
            return f"{cap}+"
        b = int(pct // bucket_size) * bucket_size
        return f"{b}-{b + bucket_size - 1}"

    def _sort(pct):
        return cap if pct >= cap else int(pct // bucket_size) * bucket_size

    df["pct_bucket"] = df[percent_col].apply(_label)
    df["pct_sort"] = df[percent_col].apply(_sort)
    return df


def compute_option_frequencies(
    df: pd.DataFrame,
    option_col: str = "option",
    percent_col: str = "percent",
    bucket_size: int = 20,
    cap: int = 140,
) -> tuple[pd.DataFrame, pd.DataFrame, list[str]]:
    """Compute per-bucket frequencies for each option.

    Args:
        df: DataFrame with option and percent columns.
        option_col: Name of the option column.
        percent_col: Name of the percent column.
        bucket_size: Width of each bucket in %.
        cap: Values >= cap are grouped into a single bucket.

    Returns:
        (grouped, totals, bucket_labels) where:
            grouped: DataFrame with pct_bucket, option, count, total, freq columns.
            totals: DataFrame with pct_bucket and total columns.
            bucket_labels: Ordered list of bucket label strings.
    """
    df = bucket_percent(df, percent_col, bucket_size, cap)

    totals = (
        df.groupby(["pct_sort", "pct_bucket"])
        .size()
        .reset_index(name="total")
        .sort_values("pct_sort")
    )
    bucket_labels = totals["pct_bucket"].tolist()

    grouped = (
        df.groupby(["pct_sort", "pct_bucket", option_col])
        .size()
        .reset_index(name="count")
    )
    grouped = grouped.merge(totals, on=["pct_sort", "pct_bucket"])
    grouped["freq"] = grouped["count"] / grouped["total"]

    return grouped, totals, bucket_labels


def plot_options_by_percent(
    df: pd.DataFrame,
    title: str = "Options by Damage %",
    option_col: str = "option",
    percent_col: str = "percent",
    bucket_size: int = 20,
    cap: int = 140,
    options: list[str] | None = None,
    colors: dict[str, str] | None = None,
    figsize: tuple[float, float] = (10, 5),
    ylim: tuple[float, float] = (0, 0.6),
    scaled_markers: bool = True,
    min_marker: float = 30,
    max_marker: float = 250,
    save_path: str | None = None,
):
    """Plot option frequency by damage % bucket as a line chart.

    Marker sizes are proportional to sample count per option per bucket.

    Args:
        df: DataFrame with option and percent columns.
        title: Plot title.
        option_col: Name of the option column.
        percent_col: Name of the percent column.
        bucket_size: Width of each bucket in %.
        cap: Values >= cap are grouped into a single bucket.
        options: Ordered list of options to plot. If None, plots all options
            sorted by overall frequency (most common first).
        colors: Dict mapping option name to color. If None, uses matplotlib defaults.
        figsize: Figure size as (width, height).
        ylim: Y-axis limits as (min, max).
        scaled_markers: If True, marker size scales with sample count.
        min_marker: Minimum marker size (points squared).
        max_marker: Maximum marker size (points squared).
        save_path: If provided, saves the figure to this path.

    Returns:
        (fig, ax) matplotlib figure and axes objects.
    """
    import matplotlib.pyplot as plt
    import seaborn as sns

    grouped, totals, bucket_labels = compute_option_frequencies(
        df, option_col, percent_col, bucket_size, cap,
    )

    if options is None:
        options = (
            grouped.groupby(option_col)["count"]
            .sum()
            .sort_values(ascending=False)
            .index.tolist()
        )

    sns.set_theme(style="whitegrid")
    fig, ax = plt.subplots(figsize=figsize)

    color_cycle = plt.rcParams["axes.prop_cycle"].by_key()["color"]

    for i, opt in enumerate(options):
        color = (colors or {}).get(opt, color_cycle[i % len(color_cycle)])
        sub = grouped[grouped[option_col] == opt].set_index("pct_bucket").reindex(bucket_labels)
        freqs = sub["freq"].fillna(0).values
        counts = sub["count"].fillna(0).values

        ax.plot(bucket_labels, freqs, linewidth=2, color=color, alpha=0.85, label=opt)

        if scaled_markers:
            global_max = grouped["count"].max()
            sizes = min_marker + (counts / max(global_max, 1)) * (max_marker - min_marker)
        else:
            sizes = 60
        ax.scatter(bucket_labels, freqs, s=sizes, color=color, alpha=0.85, zorder=5)

    ax.set_xlabel("Damage %", fontsize=12)
    ax.set_ylabel("Frequency", fontsize=12)
    ax.set_title(title, fontsize=13)
    ax.set_ylim(*ylim)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: f"{y:.0%}"))
    ax.legend(fontsize=11)

    # Sample size annotations along x-axis
    y_offset = ylim[0] - (ylim[1] - ylim[0]) * 0.06
    for _, row in totals.iterrows():
        ax.text(row["pct_bucket"], y_offset, f"n={int(row['total'])}",
                ha="center", fontsize=9, color="gray")

    plt.tight_layout()

    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches="tight")

    return fig, ax
