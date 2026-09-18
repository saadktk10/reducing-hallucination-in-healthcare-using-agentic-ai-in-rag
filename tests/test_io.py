"""Tests for src/common/io.py — JSONL I/O and schema validation."""

from pathlib import Path

import pytest

from src.common.io import Pair, Chunk, VerifierResult, CacheRecord, read_jsonl, write_jsonl


FIXTURES = Path(__file__).parent / "fixtures"


def test_read_sample_pairs() -> None:
    """Read the fixture file and validate all 10 records as Pair."""
    pairs = read_jsonl(FIXTURES / "sample_pairs.jsonl", Pair)
    assert len(pairs) == 10

    # Check label balance
    labels = [p.label for p in pairs]
    assert labels.count(0) == 5
    assert labels.count(1) == 5

    # Check question IDs are paired
    qids = [p.question_id for p in pairs]
    for qid in set(qids):
        assert qids.count(qid) == 2


def test_read_missing_file() -> None:
    """Reading a nonexistent file raises FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        read_jsonl("nonexistent.jsonl", Pair)


def test_write_and_read_roundtrip(tmp_path: Path) -> None:
    """Write records, read them back, and verify they match."""
    pairs = [
        Pair(
            pair_id="t-q1-gt",
            question_id="q1",
            experiment="exp1",
            split="dev",
            question="Test question?",
            context="Test context.",
            answer="Test answer.",
            label=0,
        ),
        Pair(
            pair_id="t-q1-hal",
            question_id="q1",
            experiment="exp1",
            split="dev",
            question="Test question?",
            context="Test context.",
            answer="Wrong answer.",
            label=1,
        ),
    ]

    path = tmp_path / "test.jsonl"
    write_jsonl(path, pairs)

    loaded = read_jsonl(path, Pair)
    assert len(loaded) == 2
    assert loaded[0].pair_id == "t-q1-gt"
    assert loaded[1].label == 1


def test_write_append_mode(tmp_path: Path) -> None:
    """Append mode adds records without overwriting."""
    path = tmp_path / "append.jsonl"

    pair1 = Pair(
        pair_id="a1",
        question_id="q1",
        experiment="exp1",
        split="dev",
        question="Q?",
        context="C.",
        answer="A.",
        label=0,
    )
    pair2 = Pair(
        pair_id="a2",
        question_id="q1",
        experiment="exp1",
        split="dev",
        question="Q?",
        context="C.",
        answer="A2.",
        label=1,
    )

    write_jsonl(path, [pair1])
    write_jsonl(path, [pair2], append=True)

    loaded = read_jsonl(path, Pair)
    assert len(loaded) == 2


def test_invalid_record_raises(tmp_path: Path) -> None:
    """A record with an invalid field raises on read."""
    path = tmp_path / "bad.jsonl"
    path.write_text('{"pair_id": "x"}\n')  # missing required fields

    with pytest.raises(ValueError):
        read_jsonl(path, Pair)


def test_pair_schema_label_values() -> None:
    """Pair label only accepts 0, 1, or None."""
    base = {
        "pair_id": "p1",
        "question_id": "q1",
        "experiment": "exp1",
        "split": "dev",
        "question": "Q?",
        "context": "C.",
        "answer": "A.",
    }

    # Valid values
    Pair(**base, label=0)
    Pair(**base, label=1)
    Pair(**base, label=None)

    # Invalid value
    with pytest.raises(Exception):
        Pair(**base, label=2)


def test_verifier_result_schema() -> None:
    """VerifierResult accepts valid data."""
    vr = VerifierResult(
        pair_id="p1",
        verifier="filter_b",
        score=0.85,
        verdict=0,
    )
    assert vr.parse_failure is False
    assert vr.details == {}


def test_chunk_schema() -> None:
    """Chunk schema validates correctly."""
    c = Chunk(chunk_id="doc1-0", doc_id="doc1", text="Some text.", n_tokens=3)
    assert c.chunk_id == "doc1-0"


def test_cache_record_schema() -> None:
    """CacheRecord schema validates correctly."""
    cr = CacheRecord(
        key="abc123",
        provider="gemini",
        model_id="gemini-flash",
        prompt_hash="def456",
        request_text="test request",
        response_text="test response",
        parsed={"verdict": "SUPPORTED"},
        input_tokens=10,
        output_tokens=5,
        latency_ms=150.0,
        attempt=1,
        mode="normal",
        timestamp_utc="2026-01-15T10:00:00Z",
    )
    assert cr.attempt == 1
