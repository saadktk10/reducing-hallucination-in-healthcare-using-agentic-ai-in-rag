# Cross-Experiment Analysis Summary

- **Experiment 1 Run ID**: `20260919-2151-bd5e507`
- **Experiment 2 Run ID**: `20261002-1129-cb0b4a7`

## Verifier Performance Ranking

### Experiment 1 Ranking (by F1 descending)

| Rank | Verifier | F1 [95% CI] | FNR |
| :--- | :--- | :--- | :--- |
| 1 | filter_b | 0.6667 [0.6667, 0.6667] | 0.0 |
| 2 | rouge | 0.6667 [0.6633, 0.67] | 0.005 |

### Experiment 2 Ranking (by F1 descending)

| Rank | Verifier | F1 [95% CI] | FNR |
| :--- | :--- | :--- | :--- |
| 1 | filter_b | 0.0861 [0.0392, 0.1395] | 0.0 |
| 2 | rouge | 0.0861 [0.0392, 0.1395] | 0.0 |

**Ranking Agreement Across Shared Verifiers**: YES
- Exp 1 order: filter_b, rouge
- Exp 2 order: filter_b, rouge

## Threshold Transfer Analysis (Filter B)

- **Frozen Dev Threshold**: `1.000000`
- **Exp 2 F1 with Frozen Dev Threshold**: `0.0861`
- **Exp 2 Oracle Best Threshold**: `0.022133` (diagnostic only, not reported as paper result)
- **Exp 2 Oracle Best F1**: `0.0909`
- **Transfer Cost Gap**: `0.0048`

## Qualitative Disagreements for Human Review

Exported 3 disagreement pairs to `results\cross\20260919-2151-bd5e507_20261002-1129-cb0b4a7\qualitative_disagreements.csv` for human clinical review.
