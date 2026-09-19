"""Run all verifiers on a given split and save predictions.

Phase 3, 5, 7 (Phase.md). Design.md §4.
Entry point:
    python -m src.run_verifiers --config configs/config.yaml --split <dev|test|rag> [--verifier <all|rouge|filter_b|filter_a>] [--run-id <id>] [--limit N]
"""

from __future__ import annotations

import argparse
import json
import logging
import math
from pathlib import Path
from typing import Any, Literal

from tqdm import tqdm

from src.common.config import Config, load_config, load_pricing
from src.common.io import Pair, VerifierResult, read_jsonl, write_jsonl
from src.common.logging_utils import setup_logging
from src.common.manifest import generate_run_id, write_manifest
from src.common.prompts import compute_hash, load_prompt
from src.evaluation.metrics import auroc, f1, fnr, fpr, precision, recall, shadow_cost_per_1k
from src.filters.base import Verifier
from src.filters.baseline_rouge import RougeLVerifier
from src.filters.filter_api import APIJudgeVerifier
from src.filters.filter_nli import NLIVerifier

logger = logging.getLogger(__name__)


def load_split_pairs(split: str, cfg: Config) -> tuple[list[Pair], Path]:
    """Load pairs for the requested split."""
    data_dir = Path(cfg.paths.data)
    if split == "dev":
        path = data_dir / "exp1_medhallu" / "dev.jsonl"
    elif split == "test":
        path = data_dir / "exp1_medhallu" / "test.jsonl"
    elif split == "rag":
        path = data_dir / "exp2_rag" / "pairs.jsonl"
    else:
        raise ValueError(f"Unknown split: {split}. Must be 'dev', 'test', or 'rag'")

    if not path.exists():
        raise FileNotFoundError(f"Split file does not exist: {path}")

    pairs = read_jsonl(path, Pair)
    logger.info("Loaded %d pairs from %s", len(pairs), path)
    return pairs, path


def resolve_run_dir(split: str, cfg: Config, explicit_run_id: str | None = None) -> tuple[Path, str]:
    """Determine output directory and run_id for verifier predictions (Rules R4.5, R4.3)."""
    results_dir = Path(cfg.paths.results)
    latest_pointer = results_dir / "LATEST.json"

    if split == "dev":
        out_dir = results_dir / "dev_tuning"
        out_dir.mkdir(parents=True, exist_ok=True)
        return out_dir, "dev_tuning"

    exp_key = "exp1" if split == "test" else "exp2"

    if explicit_run_id:
        run_id = explicit_run_id
    else:
        # Check if an active run_id exists in LATEST.json
        run_id = None
        if latest_pointer.exists():
            try:
                with open(latest_pointer, encoding="utf-8") as f:
                    latest_data = json.load(f)
                run_id = latest_data.get(exp_key)
            except Exception as e:
                logger.warning("Failed to read %s: %s", latest_pointer, e)

        if not run_id:
            run_id = generate_run_id()

    out_dir = results_dir / exp_key / run_id
    out_dir.mkdir(parents=True, exist_ok=True)

    # Update LATEST.json
    latest_data = {}
    if latest_pointer.exists():
        try:
            with open(latest_pointer, encoding="utf-8") as f:
                latest_data = json.load(f)
        except Exception:
            pass
    latest_data[exp_key] = run_id
    with open(latest_pointer, "w", encoding="utf-8") as f:
        json.dump(latest_data, f, indent=2)

    logger.info("Output directory for %s: %s (run_id: %s)", split, out_dir, run_id)
    return out_dir, run_id


def load_thresholds(cfg: Config) -> dict[str, float]:
    """Load frozen thresholds if available."""
    thresh_file = Path(cfg.paths.results) / "thresholds.json"
    if not thresh_file.exists():
        return {}

    with open(thresh_file, encoding="utf-8") as f:
        data = json.load(f)

    thresholds: dict[str, float] = {}
    if "filter_b" in data and "threshold" in data["filter_b"]:
        thresholds["filter_b"] = float(data["filter_b"]["threshold"])
    if "rouge" in data and "threshold" in data["rouge"]:
        thresholds["rouge"] = float(data["rouge"]["threshold"])

    return thresholds


