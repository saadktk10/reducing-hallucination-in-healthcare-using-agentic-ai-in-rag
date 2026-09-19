"""Tests for statistical methods — Phase 8.

Checks:
- McNemar test on known 2x2 contingency tables
- Bootstrap CI reproducibility with seed (Rule R4.1)
- Cohen's kappa agreement calculation
"""

from __future__ import annotations

import numpy as np

from src.evaluation.stats import annotator_kappa, bootstrap_ci, mcnemar_test


def test_mcnemar_known_table() -> None:
    # Table:
    # [[10, 5],
    #  [15, 20]]
    # b = 5, c = 15. Disagreements: 20 total.
    # Exact binomial p-value for 5 out of 20 with p=0.5:
    res = mcnemar_test([[10, 5], [15, 20]])
    assert "statistic" in res
    assert "pvalue" in res
    assert res["statistic"] == 5.0
    assert 0.0 < res["pvalue"] < 0.05  # Significant difference between the two models


def test_mcnemar_symmetric_table() -> None:
    # Table:
    # [[20, 10],
    #  [10, 20]]
    # b = c = 10 -> p-value = 1.0 (no significant difference)
    res = mcnemar_test([[20, 10], [10, 20]])
    assert res["statistic"] == 10.0
    assert np.isclose(res["pvalue"], 1.0)


def test_bootstrap_ci_reproducibility() -> None:
    data = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0]

    def mean_fn(sample):
        return sum(sample) / len(sample)

    est1, low1, high1 = bootstrap_ci(data, mean_fn, n_resamples=500, ci=0.95, seed=42)
    est2, low2, high2 = bootstrap_ci(data, mean_fn, n_resamples=500, ci=0.95, seed=42)

    assert est1 == est2 == 5.5
    assert low1 == low2
    assert high1 == high2
    assert low1 < 5.5 < high1


def test_annotator_kappa_perfect_and_chance() -> None:
    # Perfect agreement
    a1 = [0, 1, 0, 1, 0, 1]
    a2 = [0, 1, 0, 1, 0, 1]
    assert annotator_kappa(a1, a2) == 1.0

    # Total disagreement
    a3 = [1, 0, 1, 0, 1, 0]
    assert annotator_kappa(a1, a3) == -1.0
