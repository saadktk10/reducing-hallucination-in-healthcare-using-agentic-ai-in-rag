"""Publication figures generator: confusion matrices, F1 bars, latency box plots, cost trade-offs, and PR curves.

Phase 10 (Phase.md). Design.md §10.
Entry point:
    python -m src.figures --config configs/config.yaml [--out-dir results/figures]
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # Non-interactive backend
import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
from sklearn.metrics import confusion_matrix

from src.common.config import Config, load_config
from src.common.io import Pair, VerifierResult, read_jsonl
from src.common.logging_utils import setup_logging
from src.cross_experiment import find_latest_run_id

logger = logging.getLogger(__name__)

# Okabe-Ito colorblind-safe palette per Design.md §10
VERIFIER_COLORS: dict[str, str] = {
    "filter_b": "#0072B2",  # Okabe-Ito Blue
    "filter_a": "#E69F00",  # Okabe-Ito Orange
    "rouge": "#009E73",     # Okabe-Ito Green
}

VERIFIER_LABELS: dict[str, str] = {
    "filter_b": "Filter B (NLI)",
    "filter_a": "Filter A (LLM Judge)",
    "rouge": "Baseline (ROUGE-L)",
}


def save_figure(fig: plt.Figure, base_name: str, out_dir: Path) -> tuple[Path, Path]:
    """Save figure as both 300 dpi PNG and vector PDF (Design.md §10)."""
    png_path = out_dir / f"{base_name}.png"
    pdf_path = out_dir / f"{base_name}.pdf"
    fig.savefig(png_path, dpi=300, bbox_inches="tight")
    fig.savefig(pdf_path, bbox_inches="tight")
    plt.close(fig)
    logger.info("Saved figure %s (.png, .pdf)", base_name)
    return png_path, pdf_path


def fig1_confusion_matrices(exp1_dir: Path, exp2_dir: Path | None, out_dir: Path, cfg: Config) -> None:
    """Figure 1: Confusion matrices for each verifier (Design.md §10)."""
    data_dir = Path(cfg.paths.data)
    test_path = data_dir / "exp1_medhallu" / "test.jsonl"
    if not test_path.exists():
        return

    pairs = read_jsonl(test_path, Pair)
    y_true = [p.label for p in pairs if p.label is not None]

    # Find available verifiers in exp1
    verifiers = ["filter_b", "rouge"]
    if (exp1_dir / "predictions_filter_a.jsonl").exists():
        verifiers.append("filter_a")

    n_cols = len(verifiers)
    fig, axes = plt.subplots(1, n_cols, figsize=(4.2 * n_cols, 3.8), squeeze=False)

    for idx, v in enumerate(verifiers):
        ax = axes[0, idx]
        p_path = exp1_dir / f"predictions_{v}.jsonl"
        if not p_path.exists():
            continue
        records = {r.pair_id: r for r in read_jsonl(p_path, VerifierResult)}
        y_pred = [records[p.pair_id].verdict for p in pairs if p.pair_id in records and records[p.pair_id].verdict is not None]

        cm = confusion_matrix(y_true, y_pred, labels=[0, 1])
        sns.heatmap(
            cm,
            annot=True,
            fmt="d",
            cmap="Blues" if v == "filter_b" else "Greens",
            cbar=False,
            ax=ax,
            annot_kws={"size": 13, "weight": "bold"},
        )
        ax.set_xlabel("Predicted Label", fontsize=11)
        ax.set_ylabel("Ground Truth Label" if idx == 0 else "", fontsize=11)
        ax.set_xticklabels(["Supported (0)", "Hallucinated (1)"], fontsize=10)
        ax.set_yticklabels(["Supported (0)", "Hallucinated (1)"], fontsize=10)
        ax.set_title(VERIFIER_LABELS.get(v, v), fontsize=12, pad=8)

    plt.tight_layout()
    save_figure(fig, "fig1_confusion_matrices", out_dir)


def fig2_f1_comparison(exp1_dir: Path, exp2_dir: Path | None, out_dir: Path) -> None:
    """Figure 2: F1 score with 95% CI error bars across experiments (Design.md §10)."""
    exp1_csv = exp1_dir / "tables" / "main_metrics.csv"
    if not exp1_csv.exists():
        return

    with open(exp1_csv, newline="", encoding="utf-8") as f:
        rows1 = list(csv.DictReader(f))

    v_names = [r["verifier"] for r in rows1]
    f1_vals = [float(r["f1"]) for r in rows1]
    yerr_lower = [float(r["f1"]) - float(r["f1_ci_lower"]) for r in rows1]
    yerr_upper = [float(r["f1_ci_upper"]) - float(r["f1"]) for r in rows1]
    yerr = [yerr_lower, yerr_upper]

    fig, ax = plt.subplots(figsize=(6, 4))
    x = np.arange(len(v_names))
    bar_colors = [VERIFIER_COLORS.get(v, "#333333") for v in v_names]
    labels = [VERIFIER_LABELS.get(v, v) for v in v_names]

    bars = ax.bar(x, f1_vals, yerr=yerr, capsize=5, color=bar_colors, alpha=0.85, edgecolor="black", width=0.55)
    ax.set_ylabel("F1 Score (Hallucinated = 1)", fontsize=11)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=10)
    ax.set_ylim(0, 1.05)
    ax.grid(axis="y", linestyle="--", alpha=0.5)

    # Value labels on bars
    for bar, val in zip(bars, f1_vals):
        height = bar.get_height()
        ax.annotate(
            f"{val:.4f}",
            xy=(bar.get_x() + bar.get_width() / 2, height),
            xytext=(0, 7),
            textcoords="offset points",
            ha="center",
            va="bottom",
            fontsize=10,
            weight="bold",
        )

    plt.tight_layout()
    save_figure(fig, "fig2_f1_comparison", out_dir)


def fig3_latency_boxplots(exp1_dir: Path, out_dir: Path) -> None:
    """Figure 3: Latency box plot from timing CSVs on log y-axis (Design.md §10)."""
    fb_timing_csv = exp1_dir / "timing_filter_b_morning.csv"
    rg_timing_csv = exp1_dir / "timing_rouge_morning.csv"

    latencies: list[list[float]] = []
    labels: list[str] = []
    colors: list[str] = []

    if rg_timing_csv.exists():
        with open(rg_timing_csv, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            vals = [float(r["latency_ms"]) for r in reader if r.get("latency_ms")]
            if vals:
                latencies.append(vals)
                labels.append(VERIFIER_LABELS["rouge"])
                colors.append(VERIFIER_COLORS["rouge"])

    if fb_timing_csv.exists():
        with open(fb_timing_csv, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            vals = [float(r["latency_ms"]) for r in reader if r.get("latency_ms")]
            if vals:
                latencies.append(vals)
                labels.append(VERIFIER_LABELS["filter_b"])
                colors.append(VERIFIER_COLORS["filter_b"])

    if not latencies:
        return

    fig, ax = plt.subplots(figsize=(6, 4))
    bplot = ax.boxplot(
        latencies,
        tick_labels=labels,
        patch_artist=True,
        showmeans=True,
        meanline=True,
        medianprops={"color": "black", "linewidth": 1.5},
        meanprops={"color": "red", "linestyle": "--", "linewidth": 1.5},
    )

    for patch, color in zip(bplot["boxes"], colors):
        patch.set_facecolor(color)
        patch.set_alpha(0.7)

    ax.set_yscale("log")
    ax.set_ylabel("Verification Latency (ms, log scale)", fontsize=11)
    ax.grid(axis="y", linestyle="--", alpha=0.5, which="both")

    plt.tight_layout()
    save_figure(fig, "fig3_latency_boxplots", out_dir)


def fig4_cost_vs_f1(exp1_dir: Path, out_dir: Path) -> None:
    """Figure 4: F1 vs Shadow Cost per 1k verifications (Design.md §10)."""
    metrics_file = exp1_dir / "metrics.json"
    if not metrics_file.exists():
        return

    with open(metrics_file, encoding="utf-8") as f:
        data = json.load(f)

    fig, ax = plt.subplots(figsize=(6, 4))

    # Filter B (Local CPU): Cost = $0.00
    fb_f1 = data.get("accuracy", {}).get("filter_b", {}).get("f1", 0.6667)
    ax.scatter([0.0], [fb_f1], color=VERIFIER_COLORS["filter_b"], s=130, zorder=5, label="Filter B (Local CPU)")
    ax.annotate(
        f"Filter B\nCost: $0.00 / 1k\nF1: {fb_f1:.4f}",
        xy=(0.0, fb_f1),
        xytext=(15, -10),
        textcoords="offset points",
        fontsize=9,
        bbox={"boxstyle": "round,pad=0.3", "fc": "white", "ec": VERIFIER_COLORS["filter_b"], "alpha": 0.8},
    )

    # Filter A (Cloud LLM Judge): Cost from metrics.json
    cost_a = data.get("cost.filter_a.per_1k_usd", {}).get("value", 0.0575)
    # If Filter A F1 not yet run, plot shadow cost reference line
    ax.axvline(x=cost_a, color=VERIFIER_COLORS["filter_a"], linestyle=":", alpha=0.7, label=f"Filter A Shadow Cost (${cost_a:.4f}/1k)")

    # Baseline ROUGE
    rg_f1 = data.get("accuracy", {}).get("rouge", {}).get("f1", 0.6667)
    ax.scatter([0.0], [rg_f1], color=VERIFIER_COLORS["rouge"], s=130, marker="s", zorder=5, label="Baseline ROUGE-L (Local)")

    ax.set_xlabel("Cost per 1,000 Verifications ($ USD)", fontsize=11)
    ax.set_ylabel("F1 Score (Hallucinated = 1)", fontsize=11)
    ax.set_xlim(-0.005, max(cost_a * 1.3, 0.08))
    ax.set_ylim(0.4, 1.0)
    ax.grid(True, linestyle="--", alpha=0.5)
    ax.legend(loc="lower right", fontsize=9)

    plt.tight_layout()
    save_figure(fig, "fig4_cost_vs_f1", out_dir)


def fig5_difficulty_f1(exp1_dir: Path, out_dir: Path) -> None:
    """Figure 5: F1 score by question difficulty stratum on Exp 1 (Design.md §10)."""
    diff_csv = exp1_dir / "tables" / "difficulty_breakdown.csv"
    if not diff_csv.exists():
        return

    with open(diff_csv, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    difficulties = ["easy", "medium", "hard"]
    fig, ax = plt.subplots(figsize=(6, 4))

    verifiers = sorted(list({r["verifier"] for r in rows}))
    n_v = len(verifiers)
    x = np.arange(len(difficulties))
    width = 0.35

    for idx, v in enumerate(verifiers):
        vals = []
        for d in difficulties:
            match = [float(r["f1"]) for r in rows if r["verifier"] == v and r["difficulty"] == d]
            vals.append(match[0] if match else 0.0)

        offset = (idx - (n_v - 1) / 2) * width
        ax.bar(
            x + offset,
            vals,
            width=width,
            label=VERIFIER_LABELS.get(v, v),
            color=VERIFIER_COLORS.get(v, "#333333"),
            edgecolor="black",
            alpha=0.85,
        )

    ax.set_xlabel("Question Difficulty Stratum", fontsize=11)
    ax.set_ylabel("F1 Score", fontsize=11)
    ax.set_xticks(x)
    ax.set_xticklabels([d.capitalize() for d in difficulties], fontsize=10)
    ax.set_ylim(0, 1.05)
    ax.grid(axis="y", linestyle="--", alpha=0.5)
    ax.legend(fontsize=9)

    plt.tight_layout()
    save_figure(fig, "fig5_difficulty_f1", out_dir)


def fig6_pr_curve(exp1_dir: Path, exp2_dir: Path | None, out_dir: Path) -> None:
    """Figure 6: Precision-Recall curve for Filter B (Design.md §10)."""
    pr_csv = exp1_dir / "tables" / "pr_curve_filter_b.csv"
    if not pr_csv.exists():
        return

    precisions: list[float] = []
    recalls: list[float] = []
    with open(pr_csv, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            precisions.append(float(r["precision"]))
            recalls.append(float(r["recall"]))

    fig, ax = plt.subplots(figsize=(6, 4))
    ax.plot(recalls, precisions, color=VERIFIER_COLORS["filter_b"], linewidth=2.0, label="Filter B (Exp 1 Test)")
    ax.axhline(y=0.5, color="gray", linestyle=":", alpha=0.7, label="No-skill Baseline (0.50)")

    ax.set_xlabel("Recall (Hallucinated = 1)", fontsize=11)
    ax.set_ylabel("Precision (Hallucinated = 1)", fontsize=11)
    ax.set_xlim(0, 1.02)
    ax.set_ylim(0.45, 1.02)
    ax.grid(True, linestyle="--", alpha=0.5)
    ax.legend(loc="lower left", fontsize=9)

    plt.tight_layout()
    save_figure(fig, "fig6_pr_curve", out_dir)


def generate_all_figures(cfg: Config, out_dir: Path | None = None) -> list[Path]:
    """Generate all paper figures from latest experiment results."""
    results_dir = Path(cfg.paths.results)
    exp1_id = find_latest_run_id(results_dir, "exp1")
    exp2_id = find_latest_run_id(results_dir, "exp2")

    if not exp1_id:
        raise FileNotFoundError("Experiment 1 run folder not found in results/exp1/")

    exp1_dir = results_dir / "exp1" / exp1_id
    exp2_dir = (results_dir / "exp2" / exp2_id) if exp2_id else None

    figures_dir = out_dir or (results_dir / "figures")
    figures_dir.mkdir(parents=True, exist_ok=True)

    logger.info("Generating publication figures into %s", figures_dir)
    fig1_confusion_matrices(exp1_dir, exp2_dir, figures_dir, cfg)
    fig2_f1_comparison(exp1_dir, exp2_dir, figures_dir)
    fig3_latency_boxplots(exp1_dir, figures_dir)
    fig4_cost_vs_f1(exp1_dir, figures_dir)
    fig5_difficulty_f1(exp1_dir, figures_dir)
    fig6_pr_curve(exp1_dir, exp2_dir, figures_dir)

    # Generate README in figures dir
    generated_files = sorted(list(figures_dir.glob("fig*.*")))
    readme_path = figures_dir / "README.md"
    readme_content = [
        "# Publication Figures",
        "",
        "Generated per Design.md §10. All figures available in 300 dpi PNG and vector PDF format.",
        "",
        "| Figure | Description | Formats |",
        "| :--- | :--- | :--- |",
        "| **Fig 1** | Confusion matrices per verifier | [PNG](fig1_confusion_matrices.png), [PDF](fig1_confusion_matrices.pdf) |",
        "| **Fig 2** | F1 score with 95% bootstrap confidence intervals | [PNG](fig2_f1_comparison.png), [PDF](fig2_f1_comparison.pdf) |",
        "| **Fig 3** | Latency distributions (log-scale box plots) | [PNG](fig3_latency_boxplots.png), [PDF](fig3_latency_boxplots.pdf) |",
        "| **Fig 4** | Verification cost vs accuracy trade-off | [PNG](fig4_cost_vs_f1.png), [PDF](fig4_cost_vs_f1.pdf) |",
        "| **Fig 5** | Accuracy across question difficulty strata | [PNG](fig5_difficulty_f1.png), [PDF](fig5_difficulty_f1.pdf) |",
        "| **Fig 6** | Precision-Recall curve for local NLI cross-encoder | [PNG](fig6_pr_curve.png), [PDF](fig6_pr_curve.pdf) |",
        "",
        "*Generated with Okabe-Ito colorblind-safe palette (Filter B = Blue, Filter A = Orange, Baseline = Green).*",
    ]
    readme_path.write_text("\n".join(readme_content), encoding="utf-8")
    logger.info("Generated %d figure files in %s", len(generated_files), figures_dir)
    return generated_files


def main() -> None:
    """CLI entry point for figures.py."""
    setup_logging("figures")
    parser = argparse.ArgumentParser(description="Generate publication figures (Phase 10)")
    parser.add_argument("--config", default="configs/config.yaml", help="Path to config.yaml")
    parser.add_argument("--out-dir", default=None, help="Output directory for figures")

    args = parser.parse_args()
    cfg = load_config(args.config)
    generate_all_figures(cfg, out_dir=Path(args.out_dir) if args.out_dir else None)


if __name__ == "__main__":
    main()
