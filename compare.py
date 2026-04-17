#!/usr/bin/env python3
"""
Compare two simulation runs from the results/ directory.

Usage:
    python compare.py <run_id_A> <run_id_B>

Example:
    python compare.py v1_2_20260401_175626 v2_2_20260417_134519

If no arguments are provided, lists available runs.
"""

import sys
import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec

RESULTS_DIR = os.path.join(os.path.dirname(__file__), "results")


def list_runs() -> list[str]:
    return sorted(
        d for d in os.listdir(RESULTS_DIR)
        if os.path.isdir(os.path.join(RESULTS_DIR, d))
        and os.path.exists(os.path.join(RESULTS_DIR, d, "summary.csv"))
    )


def load_run(run_id: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    run_dir = os.path.join(RESULTS_DIR, run_id)
    summary = pd.read_csv(os.path.join(run_dir, "summary.csv"))
    runs = pd.read_csv(os.path.join(run_dir, "runs.csv"))
    return summary, runs


def plot_steps_to_clean(sumA: pd.DataFrame, sumB: pd.DataFrame, idA: str, idB: str, ax: plt.Axes, max_steps: int) -> None:
    """Side-by-side grouped bars: mean steps to clean per config."""
    configs = sumA["config"].unique()
    x = np.arange(len(configs))
    width = 0.35

    def agg(df, configs, max_steps):
        means, stds, clean_rates = [], [], []
        for c in configs:
            sub = df[df["config"] == c]["steps_to_clean"].fillna(max_steps)
            means.append(sub.mean())
            stds.append(sub.std() if len(sub) > 1 else 0)
            clean_rates.append((df[df["config"] == c]["cleaned"].sum() / len(df[df["config"] == c])) * 100)
        return np.array(means), np.array(stds), np.array(clean_rates)

    mA, sA, crA = agg(sumA, configs, max_steps)
    mB, sB, crB = agg(sumB, configs, max_steps)

    barsA = ax.bar(x - width / 2, mA, width, yerr=sA, capsize=3,
                   label=idA, color="#a8d8ea", edgecolor="black", error_kw={"elinewidth": 0.8})
    barsB = ax.bar(x + width / 2, mB, width, yerr=sB, capsize=3,
                   label=idB, color="#f4a261", edgecolor="black", error_kw={"elinewidth": 0.8})

    # Annotate clean rate %
    for bar, cr in zip(barsA, crA):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + max(sA) * 0.05,
                f"{cr:.0f}%", ha="center", va="bottom", fontsize=6, color="#1a6e99")
    for bar, cr in zip(barsB, crB):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + max(sB) * 0.05,
                f"{cr:.0f}%", ha="center", va="bottom", fontsize=6, color="#b94e10")

    ax.set_xticks(x)
    ax.set_xticklabels(configs, rotation=30, ha="right", fontsize=7)
    ax.set_ylabel("Mean steps to clean (NaN → max_steps)")
    ax.set_title("Steps to clean by configuration\n(% = fraction of runs fully cleaned)")
    ax.legend()
    ax.axhline(max_steps, color="gray", linestyle="--", linewidth=0.7, alpha=0.5)


def plot_fraction_curves(runsA: pd.DataFrame, runsB: pd.DataFrame, idA: str, idB: str,
                          configs: list[str], out_dir: str) -> None:
    """Per-config subplot: fraction_disposed curve for both runs."""
    n = len(configs)
    ncols = 3
    nrows = (n + ncols - 1) // ncols
    fig, axes = plt.subplots(nrows, ncols, figsize=(6 * ncols, 3.5 * nrows), sharey=True)
    axes = axes.flatten()

    def mean_curve(runs_df, config):
        sub = runs_df[runs_df["config"] == config]
        pivot = sub.pivot(index="step", columns="run", values="fraction_disposed")
        pivot = pivot.reindex(range(pivot.index.max() + 1)).ffill()
        return pivot.mean(axis=1), pivot.std(axis=1).fillna(0)

    for ax, config in zip(axes, configs):
        mA, sA = mean_curve(runsA, config)
        mB, sB = mean_curve(runsB, config)
        ax.plot(mA.index, mA.values, color="#1a6e99", label=idA, linewidth=1.5)
        ax.fill_between(mA.index, np.maximum(mA - sA, 0), mA + sA, alpha=0.2, color="#1a6e99")
        ax.plot(mB.index, mB.values, color="#b94e10", label=idB, linewidth=1.5)
        ax.fill_between(mB.index, np.maximum(mB - sB, 0), mB + sB, alpha=0.2, color="#b94e10")
        ax.axhline(1.0, color="gray", linestyle="--", linewidth=0.7)
        ax.set_title(config, fontsize=9)
        ax.set_xlabel("Step", fontsize=7)
        ax.set_ylabel("Fraction disposed", fontsize=7)
        ax.set_ylim(-0.05, 1.1)
        ax.legend(fontsize=6)

    for ax in axes[n:]:
        ax.set_visible(False)

    fig.suptitle("Fraction of waste disposed over time", fontsize=13)
    fig.tight_layout()
    path = os.path.join(out_dir, "fraction_curves_comparison.png")
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved {path}")