def run_verifier(
    verifier: Verifier,
    pairs: list[Pair],
    split: str,
    threshold: float | None = None,
    mode: Literal["normal", "timing"] = "normal",
) -> list[VerifierResult]:
    """Run a verifier over pairs and return results."""
    logger.info("Starting run for verifier: %s on split: %s (%d pairs)", verifier.name, split, len(pairs))
    load_time = verifier.load()
    logger.info("Verifier %s load time: %.3f s", verifier.name, load_time)

    results: list[VerifierResult] = []
    for p in tqdm(pairs, desc=f"Scoring with {verifier.name}"):
        res = verifier.score(context=p.context, answer=p.answer, pair_id=p.pair_id)

        # Apply threshold for continuous verifiers if threshold provided
        if threshold is not None and res.score is not None:
            # Score below threshold -> Hallucinated (1)
            res.verdict = 1 if res.score < threshold else 0

        results.append(res)

    return results


def compute_verifier_metrics(
    pairs: list[Pair],
    results: list[VerifierResult],
    verifier_name: str,
) -> dict[str, Any]:
    """Compute classification metrics for a single verifier's results."""
    pair_dict = {p.pair_id: p for p in pairs}
    y_true: list[int] = []
    y_pred: list[int] = []
    scores: list[float] = []
    parse_failures = 0

    for r in results:
        p = pair_dict.get(r.pair_id)
        if p is None or p.label is None:
            continue
        if r.parse_failure or r.verdict is None:
            parse_failures += 1
            continue

        y_true.append(int(p.label))
        y_pred.append(int(r.verdict))
        if r.score is not None:
            scores.append(float(r.score))

    n_evaluated = len(y_true)
    if n_evaluated == 0:
        return {"n": 0, "parse_failures": parse_failures}

    prec = precision(y_true, y_pred)
    rec = recall(y_true, y_pred)
    f1_val = f1(y_true, y_pred)
    fnr_val = fnr(y_true, y_pred)
    fpr_val = fpr(y_true, y_pred)

    auroc_val = float("nan")
    if len(scores) == n_evaluated and len(set(y_true)) > 1:
        try:
            auroc_val = auroc(y_true, scores)
        except Exception:
            pass

    return {
        "n": n_evaluated,
        "parse_failures": parse_failures,
        "precision": round(prec, 4),
        "recall": round(rec, 4),
        "f1": round(f1_val, 4),
        "fnr": round(fnr_val, 4),
        "fpr": round(fpr_val, 4),
        "auroc": round(auroc_val, 4) if not math.isnan(auroc_val) else None,
    }


