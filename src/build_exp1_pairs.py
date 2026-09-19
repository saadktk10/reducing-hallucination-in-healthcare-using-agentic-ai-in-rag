"""Build Experiment 1 pairs and splits from MedHallu.

Phase 2 (Phase.md). Entry point:
    python -m src.build_exp1_pairs --config configs/config.yaml

Produces:
    - data/exp1_medhallu/dev.jsonl (100 pairs, 50 questions)
    - data/exp1_medhallu/test.jsonl (400 pairs, 200 questions)
    - data/exp1_medhallu/split_summary.json (counts per split, difficulty, category)
"""

from __future__ import annotations

import argparse
import json
import logging
import random
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from datasets import load_dataset

from src.common.config import Config, load_config
from src.common.io import Pair, write_jsonl
from src.common.logging_utils import setup_logging

logger = logging.getLogger(__name__)


def load_medhallu(cfg: Config) -> Any:
    """Load MedHallu dataset from HuggingFace at pinned revision.

    Args:
        cfg: System configuration object.

    Returns:
        HuggingFace Dataset object.
    """
    ds_cfg = cfg.datasets.medhallu
    revision = None if ds_cfg.revision == "TBD" else ds_cfg.revision
    if revision is None:
        logger.warning(
            "MedHallu revision is TBD — loading at HEAD. "
            "Pin the revision in config.yaml (Rule R4.4)."
        )
    else:
        logger.info("Loading MedHallu at pinned revision: %s", revision)

    ds = load_dataset(ds_cfg.hf_id, ds_cfg.config, revision=revision)
    if hasattr(ds, "keys"):
        split_name = list(ds.keys())[0]
        logger.info("Using split %r from DatasetDict (available: %s)", split_name, list(ds.keys()))
        ds = ds[split_name]
    return ds


def extract_context(val: Any) -> str:
    """Extract and normalize context string from dataset Knowledge field.

    MedHallu stores Knowledge as a list of abstract sentence strings or a single string.
    Joins list elements with a single space.
    """
    if isinstance(val, list):
        return " ".join(val)
    return str(val)


def sample_and_split_questions(
    ds: Any,
    cfg: Config,
) -> tuple[list[int], list[int]]:
    """Perform deterministic stratified sampling and question-level splitting.

    1. Seeded shuffle of all row indices.
    2. Proportional stratified sampling across difficulty levels to get n_questions.
    3. Seeded shuffle of sampled questions.
    4. First dev_questions assigned to dev split, remaining to test split.

    Args:
        ds: The MedHallu dataset.
        cfg: System configuration object.

    Returns:
        Tuple of (dev_question_row_indices, test_question_row_indices).
    """
    cols = cfg.datasets.medhallu.columns
    if cols is None:
        raise ValueError("Column mapping required in config.datasets.medhallu.columns")

    rng = random.Random(cfg.seed)
    rows = list(range(len(ds)))
    rng.shuffle(rows)

    n_questions = cfg.exp1.n_questions
    dev_questions = cfg.exp1.dev_questions
    test_questions = cfg.exp1.test_questions

    if n_questions != (dev_questions + test_questions):
        raise ValueError(
            f"Config inconsistency: n_questions ({n_questions}) != "
            f"dev_questions ({dev_questions}) + test_questions ({test_questions})"
        )

    # Group row indices by difficulty stratum
    difficulty_groups: dict[str, list[int]] = {}
    for idx in rows:
        diff = str(ds[idx][cols.difficulty]) if cols.difficulty in ds.column_names else "unknown"
        difficulty_groups.setdefault(diff, []).append(idx)

    # Proportional stratified sampling
    total_available = len(rows)
    sampled_indices: list[int] = []
    for diff, indices in sorted(difficulty_groups.items()):
        proportion = len(indices) / total_available
        n_stratum = max(1, round(proportion * n_questions))
        n_stratum = min(n_stratum, len(indices))
        sampled_indices.extend(indices[:n_stratum])
        logger.info(
            "Difficulty stratum %r: %d available, sampling %d (%.1f%%)",
            diff,
            len(indices),
            n_stratum,
            proportion * 100,
        )

    # Adjust to exactly n_questions if rounding differed
    if len(sampled_indices) > n_questions:
        sampled_indices = sampled_indices[:n_questions]
    elif len(sampled_indices) < n_questions:
        needed = n_questions - len(sampled_indices)
        remaining = [i for i in rows if i not in set(sampled_indices)]
        sampled_indices.extend(remaining[:needed])

    logger.info("Total sampled questions: %d", len(sampled_indices))

    # Deterministic question-level split
    rng2 = random.Random(cfg.seed)
    rng2.shuffle(sampled_indices)

    dev_indices = sampled_indices[:dev_questions]
    test_indices = sampled_indices[dev_questions:]

    # Assert disjointness
    dev_set = set(dev_indices)
    test_set = set(test_indices)
    overlap = dev_set.intersection(test_set)
    if overlap:
        raise ValueError(f"Data leakage detected! Overlap between dev and test indices: {overlap}")

    logger.info(
        "Split %d questions into dev (%d questions) and test (%d questions) [zero overlap]",
        len(sampled_indices),
        len(dev_indices),
        len(test_indices),
    )

    return dev_indices, test_indices