def plot_delta_table(sumA: pd.DataFrame, sumB: pd.DataFrame, idA: str, idB: str,
                     configs: list[str], ax: plt.Axes, max_steps: int) -> None:
    """Table showing Δ mean steps (B - A) and Δ clean rate per config."""
    rows = []
    for c in configs:
        a = sumA[sumA["config"] == c]["steps_to_clean"].fillna(max_steps)
        b = sumB[sumB["config"] == c]["steps_to_clean"].fillna(max_steps)
        crA = sumA[sumA["config"] == c]["cleaned"].mean() * 100
        crB = sumB[sumB["config"] == c]["cleaned"].mean() * 100
        delta_steps = b.mean() - a.mean()
        delta_cr = crB - crA
        rows.append([c, f"{a.mean():.0f}", f"{b.mean():.0f}",
                     f"{delta_steps:+.0f}", f"{crA:.0f}%", f"{crB:.0f}%", f"{delta_cr:+.0f}pp"])

    headers = ["Config", f"Steps {idA}", f"Steps {idB}", "Δ Steps",
               f"Clean% {idA}", f"Clean% {idB}", "Δ Clean%"]
    ax.axis("off")
    tbl = ax.table(cellText=rows, colLabels=headers, loc="center", cellLoc="center")
    tbl.auto_set_font_size(False)
    tbl.set_fontsize(7.5)
    tbl.scale(1, 1.4)

    # Color Δ Steps: green=improvement (less steps), red=regression
    for i, row in enumerate(rows):
        delta = float(row[3])
        color = "#c8f7c5" if delta < 0 else ("#f9c0c0" if delta > 0 else "#ffffff")
        tbl[i + 1, 3].set_facecolor(color)
        delta_cr = float(row[6].replace("pp", ""))
        color_cr = "#c8f7c5" if delta_cr > 0 else ("#f9c0c0" if delta_cr < 0 else "#ffffff")
        tbl[i + 1, 6].set_facecolor(color_cr)

    ax.set_title(f"Summary comparison: {idA}  vs  {idB}", fontsize=10, pad=12)


def compare(idA: str, idB: str) -> None:
    print(f"\nComparing:\n  A = {idA}\n  B = {idB}")

    sumA, runsA = load_run(idA)
    sumB, runsB = load_run(idB)

    configs = list(sumA["config"].unique())
    max_steps_A = int(runsA["step"].max()) + 1
    max_steps_B = int(runsB["step"].max()) + 1
    max_steps = max(max_steps_A, max_steps_B)

    out_dir = os.path.join(RESULTS_DIR, f"compare_{idA}_vs_{idB}")
    os.makedirs(out_dir, exist_ok=True)

    # --- Figure 1: steps bar + delta table ---
    fig = plt.figure(figsize=(18, 12))
    gs = gridspec.GridSpec(2, 1, height_ratios=[1, 1.2], hspace=0.5)
    ax_bar = fig.add_subplot(gs[0])
    ax_tbl = fig.add_subplot(gs[1])

    plot_steps_to_clean(sumA, sumB, idA, idB, ax_bar, max_steps)
    plot_delta_table(sumA, sumB, idA, idB, configs, ax_tbl, max_steps)

    path1 = os.path.join(out_dir, "steps_comparison.png")
    fig.savefig(path1, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved {path1}")

    # --- Figure 2: per-config fraction curves ---
    plot_fraction_curves(runsA, runsB, idA, idB, configs, out_dir)

    # --- CSV delta summary ---
    delta_rows = []
    for c in configs:
        a = sumA[sumA["config"] == c]["steps_to_clean"].fillna(max_steps)
        b = sumB[sumB["config"] == c]["steps_to_clean"].fillna(max_steps)
        crA = sumA[sumA["config"] == c]["cleaned"].mean()
        crB = sumB[sumB["config"] == c]["cleaned"].mean()
        delta_rows.append({
            "config": c,
            f"mean_steps_{idA}": a.mean(),
            f"mean_steps_{idB}": b.mean(),
            "delta_steps": b.mean() - a.mean(),
            f"clean_rate_{idA}": crA,
            f"clean_rate_{idB}": crB,
            "delta_clean_rate": crB - crA,
        })
    pd.DataFrame(delta_rows).to_csv(os.path.join(out_dir, "delta_summary.csv"), index=False)
    print(f"  Saved {os.path.join(out_dir, 'delta_summary.csv')}")
    print(f"\nAll outputs in: {out_dir}/")


if __name__ == "__main__":
    available = list_runs()
    if len(sys.argv) < 3:
        print("Available runs:")
        for r in available:
            print(f"  {r}")
        print("\nUsage: python compare.py <run_id_A> <run_id_B>")
        sys.exit(0 if len(sys.argv) == 1 else 1)

    idA, idB = sys.argv[1], sys.argv[2]
    for rid in (idA, idB):
        if rid not in available:
            print(f"Error: run '{rid}' not found in {RESULTS_DIR}/")
            print("Available:", ", ".join(available))
            sys.exit(1)

    compare(idA, idB)