def update_metrics_file(
    out_dir: Path,
    verifier_name: str,
    metrics: dict[str, Any],
    results: list[VerifierResult],
    cfg: Config,
) -> None:
    """Update metrics.json in the results directory."""
    metrics_path = out_dir / "metrics.json"
    data: dict[str, Any] = {}
    if metrics_path.exists():
        try:
            with open(metrics_path, encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            pass

    if "accuracy" not in data:
        data["accuracy"] = {}
    data["accuracy"][verifier_name] = metrics

    # If filter_a, compute shadow cost if pricing available
    if verifier_name == "filter_a":
        try:
            pricing = load_pricing()
            in_tokens = [r.input_tokens for r in results if r.input_tokens is not None]
            out_tokens = [r.output_tokens for r in results if r.output_tokens is not None]
            if in_tokens and out_tokens and pricing.judge.input_per_million_usd and pricing.judge.output_per_million_usd:
                avg_in = sum(in_tokens) / len(in_tokens)
                avg_out = sum(out_tokens) / len(out_tokens)
                cost_1k = shadow_cost_per_1k(
                    avg_input_tokens=avg_in,
                    avg_output_tokens=avg_out,
                    price_per_1m_input=pricing.judge.input_per_million_usd,
                    price_per_1m_output=pricing.judge.output_per_million_usd,
                )
                data["cost.filter_a.per_1k_usd"] = {
                    "value": round(cost_1k, 4),
                    "display": f"${cost_1k:.4f}",
                    "source": str(metrics_path.as_posix()),
                    "checked_on": pricing.judge.checked_on,
                }
                logger.info("Computed shadow cost for Filter A: $%.4f per 1k calls", cost_1k)
        except Exception as e:
            logger.warning("Could not compute shadow cost: %s", e)

    with open(metrics_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    logger.info("Updated %s with metrics for %s", metrics_path, verifier_name)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run verifiers on a split.")
    parser.add_argument("--config", default="configs/config.yaml", help="Path to config YAML")
    parser.add_argument(
        "--split",
        required=True,
        choices=["dev", "test", "rag"],
        help="Split to run verifiers on: dev, test, or rag",
    )
    parser.add_argument(
        "--verifier",
        default="all",
        choices=["all", "rouge", "filter_b", "filter_a"],
        help="Which verifier to run (default: all)",
    )
    parser.add_argument(
        "--run-id",
        default=None,
        help="Explicit run ID (e.g. to append results into an existing run folder)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional limit on number of pairs to evaluate",
    )
    args = parser.parse_args()

    cfg = load_config(args.config)
    setup_logging(f"run_verifiers_{args.split}")

    pairs, split_path = load_split_pairs(args.split, cfg)
    if args.limit is not None and args.limit > 0:
        pairs = pairs[: args.limit]
        logger.info("Limited evaluation to first %d pairs", len(pairs))

    out_dir, run_id = resolve_run_dir(args.split, cfg, args.run_id)
    thresholds = load_thresholds(cfg)

    verifiers_to_run: list[Verifier] = []
    if args.verifier in ("all", "rouge"):
        verifiers_to_run.append(RougeLVerifier(field=cfg.baseline.rouge_field))
    if args.verifier in ("all", "filter_b"):
        verifiers_to_run.append(
            NLIVerifier(
                model_id=cfg.models.nli_main,
                num_threads=cfg.filter_b.num_threads,
                batch_size=cfg.filter_b.batch_size,
                max_length=cfg.filter_b.max_length,
            )
        )
    if args.verifier in ("all", "filter_a"):
        verifiers_to_run.append(APIJudgeVerifier(cfg=cfg))

    print("=" * 65)
    print(f"RUNNING VERIFIERS: split={args.split} ({len(pairs)} pairs)")
    print(f"Run ID: {run_id}")
    print(f"Output directory: {out_dir}")
    print("=" * 65)

    prompt_hash = ""
    try:
        judge_prompt = load_prompt("judge_v1.txt", base=cfg.paths.prompts)
        prompt_hash = compute_hash(judge_prompt)
    except Exception:
        pass

    for v in verifiers_to_run:
        thresh = thresholds.get(v.name)
        results = run_verifier(v, pairs, split=args.split, threshold=thresh)

        # Standard filenames per Phase.md 5a and backwards compatible filenames
        out_file = out_dir / f"predictions_{v.name}.jsonl"
        write_jsonl(out_file, results)
        if v.name == "rouge":
            write_jsonl(out_dir / "predictions_baseline_rouge.jsonl", results)

        legacy_out = out_dir / f"{v.name}_{args.split}_results.jsonl"
        write_jsonl(legacy_out, results)
        print(f"Saved {len(results)} predictions for {v.name} -> {out_file}")

        # Compute classification metrics if ground-truth labels exist
        metrics = compute_verifier_metrics(pairs, results, v.name)
        update_metrics_file(out_dir, v.name, metrics, results, cfg)

        print(f"--- Metrics for {v.name.upper()} (n={metrics.get('n')}) ---")
        for k, val in metrics.items():
            if k != "n":
                print(f"    {k}: {val}")

    # Write run manifest (Rule R4.3)
    write_manifest(
        run_dir=out_dir,
        config_snapshot=cfg.model_dump(),
        prompt_hashes={"judge_v1.txt": prompt_hash} if prompt_hash else {},
        model_ids={
            "baseline": "rougeL",
            "filter_b": cfg.models.nli_main,
            "filter_a": cfg.models.judge.model_id,
        },
        dataset_revision=cfg.datasets.medhallu.revision,
        extra={
            "split": args.split,
            "n_pairs": len(pairs),
            "thresholds": thresholds,
        },
    )

    print("\n" + "=" * 65)
    print("VERIFICATION COMPLETED SUCCESSFULLY")
    print(f"Run directory: {out_dir}")
    print("=" * 65)


if __name__ == "__main__":
    main()
