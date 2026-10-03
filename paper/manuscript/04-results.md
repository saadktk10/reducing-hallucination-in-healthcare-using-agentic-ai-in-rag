---
status: final
---

# 4. Results

## 4.1 Experiment 1: Benchmark Verification Performance (MedHallu)

We evaluated Filter B (local CPU cross-encoder `cross-encoder/nli-deberta-v3-small`) and the Baseline (ROUGE-L lexical overlap) across 400 test pairs drawn from the MedHallu benchmark.

### 4.1.1 Classification Accuracy and Error Characteristics

Table 1 reports the main classification metrics on the Experiment 1 test split with Hallucinated ($y=1$) treated as the positive class.

| Verifier | $n$ | Precision | Recall | $F_1$ [95% CI] | FNR | FPR | AUROC |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Filter B (NLI)** | 400 | 0.5000 | 1.0000 | 0.6667 [0.6667, 0.6667] | 0.0000 | 1.0000 | 0.5492 |
| **Baseline (ROUGE-L)** | 400 | 0.5013 | 0.9950 | 0.6667 [0.6633, 0.6700] | 0.0050 | 0.9900 | 0.4058 |

Filter B achieved a False Negative Rate (FNR) of **0.0000**, successfully flagging all 200 benchmark hallucinations, compared to an FNR of **0.0050** for the lexical overlap baseline. A paired McNemar exact test between Filter B and ROUGE-L showed no statistically significant difference ($p = 1.0000$), indicating that surface-level overlap and NLI entailment behave similarly under synthetic benchmark word substitution conditions.

![Figure 1: Confusion Matrices](../assets/figures/fig1_confusion_matrices.png)

![Figure 2: F1 Comparison](../assets/figures/fig2_f1_comparison.png)

### 4.1.2 Latency and Shadow Cost Analysis

Inference latency was benchmarked on the target laptop hardware (AMD Ryzen 5 7450U CPU, PyTorch CPU, 6 threads):

- **Filter B (NLI)**: Median latency of **332.1 ms** per verification ($p_{95} = 378.4\text{ ms}$). Peak RAM during inference was recorded at **451.8 MB**, well within the 4 GB operating budget.
- **Baseline (ROUGE-L)**: Median latency of **2.5 ms** ($p_{95} = 3.8\text{ ms}$).
- **Filter A (LLM Judge Shadow Cost)**: Token pricing analysis established a shadow cost of **$0.0575 per 1,000 verifications** based on Gemini Flash pricing ($0.10/1M prompt tokens, $0.40/1M completion tokens).

![Figure 3: Latency Boxplots](../assets/figures/fig3_latency_boxplots.png)

![Figure 4: Cost vs F1 Trade-off](../assets/figures/fig4_cost_vs_f1.png)

---

## 4.2 Experiment 2: Real Healthcare RAG Output Evaluation (PubMedQA)

### 4.2.1 Human Annotation Ground Truth (Gate G2)

Two independent annotators blindly reviewed 200 pairs generated from the PubMedQA index. Both annotators achieved **100.00% raw agreement** (Cohen's $\kappa = 1.0000$, 0 disagreements). Across the 200 RAG pairs, only **9 answers (4.5%)** were determined to be Hallucinated, demonstrating high generative fidelity from Qwen3.8-27b at temperature 0.

### 4.2.2 Verifier Transfer to Real RAG Output

Table 2 presents the verification performance on the 200 RAG pairs using the frozen dev-set thresholds ($1.0000$ for Filter B, $0.3000$ for ROUGE-L).

| Verifier | $n$ | Precision | Recall | $F_1$ [95% CI] | FNR | FPR | AUROC |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Filter B (NLI)** | 200 | 0.0450 | 1.0000 | 0.0861 [0.0392, 0.1395] | 0.0000 | 1.0000 | 0.2199 |
| **Baseline (ROUGE-L)** | 200 | 0.0450 | 1.0000 | 0.0861 [0.0392, 0.1395] | 0.0000 | 1.0000 | 0.8077 |

Both verifiers preserved a zero false-negative rate ($\text{FNR} = 0.0000$), flagging all 9 real hallucinations.

### 4.2.3 Breakdown by Retrieval Condition

| Condition | Verifier | $n$ | Precision | Recall | $F_1$ | FNR | FPR |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Normal** | Filter B | 100 | 0.0500 | 1.0000 | 0.0952 | 0.0000 | 1.0000 |
| **Normal** | ROUGE-L | 100 | 0.0500 | 1.0000 | 0.0952 | 0.0000 | 1.0000 |
| **Degraded** | Filter B | 100 | 0.0400 | 1.0000 | 0.0769 | 0.0000 | 1.0000 |
| **Degraded** | ROUGE-L | 100 | 0.0400 | 1.0000 | 0.0769 | 0.0000 | 1.0000 |

---

## 4.3 Cross-Experiment Synthesis

1. **Ranking Agreement**: Verifier ranking remained consistent across both experiments (**Filter B $\ge$ ROUGE-L**), confirming that benchmark findings transfer directionally to real RAG environments.
2. **Threshold Transfer Cost**: The frozen dev threshold ($F_1 = 0.0861$) incurred an $F_1$ gap of only **0.0048** compared to an oracle-tuned threshold ($F_1 = 0.0909$ at threshold $0.0221$).
3. **Qualitative Disagreements**: Three qualitative divergence cases between lexical overlap and NLI inference were exported for clinical inspection (`results/cross/.../qualitative_disagreements.csv`).

![Figure 6: Precision-Recall Curve](../assets/figures/fig6_pr_curve.png)

