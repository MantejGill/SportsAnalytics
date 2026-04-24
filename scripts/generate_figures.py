"""Generate all figures for the academic paper results."""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
import pandas as pd
from pathlib import Path

RESULTS = Path(__file__).parent / "results"
FIGS    = RESULTS / "figures"
FIGS.mkdir(exist_ok=True)

COLORS = {
    "mini":    "#2196F3",   # blue
    "gpt4o":  "#FF9800",   # orange
    "vanilla": "#4CAF50",  # green
}
LABELS = {
    "mini":    "Auto-Negotiate (GPT-4o-mini)",
    "gpt4o":  "Auto-Negotiate (GPT-4o)",
    "vanilla": "Vanilla ChatGPT (Cloro)",
}

def load():
    mini   = pd.read_csv(RESULTS / "judged_100runs.csv")
    gpt4o  = pd.read_csv(RESULTS / "auto_gpt4o_judged.csv")
    van    = pd.read_csv(RESULTS / "vanilla_judged.csv")
    mini   = mini[mini["final_status"]  != "ERROR"]
    gpt4o  = gpt4o[gpt4o["final_status"] != "ERROR"]
    van    = van[van["final_status"]    != "ERROR"]
    return mini, gpt4o, van


# ── 1. Outcome distribution bar chart ────────────────────────────────────────
def fig_outcome_distribution(mini, gpt4o, van):
    statuses = ["ACCEPTED", "MAX_ROUNDS", "WALKED_AWAY"]
    colors   = ["#43A047", "#E53935", "#FB8C00"]

    def pct(df, s):
        return (df["final_status"] == s).sum() / len(df) * 100

    data = {
        LABELS["mini"]:    [pct(mini, s)  for s in statuses],
        LABELS["gpt4o"]:  [pct(gpt4o, s) for s in statuses],
        LABELS["vanilla"]: [pct(van, s)   for s in statuses],
    }

    x = np.arange(len(data))
    fig, ax = plt.subplots(figsize=(10, 6))
    bottom = np.zeros(len(data))
    for i, (status, color) in enumerate(zip(statuses, colors)):
        vals = [data[k][i] for k in data]
        bars = ax.bar(x, vals, bottom=bottom, color=color, label=status, width=0.55, edgecolor="white", linewidth=0.8)
        for bar, val in zip(bars, vals):
            if val > 3:
                ax.text(bar.get_x() + bar.get_width()/2, bar.get_y() + val/2,
                        f"{val:.0f}%", ha="center", va="center", fontsize=11, fontweight="bold", color="white")
        bottom += np.array(vals)

    ax.set_xticks(x)
    ax.set_xticklabels(list(data.keys()), fontsize=11)
    ax.set_ylabel("Percentage of Negotiations (%)", fontsize=12)
    ax.set_title("Negotiation Outcome Distribution Across Systems", fontsize=14, fontweight="bold")
    ax.legend(loc="upper right", fontsize=10)
    ax.set_ylim(0, 110)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    plt.tight_layout()
    plt.savefig(FIGS / "outcome_distribution.png", dpi=150)
    plt.close()
    print("saved: outcome_distribution.png")


# ── 2. Judge scores grouped bar chart ────────────────────────────────────────
def fig_judge_scores(mini, gpt4o, van):
    dims = ["judge_market_alignment", "judge_player_outcome", "judge_club_outcome",
            "judge_contract_structure", "judge_reasoning_quality", "judge_overall"]
    labels = ["Market\nAlignment", "Player\nOutcome", "Club\nOutcome",
              "Contract\nStructure", "Reasoning\nQuality", "Overall"]

    x = np.arange(len(dims))
    w = 0.25
    fig, ax = plt.subplots(figsize=(13, 6))

    for i, (key, df) in enumerate([("mini", mini), ("gpt4o", gpt4o), ("vanilla", van)]):
        means = [df[d].mean() for d in dims]
        stds  = [df[d].std()  for d in dims]
        bars  = ax.bar(x + (i-1)*w, means, w, label=LABELS[key], color=COLORS[key],
                       yerr=stds, capsize=4, error_kw={"linewidth": 1.2}, edgecolor="white", linewidth=0.6)

    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=10)
    ax.set_ylabel("Score (0-10)", fontsize=12)
    ax.set_ylim(0, 12)
    ax.set_title("LLM Judge Scores by Dimension (GPT-4o Judge, 0-10)", fontsize=14, fontweight="bold")
    ax.legend(fontsize=9, loc="upper left")
    ax.axhline(7, color="gray", linestyle="--", linewidth=0.8, alpha=0.6, label="_Good threshold")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    plt.tight_layout()
    plt.savefig(FIGS / "judge_scores_comparison.png", dpi=150)
    plt.close()
    print("saved: judge_scores_comparison.png")


