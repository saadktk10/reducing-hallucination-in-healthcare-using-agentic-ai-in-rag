"""Per-experiment evaluation: tables, breakdowns, statistical tests, and summary.

Phase 8 (Phase.md). Design.md §8.
Entry point:
    python -m src.evaluate --config configs/config.yaml --exp <exp1|exp2> [--run-id <id>]
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
from collections import defaultdict
from pathlib import Path
from typing import Any, Literal

import numpy as np
from sklearn.metrics import precision_recall_curve

from src.common.config import Config, load_config
from src.common.io import Pair, VerifierResult, read_jsonl
from src.common.logging_utils import setup_logging
from src.evaluation.metrics import (
    auroc,
    f1,
    fnr,
    fpr,
    precision,
    recall,
)
from src.evaluation.stats import bootstrap_ci, mcnemar_test

logger = logging.getLogger(__name__)


def resolve_run_dir(exp: Literal["exp1", "exp2"], cfg: Config, explicit_run_id: str | None = None) -> tuple[Path, str]:
    """Resolve directory and run_id for evaluation from LATEST.json or explicit ID."""
    results_dir = Path(cfg.paths.results)
    latest_pointer = results_dir / "LATEST.json"

    run_id = explicit_run_id
    if not run_id and latest_pointer.exists():
        try:
            with open(latest_pointer, encoding="utf-8") as f:
                latest_data = json.load(f)
            run_id = latest_data.get(exp)
        except Exception as e:
            logger.warning("Failed to read %s: %s", latest_pointer, e)

    if not run_id:
        # Fall back to finding the most recent directory in results/<exp>/
        exp_dir = results_dir / exp
        if exp_dir.exists():
            subdirs = [d for d in exp_dir.iterdir() if d.is_dir()]
            if subdirs:
                subdirs.sort(key=lambda d: d.name, reverse=True)
                run_id = subdirs[0].name

    if not run_id:
        raise FileNotFoundError(f"No run found for {exp} in {results_dir / exp}. Provide --run-id.")

    run_dir = results_dir / exp / run_id
    if not run_dir.exists():
        raise FileNotFoundError(f"Run directory does not exist: {run_dir}")

    return run_dir, run_id


def load_ground_truth_pairs(exp: Literal["exp1", "exp2"], cfg: Config) -> tuple[list[Pair], Path]:
    """Load ground truth pairs for the target experiment."""
    data_dir = Path(cfg.paths.data)
    if exp == "exp1":
        path = data_dir / "exp1_medhallu" / "test.jsonl"
    else:
        path = data_dir / "exp2_rag" / "pairs.jsonl"

    if not path.exists():
        raise FileNotFoundError(
            f"Ground truth dataset does not exist: {path}. "
            + ("Ensure Phase 6 labeling and merge are complete." if exp == "exp2" else "")
        )

    pairs = read_jsonl(path, Pair)
    return pairs, path


def find_prediction_files(run_dir: Path) -> dict[str, Path]:
    """Find available verifier prediction files in the run directory."""
    pred_files: dict[str, Path] = {}
    patterns = {
        "filter_b": ["predictions_filter_b.jsonl", "filter_b_test_results.jsonl"],
        "rouge": ["predictions_rouge.jsonl", "predictions_baseline_rouge.jsonl", "rouge_test_results.jsonl"],
        "filter_a": ["predictions_filter_a.jsonl", "filter_a_test_results.jsonl"],
        "filter_b_base": ["predictions_filter_b_base.jsonl"],
    }

    for verifier, candidates in patterns.items():
        for cand in candidates:
            cand_path = run_dir / cand
            if cand_path.exists():
                pred_files[verifier] = cand_path
                break

    return pred_files


def compute_f1_bootstrap_ci_exp1(
    pairs: list[Pair],
    preds: dict[str, VerifierResult],
    seed: int = 42,
    n_resamples: int = 1000,
    ci: float = 0.95,
) -> tuple[float, float, float]:
    """Question-level bootstrap 95% CI for F1 in Exp 1 (Design.md §8.2).

    Resamples question IDs with replacement (keeping both pairs of a question together).
    """
    q_to_pairs: dict[str, list[Pair]] = defaultdict(list)
    for p in pairs:
        q_to_pairs[p.question_id].append(p)

    unique_qids = list(q_to_pairs.keys())

    def metric_fn(sampled_qids: list[str]) -> float:
        y_true: list[int] = []
        y_pred: list[int] = []
        for qid in sampled_qids:
            for p in q_to_pairs[qid]:
                res = preds.get(p.pair_id)
                if res is not None and res.verdict is not None and p.label is not None:
                    y_true.append(p.label)
                    y_pred.append(res.verdict)
        return f1(y_true, y_pred) if y_true else 0.0

    return bootstrap_ci(unique_qids, metric_fn, n_resamples=n_resamples, ci=ci, seed=seed)


def compute_f1_bootstrap_ci_exp2(
    pairs: list[Pair],
    preds: dict[str, VerifierResult],
    seed: int = 42,
    n_resamples: int = 1000,
    ci: float = 0.95,
) -> tuple[float, float, float]:
    """Pair-level bootstrap 95% CI for F1 in Exp 2 (Design.md §8.2)."""
    valid_pairs = [p for p in pairs if preds.get(p.pair_id) is not None and preds[p.pair_id].verdict is not None and p.label is not None]

    def metric_fn(sampled_pairs: list[Pair]) -> float:
        y_true = [p.label for p in sampled_pairs if p.label is not None]
        y_pred = [preds[p.pair_id].verdict for p in sampled_pairs if preds[p.pair_id].verdict is not None]
        return f1(y_true, y_pred) if y_true else 0.0

    return bootstrap_ci(valid_pairs, metric_fn, n_resamples=n_resamples, ci=ci, seed=seed)


def evaluate_experiment(
    exp: Literal["exp1", "exp2"],
    cfg: Config,
    explicit_run_id: str | None = None,
) -> dict[str, Any]:
    """Run comprehensive evaluation for exp1 or exp2."""
    run_dir, run_id = resolve_run_dir(exp, cfg, explicit_run_id)
    pairs, gt_path = load_ground_truth_pairs(exp, cfg)
    pred_files = find_prediction_files(run_dir)

    if not pred_files:
        raise FileNotFoundError(f"No prediction files found in {run_dir}")

    logger.info("Evaluating %s on %d ground-truth pairs from %s", exp, len(pairs), gt_path)
    logger.info("Found verifiers: %s", list(pred_files.keys()))

    predictions_by_verifier: dict[str, dict[str, VerifierResult]] = {}
    for verifier, pfile in pred_files.items():
        records = read_jsonl(pfile, VerifierResult)
        predictions_by_verifier[verifier] = {r.pair_id: r for r in records}

    tables_dir = run_dir / "tables"
    tables_dir.mkdir(parents=True, exist_ok=True)

    # 1. Main Metrics Table
    main_rows: list[dict[str, Any]] = []
    for verifier, preds in predictions_by_verifier.items():
        y_true: list[int] = []
        y_pred: list[int] = []
        scores: list[float] = []
        parse_fails = 0

        for p in pairs:
            res = preds.get(p.pair_id)
            if res is None:
                continue
            if res.parse_failure:
                parse_fails += 1
                continue
            if p.label is not None and res.verdict is not None:
                y_true.append(p.label)
                y_pred.append(res.verdict)
            if res.score is not None:
                scores.append(res.score)

        n = len(y_true)
        p_val = precision(y_true, y_pred) if n else 0.0
        r_val = recall(y_true, y_pred) if n else 0.0
        f1_val = f1(y_true, y_pred) if n else 0.0
        fnr_val = fnr(y_true, y_pred) if n else 0.0
        fpr_val = fpr(y_true, y_pred) if n else 0.0
        auroc_val = auroc(y_true, scores) if len(scores) == n and n > 0 else float("nan")

        # Bootstrap CI
        if exp == "exp1":
            point, ci_low, ci_high = compute_f1_bootstrap_ci_exp1(pairs, preds, seed=cfg.seed)
        else:
            point, ci_low, ci_high = compute_f1_bootstrap_ci_exp2(pairs, preds, seed=cfg.seed)

        main_rows.append({
            "verifier": verifier,
            "n": n,
            "parse_failures": parse_fails,
            "precision": round(p_val, 4),
            "recall": round(r_val, 4),
            "f1": round(f1_val, 4),
            "f1_ci_lower": round(ci_low, 4),
            "f1_ci_upper": round(ci_high, 4),
            "fnr": round(fnr_val, 4),
            "fpr": round(fpr_val, 4),
            "auroc": round(auroc_val, 4) if not np.isnan(auroc_val) else "N/A",
        })

    main_csv = tables_dir / "main_metrics.csv"
    with open(main_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "verifier", "n", "parse_failures", "precision", "recall",
            "f1", "f1_ci_lower", "f1_ci_upper", "fnr", "fpr", "auroc",
        ])
        writer.writeheader()
        writer.writerows(main_rows)

    # 2. McNemar Paired Tests
    mcnemar_rows: list[dict[str, Any]] = []
    verifiers_list = list(predictions_by_verifier.keys())
    for i in range(len(verifiers_list)):
        for j in range(i + 1, len(verifiers_list)):
            v1_name = verifiers_list[i]
            v2_name = verifiers_list[j]
            v1_preds = predictions_by_verifier[v1_name]
            v2_preds = predictions_by_verifier[v2_name]

            both_correct = 0
            v1_only = 0
            v2_only = 0
            both_incorrect = 0
            total_compared = 0

            for p in pairs:
                r1 = v1_preds.get(p.pair_id)
                r2 = v2_preds.get(p.pair_id)
                if r1 is None or r2 is None or r1.parse_failure or r2.parse_failure:
                    continue
                if p.label is None or r1.verdict is None or r2.verdict is None:
                    continue

                total_compared += 1
                c1 = (r1.verdict == p.label)
                c2 = (r2.verdict == p.label)

                if c1 and c2:
                    both_correct += 1
                elif c1 and not c2:
                    v1_only += 1
                elif not c1 and c2:
                    v2_only += 1
                else:
                    both_incorrect += 1

            table = [[both_correct, v1_only], [v2_only, both_incorrect]]
            m_res = mcnemar_test(table)

            mcnemar_rows.append({
                "comparison": f"{v1_name}_vs_{v2_name}",
                "n_compared": total_compared,
                "both_correct": both_correct,
                f"{v1_name}_only": v1_only,
                f"{v2_name}_only": v2_only,
                "both_incorrect": both_incorrect,
                "statistic": m_res["statistic"],
                "pvalue": round(m_res["pvalue"], 6),
            })

    mcnemar_csv = tables_dir / "mcnemar.csv"
    if mcnemar_rows:
        with open(mcnemar_csv, "w", newline="", encoding="utf-8") as f:
            fieldnames = list(mcnemar_rows[0].keys())
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(mcnemar_rows)

    # 3. Breakdowns
    diff_rows: list[dict[str, Any]] = []
    cat_rows: list[dict[str, Any]] = []
    cond_rows: list[dict[str, Any]] = []

    if exp == "exp1":
        # Difficulty breakdown
        difficulties = sorted(list({p.difficulty for p in pairs if p.difficulty}))
        for d in difficulties:
            d_pairs = [p for p in pairs if p.difficulty == d]
            for v_name, preds in predictions_by_verifier.items():
                y_t = [p.label for p in d_pairs if p.label is not None and p.pair_id in preds and preds[p.pair_id].verdict is not None and not preds[p.pair_id].parse_failure]
                y_p = [preds[p.pair_id].verdict for p in d_pairs if p.label is not None and p.pair_id in preds and preds[p.pair_id].verdict is not None and not preds[p.pair_id].parse_failure]
                if y_t:
                    diff_rows.append({
                        "difficulty": d,
                        "verifier": v_name,
                        "n": len(y_t),
                        "precision": round(precision(y_t, y_p), 4),
                        "recall": round(recall(y_t, y_p), 4),
                        "f1": round(f1(y_t, y_p), 4),
                        "fnr": round(fnr(y_t, y_p), 4),
                        "fpr": round(fpr(y_t, y_p), 4),
                    })

        diff_csv = tables_dir / "difficulty_breakdown.csv"
        with open(diff_csv, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["difficulty", "verifier", "n", "precision", "recall", "f1", "fnr", "fpr"])
            writer.writeheader()
            writer.writerows(diff_rows)

        # Category breakdown
        # Per Design.md §8.3: supported pairs grouped with their question's category for per-question analysis
        q_categories: dict[str, str] = {}
        for p in pairs:
            if p.category:
                q_categories[p.question_id] = p.category

        categories = sorted(list({c for c in q_categories.values()}))
        for c in categories:
            c_pairs = [p for p in pairs if q_categories.get(p.question_id) == c]
            for v_name, preds in predictions_by_verifier.items():
                y_t = [p.label for p in c_pairs if p.label is not None and p.pair_id in preds and preds[p.pair_id].verdict is not None and not preds[p.pair_id].parse_failure]
                y_p = [preds[p.pair_id].verdict for p in c_pairs if p.label is not None and p.pair_id in preds and preds[p.pair_id].verdict is not None and not preds[p.pair_id].parse_failure]
                if y_t:
                    cat_rows.append({
                        "category": c,
                        "verifier": v_name,
                        "n": len(y_t),
                        "precision": round(precision(y_t, y_p), 4),
                        "recall": round(recall(y_t, y_p), 4),
                        "f1": round(f1(y_t, y_p), 4),
                        "fnr": round(fnr(y_t, y_p), 4),
                        "fpr": round(fpr(y_t, y_p), 4),
                    })

        cat_csv = tables_dir / "category_breakdown.csv"
        with open(cat_csv, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["category", "verifier", "n", "precision", "recall", "f1", "fnr", "fpr"])
            writer.writeheader()
            writer.writerows(cat_rows)

    elif exp == "exp2":
        # Condition breakdown (normal vs degraded)
        conditions = ["normal", "degraded"]
        for cond in conditions:
            c_pairs = [p for p in pairs if p.condition == cond]
            for v_name, preds in predictions_by_verifier.items():
                y_t = [p.label for p in c_pairs if p.label is not None and p.pair_id in preds and preds[p.pair_id].verdict is not None and not preds[p.pair_id].parse_failure]
                y_p = [preds[p.pair_id].verdict for p in c_pairs if p.label is not None and p.pair_id in preds and preds[p.pair_id].verdict is not None and not preds[p.pair_id].parse_failure]
                if y_t:
                    cond_rows.append({
                        "condition": cond,
                        "verifier": v_name,
                        "n": len(y_t),
                        "precision": round(precision(y_t, y_p), 4),
                        "recall": round(recall(y_t, y_p), 4),
                        "f1": round(f1(y_t, y_p), 4),
                        "fnr": round(fnr(y_t, y_p), 4),
                        "fpr": round(fpr(y_t, y_p), 4),
                    })

        cond_csv = tables_dir / "condition_breakdown.csv"
        with open(cond_csv, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["condition", "verifier", "n", "precision", "recall", "f1", "fnr", "fpr"])
            writer.writeheader()
            writer.writerows(cond_rows)

    # 4. Precision-Recall Curve for Filter B
    if "filter_b" in predictions_by_verifier:
        fb_preds = predictions_by_verifier["filter_b"]
        y_t_fb: list[int] = []
        scores_fb: list[float] = []
        for p in pairs:
            r = fb_preds.get(p.pair_id)
            if r is not None and r.score is not None and p.label is not None and not r.parse_failure:
                y_t_fb.append(p.label)
                # Invert support score so 1 - score is the hallucination score (pos_label=1)
                scores_fb.append(1.0 - float(r.score))

        if len(set(y_t_fb)) > 1:
            p_curve, r_curve, thres_curve = precision_recall_curve(y_t_fb, scores_fb)
            pr_csv = tables_dir / "pr_curve_filter_b.csv"
            with open(pr_csv, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["precision", "recall", "threshold"])
                # Note: thresholds has len(precision) - 1
                for k in range(len(thres_curve)):
                    writer.writerow([round(p_curve[k], 5), round(r_curve[k], 5), round(thres_curve[k], 5)])
                # Write final endpoint
                writer.writerow([round(p_curve[-1], 5), round(r_curve[-1], 5), 1.0])

    # 5. Timing and Cost Summary (from timing JSONs if present)
    timing_info: dict[str, Any] = {}
    for verifier in ["filter_b", "rouge", "filter_a"]:
        t_path = run_dir / f"timing_{verifier}.json"
        if not t_path.exists():
            t_path = run_dir / f"timing_{verifier}_morning.json"
        if t_path.exists():
            try:
                with open(t_path, encoding="utf-8") as f:
                    t_data = json.load(f)
                timing_info[verifier] = t_data
            except Exception:
                pass

    # 6. Generate summary.md
    summary_path = run_dir / "summary.md"
    summary_lines = [
        f"# Evaluation Summary: {exp.upper()}",
        "",
        f"- **Run ID**: `{run_id}`",
        f"- **Dataset**: `{gt_path}` (n={len(pairs)})",
        f"- **Verifiers Evaluated**: {', '.join(predictions_by_verifier.keys())}",
        "",
        "## Main Classification Metrics",
        "",
        "| Verifier | n | Parse Failures | Precision | Recall | F1 | 95% Bootstrap CI | FNR | FPR | AUROC |",
        "| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |",
    ]
    for row in main_rows:
        ci_str = f"[{row['f1_ci_lower']:.4f}, {row['f1_ci_upper']:.4f}]"
        summary_lines.append(
            f"| {row['verifier']} | {row['n']} | {row['parse_failures']} | {row['precision']:.4f} | {row['recall']:.4f} | {row['f1']:.4f} | {ci_str} | {row['fnr']:.4f} | {row['fpr']:.4f} | {row['auroc']} |"
        )

    if mcnemar_rows:
        summary_lines.extend([
            "",
            "## Paired Significance Tests (McNemar Exact)",
            "",
            "| Comparison | n | Both Correct | V1 Only | V2 Only | Both Incorrect | Statistic | p-value |",
            "| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |",
        ])
        for m in mcnemar_rows:
            v_keys = [k for k in m.keys() if k.endswith("_only")]
            v1_k, v2_k = v_keys[0], v_keys[1]
            summary_lines.append(
                f"| {m['comparison']} | {m['n_compared']} | {m['both_correct']} | {m[v1_k]} | {m[v2_k]} | {m['both_incorrect']} | {m['statistic']} | {m['pvalue']:.6f} |"
            )

    if timing_info:
        summary_lines.extend([
            "",
            "## Latency and System Efficiency",
            "",
            "| Verifier | Pooled Median (ms) | Pooled p95 (ms) | Model Load (s) | Peak RSS (MB) |",
            "| :--- | :--- | :--- | :--- | :--- |",
        ])
        for v_name, t_data in timing_info.items():
            pooled = t_data.get("pooled", {})
            med = pooled.get("median_ms", "N/A")
            p95 = pooled.get("p95_ms", "N/A")
            load_s = t_data.get("load_time_seconds", "N/A")
            peak_mb = t_data.get("peak_rss_mb", "N/A")
            summary_lines.append(f"| {v_name} | {med} | {p95} | {load_s} | {peak_mb} |")

    if diff_rows:
        summary_lines.extend([
            "",
            "## Stratified Breakdown: Difficulty (Exp 1)",
            "",
            "| Difficulty | Verifier | n | Precision | Recall | F1 | FNR | FPR |",
            "| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |",
        ])
        for r in diff_rows:
            summary_lines.append(
                f"| {r['difficulty']} | {r['verifier']} | {r['n']} | {r['precision']:.4f} | {r['recall']:.4f} | {r['f1']:.4f} | {r['fnr']:.4f} | {r['fpr']:.4f} |"
            )

    if cat_rows:
        summary_lines.extend([
            "",
            "## Stratified Breakdown: Hallucination Category (Exp 1)",
            "",
            "| Category | Verifier | n | Precision | Recall | F1 | FNR | FPR |",
            "| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |",
        ])
        for r in cat_rows:
            summary_lines.append(
                f"| {r['category']} | {r['verifier']} | {r['n']} | {r['precision']:.4f} | {r['recall']:.4f} | {r['f1']:.4f} | {r['fnr']:.4f} | {r['fpr']:.4f} |"
            )

    if cond_rows:
        summary_lines.extend([
            "",
            "## Stratified Breakdown: Retrieval Condition (Exp 2)",
            "",
            "| Condition | Verifier | n | Precision | Recall | F1 | FNR | FPR |",
            "| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |",
        ])
        for r in cond_rows:
            summary_lines.append(
                f"| {r['condition']} | {r['verifier']} | {r['n']} | {r['precision']:.4f} | {r['recall']:.4f} | {r['f1']:.4f} | {r['fnr']:.4f} | {r['fpr']:.4f} |"
            )

    summary_lines.append("")
    summary_path.write_text("\n".join(summary_lines), encoding="utf-8")
    logger.info("Summary markdown written to %s", summary_path)

    # 7. Update metrics.json with structured site records
    metrics_file = run_dir / "metrics.json"
    existing_metrics: dict[str, Any] = {}
    if metrics_file.exists():
        try:
            with open(metrics_file, encoding="utf-8") as f:
                existing_metrics = json.load(f)
        except Exception:
            pass

    # Accuracy mapping
    accuracy_dict = existing_metrics.get("accuracy", {})
    for row in main_rows:
        v_name = row["verifier"]
        accuracy_dict[v_name] = {
            "n": row["n"],
            "parse_failures": row["parse_failures"],
            "precision": row["precision"],
            "recall": row["recall"],
            "f1": row["f1"],
            "f1_ci": [row["f1_ci_lower"], row["f1_ci_upper"]],
            "fnr": row["fnr"],
            "fpr": row["fpr"],
            "auroc": row["auroc"],
        }
        # TILE_REGISTRY keys
        ci_str = f"[{row['f1_ci_lower']:.4f}, {row['f1_ci_upper']:.4f}]"
        existing_metrics[f"{exp}.{v_name}.f1"] = {
            "value": row["f1"],
            "display": f"{row['f1']:.4f} {ci_str}",
            "ci": [row["f1_ci_lower"], row["f1_ci_upper"]],
            "source": metrics_file.as_posix(),
        }
        existing_metrics[f"{exp}.{v_name}.fnr"] = {
            "value": row["fnr"],
            "display": f"{row['fnr']:.4f}",
            "source": metrics_file.as_posix(),
        }

    # McNemar p-value tile
    for m in mcnemar_rows:
        if m["comparison"] in ("filter_a_vs_filter_b", "filter_b_vs_filter_a"):
            existing_metrics[f"{exp}.mcnemar_ab.p"] = {
                "value": m["pvalue"],
                "display": f"p = {m['pvalue']:.4f}",
                "source": metrics_file.as_posix(),
            }

    existing_metrics["accuracy"] = accuracy_dict
    with open(metrics_file, "w", encoding="utf-8") as f:
        json.dump(existing_metrics, f, indent=2)

    logger.info("Updated metrics in %s", metrics_file)

    return {
        "run_id": run_id,
        "main_metrics": main_rows,
        "mcnemar": mcnemar_rows,
        "summary_file": str(summary_path),
        "tables_dir": str(tables_dir),
    }


def main() -> None:
    """CLI entry point for evaluate.py."""
    setup_logging("evaluate")
    parser = argparse.ArgumentParser(description="Evaluate verifiers and generate publication tables")
    parser.add_argument("--config", default="configs/config.yaml", help="Path to config.yaml")
    parser.add_argument("--exp", choices=["exp1", "exp2"], required=True, help="Target experiment")
    parser.add_argument("--run-id", default=None, help="Explicit run ID")

    args = parser.parse_args()
    cfg = load_config(args.config)
    evaluate_experiment(args.exp, cfg, explicit_run_id=args.run_id)


if __name__ == "__main__":
    main()
