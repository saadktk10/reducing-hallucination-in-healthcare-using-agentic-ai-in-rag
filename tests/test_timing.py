"""Tests for timing protocol module (Design.md §9, Rules §3)."""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from src.common.config import Config
from src.common.io import Pair, VerifierResult
from src.timing import measure_verifier_timing


def test_measure_verifier_timing_basic(tmp_path: Path) -> None:
    """Test timing protocol execution with mock verifier."""
    mock_verifier = MagicMock()
    mock_verifier.name = "rouge"
    mock_verifier.load.return_value = 0.05
    mock_verifier.score.return_value = VerifierResult(
        pair_id="p1",
        verifier="rouge",
        score=0.9,
        verdict=0,
        confidence=0.9,
        latency_ms=12.5,
        details={"from_cache": False},
    )

    pairs = [
        Pair(
            pair_id=f"e1-q{i}-gt",
            question_id=f"q{i}",
            experiment="exp1",
            split="test",
            question=f"Q{i}?",
            context="C",
            answer="A",
            label=0,
        )
        for i in range(15)
    ]

    cfg = Config(
        datasets={
            "medhallu": {"hf_id": "foo", "config": "pqa", "revision": "rev1", "columns": {}},
            "pubmedqa": {"hf_id": "bar", "config": "pqa", "revision": "rev2"},
        },
    )
    cfg.timing.warmup_pairs = 2

    out_dir = tmp_path / "timing_test"
    out_dir.mkdir()

    res = measure_verifier_timing(
        verifier=mock_verifier,
        pairs=pairs,
        cfg=cfg,
        out_dir=out_dir,
        session="morning",
        limit=5,
    )

    assert res["verifier"] == "rouge"
    assert res["session"] == "morning"
    assert res["warmup_pairs"] == 2
    assert res["n_timed_pairs"] == 5
    assert "median_ms" in res["pass1"]
    assert "p95_ms" in res["pass1"]
    assert "median_ms" in res["pooled"]
    assert (out_dir / "timing_rouge_morning.json").exists()
    assert (out_dir / "timing_rouge_morning.csv").exists()
    assert (out_dir / "timing_rouge.json").exists()


def test_filter_a_cache_hit_assert(tmp_path: Path) -> None:
    """Assert that a cache hit during Filter A timing run raises AssertionError (Rule R3.2)."""
    mock_verifier = MagicMock()
    mock_verifier.name = "filter_a"
    mock_verifier.load.return_value = 0.01
    mock_verifier.score.return_value = VerifierResult(
        pair_id="p1",
        verifier="filter_a",
        score=0.9,
        verdict=0,
        confidence=0.9,
        latency_ms=5.0,
        details={"from_cache": True},  # Illegal cache hit during timing!
    )

    pairs = [
        Pair(
            pair_id=f"e1-q{i}-gt",
            question_id=f"q{i}",
            experiment="exp1",
            split="test",
            question=f"Q{i}?",
            context="C",
            answer="A",
            label=0,
        )
        for i in range(5)
    ]

    cfg = Config(
        datasets={
            "medhallu": {"hf_id": "foo", "config": "pqa", "revision": "rev1", "columns": {}},
            "pubmedqa": {"hf_id": "bar", "config": "pqa", "revision": "rev2"},
        },
    )
    cfg.timing.warmup_pairs = 1

    out_dir = tmp_path / "timing_fail"
    out_dir.mkdir()

    with pytest.raises(AssertionError, match="Cache hit detected"):
        measure_verifier_timing(
            verifier=mock_verifier,
            pairs=pairs,
            cfg=cfg,
            out_dir=out_dir,
            session="morning",
            limit=2,
        )
