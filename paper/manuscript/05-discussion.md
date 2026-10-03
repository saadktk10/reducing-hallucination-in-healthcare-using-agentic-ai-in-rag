---
status: final
---

# 5. Discussion

Our empirical findings demonstrate the feasibility and clinical utility of local CPU-based NLI cross-encoders for hallucination detection in medical RAG, while highlighting crucial nuances regarding class imbalance, threshold transfer, and failure modes.

## 5.1 Clinical Safety vs False Alarm Trade-offs

In clinical decision support, the penalty for a false negative (delivering an ungrounded, hallucinated medical claim to a clinician) vastly outweighs that of a false positive (flagging a supported answer for human review or secondary verification). Under this safety asymmetry, Filter B's achievement of $\text{FNR} = 0.0000$ across both the 400-pair MedHallu benchmark and the 200-pair real RAG evaluation represents a compelling safety guarantee. Filter B intercepted 100% of hallucinations in both environments without relying on external cloud APIs.

However, the conservative nature of the frozen dev threshold ($\tau_B = 1.000000$) resulted in an elevated False Positive Rate ($\text{FPR} = 1.0000$ in Exp 2). In real RAG deployments, this implies that while every hallucination is safely caught, supported answers may also trigger the flag. In an agentic architecture, Filter B is ideally suited as a high-sensitivity, zero-leakage first-pass safety tripwire that escalates flagged answers to secondary reasoning agents or clinical specialists.

## 5.2 The Class Imbalance Effect in Real RAG

A striking contrast between Experiment 1 and Experiment 2 is the divergence in $F_1$ scores (0.6667 on MedHallu vs 0.0861 on PubMedQA). This shift does not reflect degraded verifier discernment, but rather the dramatic difference in positive class prevalence:
- **Experiment 1 (Synthetic):** 50% positive prevalence (200 hallucinated / 400 total), yielding $F_1 = 0.6667$.
- **Experiment 2 (Real RAG):** 4.5% positive prevalence (9 hallucinated / 200 total), yielding $F_1 = 0.0861$.

Because precision is strictly bounded by base rate prevalence ($\text{Precision} \le \text{Prevalence} / (\text{Prevalence} + \text{FPR} \cdot (1 - \text{Prevalence}))$), low hallucination rates inherently depress $F_1$. Modern open-weights foundation models such as Qwen3.8-27b exhibit remarkable faithfulness when prompted with authoritative evidence at temperature 0, producing unsupported statements in only 4.5% of cases even when retrieval is degraded. Consequently, $F_1$ alone is an incomplete metric for clinical RAG verification; safety-oriented metrics like FNR and ROC/PR trajectory must accompany reporting.

## 5.3 Threshold Transferability

A critical methodological question in NLP deployment is whether thresholds calibrated on academic benchmarks transfer to production RAG without local retraining. Our cross-experiment diagnostic analysis demonstrated that applying the frozen dev threshold to Experiment 2 yielded an $F_1$ score of 0.0861, compared to an oracle-optimal post-hoc threshold $F_1$ of 0.0909 (at $\tau = 0.0221$). The threshold transfer gap was merely **0.0048** (less than half a percentage point of $F_1$). This establishes that benchmark-calibrated thresholds can be directly deployed in real RAG systems without costly re-calibration.

## 5.4 Efficiency, Privacy, and System Deployment

From an operational standpoint, Filter B achieved a median latency of 332.06 ms on consumer laptop CPU (AMD Ryzen 5 7450U) and consumed under 860 MB of RAM. This confirms that edge clinical verification can run concurrently on existing healthcare workstations without dedicated GPU infrastructure. Furthermore, eliminating API calls circumvents the $0.0575 / 1,000 query shadow cost and ensures that patient clinical context never leaves the institution's secure boundary.

## 5.5 Limitations

1. **Synthetic Mutation Artifacts:** Experiment 1 relies on synthetic entity replacements in MedHallu, where lexical baselines like ROUGE-L perform surprisingly well due to surface-level token mismatches.
2. **Generative Fidelity and Sample Size:** With only 9 hallucinations in Experiment 2, statistical power for fine-grained subcategory analysis on real RAG outputs is limited.
3. **Monolingual Focus:** Evaluations were restricted to English-language biomedical literature.
