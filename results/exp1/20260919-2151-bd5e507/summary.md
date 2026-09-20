# Evaluation Summary: EXP1

- **Run ID**: `20260919-2151-bd5e507`
- **Dataset**: `data\exp1_medhallu\test.jsonl` (n=400)
- **Verifiers Evaluated**: filter_b, rouge

## Main Classification Metrics

| Verifier | n | Parse Failures | Precision | Recall | F1 | 95% Bootstrap CI | FNR | FPR | AUROC |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| filter_b | 400 | 0 | 0.5000 | 1.0000 | 0.6667 | [0.6667, 0.6667] | 0.0000 | 1.0000 | 0.5492 |
| rouge | 400 | 0 | 0.5013 | 0.9950 | 0.6667 | [0.6633, 0.6700] | 0.0050 | 0.9900 | 0.4058 |

## Paired Significance Tests (McNemar Exact)

| Comparison | n | Both Correct | V1 Only | V2 Only | Both Incorrect | Statistic | p-value |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| filter_b_vs_rouge | 400 | 199 | 1 | 2 | 198 | 1.0 | 1.000000 |

## Latency and System Efficiency

| Verifier | Pooled Median (ms) | Pooled p95 (ms) | Model Load (s) | Peak RSS (MB) |
| :--- | :--- | :--- | :--- | :--- |
| filter_b | 332.06 | 977.95 | 3.599 | 855.66 |
| rouge | 2.5 | 4.27 | 0.0001 | 355.38 |

## Stratified Breakdown: Difficulty (Exp 1)

| Difficulty | Verifier | n | Precision | Recall | F1 | FNR | FPR |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| easy | filter_b | 108 | 0.5000 | 1.0000 | 0.6667 | 0.0000 | 1.0000 |
| easy | rouge | 108 | 0.5000 | 1.0000 | 0.6667 | 0.0000 | 1.0000 |
| hard | filter_b | 160 | 0.5000 | 1.0000 | 0.6667 | 0.0000 | 1.0000 |
| hard | rouge | 160 | 0.5032 | 0.9875 | 0.6667 | 0.0125 | 0.9750 |
| medium | filter_b | 132 | 0.5000 | 1.0000 | 0.6667 | 0.0000 | 1.0000 |
| medium | rouge | 132 | 0.5000 | 1.0000 | 0.6667 | 0.0000 | 1.0000 |

## Stratified Breakdown: Hallucination Category (Exp 1)

| Category | Verifier | n | Precision | Recall | F1 | FNR | FPR |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| Incomplete Information | filter_b | 68 | 0.5000 | 1.0000 | 0.6667 | 0.0000 | 1.0000 |
| Incomplete Information | rouge | 68 | 0.5075 | 1.0000 | 0.6733 | 0.0000 | 0.9706 |
| Mechanism and Pathway Misattribution | filter_b | 6 | 0.5000 | 1.0000 | 0.6667 | 0.0000 | 1.0000 |
| Mechanism and Pathway Misattribution | rouge | 6 | 0.5000 | 1.0000 | 0.6667 | 0.0000 | 1.0000 |
| Methodological and Evidence Fabrication | filter_b | 2 | 0.5000 | 1.0000 | 0.6667 | 0.0000 | 1.0000 |
| Methodological and Evidence Fabrication | rouge | 2 | 0.5000 | 1.0000 | 0.6667 | 0.0000 | 1.0000 |
| Misinterpretation of #Question# | filter_b | 324 | 0.5000 | 1.0000 | 0.6667 | 0.0000 | 1.0000 |
| Misinterpretation of #Question# | rouge | 324 | 0.5000 | 0.9938 | 0.6653 | 0.0062 | 0.9938 |
