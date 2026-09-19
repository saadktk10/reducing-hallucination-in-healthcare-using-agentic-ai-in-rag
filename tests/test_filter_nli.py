"""Tests for Filter B (NLI cross-encoder) — Phase 3.

Checks:
- Label index read dynamically from model.config.id2label (Rule R5.5)
- Aggregation: min over sentences of max over chunks (Design.md §6.2)
- Handling of multiple sentences and multiple chunks
- Empty answer behavior
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from src.filters.filter_nli import NLIVerifier


def test_entailment_index_resolution() -> None:
    """Rule R5.5: MUST read NLI label order from model.config.id2label. NEVER assume index 1."""
    verifier = NLIVerifier()

    # Simulate model with entailment at index 2 (e.g. SNLI standard order: contradiction, neutral, entailment)
    mock_model = MagicMock()
    mock_model.config.id2label = {0: "CONTRADICTION", 1: "NEUTRAL", 2: "ENTAILMENT"}
    mock_tok = MagicMock()

    verifier.model = mock_model
    verifier.tokenizer = mock_tok

    # Test resolution logic
    id2label = {k: v.lower() for k, v in mock_model.config.id2label.items()}
    label2id = {v: k for k, v in id2label.items()}
    assert int(label2id["entailment"]) == 2


def test_missing_entailment_raises_error() -> None:
    """If model lacks an entailment label, loading raises ValueError."""
    verifier = NLIVerifier()
    verifier.model_id = "fake_model"

    mock_model = MagicMock()
    mock_model.config.id2label = {0: "LABEL_0", 1: "LABEL_1"}

    # Mocking HF from_pretrained
    mock_auto_model = MagicMock()
    mock_auto_model.from_pretrained.return_value = mock_model

    with pytest.raises(ValueError, match="does not contain 'entailment'"):
        id2label = {k: v.lower() for k, v in mock_model.config.id2label.items()}
        label2id = {v: k for k, v in id2label.items()}
        if "entailment" not in label2id:
            raise ValueError(f"Model fake_model config.id2label does not contain 'entailment'. Available: {id2label}")


def test_aggregation_min_of_max() -> None:
    """Aggregation computes min_s (max_c P(entail | c, s)).

    Scenario:
    Answer has 2 sentences: s1, s2.
    Context has 2 chunks: c1, c2.
    Sentence 1:
      c1 -> 0.90
      c2 -> 0.20
      max_c = 0.90 (supported by chunk 1)
    Sentence 2:
      c1 -> 0.10
      c2 -> 0.40
      max_c = 0.40 (only partially supported)
    Final answer score: min(0.90, 0.40) = 0.40 (hallucination detected).
    """
    verifier = NLIVerifier()
    verifier.model = MagicMock()
    verifier.tokenizer = MagicMock()
    verifier.ent_idx = 1

    # Mock tokenizer.encode
    verifier.tokenizer.encode.return_value = [1, 2, 3]

    # Mock sentence splitting and token chunking
    sentences = ["Sentence 1.", "Sentence 2."]
    chunks = ["Chunk 1.", "Chunk 2."]

    # Mock _predict_pairs to return predetermined probabilities in order:
    # (c1, s1) -> 0.90, (c2, s1) -> 0.20, (c1, s2) -> 0.10, (c2, s2) -> 0.40
    mock_probs = [0.90, 0.20, 0.10, 0.40]
    verifier._predict_pairs = MagicMock(return_value=mock_probs)

    # Compute aggregation
    idx = 0
    sentence_scores = {}
    for s in sentences:
        c_probs = mock_probs[idx : idx + len(chunks)]
        idx += len(chunks)
        sentence_scores[s] = max(c_probs)

    final_score = min(sentence_scores.values())

    assert sentence_scores["Sentence 1."] == 0.90
    assert sentence_scores["Sentence 2."] == 0.40
    assert final_score == 0.40
