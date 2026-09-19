"""Statistical tests: McNemar test, Bootstrap Confidence Intervals, and Cohen's Kappa.

Phase 8 (Phase.md). Design.md §8.2.
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Sequence
from typing import Any

import numpy as np
from sklearn.metrics import cohen_kappa_score
from statsmodels.stats.contingency_tables import mcnemar

logger = logging.getLogger(__name__)


def mcnemar_test(table: Sequence[Sequence[int]] | np.ndarray) -> dict[str, float]:
    """Perform McNemar's exact test on a 2x2 contingency table (Design.md §8.2).

    Table format:
    [[both_correct, verifierA_only],
     [verifierB_only, both_incorrect]]

    Returns:
        Dict with "statistic" and "pvalue".
    """
    arr = np.asarray(table)
    if arr.shape != (2, 2):
        raise ValueError(f"McNemar table must be 2x2, got shape {arr.shape}")

    res = mcnemar(arr, exact=True)
    return {
        "statistic": float(res.statistic),
        "pvalue": float(res.pvalue),
    }


def bootstrap_ci(
    items: Sequence[Any],
    metric_fn: Callable[[Sequence[Any]], float],
    n_resamples: int = 1000,
    ci: float = 0.95,
    seed: int = 42,
) -> tuple[float, float, float]:
    """Compute percentile bootstrap confidence intervals.

    Args:
        items: List of units to resample (pairs or questions).
        metric_fn: Function taking a sample of items and returning a scalar float metric.
        n_resamples: Number of bootstrap iterations (default: 1000).
        ci: Confidence level (default: 0.95).
        seed: Random seed for reproducibility (Rule R4.1).

    Returns:
        Tuple of (point_estimate, ci_lower, ci_upper).
    """
    if not items:
        return 0.0, 0.0, 0.0

    point_estimate = float(metric_fn(items))
    rng = np.random.default_rng(seed)
    n = len(items)

    indices = np.arange(n)
    boot_estimates: list[float] = []

    for _ in range(n_resamples):
        sample_idx = rng.choice(indices, size=n, replace=True)
        sample = [items[i] for i in sample_idx]
        val = metric_fn(sample)
        boot_estimates.append(float(val))

    alpha = 1.0 - ci
    lower_pct = (alpha / 2.0) * 100.0
    upper_pct = (1.0 - alpha / 2.0) * 100.0

    ci_lower = float(np.percentile(boot_estimates, lower_pct))
    ci_upper = float(np.percentile(boot_estimates, upper_pct))

    return point_estimate, ci_lower, ci_upper


def annotator_kappa(
    annotator1: Sequence[int],
    annotator2: Sequence[int],
) -> float:
    """Compute Cohen's kappa for inter-annotator agreement (Design.md §8.2)."""
    if len(annotator1) != len(annotator2):
        raise ValueError("Annotator label lists must have identical lengths")
    return float(cohen_kappa_score(annotator1, annotator2))
