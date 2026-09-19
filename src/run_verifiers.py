"""Run all verifiers on a given split and save predictions.

Phase 3, 5, 7 (Phase.md). Design.md §4.
Entry point:
    python -m src.run_verifiers --config configs/config.yaml --split <dev|test|rag>
"""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
from typing import Literal

from tqdm import tqdm

from src.common.config import Config, load_config
from src.common.io import Pair, VerifierResult, read_jsonl, write_jsonl
from src.common.logging_utils import setup_logging
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


def get_output_dir(split: str, cfg: Config) -> Path:
    """Determine output directory for verifier predictions."""
    results_dir = Path(cfg.paths.results)
    if split == "dev":
        out_dir = results_dir / "dev_tuning"
    elif split == "test":
        out_dir = results_dir / "exp1"
    elif split == "rag":
        out_dir = results_dir / "exp2"
    else:
        out_dir = results_dir / split

    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir


def load_thresholds(cfg: Config) -> dict[str, float]:
    """Load frozen thresholds if available."""
    thresh_file = Path(cfg.paths.results) / "thresholds.json"
    if not thresh_file.exists():
        return {}

    with open(thresh_file) as f:
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

    out_dir = get_output_dir(args.split, cfg)
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

    print("=" * 60)
    print(f"RUNNING VERIFIERS: split={args.split} ({len(pairs)} pairs)")
    print(f"Output directory: {out_dir}")
    print("=" * 60)

    for v in verifiers_to_run:
        thresh = thresholds.get(v.name)
        results = run_verifier(v, pairs, split=args.split, threshold=thresh)

        out_file = out_dir / f"{v.name}_{args.split}_results.jsonl"
        write_jsonl(out_file, results)
        print(f"Saved {len(results)} results for {v.name} -> {out_file}")

    print("=" * 60)
    print("VERIFICATION COMPLETED")
    print("=" * 60)


if __name__ == "__main__":
    main()
