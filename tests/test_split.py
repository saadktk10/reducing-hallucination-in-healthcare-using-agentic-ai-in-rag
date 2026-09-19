"""Tests for Experiment 1 data splits — Phase 2.

Checks:
- No question ID in both dev and test (strict disjointness)
- Correct counts: dev=100 pairs (50 questions), test=400 pairs (200 questions)
- 50/50 label balance in each split
- Difficulty strata present across splits
- Exact match between Phase 2 dev set and Phase 1 pilot provisional dev set
- Valid schema compliance for all Pair objects
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from src.build_exp1_pairs import (
    build_pairs,
    extract_context,
    generate_split_summary,
    sample_and_split_questions,
)
from src.common.config import Config
from src.common.io import Pair, read_jsonl


class MockDataset:
    """Mock HuggingFace dataset for deterministic unit testing without network."""

    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self.rows = rows
        self.column_names = list(rows[0].keys()) if rows else []

    def __len__(self) -> int:
        return len(self.rows)

    def __getitem__(self, idx: int) -> dict[str, Any]:
        return self.rows[idx]


@pytest.fixture
def mock_dataset() -> MockDataset:
    """Create a mock 300-row dataset with difficulty and category columns."""
    rows = []
    diffs = ["easy"] * 100 + ["medium"] * 100 + ["hard"] * 100
    for i in range(300):
        rows.append({
            "Question": f"Medical question {i}?",
            "Knowledge": [f"Sentence 1 about {i}.", f"Sentence 2 about {i}."],
            "Ground Truth": f"True medical answer {i}.",
            "Hallucinated Answer": f"Hallucinated claim {i}.",
            "Difficulty Level": diffs[i],
            "Category of Hallucination": f"Category {i % 4}",
        })
    return MockDataset(rows)


@pytest.fixture
def sample_cfg() -> Config:
    """Create a minimal valid configuration with datasets configured."""
    minimal = {
        "datasets": {
            "medhallu": {
                "hf_id": "test",
                "config": "test",
                "columns": {
                    "question": "Question",
                    "context": "Knowledge",
                    "ground_truth": "Ground Truth",
                    "hallucinated": "Hallucinated Answer",
                    "difficulty": "Difficulty Level",
                    "category": "Category of Hallucination",
                },
            },
            "pubmedqa": {"hf_id": "test", "config": "test"},
        },
    }
    return Config(**minimal)


class TestMockSplits:
    """Unit tests for sampling and splitting logic on mock data."""

    def test_extract_context(self) -> None:
        """Context joins lists with space and converts non-lists to str."""
        assert extract_context(["Hello", "World"]) == "Hello World"
        assert extract_context("Single string") == "Single string"

    def test_sampling_counts_and_disjointness(
        self, mock_dataset: MockDataset, sample_cfg: Config
    ) -> None:
        """sample_and_split_questions returns exact split sizes with 0 overlap."""
        dev_idx, test_idx = sample_and_split_questions(mock_dataset, sample_cfg)

        assert len(dev_idx) == 50
        assert len(test_idx) == 200
        assert len(set(dev_idx)) == 50
        assert len(set(test_idx)) == 200
        assert set(dev_idx).intersection(set(test_idx)) == set()

    def test_build_pairs_structure_and_balance(
        self, mock_dataset: MockDataset, sample_cfg: Config
    ) -> None:
        """build_pairs creates 2 * N pairs with 50/50 label balance."""
        indices = [0, 1, 2, 3, 4]
        pairs = build_pairs(mock_dataset, indices, split="dev", cfg=sample_cfg, start_qid_idx=0)

        assert len(pairs) == 10
        assert sum(1 for p in pairs if p.label == 0) == 5
        assert sum(1 for p in pairs if p.label == 1) == 5

        # Check pairing
        for i in range(5):
            qid = f"q{i:03d}"
            q_pairs = [p for p in pairs if p.question_id == qid]
            assert len(q_pairs) == 2
            pair_ids = {p.pair_id for p in q_pairs}
            assert pair_ids == {f"e1-{qid}-gt", f"e1-{qid}-hal"}
            labels = {p.label for p in q_pairs}
            assert labels == {0, 1}

    def test_generate_split_summary(
        self, mock_dataset: MockDataset, sample_cfg: Config
    ) -> None:
        """Summary computes accurate split counts."""
        dev_pairs = build_pairs(
            mock_dataset, [0, 1], split="dev", cfg=sample_cfg, start_qid_idx=0
        )
        test_pairs = build_pairs(
            mock_dataset, [2, 3, 4], split="test", cfg=sample_cfg, start_qid_idx=2
        )

        summary = generate_split_summary(dev_pairs, test_pairs, sample_cfg)
        assert summary["total_questions"] == 5
        assert summary["total_pairs"] == 10
        assert summary["splits"]["dev"]["n_questions"] == 2
        assert summary["splits"]["dev"]["n_pairs"] == 4
        assert summary["splits"]["test"]["n_questions"] == 3
        assert summary["splits"]["test"]["n_pairs"] == 6


class TestExp1DiskArtifacts:
    """Integration checks on actual generated artifacts on disk (if present)."""

    @pytest.fixture
    def exp1_paths(self) -> tuple[Path, Path, Path]:
        dev_path = Path("data/exp1_medhallu/dev.jsonl")
        test_path = Path("data/exp1_medhallu/test.jsonl")
        summary_path = Path("data/exp1_medhallu/split_summary.json")
        return dev_path, test_path, summary_path

    def test_disk_counts_and_disjointness(
        self, exp1_paths: tuple[Path, Path, Path]
    ) -> None:
        """If data exists on disk, verify pair counts and strict disjointness."""
        dev_path, test_path, summary_path = exp1_paths
        if not dev_path.exists() or not test_path.exists():
            pytest.skip("Exp 1 data files not yet generated on disk")

        dev_pairs = read_jsonl(dev_path, Pair)
        test_pairs = read_jsonl(test_path, Pair)

        assert len(dev_pairs) == 100, f"Expected 100 dev pairs, got {len(dev_pairs)}"
        assert len(test_pairs) == 400, f"Expected 400 test pairs, got {len(test_pairs)}"

        dev_qids = {p.question_id for p in dev_pairs}
        test_qids = {p.question_id for p in test_pairs}

        assert len(dev_qids) == 50
        assert len(test_qids) == 200
        assert dev_qids.intersection(test_qids) == set(), "Question IDs must be completely disjoint!"

        # Question text disjointness
        dev_texts = {p.question for p in dev_pairs}
        test_texts = {p.question for p in test_pairs}
        assert dev_texts.intersection(test_texts) == set(), "Question texts must be completely disjoint!"

    def test_disk_label_balance(self, exp1_paths: tuple[Path, Path, Path]) -> None:
        """Both dev and test must have exact 50/50 label balance."""
        dev_path, test_path, _ = exp1_paths
        if not dev_path.exists() or not test_path.exists():
            pytest.skip("Exp 1 data files not yet generated on disk")

        dev_pairs = read_jsonl(dev_path, Pair)
        test_pairs = read_jsonl(test_path, Pair)

        assert sum(1 for p in dev_pairs if p.label == 0) == 50
        assert sum(1 for p in dev_pairs if p.label == 1) == 50
        assert sum(1 for p in test_pairs if p.label == 0) == 200
        assert sum(1 for p in test_pairs if p.label == 1) == 200

    def test_difficulty_strata_represented(self, exp1_paths: tuple[Path, Path, Path]) -> None:
        """All difficulty strata (easy, medium, hard) must be present in both splits."""
        dev_path, test_path, _ = exp1_paths
        if not dev_path.exists() or not test_path.exists():
            pytest.skip("Exp 1 data files not yet generated on disk")

        dev_pairs = read_jsonl(dev_path, Pair)
        test_pairs = read_jsonl(test_path, Pair)

        expected_strata = {"easy", "medium", "hard"}
        dev_diffs = {p.difficulty for p in dev_pairs}
        test_diffs = {p.difficulty for p in test_pairs}

        assert expected_strata.issubset(dev_diffs), f"Missing strata in dev: {expected_strata - dev_diffs}"
        assert expected_strata.issubset(test_diffs), f"Missing strata in test: {expected_strata - test_diffs}"

    def test_provisional_pilot_dev_match(self, exp1_paths: tuple[Path, Path, Path]) -> None:
        """Phase 2 dev set must match the Phase 1 pilot provisional dev set."""
        dev_path, _, _ = exp1_paths
        rouge_path = Path("data/pilot/rouge_results.json")

        if not dev_path.exists() or not rouge_path.exists():
            pytest.skip("Dev file or pilot rouge results not present")

        dev_pairs = read_jsonl(dev_path, Pair)
        with open(rouge_path) as f:
            rouge_data = json.load(f)

        pilot_scores = rouge_data.get("per_pair_scores", [])
        assert len(dev_pairs) == len(pilot_scores)

        for dev_p, pilot_p in zip(dev_pairs, pilot_scores):
            assert dev_p.pair_id == pilot_p["pair_id"]
            assert dev_p.question_id == pilot_p["question_id"]
            assert dev_p.label == pilot_p["label"]
            assert dev_p.difficulty == pilot_p["difficulty"]

    def test_summary_matches_data(self, exp1_paths: tuple[Path, Path, Path]) -> None:
        """Split summary counts must match the actual data on disk."""
        dev_path, test_path, summary_path = exp1_paths
        if not summary_path.exists() or not dev_path.exists() or not test_path.exists():
            pytest.skip("Exp 1 summary or data files not present")

        with open(summary_path) as f:
            summary = json.load(f)

        dev_pairs = read_jsonl(dev_path, Pair)
        test_pairs = read_jsonl(test_path, Pair)

        assert summary["total_pairs"] == len(dev_pairs) + len(test_pairs)
        assert summary["splits"]["dev"]["n_pairs"] == len(dev_pairs)
        assert summary["splits"]["test"]["n_pairs"] == len(test_pairs)
        assert summary["splits"]["dev"]["n_questions"] == len({p.question_id for p in dev_pairs})
        assert summary["splits"]["test"]["n_questions"] == len({p.question_id for p in test_pairs})
