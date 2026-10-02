---
status: draft
---

# 1. Introduction

Retrieval-Augmented Generation (RAG) has emerged as the premier architectural paradigm for deploying Large Language Models (LLMs) in high-stakes domains such as healthcare. By retrieving authoritative context—such as peer-reviewed clinical trials, biomedical abstracts, and clinical practice guidelines—before generating answers, RAG systems ground responses in verifiable medical evidence. Despite these architectural safeguards, generative LLMs continue to exhibit hallucinations: generating fluent, plausible assertions that contradict or find no support in the retrieved evidence. In healthcare applications, undetected hallucinations carry catastrophic clinical risks, ranging from incorrect dosing schedules to contraindicated drug recommendations.

To safeguard healthcare RAG pipelines, verification filters are positioned between generation and delivery to assess the faithfulness of an answer against its retrieved context. Contemporary enterprise architectures overwhelmingly rely on "LLM-as-a-judge" systems, calling commercial cloud models (e.g., GPT-4 or Gemini) via remote APIs. However, this cloud-centric approach poses severe trade-offs:

1. **Patient Data Privacy & Compliance:** Sending clinical queries and patient context to external commercial APIs raises substantial regulatory and confidentiality concerns under HIPAA and GDPR.
2. **Operational Latency:** Remote API calls introduce variable network latency, frequently exceeding 1,000 ms, disrupting real-time clinical workflows.
3. **Cumulative Cost:** Enterprise-scale agentic loops and high-volume clinical deployments incur compounding API query costs.

These challenges motivate the central hypothesis of this study: *A lightweight, specialized Natural Language Inference (NLI) cross-encoder running locally on consumer-grade CPU hardware can provide robust, zero-marginal-cost hallucination verification without compromising clinical safety.*

This paper makes the following empirical contributions:

- **Controlled Synthetic Benchmark Evaluation (Experiment 1):** We evaluate the local NLI cross-encoder (`cross-encoder/nli-deberta-v3-small`) against a lexical overlap baseline (ROUGE-L) on a 400-pair test split derived from the MedHallu benchmark ($n=400$, 200 questions).
- **Real-World RAG Pipeline Evaluation (Experiment 2):** We build an end-to-end medical RAG pipeline using a 1,790-chunk PubMedQA corpus and an open-weights generator (`qwen/qwen3.8-27b` via Groq at temperature 0). We generate 200 answers across normal and degraded retrieval conditions and establish ground truth through independent double-annotation by two human annotators (achieving Cohen's $\kappa = 1.0000$).
- **Cross-Experiment Domain Transfer Analysis:** We test whether verifier performance rankings and decision thresholds tuned on synthetic benchmark dev sets transfer effectively to real clinical RAG generation.
- **Hardware & Efficiency Profiling:** We provide comprehensive latency, memory, and cost benchmarks on standard laptop hardware (AMD Ryzen 5 7450U CPU, PyTorch CPU, 6 threads).

All experimental configurations, prompts, and thresholds were pre-registered and frozen, and all code and cached responses are released for complete reproducibility.
