# Evaluation Summary: EXP2

- **Run ID**: `20261002-1129-cb0b4a7`
- **Dataset**: `data\exp2_rag\pairs.jsonl` (n=200)
- **Verifiers Evaluated**: filter_b, rouge

## Main Classification Metrics

| Verifier | n | Parse Failures | Precision | Recall | F1 | 95% Bootstrap CI | FNR | FPR | AUROC |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| filter_b | 200 | 0 | 0.0450 | 1.0000 | 0.0861 | [0.0392, 0.1395] | 0.0000 | 1.0000 | 0.2199 |
| rouge | 200 | 0 | 0.0450 | 1.0000 | 0.0861 | [0.0392, 0.1395] | 0.0000 | 1.0000 | 0.8077 |

## Paired Significance Tests (McNemar Exact)

| Comparison | n | Both Correct | V1 Only | V2 Only | Both Incorrect | Statistic | p-value |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| filter_b_vs_rouge | 200 | 9 | 0 | 0 | 191 | 0.0 | 1.000000 |

## Stratified Breakdown: Retrieval Condition (Exp 2)

| Condition | Verifier | n | Precision | Recall | F1 | FNR | FPR |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| normal | filter_b | 100 | 0.0500 | 1.0000 | 0.0952 | 0.0000 | 1.0000 |
| normal | rouge | 100 | 0.0500 | 1.0000 | 0.0952 | 0.0000 | 1.0000 |
| degraded | filter_b | 100 | 0.0400 | 1.0000 | 0.0769 | 0.0000 | 1.0000 |
| degraded | rouge | 100 | 0.0400 | 1.0000 | 0.0769 | 0.0000 | 1.0000 |
