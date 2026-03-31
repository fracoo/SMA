#!/usr/bin/env python3
"""
Batch simulation runner for RobotModel.

Usage:
    python simulate.py

Outputs:
    results/runs.csv       
        — per-step data for all runs
    results/summary.csv    
        — one row per run (steps to clean, etc.)
    results/plots/         
        — generated figures
"""

import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "15_robot_mission_MAS2026"))

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from model import RobotModel


# Configuration

MAX_STEPS = 5000
N_RUNS = 20  # independent runs per configuration (different seeds)
VERSION = "v0_1"

# Each entry: (label, params dict)
# n_waste = number of red waste units; total waste = 7 * n_waste (4 green + 2 yellow + 1 red)
CONFIGS = [
    # Vary number of robots on a fixed medium grid (n_waste=2 -> 14 total waste)
    ("1 robot/color",   {"n_green": 1, "n_yellow": 1, "n_red": 1,  "n_waste": 2, "height": 15, "width": 15}),
    ("3 robots/color",  {"n_green": 3, "n_yellow": 3, "n_red": 3,  "n_waste": 2, "height": 15, "width": 15}),
    ("10 robots/color", {"n_green": 10,"n_yellow": 10,"n_red": 10, "n_waste": 2, "height": 15, "width": 15}),
    ("14 robots/color", {"n_green": 14,"n_yellow": 14,"n_red": 14, "n_waste": 2, "height": 15, "width": 15}),
    # Vary width only
    # width must be divisible by 3; height fixed at 15; 5 robots/color
    ("Narrow (w=9)",  {"n_green": 5, "n_yellow": 5, "n_red": 5, "n_waste": 2, "height": 15, "width": 9}),
    ("Medium (w=15)", {"n_green": 5, "n_yellow": 5, "n_red": 5, "n_waste": 2, "height": 15, "width": 15}),
    ("Wide (w=21)",   {"n_green": 5, "n_yellow": 5, "n_red": 5, "n_waste": 2, "height": 15, "width": 21}),
    ("Very wide (w=30)", {"n_green": 5, "n_yellow": 5, "n_red": 5, "n_waste": 2, "height": 15, "width": 30}),
    # Vary height only
    # height fixed; width fixed at 15; 5 robots/color
    ("Short (h=6)",   {"n_green": 5, "n_yellow": 5, "n_red": 5, "n_waste": 2, "height": 6,  "width": 15}),
    ("Medium (h=15)", {"n_green": 5, "n_yellow": 5, "n_red": 5, "n_waste": 2, "height": 15, "width": 15}),
    ("Tall (h=24)",   {"n_green": 5, "n_yellow": 5, "n_red": 5, "n_waste": 2, "height": 24, "width": 15}),
    ("Very tall (h=36)", {"n_green": 5, "n_yellow": 5, "n_red": 5, "n_waste": 2, "height": 36, "width": 15}),
    # Vary waste density (5 robots/color, 15x15 grid)
    ("Low waste (n=1, 7 total)",   {"n_green": 5, "n_yellow": 5, "n_red": 5, "n_waste": 1, "height": 15, "width": 15}),
    ("High waste (n=4, 28 total)", {"n_green": 5, "n_yellow": 5, "n_red": 5, "n_waste": 4, "height": 15, "width": 15}),
    ("Very high waste (n=10, 70 total)", {"n_green": 5, "n_yellow": 5, "n_red": 5, "n_waste": 10, "height": 15, "width": 15}),
]

# Simulation helpers

def run_single(params: dict, seed: int) -> tuple[pd.DataFrame, bool]:
    """Run one simulation until cleaned or MAX_STEPS. Returns (timeseries_df, cleaned_fully)."""
    model = RobotModel(**params, seed=seed)
    for _ in range(MAX_STEPS):
        if model.waste_disposed >= model.total_initial_waste:
            break
        model.step()

    df = model.datacollector.get_model_vars_dataframe()
    df.index.name = "step"
    df = df.reset_index()
    cleaned = model.waste_disposed >= model.total_initial_waste
    return df, cleaned