def build_pairs(
    ds: Any,
    indices: list[int],
    split: Literal["dev", "test"],
    cfg: Config,
    start_qid_idx: int = 0,
) -> list[Pair]:
    """Build validated Pair objects for a list of question indices.

    For each question index, builds exactly two pairs:
      1. Ground truth pair (label=0, Supported)
      2. Hallucinated pair (label=1, Hallucinated)

    Args:
        ds: MedHallu dataset.
        indices: Dataset row indices for this split.
        split: "dev" or "test".
        cfg: Configuration object.
        start_qid_idx: Starting index for question ID formatting (e.g. 0 -> q000).

    Returns:
        List of validated Pair objects.
    """
    cols = cfg.datasets.medhallu.columns
    if cols is None:
        raise ValueError("Column mapping required in config.datasets.medhallu.columns")

    pairs: list[Pair] = []
    for offset, idx in enumerate(indices):
        row = ds[idx]
        qid_num = start_qid_idx + offset
        qid = f"q{qid_num:03d}"

        question_text = str(row[cols.question])
        context_text = extract_context(row[cols.context])
        gt_answer = str(row[cols.ground_truth])
        hal_answer = str(row[cols.hallucinated])
        diff = str(row[cols.difficulty]) if cols.difficulty in ds.column_names else None
        cat = str(row[cols.category]) if cols.category in ds.column_names else None

        # Ground truth pair (label=0, Supported)
        gt_pair = Pair(
            pair_id=f"e1-{qid}-gt",
            question_id=qid,
            experiment="exp1",
            split=split,
            question=question_text,
            context=context_text,
            answer=gt_answer,
            label=0,
            difficulty=diff,
            category=cat,
            condition=None,
            source_doc_id=None,
        )
        pairs.append(gt_pair)

        # Hallucinated pair (label=1, Hallucinated)
        hal_pair = Pair(
            pair_id=f"e1-{qid}-hal",
            question_id=qid,
            experiment="exp1",
            split=split,
            question=question_text,
            context=context_text,
            answer=hal_answer,
            label=1,
            difficulty=diff,
            category=cat,
            condition=None,
            source_doc_id=None,
        )
        pairs.append(hal_pair)

    logger.info("Built %d pairs (%d questions) for split %s", len(pairs), len(indices), split)
    return pairs


def generate_split_summary(
    dev_pairs: list[Pair],
    test_pairs: list[Pair],
    cfg: Config,
) -> dict[str, Any]:
    """Compute summary statistics for Experiment 1 splits.

    Args:
        dev_pairs: All pairs in the dev split.
        test_pairs: All pairs in the test split.
        cfg: Configuration object.

    Returns:
        Dictionary with full split counts and distributions.
    """
    dev_qids = {p.question_id for p in dev_pairs}
    test_qids = {p.question_id for p in test_pairs}

    dev_diff_pairs = Counter(p.difficulty for p in dev_pairs)
    test_diff_pairs = Counter(p.difficulty for p in test_pairs)

    # Unique question difficulty distribution
    dev_q_diff = {p.question_id: p.difficulty for p in dev_pairs}
    test_q_diff = {p.question_id: p.difficulty for p in test_pairs}
    dev_diff_questions = Counter(dev_q_diff.values())
    test_diff_questions = Counter(test_q_diff.values())

    # Category distribution
    dev_cat_pairs = Counter(p.category for p in dev_pairs if p.category is not None)
    test_cat_pairs = Counter(p.category for p in test_pairs if p.category is not None)

    dev_q_cat = {p.question_id: p.category for p in dev_pairs if p.category is not None}
    test_q_cat = {p.question_id: p.category for p in test_pairs if p.category is not None}
    dev_cat_questions = Counter(dev_q_cat.values())
    test_cat_questions = Counter(test_q_cat.values())

    all_q_diff = {**dev_q_diff, **test_q_diff}
    all_diff_questions = Counter(all_q_diff.values())

    all_q_cat = {**dev_q_cat, **test_q_cat}
    all_cat_questions = Counter(all_q_cat.values())

    summary: dict[str, Any] = {
        "experiment": "exp1",
        "dataset": cfg.datasets.medhallu.hf_id,
        "revision": cfg.datasets.medhallu.revision,
        "seed": cfg.seed,
        "total_questions": len(dev_qids) + len(test_qids),
        "total_pairs": len(dev_pairs) + len(test_pairs),
        "splits": {
            "dev": {
                "n_questions": len(dev_qids),
                "n_pairs": len(dev_pairs),
                "labels": dict(Counter(p.label for p in dev_pairs)),
                "difficulty_counts_pairs": dict(sorted(dev_diff_pairs.items())),
                "difficulty_counts_questions": dict(sorted(dev_diff_questions.items())),
                "category_counts_pairs": dict(sorted(dev_cat_pairs.items())),
                "category_counts_questions": dict(sorted(dev_cat_questions.items())),
            },
            "test": {
                "n_questions": len(test_qids),
                "n_pairs": len(test_pairs),
                "labels": dict(Counter(p.label for p in test_pairs)),
                "difficulty_counts_pairs": dict(sorted(test_diff_pairs.items())),
                "difficulty_counts_questions": dict(sorted(test_diff_questions.items())),
                "category_counts_pairs": dict(sorted(test_cat_pairs.items())),
                "category_counts_questions": dict(sorted(test_cat_questions.items())),
            },
        },
        "overall": {
            "difficulty_counts_questions": dict(sorted(all_diff_questions.items())),
            "category_counts_questions": dict(sorted(all_cat_questions.items())),
        },
        "created_at": datetime.now(UTC).isoformat(),
    }
    return summary


