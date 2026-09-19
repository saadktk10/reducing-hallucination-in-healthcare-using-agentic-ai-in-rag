"""Tune Filter B and ROUGE-L thresholds on Exp 1 dev split only.

Phase 3d (Phase.md). Design.md §6.4. Writes results/thresholds.json.
Rule R1.2: MUST tune Filter B and ROUGE-L thresholds on Exp 1 dev only, by maximum F1 with Hallucinated as positive.
Rule R1.3: NEVER retune thresholds for Exp 2. Apply the Exp 1 dev thresholds unchanged.
"""

from __future__ import annotations

import argparse
import json
import logging
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from src.common.config import Config, load_config
from src.common.io import Pair, VerifierResult, read_jsonl
from src.common.logging_utils import setup_logging
from src.evaluation.metrics import f1, fnr, precision, recall

logger = logging.getLogger(__name__)


def find_optimal_threshold(
    y_true: Sequence[int],
    scores: Sequence[float],
) -> dict[str, float]:
    """Sweep candidate thresholds to find the one maximizing F1 (Hallucinated=1).

    Support scores: higher means more supported.
    Decision rule: predicted_label = 1 (Hallucinated) if score < threshold else 0 (Supported).
    Ties broken by lower FNR (False Negative Rate) per Design.md §6.4.

    Args:
        y_true: Ground truth binary labels (0=Supported, 1=Hallucinated).
        scores: Continuous verifier support scores.

    Returns:
        Dict with optimal threshold, dev_f1, dev_precision, dev_recall, dev_fnr.
    """
    if not scores or not y_true:
        raise ValueError("Cannot tune threshold on empty data")

    unique_scores = sorted(set(scores))
    # Candidates include boundaries and midpoints
    candidates = [0.0]
    for i in range(len(unique_scores) - 1):
        candidates.append(unique_scores[i])
        candidates.append((unique_scores[i] + unique_scores[i + 1]) / 2.0)
    candidates.append(unique_scores[-1])
    candidates.append(1.0)
    candidates = sorted(set(candidates))

    best_thresh = candidates[0]
    best_f1 = -1.0
    best_fnr = 2.0
    best_p = 0.0
    best_r = 0.0

    for t in candidates:
        y_pred = [1 if s < t else 0 for s in scores]
        curr_f1 = f1(y_true, y_pred)
        curr_fnr = fnr(y_true, y_pred)

        # Maximize F1, tie-break on lower FNR
        if (curr_f1 > best_f1) or (abs(curr_f1 - best_f1) < 1e-7 and curr_fnr < best_fnr):
            best_f1 = curr_f1
            best_fnr = curr_fnr
            best_thresh = t
            best_p = precision(y_true, y_pred)
            best_r = recall(y_true, y_pred)

    return {
        "threshold": float(best_thresh),
        "dev_f1": float(best_f1),
        "dev_precision": float(best_p),
        "dev_recall": float(best_r),
        "dev_fnr": float(best_fnr),
    }


def tune_dev_thresholds(
    dev_pairs: list[Pair],
    filter_b_results: list[VerifierResult],
    rouge_results: list[VerifierResult],
    cfg: Config,
    output_path: Path | str = "results/thresholds.json",
) -> dict[str, Any]:
    """Tune thresholds on dev split results and write results/thresholds.json."""
    pair_labels = {p.pair_id: p.label for p in dev_pairs}

    # Filter B
    fb_true = [pair_labels[r.pair_id] for r in filter_b_results if r.score is not None]
    fb_scores = [r.score for r in filter_b_results if r.score is not None]
    fb_opt = find_optimal_threshold(fb_true, fb_scores)
    logger.info(
        "Filter B optimal dev threshold: %.4f (F1=%.4f, P=%.4f, R=%.4f)",
        fb_opt["threshold"],
        fb_opt["dev_f1"],
        fb_opt["dev_precision"],
        fb_opt["dev_recall"],
    )

    # ROUGE-L
    rouge_true = [pair_labels[r.pair_id] for r in rouge_results if r.score is not None]
    rouge_scores = [r.score for r in rouge_results if r.score is not None]
    rouge_opt = find_optimal_threshold(rouge_true, rouge_scores)
    logger.info(
        "ROUGE-L optimal dev threshold: %.4f (F1=%.4f, P=%.4f, R=%.4f)",
        rouge_opt["threshold"],
        rouge_opt["dev_f1"],
        rouge_opt["dev_precision"],
        rouge_opt["dev_recall"],
    )

    thresholds_data: dict[str, Any] = {
        "filter_b": {
            "threshold": fb_opt["threshold"],
            "dev_f1": fb_opt["dev_f1"],
            "dev_precision": fb_opt["dev_precision"],
            "dev_recall": fb_opt["dev_recall"],
            "dev_fnr": fb_opt["dev_fnr"],
            "model_id": cfg.models.nli_main,
            "tuned_on": "exp1_dev",
            "date": datetime.now(UTC).strftime("%Y-%m-%d"),
        },
        "rouge": {
            "threshold": rouge_opt["threshold"],
            "variant": cfg.baseline.rouge_field,
            "dev_f1": rouge_opt["dev_f1"],
            "dev_precision": rouge_opt["dev_precision"],
            "dev_recall": rouge_opt["dev_recall"],
            "dev_fnr": rouge_opt["dev_fnr"],
            "tuned_on": "exp1_dev",
            "date": datetime.now(UTC).strftime("%Y-%m-%d"),
        },
    }

    out_file = Path(output_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)
    with open(out_file, "w") as f:
        json.dump(thresholds_data, f, indent=2)

    logger.info("Wrote frozen thresholds to %s", out_file)
    return thresholds_data


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Tune Filter B and ROUGE-L thresholds on Exp 1 dev split."
    )
    parser.add_argument("--config", default="configs/config.yaml", help="Path to config YAML")
    parser.add_argument(
        "--output", default="results/thresholds.json", help="Output path for thresholds JSON"
    )
    args = parser.parse_args()

    cfg = load_config(args.config)
    setup_logging("tune_thresholds")

    dev_path = Path(cfg.paths.data) / "exp1_medhallu" / "dev.jsonl"
    dev_pairs = read_jsonl(dev_path, Pair)

    results_dir = Path(cfg.paths.results) / "dev_tuning"
    fb_file = results_dir / "filter_b_dev_results.jsonl"
    rouge_file = results_dir / "rouge_dev_results.jsonl"

    if not fb_file.exists() or not rouge_file.exists():
        raise FileNotFoundError(
            f"Dev verifier results not found in {results_dir}. "
            f"Run 'python -m src.run_verifiers --config configs/config.yaml --split dev' first."
        )

    fb_results = read_jsonl(fb_file, VerifierResult)
    rouge_results = read_jsonl(rouge_file, VerifierResult)

    summary = tune_dev_thresholds(
        dev_pairs, fb_results, rouge_results, cfg, output_path=args.output
    )

    print("\n" + "=" * 60)
    print("THRESHOLD TUNING COMPLETE (Phase 3d)")
    print("=" * 60)
    print(f"Filter B: threshold = {summary['filter_b']['threshold']:.4f} (dev F1 = {summary['filter_b']['dev_f1']:.4f})")
    print(f"ROUGE-L:  threshold = {summary['rouge']['threshold']:.4f} (dev F1 = {summary['rouge']['dev_f1']:.4f})")
    print(f"Written to: {args.output}")
    print("=" * 60)


if __name__ == "__main__":
    main()
