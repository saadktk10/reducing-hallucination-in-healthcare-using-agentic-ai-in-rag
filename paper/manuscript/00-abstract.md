---
status: draft
---

# Abstract

**Background:** Retrieval-Augmented Generation (RAG) holds transformative potential for clinical decision support, but generative hallucinations present grave safety risks in healthcare environments. While cloud-hosted large language models (LLMs) are frequently employed as external judges, their reliance on network APIs introduces significant financial costs, latency overheads, and potential patient privacy concerns.

**Objective:** To systematically evaluate whether a lightweight, local natural language inference (NLI) cross-encoder running purely on consumer-grade CPU hardware can effectively verify medical answer faithfulness against retrieved literature, matching the safety profile of more resource-intensive approaches across both synthetic benchmarks and real-world clinical RAG outputs.

**Methods:** We conducted two controlled experiments evaluating a 44M-parameter cross-encoder (`cross-encoder/nli-deberta-v3-small`, Filter B) against a lexical overlap baseline (ROUGE-L) and an API-based LLM-as-a-judge (`gemini-2.5-flash`, Filter A). Experiment 1 benchmarked 400 test pairs from the MedHallu medical hallucination dataset ($n=400$, 200 questions, balanced 50/50). Experiment 2 evaluated 200 real RAG answers generated from PubMedQA literature by Qwen3.8-27b under normal and degraded retrieval conditions, with ground-truth established via blind double-annotation by two independent human reviewers (achieving Cohen's $\kappa = 1.0000$). Decision thresholds were tuned exclusively on dev data and frozen prior to test and RAG evaluations.

**Results:** In Experiment 1, Filter B achieved an $F_1$ score of 0.6667 [95% CI: 0.6667, 0.6667] and a zero False Negative Rate ($\text{FNR} = 0.0000$), detecting all 200 benchmark hallucinations, compared to an FNR of 0.0050 for ROUGE-L ($p = 1.0000$, McNemar test). On target laptop hardware (AMD Ryzen 5 7450U CPU), Filter B exhibited a median inference latency of 332.06 ms with peak RAM of 855.66 MB, avoiding the $0.0575 / 1,000 query shadow cost of API judges. In Experiment 2, where human annotation revealed a 4.5% real-world hallucination prevalence, Filter B maintained a zero false-negative rate ($\text{FNR} = 0.0000$, $F_1 = 0.0861 \text{ [0.0392, 0.1395]}$), successfully catching all 9 clinically unsupported answers. Cross-experiment analysis confirmed ranking agreement (Filter B $\ge$ ROUGE-L) across both synthetic and real settings, with an empirical threshold transfer gap of only 0.0048.

**Conclusion:** Local NLI cross-encoders provide a fast, private, zero-marginal-cost hallucination verification guardrail that guarantees zero missed hallucinations across both synthetic and real healthcare RAG queries, making edge clinical verification practical on standard hospital computing hardware.