# ── 3. Radar chart (3-system) ─────────────────────────────────────────────────
def fig_radar(mini, gpt4o, van):
    dims   = ["judge_market_alignment", "judge_player_outcome", "judge_club_outcome",
              "judge_contract_structure", "judge_reasoning_quality", "judge_overall"]
    labels = ["Market Alignment", "Player Outcome", "Club Outcome",
              "Contract Structure", "Reasoning Quality", "Overall"]
    N = len(dims)
    angles = np.linspace(0, 2*np.pi, N, endpoint=False).tolist()
    angles += angles[:1]

    fig, ax = plt.subplots(figsize=(7, 7), subplot_kw={"polar": True})
    for key, df in [("mini", mini), ("gpt4o", gpt4o), ("vanilla", van)]:
        vals = [df[d].mean() for d in dims] + [df[dims[0]].mean()]
        ax.plot(angles, vals, "o-", linewidth=2, color=COLORS[key], label=LABELS[key])
        ax.fill(angles, vals, alpha=0.10, color=COLORS[key])

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels, size=9)
    ax.set_ylim(0, 10)
    ax.set_yticks([2, 4, 6, 8, 10])
    ax.set_yticklabels(["2", "4", "6", "8", "10"], size=7, color="gray")
    ax.set_title("LLM Judge Radar: All Systems", pad=20, fontsize=13, fontweight="bold")
    ax.legend(loc="upper right", bbox_to_anchor=(1.35, 1.15), fontsize=8)
    plt.tight_layout()
    plt.savefig(FIGS / "radar_chart_3way.png", dpi=150, bbox_inches="tight")
    plt.close()
    print("saved: radar_chart_3way.png")


# ── 4. Final salary distributions ────────────────────────────────────────────
def fig_salary_distribution(mini, gpt4o, van):
    fig, axes = plt.subplots(1, 3, figsize=(15, 5), sharey=True)
    bins = np.linspace(0, 45_000_000, 25)
    for ax, (key, df), title in zip(axes,
            [("mini", mini), ("gpt4o", gpt4o), ("vanilla", van)],
            [LABELS["mini"], LABELS["gpt4o"], LABELS["vanilla"]]):
        sal = df["final_salary_eur"].dropna() / 1e6
        ax.hist(sal, bins=bins/1e6, color=COLORS[key], edgecolor="white", linewidth=0.7, alpha=0.85)
        ax.axvline(sal.mean(), color="black", linestyle="--", linewidth=1.5, label=f"Mean: EUR {sal.mean():.1f}M")
        ax.axvline(sal.median(), color="red", linestyle=":", linewidth=1.5, label=f"Median: EUR {sal.median():.1f}M")
        ax.set_title(title, fontsize=10, fontweight="bold")
        ax.set_xlabel("Annual Base Salary (EUR M)", fontsize=9)
        ax.legend(fontsize=8)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
    axes[0].set_ylabel("Number of Negotiations", fontsize=10)
    fig.suptitle("Final Salary Distribution by System", fontsize=13, fontweight="bold", y=1.01)
    plt.tight_layout()
    plt.savefig(FIGS / "salary_distribution.png", dpi=150, bbox_inches="tight")
    plt.close()
    print("saved: salary_distribution.png")


# ── 5. Budget tier breakdown (auto-mini) ─────────────────────────────────────
def fig_budget_tier(mini, van):
    tiers = ["tight", "low", "market", "high", "generous"]
    metrics = ["market_realism", "outcome_quality_club", "outcome_quality_player", "compliance_rate"]
    m_labels = ["Market Realism", "Club Outcome", "Player Outcome", "Compliance Rate"]
    scales   = [1, 1, 1, 100]

    fig, axes = plt.subplots(1, 4, figsize=(16, 5))
    x = np.arange(len(tiers))
    w = 0.35

    for ax, metric, label, scale in zip(axes, metrics, m_labels, scales):
        mini_vals = [mini[mini["budget_tier"]==t][metric].mean()*scale for t in tiers]
        van_vals  = [van[van["budget_tier"]==t][metric].mean()*scale  for t in tiers]
        ax.bar(x - w/2, mini_vals, w, color=COLORS["mini"],    label="Auto-mini", edgecolor="white")
        ax.bar(x + w/2, van_vals,  w, color=COLORS["vanilla"], label="Vanilla",   edgecolor="white")
        ax.set_title(label, fontsize=10, fontweight="bold")
        ax.set_xticks(x)
        ax.set_xticklabels([t.capitalize() for t in tiers], fontsize=8, rotation=15)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        if metric == "compliance_rate":
            ax.set_ylabel("Rate x100 (%)", fontsize=8)
        axes[0].legend(fontsize=8)

    fig.suptitle("Auto-Negotiate vs Vanilla by Budget Tier", fontsize=13, fontweight="bold")
    plt.tight_layout()
    plt.savefig(FIGS / "budget_tier_breakdown.png", dpi=150, bbox_inches="tight")
    plt.close()
    print("saved: budget_tier_breakdown.png")


