"""Tests for src/common/prompts.py — prompt loading, freezing, and hash verification."""

import json
from pathlib import Path

import pytest

from src.common.prompts import (
    PromptHashMismatchError,
    compute_hash,
    fill_prompt,
    freeze_prompt,
    load_prompt,
    verify_frozen,
)


@pytest.fixture
def prompt_dir(tmp_path: Path) -> Path:
    """Create a temp prompts directory with a test prompt."""
    prompts = tmp_path / "prompts"
    prompts.mkdir()

    # Write a test prompt
    (prompts / "test_v1.txt").write_text(
        'You are a judge. Context: {context}\nAnswer: {answer}\nReturn JSON: {"verdict": "SUPPORTED"}',
        encoding="utf-8",
    )

    # Write empty FROZEN.json
    (prompts / "FROZEN.json").write_text("{}", encoding="utf-8")

    return prompts


def test_compute_hash_deterministic() -> None:
    """Same text always produces the same hash."""
    h1 = compute_hash("hello world")
    h2 = compute_hash("hello world")
    assert h1 == h2
    assert len(h1) == 64


def test_compute_hash_different_text() -> None:
    """Different text produces different hashes."""
    h1 = compute_hash("text1")
    h2 = compute_hash("text2")
    assert h1 != h2


def test_load_prompt(prompt_dir: Path) -> None:
    """Load an existing prompt file."""
    text = load_prompt("test_v1.txt", base=prompt_dir)
    assert "{context}" in text
    assert "{answer}" in text


def test_load_prompt_missing(prompt_dir: Path) -> None:
    """Loading a missing prompt raises FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        load_prompt("nonexistent.txt", base=prompt_dir)


def test_freeze_and_verify(prompt_dir: Path) -> None:
    """Freeze a prompt, then verify it succeeds."""
    prompt_hash = freeze_prompt("test_v1.txt", base=prompt_dir)

    # FROZEN.json should have the hash
    frozen = json.loads((prompt_dir / "FROZEN.json").read_text())
    assert frozen["test_v1.txt"] == prompt_hash

    # Verification should pass
    text = verify_frozen("test_v1.txt", base=prompt_dir)
    assert "{context}" in text


def test_verify_frozen_mismatch(prompt_dir: Path) -> None:
    """Modifying a frozen prompt triggers PromptHashMismatchError."""
    freeze_prompt("test_v1.txt", base=prompt_dir)

    # Tamper with the prompt
    (prompt_dir / "test_v1.txt").write_text("modified prompt", encoding="utf-8")

    with pytest.raises(PromptHashMismatchError):
        verify_frozen("test_v1.txt", base=prompt_dir)


def test_verify_frozen_not_listed(prompt_dir: Path) -> None:
    """Verifying a prompt not in FROZEN.json raises KeyError."""
    with pytest.raises(KeyError):
        verify_frozen("test_v1.txt", base=prompt_dir)


def test_fill_prompt() -> None:
    """Template filling uses str.replace, not str.format (preserves JSON braces)."""
    template = 'Context: {context}\nAnswer: {answer}\n{"verdict": "SUPPORTED"}'
    filled = fill_prompt(template, context="Some context.", answer="Some answer.")
    assert "Some context." in filled
    assert "Some answer." in filled
    assert '{"verdict": "SUPPORTED"}' in filled  # JSON braces preserved
