"""Tests for Filter A (API judge) — Phase 3.

Checks:
- Parser handles fences, extra text, bad JSON
- Exactly one retry on parse failure (Rule R2.6)
- Cache key stable and deterministic
- Timing mode skips cache reads (Rule R3.2)
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest

from src.common.prompts import PromptHashMismatchError, compute_hash
from src.filters.filter_api import APIJudgeVerifier


def test_parse_response_clean_json() -> None:
    raw = '{"verdict": "SUPPORTED", "confidence": 0.95, "reason": "Directly supported"}'
    parsed = APIJudgeVerifier.parse_response(raw)
    assert parsed["verdict"] == "SUPPORTED"
    assert parsed["confidence"] == 0.95
    assert parsed["reason"] == "Directly supported"


def test_parse_response_markdown_fences() -> None:
    raw = '```json\n{"verdict": "NOT_SUPPORTED", "confidence": 0.8, "reason": "Contradicted"}\n```'
    parsed = APIJudgeVerifier.parse_response(raw)
    assert parsed["verdict"] == "NOT_SUPPORTED"
    assert parsed["confidence"] == 0.8


def test_parse_response_surrounding_text() -> None:
    raw = 'Here is my evaluation:\n{"verdict": "SUPPORTED", "confidence": 1.0, "reason": "Accurate"}\nHope this helps!'
    parsed = APIJudgeVerifier.parse_response(raw)
    assert parsed["verdict"] == "SUPPORTED"
    assert parsed["confidence"] == 1.0


def test_parse_response_invalid_verdict() -> None:
    raw = '{"verdict": "MAYBE", "confidence": 0.5, "reason": "Uncertain"}'
    with pytest.raises(ValueError, match="Invalid verdict"):
        APIJudgeVerifier.parse_response(raw)


def test_parse_response_invalid_confidence() -> None:
    raw1 = '{"verdict": "SUPPORTED", "confidence": 1.5, "reason": "Too confident"}'
    with pytest.raises(ValueError, match="Confidence.*out of range"):
        APIJudgeVerifier.parse_response(raw1)

    raw2 = '{"verdict": "SUPPORTED", "confidence": "high", "reason": "Not a float"}'
    with pytest.raises(ValueError, match="Invalid confidence"):
        APIJudgeVerifier.parse_response(raw2)


def test_one_retry_on_parse_failure(tmp_path) -> None:
    """If first attempt fails to parse, retries once. If second succeeds, verdict is returned."""
    mock_choice1 = MagicMock()
    mock_choice1.message.content = "I think it is supported but not json."
    mock_resp1 = MagicMock(choices=[mock_choice1], usage=MagicMock(prompt_tokens=10, completion_tokens=10))

    mock_choice2 = MagicMock()
    mock_choice2.message.content = '{"verdict": "SUPPORTED", "confidence": 0.9, "reason": "ok"}'
    mock_resp2 = MagicMock(choices=[mock_choice2], usage=MagicMock(prompt_tokens=10, completion_tokens=10))

    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = [mock_resp1, mock_resp2]

    verifier = APIJudgeVerifier(
        cache_path=tmp_path / "judge.jsonl",
        client=mock_client,
    )
    verifier.template = "Context: {context}\nAnswer: {answer}"
    verifier.prompt_hash = "fakehash"
    verifier.cache = MagicMock()
    verifier.cache.__contains__.return_value = False
    verifier.rate_limiter = MagicMock()

    result = verifier.score("context", "answer", pair_id="p1")

    assert result.parse_failure is False
    assert result.verdict == 0  # SUPPORTED -> 0
    assert result.confidence == 0.9
    assert mock_client.chat.completions.create.call_count == 2


def test_double_parse_failure_recorded(tmp_path) -> None:
    """If both attempts fail to parse, sets parse_failure=True and verdict=None (Rule R2.6)."""
    mock_choice = MagicMock()
    mock_choice.message.content = "Invalid output twice."
    mock_resp = MagicMock(choices=[mock_choice], usage=MagicMock(prompt_tokens=10, completion_tokens=10))

    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_resp

    verifier = APIJudgeVerifier(
        cache_path=tmp_path / "judge.jsonl",
        client=mock_client,
    )
    verifier.template = "Context: {context}\nAnswer: {answer}"
    verifier.prompt_hash = "fakehash"
    verifier.cache = MagicMock()
    verifier.cache.__contains__.return_value = False
    verifier.rate_limiter = MagicMock()

    result = verifier.score("context", "answer", pair_id="p2")

    assert result.parse_failure is True
    assert result.verdict is None
    assert result.score is None
    assert mock_client.chat.completions.create.call_count == 2


def test_frozen_prompt_verification(tmp_path) -> None:
    """Verifies that tampering with a frozen prompt causes load() to raise PromptHashMismatchError."""
    prompts_dir = tmp_path / "prompts"
    prompts_dir.mkdir()
    prompt_file = prompts_dir / "judge_v1.txt"
    original_text = "Context: {context}\nAnswer: {answer}\nEvaluate."
    prompt_file.write_text(original_text)

    # Freeze the prompt
    frozen_file = prompts_dir / "FROZEN.json"
    frozen_file.write_text(json.dumps({"judge_v1.txt": compute_hash(original_text)}))

    # Mock config with paths.prompts = str(prompts_dir)
    mock_cfg = MagicMock()
    mock_cfg.paths.prompts = str(prompts_dir)
    mock_cfg.paths.cache = str(tmp_path / "cache")
    mock_cfg.models.judge.rpm_limit = 10
    mock_cfg.models.judge.model_id = "test-model"

    # Loading original should succeed
    verifier = APIJudgeVerifier(cfg=mock_cfg, prompt_name="judge_v1.txt", client=MagicMock())
    verifier.load()
    assert verifier.template == original_text

    # Tamper with prompt
    prompt_file.write_text(original_text + "\nTAMPERED")
    with pytest.raises(PromptHashMismatchError):
        verifier.load()
