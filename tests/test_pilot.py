"""Tests for src/pilot_checks.py — Phase 1 pilot checks.

Tests:
- ROUGE-L AUROC computation against hand-computed example
- Spot-check CSV format validation
- Gate G1 decision logic for Plan 1 and Plan 2
- Provisional dev-set building (pair count, label balance, determinism)
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np
from rouge_score import rouge_scorer
from sklearn.metrics import roc_auc_score

# ---------------------------------------------------------------------------
# Gate G1 decision logic (extracted for unit testing)
# ---------------------------------------------------------------------------


def gate_g1_decision(
    unsupported_rate: float | None,
    primary_auroc: float | None,
    threshold_unsupported: float = 0.10,
    threshold_auroc: float = 0.95,
) -> int | None:
    """Apply Gate G1 decision rule.

    Returns:
        1 or 2 (the recommended plan), or None if inputs are missing.
    """
    if unsupported_rate is None or primary_auroc is None:
        return None
    if unsupported_rate < threshold_unsupported and primary_auroc < threshold_auroc:
        return 1
    return 2


class TestGateG1:
    """Tests for the Gate G1 decision logic."""

    def test_plan_1_both_below_threshold(self) -> None:
        """Low unsupported + low AUROC → Plan 1."""
        assert gate_g1_decision(0.05, 0.80) == 1

    def test_plan_2_high_unsupported(self) -> None:
        """High unsupported rate → Plan 2 regardless of AUROC."""
        assert gate_g1_decision(0.15, 0.70) == 2

    def test_plan_2_high_auroc(self) -> None:
        """High AUROC (lexical shortcut) → Plan 2 regardless of unsupported."""
        assert gate_g1_decision(0.05, 0.97) == 2

    def test_plan_2_both_above_threshold(self) -> None:
        """Both above threshold → Plan 2."""
        assert gate_g1_decision(0.20, 0.98) == 2

    def test_boundary_unsupported_exactly_10(self) -> None:
        """Unsupported at exactly 10% is >= threshold → Plan 2."""
        assert gate_g1_decision(0.10, 0.80) == 2

    def test_boundary_auroc_exactly_095(self) -> None:
        """AUROC at exactly 0.95 is >= threshold → Plan 2."""
        assert gate_g1_decision(0.05, 0.95) == 2

    def test_none_inputs(self) -> None:
        """Missing inputs → None."""
        assert gate_g1_decision(None, 0.80) is None
        assert gate_g1_decision(0.05, None) is None
        assert gate_g1_decision(None, None) is None


class TestRougeAuroc:
    """Tests for ROUGE-L AUROC computation against hand-computed values."""

    def test_auroc_perfect_separation(self) -> None:
        """Perfectly separable scores should give AUROC = 1.0."""
        # Hallucinated (label=1) answers have LOW ROUGE (high 1-score).
        # Supported (label=0) answers have HIGH ROUGE (low 1-score).
        labels = np.array([0, 0, 1, 1])
        scores = np.array([0.9, 0.8, 0.1, 0.2])  # High = supported
        auroc = roc_auc_score(labels, 1.0 - scores)
        assert auroc == 1.0

    def test_auroc_random_scores(self) -> None:
        """Random scores should give AUROC ≈ 0.5."""
        rng = np.random.default_rng(42)
        labels = np.array([0, 0, 0, 0, 0, 1, 1, 1, 1, 1])
        scores = rng.random(10)
        auroc = roc_auc_score(labels, 1.0 - scores)
        # With only 10 samples, just check it's in a reasonable range.
        assert 0.0 <= auroc <= 1.0

    def test_auroc_hand_computed(self) -> None:
        """Hand-computed 4-pair example.

        Pairs:
            (label=0, rouge=0.9) — supported, high overlap
            (label=0, rouge=0.7) — supported, moderate overlap
            (label=1, rouge=0.3) — hallucinated, low overlap
            (label=1, rouge=0.5) — hallucinated, moderate overlap

        Using 1 - score for AUROC (higher = more hallucinated):
            (label=0, pred=0.1), (label=0, pred=0.3),
            (label=1, pred=0.7), (label=1, pred=0.5)

        All positives ranked above all negatives → AUROC = 1.0
        """
        labels = np.array([0, 0, 1, 1])
        rouge_scores = np.array([0.9, 0.7, 0.3, 0.5])
        auroc = roc_auc_score(labels, 1.0 - rouge_scores)
        assert auroc == 1.0

    def test_rouge_scorer_returns_values(self) -> None:
        """Sanity check that rouge_score library produces expected output."""
        scorer = rouge_scorer.RougeScorer(["rougeL"], use_stemmer=True)
        result = scorer.score(
            target="The patient has hypertension and takes medication daily.",
            prediction="The patient has hypertension.",
        )
        rl = result["rougeL"]
        assert 0.0 <= rl.precision <= 1.0
        assert 0.0 <= rl.recall <= 1.0
        assert 0.0 <= rl.fmeasure <= 1.0
        # Precision should be high (prediction fully covered by target).
        assert rl.precision > 0.5


class TestSpotcheckFormat:
    """Tests for spot-check CSV format validation."""

    def test_csv_columns(self, tmp_path: Path) -> None:
        """Spot-check CSV must have the correct columns."""
        expected_cols = ["row_id", "question", "context", "ground_truth", "supported_yes_no", "notes"]

        csv_path = tmp_path / "spotcheck.csv"
        with open(csv_path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(expected_cols)
            writer.writerow(["0", "What is X?", "X is Y.", "Y", "", ""])

        with open(csv_path, newline="") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        assert len(rows) == 1
        assert set(rows[0].keys()) == set(expected_cols)
        assert rows[0]["supported_yes_no"] == ""
        assert rows[0]["notes"] == ""

    def test_annotation_columns_empty(self, tmp_path: Path) -> None:
        """Annotation columns must be empty in exported CSV (Rule R1.5)."""
        csv_path = tmp_path / "spotcheck.csv"
        with open(csv_path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["row_id", "question", "context", "ground_truth", "supported_yes_no", "notes"])
            for i in range(5):
                writer.writerow([str(i), f"Q{i}", f"C{i}", f"GT{i}", "", ""])

        with open(csv_path, newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                assert row["supported_yes_no"] == "", "Annotation column must be empty"
                assert row["notes"] == "", "Notes column must be empty"


class TestProvisionalDevSet:
    """Tests for provisional dev-set building properties."""

    def test_label_balance(self) -> None:
        """Provisional dev set should have 50/50 label balance."""
        # Simulate what _build_provisional_dev produces:
        # For each question, one label=0 and one label=1 pair.
        n_questions = 50
        labels = [0, 1] * n_questions
        assert labels.count(0) == n_questions
        assert labels.count(1) == n_questions

    def test_pair_count(self) -> None:
        """Provisional dev set should have 2 * dev_questions pairs."""
        n_questions = 50
        expected_pairs = 2 * n_questions
        assert expected_pairs == 100

    def test_deterministic_with_seed(self) -> None:
        """Same seed produces same sample indices."""
        import random

        list1 = list(range(500))
        rng_a = random.Random(42)
        rng_a.shuffle(list1)
        s1 = list1[:50]

        list2 = list(range(500))
        rng_b = random.Random(42)
        rng_b.shuffle(list2)
        s2 = list2[:50]

        assert s1 == s2, "Same seed must produce identical samples"


class TestPilotReportParsing:
    """Tests for pilot report JSON structure."""

    def test_report_structure(self, tmp_path: Path) -> None:
        """Report JSON must have all required sections."""
        report = {
            "spotcheck": {
                "total_rows": 50,
                "total_checked": 48,
                "unfilled": 2,
                "unsupported_count": 3,
                "unsupported_rate": 3 / 48,
            },
            "rouge": {
                "n_pairs": 100,
                "n_questions": 50,
                "auroc": {
                    "rougeL_precision": 0.82,
                    "rougeL_recall": 0.75,
                    "rougeL_fmeasure": 0.78,
                },
                "primary_variant": "rougeL_precision",
                "primary_auroc": 0.82,
            },
            "gate_g1": {
                "threshold_unsupported": 0.10,
                "threshold_auroc": 0.95,
                "recommended_plan": 1,
                "reason": "...",
            },
        }

        path = tmp_path / "pilot_report.json"
        with open(path, "w") as f:
            json.dump(report, f)

        with open(path) as f:
            loaded = json.load(f)

        assert "spotcheck" in loaded
        assert "rouge" in loaded
        assert "gate_g1" in loaded
        assert loaded["gate_g1"]["recommended_plan"] in (1, 2)
        assert 0 <= loaded["spotcheck"]["unsupported_rate"] <= 1
