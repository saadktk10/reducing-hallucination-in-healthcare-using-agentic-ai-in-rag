"""Cross-experiment analysis: ranking agreement, threshold transfer, and qualitative disagreement export.

Phase 9 (Phase.md). Design.md §8.4.
Entry point:
    python -m src.cross_experiment --config configs/config.yaml [--run-id-exp1 <id>] [--run-id-exp2 <id>] [--out-dir <path>]
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
from pathlib import Path
from typing import Any

from src.common.config import Config, load_config
from src.common.io import Pair, VerifierResult, read_jsonl
from src.common.logging_utils import setup_logging
from src.evaluation.metrics import f1

logger = logging.getLogger(__name__)


def find_latest_run_id(results_dir: Path, exp: str) -> str | None:
    """Find the latest run ID for an experiment from LATEST.json or directory scan."""
    latest_file = results_dir / "LATEST.json"
    if latest_file.exists():
        try:
            with open(latest_file, encoding="utf-8") as f:
                data = json.load(f)
            if exp in data:
                return data[exp]
        except Exception:
            pass

    exp_dir = results_dir / exp
    if exp_dir.exists():
        subdirs = [d for d in exp_dir.iterdir() if d.is_dir()]
        if subdirs:
            subdirs.sort(key=lambda d: d.name, reverse=True)
            return subdirs[0].name
    return None


def run_cross_experiment_analysis(
    cfg: Config,
    run_id_exp1: str | None = None,
    run_id_exp2: str | None = None,
    out_dir: Path | None = None,
) -> dict[str, Any]:
    """Execute cross-experiment analyses and export cross_summary.md."""
    results_dir = Path(cfg.paths.results)
    exp1_id = run_id_exp1 or find_latest_run_id(results_dir, "exp1")
    exp2_id = run_id_exp2 or find_latest_run_id(results_dir, "exp2")

    if not exp1_id:
        raise FileNotFoundError("Could not find any completed run for Experiment 1 in results/exp1/")

    exp1_dir = results_dir / "exp1" / exp1_id
    exp2_dir = (results_dir / "exp2" / exp2_id) if exp2_id else None

    target_dir = out_dir or (results_dir / "cross" / (exp1_id if not exp2_id else f"{exp1_id}_{exp2_id}"))
    target_dir.mkdir(parents=True, exist_ok=True)

    summary_lines = [
        "# Cross-Experiment Analysis Summary",
        "",
        f"- **Experiment 1 Run ID**: `{exp1_id}`",
        f"- **Experiment 2 Run ID**: `{exp2_id if exp2_id else 'Pending Human Labeling (Phase 6 / Gate G2)'}`",
        "",
    ]

    # 1. Load Experiment 1 main metrics
    exp1_metrics_csv = exp1_dir / "tables" / "main_metrics.csv"
    exp1_metrics: list[dict[str, Any]] = []
    if exp1_metrics_csv.exists():
        with open(exp1_metrics_csv, newline="", encoding="utf-8") as f:
            exp1_metrics = list(csv.DictReader(f))

    # 2. Ranking check
    ranking_agrees: bool | None = None
    summary_lines.extend([
        "## Verifier Performance Ranking",
        "",
    ])

    if exp1_metrics:
        # Sort Exp 1 by F1 descending
        exp1_by_f1 = sorted(exp1_metrics, key=lambda x: float(x.get("f1", 0.0)), reverse=True)
        summary_lines.extend([
            "### Experiment 1 Ranking (by F1 descending)",
            "",
            "| Rank | Verifier | F1 [95% CI] | FNR |",
            "| :--- | :--- | :--- | :--- |",
        ])
        for idx, row in enumerate(exp1_by_f1, 1):
            ci_str = f"[{row.get('f1_ci_lower', '')}, {row.get('f1_ci_upper', '')}]"
            summary_lines.append(f"| {idx} | {row['verifier']} | {row['f1']} {ci_str} | {row['fnr']} |")

    exp2_metrics: list[dict[str, Any]] = []
    if exp2_dir and (exp2_dir / "tables" / "main_metrics.csv").exists():
        with open(exp2_dir / "tables" / "main_metrics.csv", newline="", encoding="utf-8") as f:
            exp2_metrics = list(csv.DictReader(f))

        exp2_by_f1 = sorted(exp2_metrics, key=lambda x: float(x.get("f1", 0.0)), reverse=True)
        summary_lines.extend([
            "",
            "### Experiment 2 Ranking (by F1 descending)",
            "",
            "| Rank | Verifier | F1 [95% CI] | FNR |",
            "| :--- | :--- | :--- | :--- |",
        ])
        for idx, row in enumerate(exp2_by_f1, 1):
            ci_str = f"[{row.get('f1_ci_lower', '')}, {row.get('f1_ci_upper', '')}]"
            summary_lines.append(f"| {idx} | {row['verifier']} | {row['f1']} {ci_str} | {row['fnr']} |")

        exp1_order = [r["verifier"] for r in exp1_by_f1]
        exp2_order = [r["verifier"] for r in exp2_by_f1]
        common = [v for v in exp1_order if v in exp2_order]
        order1 = [v for v in exp1_order if v in common]
        order2 = [v for v in exp2_order if v in common]
        ranking_agrees = (order1 == order2)

        summary_lines.extend([
            "",
            f"**Ranking Agreement Across Shared Verifiers**: {'YES' if ranking_agrees else 'NO'}",
            f"- Exp 1 order: {', '.join(order1)}",
            f"- Exp 2 order: {', '.join(order2)}",
        ])
    else:
        summary_lines.extend([
            "",
            "> [!NOTE]",
            "> Experiment 2 results are pending completion of human labeling (Phase 6, Gate G2) and Phase 7 execution.",
            "> Ranking agreement check will evaluate automatically once Exp 2 is available.",
        ])

    # 3. Threshold Transfer Check (Filter B on Exp 2)
    summary_lines.extend([
        "",
        "## Threshold Transfer Analysis (Filter B)",
        "",
    ])

    data_dir = Path(cfg.paths.data)
    exp2_pairs_file = data_dir / "exp2_rag" / "pairs.jsonl"
    if exp2_dir and exp2_pairs_file.exists() and (exp2_dir / "predictions_filter_b.jsonl").exists():
        pairs2 = read_jsonl(exp2_pairs_file, Pair)
        preds2 = {r.pair_id: r for r in read_jsonl(exp2_dir / "predictions_filter_b.jsonl", VerifierResult)}

        # Load frozen dev threshold
        thresholds_file = results_dir / "thresholds.json"
        dev_threshold = 0.5
        if thresholds_file.exists():
            try:
                with open(thresholds_file, encoding="utf-8") as f:
                    th_data = json.load(f)
                dev_threshold = th_data.get("filter_b", {}).get("threshold", 0.5)
            except Exception:
                pass

        y_true: list[int] = []
        scores: list[float] = []
        for p in pairs2:
            r = preds2.get(p.pair_id)
            if r is not None and r.score is not None and p.label is not None and not r.parse_failure:
                y_true.append(p.label)
                scores.append(r.score)

        if y_true:
            # Dev threshold F1
            dev_preds = [1 if s < dev_threshold else 0 for s in scores]
            dev_f1 = f1(y_true, dev_preds)

            # Oracle sweep
            best_oracle_th = dev_threshold
            best_oracle_f1 = dev_f1
            for cand_th in sorted(list(set(scores))):
                cand_preds = [1 if s < cand_th else 0 for s in scores]
                cand_f1 = f1(y_true, cand_preds)
                if cand_f1 > best_oracle_f1:
                    best_oracle_f1 = cand_f1
                    best_oracle_th = cand_th

            transfer_gap = best_oracle_f1 - dev_f1
            summary_lines.extend([
                f"- **Frozen Dev Threshold**: `{dev_threshold:.6f}`",
                f"- **Exp 2 F1 with Frozen Dev Threshold**: `{dev_f1:.4f}`",
                f"- **Exp 2 Oracle Best Threshold**: `{best_oracle_th:.6f}` (diagnostic only, not reported as paper result)",
                f"- **Exp 2 Oracle Best F1**: `{best_oracle_f1:.4f}`",
                f"- **Transfer Cost Gap**: `{transfer_gap:.4f}`",
            ])
    else:
        summary_lines.append("Awaiting labeled Experiment 2 ground truth and Filter B predictions.")

    # 4. Qualitative Disagreement Export
    summary_lines.extend([
        "",
        "## Qualitative Disagreements for Human Review",
        "",
    ])

    disagree_csv = target_dir / "qualitative_disagreements.csv"
    disagreements: list[dict[str, Any]] = []

    # Check Exp 1 disagreements between Filter B and Baseline ROUGE
    exp1_test_file = data_dir / "exp1_medhallu" / "test.jsonl"
    fb_file = exp1_dir / "predictions_filter_b.jsonl"
    rg_file = exp1_dir / "predictions_rouge.jsonl"

    if exp1_test_file.exists() and fb_file.exists() and rg_file.exists():
        exp1_pairs = read_jsonl(exp1_test_file, Pair)
        fb_preds = {r.pair_id: r for r in read_jsonl(fb_file, VerifierResult)}
        rg_preds = {r.pair_id: r for r in read_jsonl(rg_file, VerifierResult)}

        for p in exp1_pairs:
            r_fb = fb_preds.get(p.pair_id)
            r_rg = rg_preds.get(p.pair_id)
            if r_fb and r_rg and r_fb.verdict != r_rg.verdict:
                disagreements.append({
                    "experiment": "exp1",
                    "pair_id": p.pair_id,
                    "question": p.question,
                    "context": p.context[:300] + "..." if len(p.context) > 300 else p.context,
                    "answer": p.answer,
                    "ground_truth_label": p.label,
                    "filter_b_verdict": r_fb.verdict,
                    "rouge_verdict": r_rg.verdict,
                    "filter_b_score": f"{r_fb.score:.4f}" if r_fb.score is not None else "",
                    "human_clinical_notes": "",
                })

    if disagreements:
        with open(disagree_csv, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=[
                "experiment", "pair_id", "question", "context", "answer",
                "ground_truth_label", "filter_b_verdict", "rouge_verdict",
                "filter_b_score", "human_clinical_notes",
            ])
            writer.writeheader()
            writer.writerows(disagreements)
        summary_lines.append(f"Exported {len(disagreements)} disagreement pairs to `{disagree_csv}` for human clinical review.")
    else:
        summary_lines.append("No verifier disagreements found in current results.")

    summary_lines.append("")
    summary_md = target_dir / "cross_summary.md"
    summary_md.write_text("\n".join(summary_lines), encoding="utf-8")
    logger.info("Cross-experiment summary written to %s", summary_md)

    # Save metrics JSON
    metrics_file = target_dir / "cross_metrics.json"
    with open(metrics_file, "w", encoding="utf-8") as f:
        json.dump({
            "exp1_id": exp1_id,
            "exp2_id": exp2_id,
            "ranking_agrees": ranking_agrees,
            "n_disagreements": len(disagreements),
        }, f, indent=2)

    return {
        "exp1_id": exp1_id,
        "exp2_id": exp2_id,
        "ranking_agrees": ranking_agrees,
        "summary_file": str(summary_md),
        "target_dir": str(target_dir),
    }


def main() -> None:
    """CLI entry point for cross_experiment.py."""
    setup_logging("cross_experiment")
    parser = argparse.ArgumentParser(description="Cross-experiment analysis (Phase 9)")
    parser.add_argument("--config", default="configs/config.yaml", help="Path to config.yaml")
    parser.add_argument("--run-id-exp1", default=None, help="Explicit Exp 1 run ID")
    parser.add_argument("--run-id-exp2", default=None, help="Explicit Exp 2 run ID")
    parser.add_argument("--out-dir", default=None, help="Output directory")

    args = parser.parse_args()
    cfg = load_config(args.config)
    run_cross_experiment_analysis(
        cfg,
        run_id_exp1=args.run_id_exp1,
        run_id_exp2=args.run_id_exp2,
        out_dir=Path(args.out_dir) if args.out_dir else None,
    )


if __name__ == "__main__":
    main()
