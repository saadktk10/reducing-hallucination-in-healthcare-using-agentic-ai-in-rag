"""Pilot checks: field inspection, spot-check export, ROUGE-L baseline, and report.

Phase 1 (Phase.md). Entry point: python -m src.pilot_checks --config configs/config.yaml --step <step>

Steps:
    fields    — Load MedHallu, print columns/types, export 20 rows (Task 1).
    spotcheck — Sample 50 rows, export CSV with empty annotation columns (Task 2).
    rouge     — Build provisional dev set, compute ROUGE-L AUROC (Task 4).
    report    — Read annotations + rouge, apply Gate G1 decision rule (Task 5).
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import random
import sys
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
from datasets import load_dataset
from rouge_score import rouge_scorer
from sklearn.metrics import roc_auc_score

from src.common.config import Config, load_config
from src.common.logging_utils import setup_logging

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load_medhallu(cfg: Config) -> Any:
    """Load MedHallu dataset from HuggingFace.

    If revision is 'TBD', loads HEAD and logs a warning.

    Returns:
        A HuggingFace Dataset object.
    """
    ds_cfg = cfg.datasets.medhallu
    revision = None if ds_cfg.revision == "TBD" else ds_cfg.revision
    if revision is None:
        logger.warning(
            "MedHallu revision is TBD — downloading at HEAD. "
            "Pin the revision in config.yaml after inspecting fields (Rule R4.4)."
        )
    ds = load_dataset(ds_cfg.hf_id, ds_cfg.config, revision=revision)
    # MedHallu is a single split; get the underlying dataset.
    if hasattr(ds, "keys"):
        # DatasetDict — pick the first (and usually only) split.
        split_name = list(ds.keys())[0]
        logger.info("Using split %r from DatasetDict (available: %s)", split_name, list(ds.keys()))
        ds = ds[split_name]
    return ds


def _get_context(row: dict[str, Any], col_name: str) -> str:
    """Get context string from a dataset row.

    The MedHallu 'Knowledge' column is List[str] (multiple abstract sentences).
    This helper joins them into a single string.
    """
    val = row[col_name]
    if isinstance(val, list):
        return " ".join(val)
    return str(val)


def _validate_columns(ds: Any, cfg: Config) -> dict[str, bool]:
    """Check that expected column names from config exist in the dataset.

    Returns:
        A dict mapping config_key -> whether the column was found.
    """
    actual_cols = set(ds.column_names)
    cols_cfg = cfg.datasets.medhallu.columns
    if cols_cfg is None:
        logger.error("No column mapping in config.datasets.medhallu.columns")
        return {}

    results: dict[str, bool] = {}
    for field in ["question", "context", "ground_truth", "hallucinated", "difficulty", "category"]:
        expected = getattr(cols_cfg, field, None)
        found = expected in actual_cols if expected else False
        results[field] = found
        if not found:
            logger.error("Expected column %r (config key: %s) NOT FOUND in dataset", expected, field)
        else:
            logger.info("Column %r (config key: %s) ✓ found", expected, field)
    return results


def _build_provisional_dev(
    ds: Any, cfg: Config
) -> list[dict[str, Any]]:
    """Build a provisional 100-pair dev set using the same logic as Phase 2.

    Same seed, same stratification, same question-level splitting — so the
    pilot dev set matches the final Phase 2 dev set.

    Returns:
        A list of Pair-like dicts with fields: pair_id, question_id, question,
        context, answer, label, difficulty, category, split.
    """
    cols = cfg.datasets.medhallu.columns
    assert cols is not None, "Column mapping required"

    rng = random.Random(cfg.seed)

    # Group rows by question text to handle duplicates.
    # Each MedHallu row gives us a question with both ground_truth and hallucinated.
    rows = list(range(len(ds)))
    rng.shuffle(rows)

    # Stratified sample of n_questions by difficulty.
    n_questions = cfg.exp1.n_questions
    dev_questions = cfg.pilot.rouge_dev_questions

    # Group by difficulty.
    difficulty_groups: dict[str, list[int]] = {}
    for idx in rows:
        diff = str(ds[idx][cols.difficulty]) if cols.difficulty in ds.column_names else "unknown"
        difficulty_groups.setdefault(diff, []).append(idx)

    # Proportional stratified sample.
    total_available = len(rows)
    sampled_indices: list[int] = []
    for diff, indices in sorted(difficulty_groups.items()):
        proportion = len(indices) / total_available
        n_stratum = max(1, round(proportion * n_questions))
        # Don't exceed available.
        n_stratum = min(n_stratum, len(indices))
        sampled_indices.extend(indices[:n_stratum])
        logger.info(
            "Difficulty %r: %d available, sampling %d (%.1f%%)",
            diff, len(indices), n_stratum, proportion * 100,
        )

    # Trim to exactly n_questions.
    sampled_indices = sampled_indices[:n_questions]
    logger.info("Total sampled questions: %d", len(sampled_indices))

    # Split: first dev_questions to dev, rest to test — by question.
    # Shuffle sampled indices with same seed for deterministic split.
    rng2 = random.Random(cfg.seed)
    rng2.shuffle(sampled_indices)

    # Build pairs for dev only (that's what we need for the pilot ROUGE check).
    pairs: list[dict[str, Any]] = []
    for i, idx in enumerate(sampled_indices[:dev_questions]):
        row = ds[idx]
        qid = f"q{i:03d}"

        # Ground truth pair (label=0, Supported).
        pairs.append({
            "pair_id": f"e1-{qid}-gt",
            "question_id": qid,
            "question": row[cols.question],
            "context": _get_context(row, cols.context),
            "answer": row[cols.ground_truth],
            "label": 0,
            "difficulty": str(row[cols.difficulty]) if cols.difficulty in ds.column_names else None,
            "category": str(row[cols.category]) if cols.category in ds.column_names else None,
            "split": "dev",
        })

        # Hallucinated pair (label=1, Hallucinated).
        pairs.append({
            "pair_id": f"e1-{qid}-hal",
            "question_id": qid,
            "question": row[cols.question],
            "context": _get_context(row, cols.context),
            "answer": row[cols.hallucinated],
            "label": 1,
            "difficulty": str(row[cols.difficulty]) if cols.difficulty in ds.column_names else None,
            "category": str(row[cols.category]) if cols.category in ds.column_names else None,
            "split": "dev",
        })

    logger.info("Built %d provisional dev pairs from %d questions", len(pairs), dev_questions)
    return pairs


# ---------------------------------------------------------------------------
# Step implementations
# ---------------------------------------------------------------------------


def step_fields(cfg: Config) -> None:
    """Task 1: Load MedHallu, print columns/types, export 20 rows."""
    logger.info("=== Step: fields ===")
    ds = _load_medhallu(cfg)

    out_dir = Path(cfg.paths.data) / "pilot"
    out_dir.mkdir(parents=True, exist_ok=True)

    # Column info.
    col_info: list[dict[str, str]] = []
    for col_name in ds.column_names:
        feat = ds.features[col_name]
        col_info.append({"name": col_name, "dtype": str(feat)})
        logger.info("  Column: %-30s  Type: %s", col_name, feat)

    # Validate expected columns.
    col_checks = _validate_columns(ds, cfg)

    # Export first N rows.
    n = cfg.pilot.fields_n
    sample_rows: list[dict[str, Any]] = []
    for i in range(min(n, len(ds))):
        row = {}
        for col in ds.column_names:
            val = ds[i][col]
            # Convert non-serializable types.
            if hasattr(val, "item"):
                val = val.item()
            row[col] = val
        sample_rows.append(row)

    # Get dataset info.
    ds_info = {
        "hf_id": cfg.datasets.medhallu.hf_id,
        "config": cfg.datasets.medhallu.config,
        "revision_requested": cfg.datasets.medhallu.revision,
        "num_rows": len(ds),
        "num_columns": len(ds.column_names),
        "columns": col_info,
        "column_checks": col_checks,
        "sample_rows": sample_rows,
        "exported_at": datetime.now(UTC).isoformat(),
    }

    out_path = out_dir / "fields_20.json"
    with open(out_path, "w") as f:
        json.dump(ds_info, f, indent=2, ensure_ascii=False, default=str)

    logger.info("Wrote %d sample rows to %s", n, out_path)
    logger.info("Dataset has %d rows, %d columns", len(ds), len(ds.column_names))

    # Report any column mismatches.
    mismatches = [k for k, v in col_checks.items() if not v]
    if mismatches:
        logger.error(
            "COLUMN MISMATCH — update config.yaml columns: %s", mismatches
        )
        print(f"\n⚠️  Column mismatches found: {mismatches}")
        print("   Update configs/config.yaml datasets.medhallu.columns before proceeding.")
    else:
        print("\n✅ All expected columns found in MedHallu dataset.")
    print(f"   Dataset: {len(ds)} rows, {len(ds.column_names)} columns")
    print(f"   Output: {out_path}")


def step_spotcheck(cfg: Config) -> None:
    """Task 2: Sample 50 rows, export CSV for human annotation."""
    logger.info("=== Step: spotcheck ===")
    ds = _load_medhallu(cfg)
    cols = cfg.datasets.medhallu.columns
    assert cols is not None, "Column mapping required in config"

    out_dir = Path(cfg.paths.data) / "pilot"
    out_dir.mkdir(parents=True, exist_ok=True)

    # Seeded sample.
    n = cfg.pilot.spotcheck_n
    rng = random.Random(cfg.seed)
    indices = list(range(len(ds)))
    rng.shuffle(indices)
    sample_indices = sorted(indices[:n])

    logger.info("Sampled %d rows (seed=%d): indices %s", n, cfg.seed, sample_indices)

    out_path = out_dir / "spotcheck_50.csv"
    with open(out_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["row_id", "question", "context", "ground_truth", "supported_yes_no", "notes"])
        for idx in sample_indices:
            row = ds[idx]
            writer.writerow([
                idx,
                row[cols.question],
                _get_context(row, cols.context),
                row[cols.ground_truth],
                "",  # supported_yes_no — left empty for humans (Rule R1.5)
                "",  # notes — left empty for humans
            ])

    logger.info("Wrote spot-check CSV to %s (%d rows)", out_path, n)
    print(f"\n✅ Spot-check CSV exported: {out_path}")
    print(f"   {n} rows sampled (seed={cfg.seed})")
    print("   ⚠️  Both researchers must fill 'supported_yes_no' column independently (Rule R1.5)")


def step_rouge(cfg: Config) -> None:
    """Task 4: Build provisional dev set, compute ROUGE-L AUROC."""
    logger.info("=== Step: rouge ===")
    ds = _load_medhallu(cfg)

    # Build provisional dev set (same logic as Phase 2, same seed).
    pairs = _build_provisional_dev(ds, cfg)
    if not pairs:
        logger.error("No pairs built — check column mapping")
        sys.exit(1)

    # Compute ROUGE-L scores.
    scorer = rouge_scorer.RougeScorer(["rougeL"], use_stemmer=True)

    results: list[dict[str, Any]] = []
    for pair in pairs:
        scores = scorer.score(target=pair["context"], prediction=pair["answer"])
        rouge_l = scores["rougeL"]
        results.append({
            "pair_id": pair["pair_id"],
            "question_id": pair["question_id"],
            "label": pair["label"],
            "difficulty": pair["difficulty"],
            "rougeL_precision": rouge_l.precision,
            "rougeL_recall": rouge_l.recall,
            "rougeL_fmeasure": rouge_l.fmeasure,
        })

    # Compute AUROC for each variant.
    labels = np.array([r["label"] for r in results])
    auroc_results: dict[str, float] = {}

    for variant in ["rougeL_precision", "rougeL_recall", "rougeL_fmeasure"]:
        scores_arr = np.array([r[variant] for r in results])
        # Score direction: high = more supported. For AUROC with Hallucinated as
        # positive, use 1 - score (Design.md §3.4 score direction convention).
        try:
            auroc = float(roc_auc_score(labels, 1.0 - scores_arr))
            auroc_results[variant] = auroc
            logger.info("AUROC (%s): %.4f", variant, auroc)
        except ValueError as e:
            logger.error("Cannot compute AUROC for %s: %s", variant, e)
            auroc_results[variant] = float("nan")

    # Summary stats.
    label_counts = Counter(r["label"] for r in results)
    difficulty_counts = Counter(r["difficulty"] for r in results)

    out_dir = Path(cfg.paths.data) / "pilot"
    out_dir.mkdir(parents=True, exist_ok=True)

    rouge_output = {
        "n_pairs": len(results),
        "n_questions": len(set(r["question_id"] for r in results)),
        "label_distribution": dict(label_counts),
        "difficulty_distribution": dict(difficulty_counts),
        "auroc": auroc_results,
        "primary_variant": f"rougeL_{cfg.baseline.rouge_field}",
        "primary_auroc": auroc_results.get(f"rougeL_{cfg.baseline.rouge_field}", float("nan")),
        "seed": cfg.seed,
        "per_pair_scores": results,
        "computed_at": datetime.now(UTC).isoformat(),
    }

    out_path = out_dir / "rouge_results.json"
    with open(out_path, "w") as f:
        json.dump(rouge_output, f, indent=2, default=str)

    logger.info("Wrote ROUGE-L results to %s", out_path)
    print(f"\n✅ ROUGE-L AUROC computed on {len(results)} provisional dev pairs")
    print(f"   Labels: {dict(label_counts)}")
    for variant, auroc in auroc_results.items():
        marker = " ← primary" if variant == f"rougeL_{cfg.baseline.rouge_field}" else ""
        print(f"   AUROC ({variant}): {auroc:.4f}{marker}")
    print(f"   Output: {out_path}")


def step_report(cfg: Config) -> None:
    """Task 5: Read annotations + rouge results, apply Gate G1 decision rule."""
    logger.info("=== Step: report ===")
    data_dir = Path(cfg.paths.data) / "pilot"
    results_dir = Path(cfg.paths.results) / "pilot"
    results_dir.mkdir(parents=True, exist_ok=True)

    # --- Read spot-check annotations ---
    spotcheck_path = data_dir / "spotcheck_50.csv"
    if not spotcheck_path.exists():
        logger.error("Spot-check CSV not found: %s — run --step spotcheck first", spotcheck_path)
        sys.exit(1)

    with open(spotcheck_path, newline="") as f:
        reader = csv.DictReader(f)
        spotcheck_rows = list(reader)

    total_checked = 0
    unsupported_count = 0
    unfilled = 0
    for row in spotcheck_rows:
        val = row.get("supported_yes_no", "").strip().lower()
        if val == "":
            unfilled += 1
            continue
        total_checked += 1
        if val in ("no", "n", "0", "false", "unsupported"):
            unsupported_count += 1

    if unfilled > 0:
        logger.warning(
            "%d of %d spot-check rows have empty 'supported_yes_no' — "
            "are humans done annotating?",
            unfilled, len(spotcheck_rows),
        )

    unsupported_rate = unsupported_count / total_checked if total_checked > 0 else None

    # --- Read ROUGE results ---
    rouge_path = data_dir / "rouge_results.json"
    if not rouge_path.exists():
        logger.error("ROUGE results not found: %s — run --step rouge first", rouge_path)
        sys.exit(1)

    with open(rouge_path) as f:
        rouge_data = json.load(f)

    primary_auroc = rouge_data.get("primary_auroc")
    auroc_all = rouge_data.get("auroc", {})

    # --- Apply Gate G1 decision rule ---
    # Phase.md: Unsupported < 10% AND ROUGE-L AUROC < 0.95 → Plan 1
    #           Otherwise → Plan 2
    gate_threshold_unsupported = 0.10
    gate_threshold_auroc = 0.95

    if unsupported_rate is not None and primary_auroc is not None:
        plan_1_eligible = (
            unsupported_rate < gate_threshold_unsupported
            and primary_auroc < gate_threshold_auroc
        )
        recommended_plan = 1 if plan_1_eligible else 2
        gate_reason = (
            f"Unsupported rate={unsupported_rate:.1%} "
            f"({'<' if unsupported_rate < gate_threshold_unsupported else '>='} 10%), "
            f"ROUGE-L AUROC={primary_auroc:.4f} "
            f"({'<' if primary_auroc < gate_threshold_auroc else '>='} 0.95) "
            f"→ Plan {recommended_plan}"
        )
    else:
        recommended_plan = None
        gate_reason = "Cannot compute — missing annotations or ROUGE data"

    # --- Write pilot report JSON ---
    report = {
        "spotcheck": {
            "total_rows": len(spotcheck_rows),
            "total_checked": total_checked,
            "unfilled": unfilled,
            "unsupported_count": unsupported_count,
            "unsupported_rate": unsupported_rate,
        },
        "rouge": {
            "n_pairs": rouge_data.get("n_pairs"),
            "n_questions": rouge_data.get("n_questions"),
            "auroc": auroc_all,
            "primary_variant": rouge_data.get("primary_variant"),
            "primary_auroc": primary_auroc,
        },
        "gate_g1": {
            "threshold_unsupported": gate_threshold_unsupported,
            "threshold_auroc": gate_threshold_auroc,
            "recommended_plan": recommended_plan,
            "reason": gate_reason,
        },
        "generated_at": datetime.now(UTC).isoformat(),
    }

    report_json_path = data_dir / "pilot_report.json"
    with open(report_json_path, "w") as f:
        json.dump(report, f, indent=2, default=str)

    # --- Write site metrics JSON for site_export.py ---
    metrics_path = results_dir / "metrics.json"
    pilot_metrics = {
        "pilot.unsupported_rate": {
            "value": unsupported_rate,
            "display": f"{unsupported_rate:.1%}" if unsupported_rate is not None else "N/A",
            "source": "results/pilot/metrics.json",
        },
        "pilot.rouge_auroc": {
            "value": primary_auroc,
            "display": f"{primary_auroc:.4f}" if primary_auroc is not None else "N/A",
            "source": "results/pilot/metrics.json",
        },
    }
    with open(metrics_path, "w") as f:
        json.dump(pilot_metrics, f, indent=2)

    # --- Write pilot report Markdown ---
    report_md_path = results_dir / "pilot_report.md"
    md_lines = [
        "# Pilot Report — Gate G1 Decision",
        "",
        f"Generated: {report['generated_at']}",
        "",
        "## Risk 1: Unsupported Ground-Truth Answers",
        "",
        f"- Rows checked: {total_checked} / {len(spotcheck_rows)}",
        f"- Unsupported count: {unsupported_count}",
        f"- Unsupported rate: {unsupported_rate:.1%}" if unsupported_rate is not None else "- Unsupported rate: N/A",
        f"- Threshold: < {gate_threshold_unsupported:.0%}",
        "",
        "## Risk 2: Lexical Overlap Shortcut (ROUGE-L AUROC)",
        "",
        f"- Dev pairs: {rouge_data.get('n_pairs')}",
        f"- Dev questions: {rouge_data.get('n_questions')}",
    ]
    for variant, auroc in auroc_all.items():
        primary_marker = " ← primary" if variant == rouge_data.get("primary_variant") else ""
        md_lines.append(f"- AUROC ({variant}): {auroc:.4f}{primary_marker}")
    md_lines.extend([
        f"- Threshold: < {gate_threshold_auroc}",
        "",
        "## Gate G1 Decision",
        "",
        f"**{gate_reason}**",
        "",
        "| Condition | Plan |",
        "| --- | --- |",
        "| Unsupported < 10% AND AUROC < 0.95 | Plan 1: Exp 1 main, Exp 2 = 100-pair validation |",
        "| Otherwise | Plan 2: Exp 2 main, grow to 200 pairs, Exp 1 secondary |",
        "",
        f"**Recommendation: Plan {recommended_plan}**" if recommended_plan else "**Cannot determine — complete annotations first.**",
        "",
        "---",
        "*This report is generated by code. Researchers make the final plan decision (Rule R1.5).*",
        "",
    ])

    with open(report_md_path, "w") as f:
        f.write("\n".join(md_lines))

    logger.info("Wrote pilot report JSON: %s", report_json_path)
    logger.info("Wrote pilot report MD: %s", report_md_path)

    print(f"\n{'=' * 60}")
    print("PILOT REPORT — GATE G1")
    print(f"{'=' * 60}")
    print(f"  Unsupported rate: {unsupported_rate:.1%}" if unsupported_rate is not None else "  Unsupported rate: N/A")
    print(f"  ROUGE-L AUROC:    {primary_auroc:.4f}" if primary_auroc is not None else "  ROUGE-L AUROC:    N/A")
    print(f"  → {gate_reason}")
    print(f"{'=' * 60}")
    print(f"  JSON: {report_json_path}")
    print(f"  Markdown: {report_md_path}")
    if unfilled > 0:
        print(f"\n  ⚠️  {unfilled} rows still unfilled — complete annotations first!")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

STEPS = {
    "fields": step_fields,
    "spotcheck": step_spotcheck,
    "rouge": step_rouge,
    "report": step_report,
}


def main() -> None:
    """CLI entry point for pilot checks."""
    parser = argparse.ArgumentParser(
        description="Phase 1 pilot checks for MedHallu dataset.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Steps:\n"
            "  fields     Load MedHallu, inspect columns, export sample rows\n"
            "  spotcheck  Sample 50 rows, export CSV for human annotation\n"
            "  rouge      Build provisional dev set, compute ROUGE-L AUROC\n"
            "  report     Read annotations + ROUGE results, apply Gate G1\n"
        ),
    )
    parser.add_argument("--config", default="configs/config.yaml", help="Path to config YAML")
    parser.add_argument("--step", required=True, choices=list(STEPS.keys()), help="Which step to run")
    args = parser.parse_args()

    cfg = load_config(args.config)
    setup_logging("pilot_checks")

    step_fn = STEPS[args.step]
    step_fn(cfg)


if __name__ == "__main__":
    main()