# ── 6. Rounds used distribution ──────────────────────────────────────────────
def fig_rounds(mini, gpt4o):
    fig, axes = plt.subplots(1, 2, figsize=(12, 5), sharey=True)
    for ax, (key, df) in zip(axes, [("mini", mini), ("gpt4o", gpt4o)]):
        counts = df["rounds_used"].value_counts().sort_index()
        ax.bar(counts.index, counts.values, color=COLORS[key], edgecolor="white", linewidth=0.8)
        ax.set_xlabel("Rounds Used", fontsize=11)
        ax.set_title(LABELS[key], fontsize=10, fontweight="bold")
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.set_xticks(range(1, 9))
        for xi, yi in zip(counts.index, counts.values):
            ax.text(xi, yi + 0.3, str(yi), ha="center", va="bottom", fontsize=9)
    axes[0].set_ylabel("Number of Negotiations", fontsize=11)
    fig.suptitle("Rounds Used Distribution: mini vs GPT-4o", fontsize=13, fontweight="bold")
    plt.tight_layout()
    plt.savefig(FIGS / "rounds_distribution.png", dpi=150)
    plt.close()
    print("saved: rounds_distribution.png")


# ── 7. Key metrics box plots ──────────────────────────────────────────────────
def fig_boxplots(mini, gpt4o, van):
    metrics = ["market_realism", "outcome_quality_player", "outcome_quality_club", "compliance_rate"]
    labels  = ["Market Realism\n(0-100)", "Player Outcome\nQuality (0-100)",
               "Club Outcome\nQuality (0-100)", "Compliance Rate\n(0-1)"]
    scales  = [1, 1, 1, 100]

    fig, axes = plt.subplots(1, 4, figsize=(16, 6))
    for ax, metric, label, scale in zip(axes, metrics, labels, scales):
        data = [mini[metric].dropna()*scale, gpt4o[metric].dropna()*scale, van[metric].dropna()*scale]
        bp = ax.boxplot(data, patch_artist=True, medianprops={"color": "black", "linewidth": 2},
                        whiskerprops={"linewidth": 1.2}, capprops={"linewidth": 1.2})
        for patch, color in zip(bp["boxes"], [COLORS["mini"], COLORS["gpt4o"], COLORS["vanilla"]]):
            patch.set_facecolor(color)
            patch.set_alpha(0.8)
        ax.set_xticklabels(["Auto\nmini", "Auto\nGPT-4o", "Vanilla"], fontsize=9)
        ax.set_title(label, fontsize=10, fontweight="bold")
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)

    fig.suptitle("Distribution of Key Metrics Across Systems", fontsize=13, fontweight="bold")
    plt.tight_layout()
    plt.savefig(FIGS / "metric_boxplots.png", dpi=150)
    plt.close()
    print("saved: metric_boxplots.png")


# ── 8. Overall summary comparison ────────────────────────────────────────────
def fig_summary(mini, gpt4o, van):
    categories = ["Market\nRealism", "Player\nOutcome", "Club\nOutcome",
                  "Compliance\nRate", "Judge\nOverall"]
    metrics    = ["market_realism", "outcome_quality_player", "outcome_quality_club",
                  "compliance_rate", "judge_overall"]
    # Normalise all to 0-10 scale
    scales = [0.1, 0.1, 0.1, 10, 1]

    fig, ax = plt.subplots(figsize=(11, 6))
    x = np.arange(len(categories))
    w = 0.25

    for i, (key, df) in enumerate([("mini", mini), ("gpt4o", gpt4o), ("vanilla", van)]):
        vals = [df[m].mean() * s for m, s in zip(metrics, scales)]
        bars = ax.bar(x + (i-1)*w, vals, w, label=LABELS[key], color=COLORS[key],
                      edgecolor="white", linewidth=0.6)
        for bar, val in zip(bars, vals):
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.08,
                    f"{val:.1f}", ha="center", va="bottom", fontsize=8)

    ax.set_xticks(x)
    ax.set_xticklabels(categories, fontsize=11)
    ax.set_ylabel("Score (normalised to 0-10)", fontsize=12)
    ax.set_ylim(0, 12)
    ax.set_title("Summary: All Key Metrics Normalised to 0-10 Scale", fontsize=14, fontweight="bold")
    ax.legend(fontsize=9)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    plt.tight_layout()
    plt.savefig(FIGS / "summary_comparison.png", dpi=150)
    plt.close()
    print("saved: summary_comparison.png")


