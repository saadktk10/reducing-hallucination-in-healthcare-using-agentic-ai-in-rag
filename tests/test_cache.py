"""Tests for src/common/cache.py — append-only JSONL cache."""

from pathlib import Path

import pytest

from src.common.cache import JsonlCache, make_cache_key
from src.common.io import CacheRecord


def _make_record(key: str = "testkey") -> CacheRecord:
    """Create a minimal valid CacheRecord for testing."""
    return CacheRecord(
        key=key,
        provider="gemini",
        model_id="test-model",
        prompt_hash="abc123",
        request_text="test request",
        response_text="test response",
        parsed=None,
        input_tokens=10,
        output_tokens=5,
        latency_ms=100.0,
        attempt=1,
        mode="normal",
        timestamp_utc="2026-01-15T10:00:00Z",
    )


def test_make_cache_key_deterministic() -> None:
    """Same inputs always produce the same key."""
    k1 = make_cache_key("model", "hash", "context", "answer")
    k2 = make_cache_key("model", "hash", "context", "answer")
    assert k1 == k2
    assert len(k1) == 64  # SHA-256 hex


def test_make_cache_key_different_inputs() -> None:
    """Different inputs produce different keys."""
    k1 = make_cache_key("model", "hash", "context", "answer1")
    k2 = make_cache_key("model", "hash", "context", "answer2")
    assert k1 != k2


def test_cache_empty(tmp_path: Path) -> None:
    """New cache with no file starts empty."""
    cache = JsonlCache(tmp_path / "cache.jsonl")
    assert len(cache) == 0
    assert cache.get("missing") is None


def test_cache_append_and_get(tmp_path: Path) -> None:
    """Appended records are retrievable by key."""
    cache_path = tmp_path / "cache.jsonl"
    cache = JsonlCache(cache_path)

    record = _make_record("key1")
    cache.append(record)

    assert len(cache) == 1
    assert "key1" in cache
    assert cache.get("key1") is not None
    assert cache.get("key1").provider == "gemini"


def test_cache_persistence(tmp_path: Path) -> None:
    """Cache survives reload from disk."""
    cache_path = tmp_path / "cache.jsonl"

    # Write
    cache1 = JsonlCache(cache_path)
    cache1.append(_make_record("persisted"))

    # Reload
    cache2 = JsonlCache(cache_path)
    assert len(cache2) == 1
    assert cache2.get("persisted") is not None


def test_cache_contains(tmp_path: Path) -> None:
    """The 'in' operator works for cache keys."""
    cache = JsonlCache(tmp_path / "cache.jsonl")
    cache.append(_make_record("exists"))

    assert "exists" in cache
    assert "nope" not in cache