def run_all() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Run all configurations and return (runs_df, summary_df)."""
    all_runs = []
    summary_rows = []

    for label, params in CONFIGS:
        print(f"\nConfig: {label}")
        for run_i in range(N_RUNS):
            seed = 107 + run_i * 17
            df, cleaned = run_single(params, seed)
            df["config"] = label
            df["run"] = run_i
            for k, v in params.items():
                df[k] = v
            all_runs.append(df)

            steps_to_clean = int(df["step"].max()) if cleaned else None
            summary_rows.append({
                "config": label,
                "run": run_i,
                "cleaned": cleaned,
                "steps_to_clean": steps_to_clean,
                **params,
            })
            status = f"cleaned in {steps_to_clean} steps" if cleaned else f"not fully cleaned ({df['fraction_disposed'].iloc[-1]:.1%} done)"
            print(f"  run {run_i + 1}/{N_RUNS}: {status}")

    runs_df = pd.concat(all_runs, ignore_index=True)
    summary_df = pd.DataFrame(summary_rows)
    return runs_df, summary_df


# Plotting

def plot_fraction_over_time(runs_df: pd.DataFrame, out_dir: str) -> None:
    """One subplot per config: mean fraction disposed +/- std across runs."""
    configs = runs_df["config"].unique()
    n = len(configs)
    ncols = 2
    nrows = (n + 1) // ncols

    fig, axes = plt.subplots(nrows, ncols, figsize=(14, 4 * nrows), sharey=True)
    axes = axes.flatten()

    for ax, config in zip(axes, configs):
        sub = runs_df[runs_df["config"] == config]
        grouped = sub.groupby("step")["fraction_disposed"]
        mean = grouped.mean()
        std = grouped.std().fillna(0)

        ax.plot(mean.index, mean.values, label="mean")
        ax.fill_between(mean.index, mean - std, mean + std, alpha=0.3, label="±1 std")
        ax.axhline(1.0, color="gray", linestyle="--", linewidth=0.8)
        ax.set_title(config, fontsize=10)
        ax.set_xlabel("Step")
        ax.set_ylabel("Fraction disposed")
        ax.set_ylim(-0.05, 1.1)
        ax.legend(fontsize=8)

    # hide unused subplots
    for ax in axes[n:]:
        ax.set_visible(False)

    fig.suptitle("Fraction of waste disposed over time", fontsize=13, y=1.01)
    fig.tight_layout()
    path = os.path.join(out_dir, "fraction_disposed_over_time.png")
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved {path}")


def plot_cleanup_rate_comparison(summary_df: pd.DataFrame, out_dir: str) -> None:
    """Bar chart: mean steps to clean + % of runs that fully cleaned."""
    configs_order = [c for c, _ in CONFIGS]

    means, stds, pct_cleaned = [], [], []
    for config in configs_order:
        sub = summary_df[summary_df["config"] == config]
        # Uncleaned runs are censored at MAX_STEPS so every run is counted,
        # avoiding the bias of averaging only the lucky successful runs.
        all_steps = sub["steps_to_clean"].fillna(MAX_STEPS)
        means.append(all_steps.mean())
        stds.append(all_steps.std() if len(all_steps) > 1 else 0)
        pct_cleaned.append(100 * sub["cleaned"].mean())

    x = np.arange(len(configs_order))
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(max(10, len(configs_order) * 1.5), 8))

    bars = ax1.bar(x, means, yerr=stds, capsize=5, color="#a8d8ea", edgecolor="black")
    ax1.axhline(MAX_STEPS, color="red", linestyle="--", linewidth=0.8, alpha=0.5, label=f"MAX_STEPS ({MAX_STEPS})")
    ax1.set_xticks(x)
    ax1.set_xticklabels(configs_order, rotation=25, ha="right")
    ax1.set_ylabel("Mean steps to clean")
    ax1.set_title("Mean steps to fully clean (uncleaned runs counted as MAX_STEPS)")
    ax1.legend(fontsize=8)

    ax2.bar(x, pct_cleaned, color="#ffd3b6", edgecolor="black")
    ax2.set_xticks(x)
    ax2.set_xticklabels(configs_order, rotation=25, ha="right")
    ax2.set_ylabel("% runs fully cleaned")
    ax2.set_ylim(0, 110)
    ax2.set_title(f"Fraction of runs fully cleaned within {MAX_STEPS} steps")

    fig.tight_layout()
    path = os.path.join(out_dir, "cleanup_rate_comparison.png")
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved {path}")


if __name__ == "__main__":
    run_id = f"{VERSION}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    out_dir = os.path.join(os.path.dirname(__file__), "results", run_id)
    plots_dir = os.path.join(out_dir, "plots")
    os.makedirs(plots_dir, exist_ok=True)
    print(f"Run ID: {run_id}")

    print("Running simulations :")
    runs_df, summary_df = run_all()

    runs_df.to_csv(os.path.join(out_dir, "runs.csv"), index=False)
    summary_df.to_csv(os.path.join(out_dir, "summary.csv"), index=False)
    print(f"\nData saved to {out_dir}/")

    print("\nGenerating plots :")
    plot_fraction_over_time(runs_df, plots_dir)
    plot_cleanup_rate_comparison(summary_df, plots_dir)

    print("\nDone.")
