"""Tests for Phase 8 evaluation module (src/evaluate.py)."""

from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from src.common.config import Config
from src.common.io import Pair, VerifierResult, write_jsonl
from src.evaluate import (
    compute_f1_bootstrap_ci_exp1,
    compute_f1_bootstrap_ci_exp2,
    evaluate_experiment,
    find_prediction_files,
    resolve_run_dir,
)


@pytest.fixture
def dummy_env(tmp_path: Path) -> tuple[Config, Path, Path]:
    """Create a minimal mock environment for testing evaluation."""
    data_dir = tmp_path / "data"
    results_dir = tmp_path / "results"
    exp1_data = data_dir / "exp1_medhallu"
    exp1_data.mkdir(parents=True)

    # 4 questions, 8 pairs
    pairs: list[Pair] = []
    for q_idx in range(4):
        qid = f"q{q_idx:03d}"
        diff = "easy" if q_idx % 2 == 0 else "hard"
        cat = "category_A" if q_idx < 2 else "category_B"
        # ground truth pair
        pairs.append(
            Pair(
                pair_id=f"e1-{qid}-gt",
                question_id=qid,
                experiment="exp1",
                split="test",
                question=f"Question {qid}",
                context="Context text",
                answer="Supported answer",
                label=0,
                difficulty=diff,
                category=cat,
            )
        )
        # hallucinated pair
        pairs.append(
            Pair(
                pair_id=f"e1-{qid}-hal",
                question_id=qid,
                experiment="exp1",
                split="test",
                question=f"Question {qid}",
                context="Context text",
                answer="Hallucinated answer",
                label=1,
                difficulty=diff,
                category=cat,
            )
        )

    test_jsonl = exp1_data / "test.jsonl"
    write_jsonl(test_jsonl, pairs)

    # Run directory
    run_id = "20260920-0000-testrun"
    run_dir = results_dir / "exp1" / run_id
    run_dir.mkdir(parents=True)

    # Verifier 1 (filter_b): predicts all 1
    v1_results = [
        VerifierResult(
            pair_id=p.pair_id,
            verifier="filter_b",
            score=0.1,
            verdict=1,
            confidence=0.1,
        )
        for p in pairs
    ]
    write_jsonl(run_dir / "predictions_filter_b.jsonl", v1_results)

    # Verifier 2 (rouge): predicts correctly on all
    v2_results = [
        VerifierResult(
            pair_id=p.pair_id,
            verifier="rouge",
            score=0.8 if p.label == 0 else 0.2,
            verdict=p.label,
            confidence=0.8,
        )
        for p in pairs
    ]
    write_jsonl(run_dir / "predictions_rouge.jsonl", v2_results)

    # LATEST.json
    latest_file = results_dir / "LATEST.json"
    with open(latest_file, "w", encoding="utf-8") as f:
        json.dump({"exp1": run_id}, f)

    # Load base config and override paths
    from src.common.config import load_config
    cfg = load_config("configs/config.yaml")
    cfg.paths.data = str(data_dir)
    cfg.paths.results = str(results_dir)

    return cfg, run_dir, test_jsonl


def test_resolve_run_dir(dummy_env: tuple[Config, Path, Path]) -> None:
    cfg, expected_run_dir, _ = dummy_env
    resolved_dir, run_id = resolve_run_dir("exp1", cfg)
    assert resolved_dir == expected_run_dir
    assert run_id == "20260920-0000-testrun"


def test_find_prediction_files(dummy_env: tuple[Config, Path, Path]) -> None:
    _, run_dir, _ = dummy_env
    pfiles = find_prediction_files(run_dir)
    assert "filter_b" in pfiles
    assert "rouge" in pfiles
    assert pfiles["filter_b"].name == "predictions_filter_b.jsonl"


def test_compute_f1_bootstrap_ci_exp1(dummy_env: tuple[Config, Path, Path]) -> None:
    cfg, run_dir, test_jsonl = dummy_env
    from src.common.io import read_jsonl

    pairs = read_jsonl(test_jsonl, Pair)
    records = read_jsonl(run_dir / "predictions_rouge.jsonl", VerifierResult)
    preds = {r.pair_id: r for r in records}

    point, low, high = compute_f1_bootstrap_ci_exp1(pairs, preds, seed=42, n_resamples=100)
    assert point == 1.0
    assert low == 1.0
    assert high == 1.0


def test_compute_f1_bootstrap_ci_exp2(dummy_env: tuple[Config, Path, Path]) -> None:
    cfg, run_dir, test_jsonl = dummy_env
    from src.common.io import read_jsonl

    pairs = read_jsonl(test_jsonl, Pair)
    records = read_jsonl(run_dir / "predictions_filter_b.jsonl", VerifierResult)
    preds = {r.pair_id: r for r in records}

    point, low, high = compute_f1_bootstrap_ci_exp2(pairs, preds, seed=42, n_resamples=100)
    assert round(point, 4) == round(4 / 6, 4)  # TP=4, FP=4, FN=0 -> F1 = 8/12 = 0.6667
    assert 0.0 < low <= high <= 1.0


def test_evaluate_experiment_exp1(dummy_env: tuple[Config, Path, Path]) -> None:
    cfg, run_dir, _ = dummy_env
    res = evaluate_experiment("exp1", cfg)

    assert res["run_id"] == "20260920-0000-testrun"
    tables_dir = run_dir / "tables"
    assert tables_dir.exists()
    assert (tables_dir / "main_metrics.csv").exists()
    assert (tables_dir / "mcnemar.csv").exists()
    assert (tables_dir / "difficulty_breakdown.csv").exists()
    assert (tables_dir / "category_breakdown.csv").exists()
    assert (tables_dir / "pr_curve_filter_b.csv").exists()
    assert (run_dir / "summary.md").exists()
    assert (run_dir / "metrics.json").exists()

    # Check main metrics contents
    with open(tables_dir / "main_metrics.csv", encoding="utf-8") as f:
        reader = list(csv.DictReader(f))
        assert len(reader) == 2
        names = {r["verifier"] for r in reader}
        assert names == {"filter_b", "rouge"}

    # Check metrics.json keys
    with open(run_dir / "metrics.json", encoding="utf-8") as f:
        metrics = json.load(f)
        assert "exp1.filter_b.f1" in metrics
        assert "exp1.rouge.f1" in metrics
