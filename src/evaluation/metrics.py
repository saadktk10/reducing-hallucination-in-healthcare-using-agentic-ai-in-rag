"""Evaluation metrics: Precision, Recall, F1, FNR, FPR, AUROC, latency, and shadow cost.

Phase 8 (Phase.md). Design.md §8.1.
All classification metrics treat Hallucinated (label=1) as the positive class (Agent.md §3).
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from typing import Any

import numpy as np
from sklearn.metrics import f1_score, precision_score, recall_score, roc_auc_score

logger = logging.getLogger(__name__)


def precision(y_true: Sequence[int], y_pred: Sequence[int]) -> float:
    """Precision for Hallucinated class (pos_label=1)."""
    return float(precision_score(y_true, y_pred, pos_label=1, zero_division=0))


def recall(y_true: Sequence[int], y_pred: Sequence[int]) -> float:
    """Recall for Hallucinated class (pos_label=1)."""
    return float(recall_score(y_true, y_pred, pos_label=1, zero_division=0))


def f1(y_true: Sequence[int], y_pred: Sequence[int]) -> float:
    """F1 score for Hallucinated class (pos_label=1)."""
    return float(f1_score(y_true, y_pred, pos_label=1, zero_division=0))


def fnr(y_true: Sequence[int], y_pred: Sequence[int]) -> float:
    """False Negative Rate: FN / (FN + TP).

    Proportion of true hallucinations that escaped undetected (falsely called Supported).
    """
    tp = sum(1 for yt, yp in zip(y_true, y_pred) if yt == 1 and yp == 1)
    fn = sum(1 for yt, yp in zip(y_true, y_pred) if yt == 1 and yp == 0)
    denom = fn + tp
    return float(fn / denom) if denom > 0 else 0.0


def fpr(y_true: Sequence[int], y_pred: Sequence[int]) -> float:
    """False Positive Rate: FP / (FP + TN).

    Proportion of truly supported answers falsely flagged as Hallucinated.
    """
    fp = sum(1 for yt, yp in zip(y_true, y_pred) if yt == 0 and yp == 1)
    tn = sum(1 for yt, yp in zip(y_true, y_pred) if yt == 0 and yp == 0)
    denom = fp + tn
    return float(fp / denom) if denom > 0 else 0.0


def auroc(y_true: Sequence[int], scores: Sequence[float]) -> float:
    """Area Under ROC Curve with Hallucinated as positive.

    Note: Input scores are support scores (higher = more supported).
    Inversion: 1 - score is the hallucination score (higher = more likely hallucinated).
    """
    if len(set(y_true)) < 2:
        logger.warning("AUROC undefined for single-class labels")
        return float("nan")
    # Invert so higher score corresponds to pos_label=1
    inverted_scores = [1.0 - float(s) for s in scores]
    return float(roc_auc_score(y_true, inverted_scores))


def latency_summary(latencies_ms: Sequence[float]) -> dict[str, Any]:
    """Compute summary statistics for latency measurements in milliseconds."""
    if not latencies_ms:
        return {"median_ms": 0.0, "p95_ms": 0.0, "mean_ms": 0.0, "n": 0}
    arr = np.array(latencies_ms, dtype=float)
    return {
        "median_ms": float(np.median(arr)),
        "p95_ms": float(np.percentile(arr, 95)),
        "mean_ms": float(np.mean(arr)),
        "n": len(arr),
    }


def shadow_cost_per_1k(
    avg_input_tokens: float,
    avg_output_tokens: float,
    price_per_1m_input: float,
    price_per_1m_output: float,
) -> float:
    """Compute shadow cost per 1,000 verifications in USD (Design.md §8.1).

    Formula: 1000 * (avg_in * in_price + avg_out * out_price) / 1_000_000
    """
    return float(
        1000.0
        * (
            avg_input_tokens * price_per_1m_input
            + avg_output_tokens * price_per_1m_output
        )
        / 1_000_000.0
    )