def build_exp1_dataset(
    cfg: Config,
    output_dir: Path | str | None = None,
) -> dict[str, Any]:
    """Execute the end-to-end Experiment 1 pair building pipeline.

    Loads MedHallu, performs stratified sampling & split, builds dev & test JSONL,
    and writes split_summary.json.

    Args:
        cfg: System configuration object.
        output_dir: Optional custom output directory. Defaults to data/exp1_medhallu.

    Returns:
        The split summary dictionary.
    """
    logger.info("Starting Experiment 1 pair generation...")
    ds = load_medhallu(cfg)

    dev_indices, test_indices = sample_and_split_questions(ds, cfg)

    # Build dev pairs (start_qid_idx=0 -> q000..q049)
    dev_pairs = build_pairs(ds, dev_indices, split="dev", cfg=cfg, start_qid_idx=0)

    # Build test pairs (start_qid_idx=len(dev_indices) -> q050..q249)
    test_pairs = build_pairs(
        ds, test_indices, split="test", cfg=cfg, start_qid_idx=len(dev_indices)
    )

    out_path = Path(output_dir) if output_dir else Path(cfg.paths.data) / "exp1_medhallu"
    out_path.mkdir(parents=True, exist_ok=True)

    dev_file = out_path / "dev.jsonl"
    test_file = out_path / "test.jsonl"
    summary_file = out_path / "split_summary.json"

    # Write validated JSONL files
    write_jsonl(dev_file, dev_pairs)
    write_jsonl(test_file, test_pairs)

    # Generate and write summary
    summary = generate_split_summary(dev_pairs, test_pairs, cfg)
    with open(summary_file, "w") as f:
        json.dump(summary, f, indent=2, default=str)

    logger.info("Wrote dev pairs: %s (%d pairs)", dev_file, len(dev_pairs))
    logger.info("Wrote test pairs: %s (%d pairs)", test_file, len(test_pairs))
    logger.info("Wrote split summary: %s", summary_file)

    return summary


def main() -> None:
    """CLI entry point for building Experiment 1 pairs."""
    parser = argparse.ArgumentParser(
        description="Build Experiment 1 pairs and dev/test splits from MedHallu (Phase 2).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--config", default="configs/config.yaml", help="Path to config YAML")
    parser.add_argument("--output-dir", default=None, help="Custom output directory for data files")
    args = parser.parse_args()

    cfg = load_config(args.config)
    setup_logging("build_exp1_pairs")

    summary = build_exp1_dataset(cfg, output_dir=args.output_dir)

    print("\n" + "=" * 60)
    print("EXPERIMENT 1 PAIRS & SPLITS COMPLETE (Phase 2)")
    print("=" * 60)
    print(f"Dataset revision: {summary['revision']}")
    print(f"Total questions:  {summary['total_questions']}")
    print(f"Total pairs:      {summary['total_pairs']}")
    print(
        f"Dev split:        {summary['splits']['dev']['n_pairs']} pairs "
        f"({summary['splits']['dev']['n_questions']} questions, labels={summary['splits']['dev']['labels']})"
    )
    print(
        f"Test split:       {summary['splits']['test']['n_pairs']} pairs "
        f"({summary['splits']['test']['n_questions']} questions, labels={summary['splits']['test']['labels']})"
    )
    print("=" * 60)


if __name__ == "__main__":
    main()
