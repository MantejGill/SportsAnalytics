"""
Analyze and compare Auto-Negotiate vs Vanilla negotiation results.

Usage:
    # Auto-Negotiate only (13 quantitative metrics):
    python scripts/analyze_results.py --auto results/judged_100runs.csv

    # With vanilla comparison:
    python scripts/analyze_results.py \
        --auto    results/judged_100runs.csv \
        --vanilla results/vanilla_results.csv

    # Write empty vanilla template:
    python scripts/analyze_results.py --write-template

Outputs:
    results/summary_stats.csv      — per-metric stats table
    results/comparison_table.tex   — LaTeX table (if --vanilla provided)
    results/radar_chart.png        — judge score radar (if judge cols present)
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

RESULTS_DIR = Path(__file__).parent / "results"

QUANT_METRICS = [
    "market_realism",
    "outcome_quality_club",
    "outcome_quality_player",
    "efficiency",
    "compliance_rate",
    "concession_rate_club",
    "concession_rate_player",
    "concession_rate_club_pct",
    "concession_rate_player_pct",
    "rounds_used",
    "final_salary_eur",
]

JUDGE_METRICS = [
    "judge_market_alignment",
    "judge_player_outcome",
    "judge_club_outcome",
    "judge_contract_structure",
    "judge_reasoning_quality",
    "judge_overall",
]

JUDGE_LABELS = [
    "Market Alignment",
    "Player Outcome",
    "Club Outcome",
    "Contract Structure",
    "Reasoning Quality",
    "Overall",
]


# ---------------------------------------------------------------------------
# Stats helpers
# ---------------------------------------------------------------------------

def describe(series: pd.Series) -> dict:
    s = series.dropna()
    return {
        "n":      len(s),
        "mean":   round(s.mean(), 3) if len(s) else float("nan"),
        "std":    round(s.std(),  3) if len(s) else float("nan"),
        "median": round(s.median(), 3) if len(s) else float("nan"),
        "min":    round(s.min(),  3) if len(s) else float("nan"),
        "max":    round(s.max(),  3) if len(s) else float("nan"),
    }


def welch_pvalue(a: pd.Series, b: pd.Series) -> float:
    a, b = a.dropna(), b.dropna()
    if len(a) < 2 or len(b) < 2:
        return float("nan")
    _, p = stats.ttest_ind(a, b, equal_var=False)
    return round(float(p), 4)


# ---------------------------------------------------------------------------
# Summary stats
# ---------------------------------------------------------------------------

def compute_summary(df: pd.DataFrame, label: str) -> pd.DataFrame:
    all_metrics = [m for m in QUANT_METRICS + JUDGE_METRICS if m in df.columns]
    rows = []
    for m in all_metrics:
        d = describe(df[m])
        rows.append({"metric": m, "system": label, **d})
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Outcome distribution
# ---------------------------------------------------------------------------

def outcome_dist(df: pd.DataFrame) -> pd.Series:
    return df["final_status"].value_counts(normalize=False)


# ---------------------------------------------------------------------------
# LaTeX comparison table
# ---------------------------------------------------------------------------

def make_latex_table(auto_df: pd.DataFrame, vanilla_df: pd.DataFrame) -> str:
    all_metrics = [m for m in QUANT_METRICS + JUDGE_METRICS if m in auto_df.columns or m in vanilla_df.columns]

    lines = [
        r"\begin{table}[h]",
        r"\centering",
        r"\caption{Auto-Negotiate vs Vanilla: Metric Comparison (mean $\pm$ std)}",
        r"\label{tab:comparison}",
        r"\begin{tabular}{lrrr}",
        r"\hline",
        r"\textbf{Metric} & \textbf{Auto-Negotiate} & \textbf{Vanilla} & \textbf{p-value} \\",
        r"\hline",
    ]

    for m in all_metrics:
        a = auto_df[m].dropna() if m in auto_df.columns else pd.Series(dtype=float)
        v = vanilla_df[m].dropna() if m in vanilla_df.columns else pd.Series(dtype=float)
        a_str = f"{a.mean():.2f} $\\pm$ {a.std():.2f}" if len(a) else "---"
        v_str = f"{v.mean():.2f} $\\pm$ {v.std():.2f}" if len(v) else "---"
        p = welch_pvalue(a, v) if len(a) >= 2 and len(v) >= 2 else float("nan")
        p_str = f"{p:.4f}" if not np.isnan(p) else "---"
        label = m.replace("_", r"\_")
        lines.append(f"{label} & {a_str} & {v_str} & {p_str} \\\\")

    lines += [
        r"\hline",
        r"\end{tabular}",
        r"\end{table}",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Radar chart
# ---------------------------------------------------------------------------

def make_radar_chart(auto_df: pd.DataFrame, vanilla_df: pd.DataFrame | None, output_path: Path) -> None:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        available = [m for m in JUDGE_METRICS if m in auto_df.columns]
        if not available:
            print("No judge columns found — skipping radar chart.")
            return

        labels = [JUDGE_LABELS[JUDGE_METRICS.index(m)] for m in available]
        N = len(labels)
        angles = np.linspace(0, 2 * np.pi, N, endpoint=False).tolist()
        angles += angles[:1]

        fig, ax = plt.subplots(figsize=(6, 6), subplot_kw={"polar": True})

        auto_vals = [auto_df[m].mean() for m in available] + [auto_df[available[0]].mean()]
        ax.plot(angles, auto_vals, "b-o", linewidth=2, label="Auto-Negotiate")
        ax.fill(angles, auto_vals, "b", alpha=0.15)

        if vanilla_df is not None:
            van_available = [m for m in available if m in vanilla_df.columns]
            if van_available:
                van_vals = [vanilla_df[m].mean() if m in vanilla_df.columns else 0.0 for m in available]
                van_vals += [van_vals[0]]
                ax.plot(angles, van_vals, "r-o", linewidth=2, label="Vanilla")
                ax.fill(angles, van_vals, "r", alpha=0.15)

        ax.set_xticks(angles[:-1])
        ax.set_xticklabels(labels, size=9)
        ax.set_ylim(0, 10)
        ax.set_yticks([2, 4, 6, 8, 10])
        ax.set_title("LLM Judge Scores (mean, 0–10)", pad=20)
        ax.legend(loc="upper right", bbox_to_anchor=(1.3, 1.1))

        plt.tight_layout()
        plt.savefig(output_path, dpi=150, bbox_inches="tight")
        plt.close()
        print(f"Radar chart saved: {output_path}")
    except ImportError:
        print("matplotlib not installed — skipping radar chart.")


# ---------------------------------------------------------------------------
# Vanilla template
# ---------------------------------------------------------------------------

def write_template(path: Path) -> None:
    columns = [
        "run_id", "player_name", "club_name", "budget_eur", "budget_tier",
        "player_position", "player_age", "market_mid_eur", "walk_away_threshold_eur",
        "final_status", "rounds_used", "max_rounds",
        "market_realism", "outcome_quality_club", "outcome_quality_player",
        "efficiency", "compliance_rate",
        "concession_rate_club", "concession_rate_player",
        "concession_rate_club_pct", "concession_rate_player_pct",
        "final_salary_eur",
        "judge_market_alignment", "judge_player_outcome", "judge_club_outcome",
        "judge_contract_structure", "judge_reasoning_quality", "judge_overall",
        "judge_justifications",
        "error",
    ]
    pd.DataFrame(columns=columns).to_csv(path, index=False)
    print(f"Vanilla template written: {path}")
    print("Fill one row per vanilla negotiation, then run:")
    print("  python scripts/analyze_results.py --auto results/judged_100runs.csv --vanilla results/vanilla_results.csv")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze and compare negotiation results")
    parser.add_argument("--auto",           help="Auto-Negotiate results CSV (required unless --write-template)")
    parser.add_argument("--vanilla",        help="Vanilla results CSV for comparison")
    parser.add_argument("--write-template", action="store_true", help="Write empty vanilla template CSV")
    args = parser.parse_args()

    RESULTS_DIR.mkdir(exist_ok=True)

    if args.write_template:
        write_template(RESULTS_DIR / "vanilla_template.csv")

    if not args.auto:
        return

    auto_df = pd.read_csv(args.auto)
    vanilla_df = pd.read_csv(args.vanilla) if args.vanilla else None

    print(f"\n{'='*60}")
    print(f"AUTO-NEGOTIATE  n={len(auto_df)}")
    print(f"{'='*60}")

    # Outcome distribution
    print("\nOutcome distribution:")
    print(outcome_dist(auto_df).to_string())

    # Summary stats
    auto_summary = compute_summary(auto_df, "Auto-Negotiate")
    print("\nMetric summary (Auto-Negotiate):")
    print(auto_summary.to_string(index=False))

    all_summaries = [auto_summary]

    if vanilla_df is not None:
        print(f"\n{'='*60}")
        print(f"VANILLA  n={len(vanilla_df)}")
        print(f"{'='*60}")
        print("\nOutcome distribution:")
        print(outcome_dist(vanilla_df).to_string())
        van_summary = compute_summary(vanilla_df, "Vanilla")
        print("\nMetric summary (Vanilla):")
        print(van_summary.to_string(index=False))
        all_summaries.append(van_summary)

    # Save summary CSV
    summary_path = RESULTS_DIR / "summary_stats.csv"
    pd.concat(all_summaries).to_csv(summary_path, index=False)
    print(f"\nSummary stats saved: {summary_path}")

    # LaTeX table
    if vanilla_df is not None:
        tex = make_latex_table(auto_df, vanilla_df)
        tex_path = RESULTS_DIR / "comparison_table.tex"
        tex_path.write_text(tex)
        print(f"LaTeX table saved: {tex_path}")

    # Radar chart
    judge_cols = [m for m in JUDGE_METRICS if m in auto_df.columns]
    if judge_cols:
        make_radar_chart(auto_df, vanilla_df, RESULTS_DIR / "radar_chart.png")

    # Subgroup breakdowns
    for group_col in ("budget_tier", "player_position"):
        if group_col not in auto_df.columns:
            continue
        quant_available = [m for m in QUANT_METRICS if m in auto_df.columns]
        print(f"\n--- Breakdown by {group_col} (Auto-Negotiate) ---")
        for grp_val, grp_df in auto_df.groupby(group_col):
            row = {group_col: grp_val, "n": len(grp_df)}
            for m in quant_available[:5]:  # top 5 for console brevity
                row[m] = f"{grp_df[m].mean():.1f}"
            print(row)


if __name__ == "__main__":
    main()
