# Evaluation & Statistics (`src/evaluation/`)

This directory contains evaluation metric calculations, financial shadow cost estimators, and statistical significance testing.

## Modules

| Module | Purpose |
| :--- | :--- |
| `metrics.py` | Computes classification metrics on binary labels (1=hallucinated, 0=supported): Precision, Recall, F1, False Negative Rate (FNR), False Positive Rate (FPR). |
| `cost.py` | Estimates the shadow dollar cost of Filter A API calls per 1,000 verifications based on `configs/pricing.yaml` and recorded token usage. |
| `stats.py` | Statistical hypothesis testing: exact McNemar test for paired verifier decisions and stratified bootstrap resampling for 95% confidence intervals. |

## Standards

- In this study, the positive class is always `label = 1` (hallucination). Precision and Recall reflect hallucination detection accuracy.
- False Negative Rate (FNR = hallucinations passed through unflagged) is the primary clinical safety metric (Design.md §8).

---
*Research prototype. Not for clinical use.*
