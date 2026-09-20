"""Tests for Phase 9 cross-experiment analysis module (src/cross_experiment.py)."""

from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from src.common.config import Config, load_config
from src.common.io import Pair, VerifierResult, write_jsonl
from src.cross_experiment import find_latest_run_id, run_cross_experiment_analysis


@pytest.fixture
def mock_experiments(tmp_path: Path) -> tuple[Config, str, str]:
    data_dir = tmp_path / "data"
    results_dir = tmp_path / "results"
    exp1_data = data_dir / "exp1_medhallu"
    exp2_data = data_dir / "exp2_rag"
    exp1_data.mkdir(parents=True)
    exp2_data.mkdir(parents=True)

    # 2 questions, 4 pairs for exp1
    pairs1 = [
        Pair(pair_id="e1-q1-gt", question_id="q1", experiment="exp1", split="test", question="Q1", context="C1", answer="A1", label=0),
        Pair(pair_id="e1-q1-hal", question_id="q1", experiment="exp1", split="test", question="Q1", context="C1", answer="A1", label=1),
        Pair(pair_id="e1-q2-gt", question_id="q2", experiment="exp1", split="test", question="Q2", context="C2", answer="A2", label=0),
        Pair(pair_id="e1-q2-hal", question_id="q2", experiment="exp1", split="test", question="Q2", context="C2", answer="A2", label=1),
    ]
    write_jsonl(exp1_data / "test.jsonl", pairs1)

    # 2 pairs for exp2
    pairs2 = [
        Pair(pair_id="e2-q1", question_id="q1", experiment="exp2", split="rag", question="Q1", context="C1", answer="A1", label=0, condition="normal"),
        Pair(pair_id="e2-q2", question_id="q2", experiment="exp2", split="rag", question="Q2", context="C2", answer="A2", label=1, condition="degraded"),
    ]
    write_jsonl(exp2_data / "pairs.jsonl", pairs2)

    run1_id = "20260920-1000-exp1"
    run2_id = "20260920-2000-exp2"
    r1_dir = results_dir / "exp1" / run1_id
    r2_dir = results_dir / "exp2" / run2_id
    (r1_dir / "tables").mkdir(parents=True)
    (r2_dir / "tables").mkdir(parents=True)

    # Main metrics CSVs
    with open(r1_dir / "tables" / "main_metrics.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["verifier", "f1", "fnr", "f1_ci_lower", "f1_ci_upper"])
        writer.writeheader()
        writer.writerow({"verifier": "filter_b", "f1": "0.80", "fnr": "0.10", "f1_ci_lower": "0.75", "f1_ci_upper": "0.85"})
        writer.writerow({"verifier": "rouge", "f1": "0.60", "fnr": "0.20", "f1_ci_lower": "0.55", "f1_ci_upper": "0.65"})

    with open(r2_dir / "tables" / "main_metrics.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["verifier", "f1", "fnr", "f1_ci_lower", "f1_ci_upper"])
        writer.writeheader()
        writer.writerow({"verifier": "filter_b", "f1": "0.75", "fnr": "0.15", "f1_ci_lower": "0.70", "f1_ci_upper": "0.80"})
        writer.writerow({"verifier": "rouge", "f1": "0.55", "fnr": "0.25", "f1_ci_lower": "0.50", "f1_ci_upper": "0.60"})

    # Predictions
    preds1_fb = [VerifierResult(pair_id="e1-q1-gt", verifier="filter_b", score=0.9, verdict=0),
                 VerifierResult(pair_id="e1-q1-hal", verifier="filter_b", score=0.1, verdict=1),
                 VerifierResult(pair_id="e1-q2-gt", verifier="filter_b", score=0.9, verdict=0),
                 VerifierResult(pair_id="e1-q2-hal", verifier="filter_b", score=0.1, verdict=1)]
    preds1_rg = [VerifierResult(pair_id="e1-q1-gt", verifier="rouge", score=0.9, verdict=0),
                 VerifierResult(pair_id="e1-q1-hal", verifier="rouge", score=0.9, verdict=0),  # Disagreement here
                 VerifierResult(pair_id="e1-q2-gt", verifier="rouge", score=0.9, verdict=0),
                 VerifierResult(pair_id="e1-q2-hal", verifier="rouge", score=0.1, verdict=1)]
    write_jsonl(r1_dir / "predictions_filter_b.jsonl", preds1_fb)
    write_jsonl(r1_dir / "predictions_rouge.jsonl", preds1_rg)

    preds2_fb = [VerifierResult(pair_id="e2-q1", verifier="filter_b", score=0.8, verdict=0),
                 VerifierResult(pair_id="e2-q2", verifier="filter_b", score=0.2, verdict=1)]
    write_jsonl(r2_dir / "predictions_filter_b.jsonl", preds2_fb)

    # Thresholds
    with open(results_dir / "thresholds.json", "w", encoding="utf-8") as f:
        json.dump({"filter_b": {"threshold": 0.5}}, f)

    # LATEST.json
    with open(results_dir / "LATEST.json", "w", encoding="utf-8") as f:
        json.dump({"exp1": run1_id, "exp2": run2_id}, f)

    cfg = load_config("configs/config.yaml")
    cfg.paths.data = str(data_dir)
    cfg.paths.results = str(results_dir)

    return cfg, run1_id, run2_id


def test_find_latest_run_id(mock_experiments: tuple[Config, str, str]) -> None:
    cfg, r1, r2 = mock_experiments
    results_dir = Path(cfg.paths.results)
    assert find_latest_run_id(results_dir, "exp1") == r1
    assert find_latest_run_id(results_dir, "exp2") == r2


def test_cross_experiment_ranking_agreement(mock_experiments: tuple[Config, str, str]) -> None:
    cfg, r1, r2 = mock_experiments
    res = run_cross_experiment_analysis(cfg, run_id_exp1=r1, run_id_exp2=r2)

    assert res["ranking_agrees"] is True
    target_dir = Path(res["target_dir"])
    assert (target_dir / "cross_summary.md").exists()
    assert (target_dir / "qualitative_disagreements.csv").exists()

    # Verify disagreements file
    with open(target_dir / "qualitative_disagreements.csv", encoding="utf-8") as f:
        disagreements = list(csv.DictReader(f))
        assert len(disagreements) == 1
        assert disagreements[0]["pair_id"] == "e1-q1-hal"