# ── 9. Player position heatmap ────────────────────────────────────────────────
def fig_position_heatmap(mini):
    positions = ["ST", "RW", "LW", "CM", "CAM", "CDM", "CB"]
    metrics   = ["market_realism", "outcome_quality_player", "outcome_quality_club", "compliance_rate"]
    m_labels  = ["Market\nRealism", "Player\nOutcome", "Club\nOutcome", "Compliance\nx100"]
    scales    = [1, 1, 1, 100]

    matrix = []
    pos_labels = []
    for pos in positions:
        sub = mini[mini["player_position"] == pos]
        if len(sub) == 0:
            continue
        pos_labels.append(f"{pos} (n={len(sub)})")
        row = [sub[m].mean() * s for m, s in zip(metrics, scales)]
        matrix.append(row)

    matrix = np.array(matrix)
    fig, ax = plt.subplots(figsize=(10, 6))
    im = ax.imshow(matrix, cmap="RdYlGn", aspect="auto", vmin=0, vmax=100)
    ax.set_xticks(range(len(m_labels)))
    ax.set_xticklabels(m_labels, fontsize=10)
    ax.set_yticks(range(len(pos_labels)))
    ax.set_yticklabels(pos_labels, fontsize=10)
    for i in range(len(pos_labels)):
        for j in range(len(m_labels)):
            ax.text(j, i, f"{matrix[i,j]:.1f}", ha="center", va="center",
                    fontsize=10, fontweight="bold",
                    color="white" if matrix[i,j] < 40 or matrix[i,j] > 80 else "black")
    plt.colorbar(im, ax=ax, label="Score (0-100)")
    ax.set_title("Auto-Negotiate (mini): Metrics by Player Position", fontsize=13, fontweight="bold")
    plt.tight_layout()
    plt.savefig(FIGS / "position_heatmap.png", dpi=150)
    plt.close()
    print("saved: position_heatmap.png")


# ── 10. Concession rate analysis ──────────────────────────────────────────────
def fig_concession(mini, gpt4o):
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    for ax, (key, df), title in zip(axes,
            [("mini", mini), ("gpt4o", gpt4o)],
            ["Club Concession Rate by Budget Tier (Auto-mini)", "Club Concession Rate by Budget Tier (Auto-GPT-4o)"]):
        tiers = ["tight", "low", "market", "high", "generous"]
        vals  = [df[df["budget_tier"]==t]["concession_rate_club"].mean()/1e6 for t in tiers]
        colors_t = ["#E53935", "#FF7043", "#FFA726", "#66BB6A", "#42A5F5"]
        bars = ax.bar(tiers, vals, color=colors_t, edgecolor="white", linewidth=0.8)
        for bar, val in zip(bars, vals):
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.01,
                    f"EUR {val:.2f}M", ha="center", va="bottom", fontsize=8)
        ax.set_xlabel("Budget Tier", fontsize=10)
        ax.set_ylabel("Avg Club Concession per Round (EUR M)", fontsize=10)
        ax.set_title(LABELS[key], fontsize=10, fontweight="bold")
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)

    fig.suptitle("Club Concession Rate: How Much the Club Gives Per Round", fontsize=13, fontweight="bold")
    plt.tight_layout()
    plt.savefig(FIGS / "concession_analysis.png", dpi=150)
    plt.close()
    print("saved: concession_analysis.png")


if __name__ == "__main__":
    mini, gpt4o, van = load()
    print(f"Loaded: mini={len(mini)}, gpt4o={len(gpt4o)}, vanilla={len(van)}")
    fig_outcome_distribution(mini, gpt4o, van)
    fig_judge_scores(mini, gpt4o, van)
    fig_radar(mini, gpt4o, van)
    fig_salary_distribution(mini, gpt4o, van)
    fig_budget_tier(mini, van)
    fig_rounds(mini, gpt4o)
    fig_boxplots(mini, gpt4o, van)
    fig_summary(mini, gpt4o, van)
    fig_position_heatmap(mini)
    fig_concession(mini, gpt4o)
    print(f"\nAll figures saved to {FIGS}")
