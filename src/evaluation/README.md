# Evaluation & Statistics (`src/evaluation/`)

This directory contains evaluation metric calculations, financial shadow cost estimators, and statistical significance testing.

## Modules

| Module | Purpose |
| :--- | :--- |
| `metrics.py` | Computes classification metrics on binary labels (1=hallucinated, 0=supported): Precision, Recall, F1, FNR, FPR, AUROC, latency summaries, and shadow cost per 1,000 verifications (Design.md §8.1). |
| `stats.py` | Statistical hypothesis testing: exact McNemar test for paired verifier decisions, percentile bootstrap resampling for 95% confidence intervals, and Cohen's kappa for annotators (Design.md §8.2). |

## Standards

- In this study, the positive class is always `label = 1` (hallucination). Precision and Recall reflect hallucination detection accuracy.
- False Negative Rate (FNR = hallucinations passed through unflagged) is the primary clinical safety metric (Design.md §8).

---
*Research prototype. Not for clinical use.*
