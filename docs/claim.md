# Central Claim and Research Questions

## The One Claim

> A lightweight local NLI cross-encoder (`cross-encoder/nli-deberta-v3-small`) running on consumer laptop CPU achieves a zero false-negative rate ($\text{FNR} = 0.0000$) across both synthetic benchmark evaluations (MedHallu, $n=400$) and real medical RAG generations (PubMedQA, $n=200$), maintaining performance parity with frozen thresholds at 332 ms median latency and zero marginal API cost, with verifier ranking agreement confirmed across both benchmark and real-world evaluation settings.

---

## Research Questions

The following research questions guide this study (Methodology C, section 12):

1. **RQ1 (Detection Accuracy & Safety):** Can a local NLI cross-encoder match or exceed an API-based LLM judge at detecting hallucinated medical answers, measured by F1 and FNR on the MedHallu benchmark?
2. **RQ2 (Domain & Generation Transfer):** Does the ranking of verifiers observed on the synthetic benchmark transfer to real RAG-generated output evaluated against independent human ground truth?
3. **RQ3 (Latency & Cost Trade-offs):** What are the latency, memory, and operational cost trade-offs between local CPU verification and API-based LLM judges in a healthcare agentic RAG pipeline?
4. **RQ4 (Error Stratification & Failure Modes):** Which hallucination categories (incomplete information, misinterpretation, fabrication) and retrieval conditions (normal vs degraded context) are most sensitive to verifier choice?
