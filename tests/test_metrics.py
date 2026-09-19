"""Tests for evaluation metrics — Phase 8.

Checks against hand-computed examples (Rule R5.3):
- Precision, Recall, F1 (pos_label=1)
- FNR, FPR
- AUROC with score inversion
- Latency summary (median, p95, mean)
- Shadow cost formula
"""

from __future__ import annotations

import math

from src.evaluation.metrics import (
    auroc,
    f1,
    fnr,
    fpr,
    latency_summary,
    precision,
    recall,
    shadow_cost_per_1k,
)


def test_hand_computed_binary_classification_metrics() -> None:
    """Check P, R, F1, FNR, FPR against hand-computed 2x2 confusion matrix."""
    # y_true: 0=Supported, 1=Hallucinated
    # Row 0: True 0, Pred 0 (TN)
    # Row 1: True 0, Pred 1 (FP)
    # Row 2: True 1, Pred 0 (FN)
    # Row 3: True 1, Pred 1 (TP)
    y_true = [0, 0, 1, 1]
    y_pred = [0, 1, 0, 1]

    # TP=1, FP=1, TN=1, FN=1
    assert precision(y_true, y_pred) == 0.5
    assert recall(y_true, y_pred) == 0.5
    assert f1(y_true, y_pred) == 0.5
    assert fnr(y_true, y_pred) == 0.5
    assert fpr(y_true, y_pred) == 0.5


def test_perfect_and_worst_classification() -> None:
    y_true = [1, 1, 0, 0]
    y_perfect = [1, 1, 0, 0]

    assert precision(y_true, y_perfect) == 1.0
    assert recall(y_true, y_perfect) == 1.0
    assert f1(y_true, y_perfect) == 1.0
    assert fnr(y_true, y_perfect) == 0.0
    assert fpr(y_true, y_perfect) == 0.0

    y_worst = [0, 0, 1, 1]
    assert precision(y_true, y_worst) == 0.0
    assert recall(y_true, y_worst) == 0.0
    assert f1(y_true, y_worst) == 0.0
    assert fnr(y_true, y_worst) == 1.0
    assert fpr(y_true, y_worst) == 1.0


def test_auroc_hand_computed() -> None:
    """AUROC with support scores (higher = more supported, so 1 - score is hallucination score)."""
    # Supported answers have high support scores: 0.9, 0.8
    # Hallucinated answers have low support scores: 0.2, 0.1
    y_true = [0, 0, 1, 1]
    support_scores = [0.9, 0.8, 0.2, 0.1]
    # Inverted (hallucination scores): [0.1, 0.2, 0.8, 0.9] -> perfect separation -> AUROC = 1.0
    assert auroc(y_true, support_scores) == 1.0

    # Inverted separation -> AUROC = 0.0
    reversed_scores = [0.1, 0.2, 0.8, 0.9]
    assert auroc(y_true, reversed_scores) == 0.0


def test_latency_summary_hand_computed() -> None:
    latencies = [10.0, 20.0, 30.0, 40.0, 50.0]
    summary = latency_summary(latencies)
    assert summary["n"] == 5
    assert summary["median_ms"] == 30.0
    assert summary["mean_ms"] == 30.0
    assert math.isclose(summary["p95_ms"], 48.0, rel_tol=1e-2)


def test_shadow_cost_hand_computed() -> None:
    # 100 prompt tokens, 10 completion tokens
    # $0.10 per 1M prompt tokens, $0.40 per 1M completion tokens
    # Total for 1 query: 100 * 0.10e-6 + 10 * 0.40e-6 = 1.4e-5 USD
    # For 1,000 queries: 1.4e-5 * 1000 = 0.014 USD
    cost = shadow_cost_per_1k(
        avg_input_tokens=100.0,
        avg_output_tokens=10.0,
        price_per_1m_input=0.10,
        price_per_1m_output=0.40,
    )
    assert math.isclose(cost, 0.014, rel_tol=1e-6)
