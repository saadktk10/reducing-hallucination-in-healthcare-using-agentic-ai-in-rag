---
status: draft
---

# 2. Related Work

The problem of hallucination detection in clinical language modeling intersects three key research areas: factuality verification benchmarks, LLM-as-a-judge methodologies, and local Natural Language Inference (NLI) architectures.

## 2.1 Hallucination in Clinical Natural Language Processing

Biomedical question-answering datasets such as PubMedQA and MedQA have enabled rapid progress in medical foundation models. However, comprehensive evaluations reveal that generative models frequently produce plausible fabrications when synthesizing biomedical texts. Benchmarks like MedHallu (Chen et al., 2024) specifically curate pairs of clinical contexts, questions, supported ground truth answers, and synthetically mutated hallucinated answers across categories such as entity swapping, relation inversion, and methodological fabrication. In high-stakes clinical domains, evaluation protocols must prioritize the **False Negative Rate (FNR)** above standard precision, since an undetected clinical hallucination poses far greater hazard than an over-cautious false alarm.

## 2.2 LLM-as-a-Judge and Remote Verification

Prompting large foundation models to serve as evaluators has gained widespread adoption (Zheng et al., 2023). In medical RAG pipelines, external cloud judges such as GPT-4 or Gemini 1.5/2.5 Flash are frequently prompted with strict rubrics to assess evidence attribution. While external benchmarks report high macro-F1 scores (typically around 0.72) for frontier models, commercial API reliance imposes significant operational liabilities. Network-based inference exhibits substantial latency variance (frequently exceeding 1,200 ms per call), and recurring API costs accumulate rapidly in recursive agentic workflows. Furthermore, cloud processing of sensitive clinical narratives often runs counter to institutional governance policies.

## 2.3 Local Cross-Encoders and Edge NLI

Natural Language Inference (NLI) frames faithfulness verification as premise-hypothesis entailment: the retrieved context serves as the premise and each generated sentence serves as a hypothesis. Prior work demonstrates that cross-encoder architectures, where premise and hypothesis are concatenated and passed through joint bidirectional self-attention (e.g., DeBERTa), outperform bi-encoder dual encoders by capturing nuanced token-level cross-interactions. While large foundation cross-encoders offer strong performance, compact models like `cross-encoder/nli-deberta-v3-small` (44 million parameters) can execute efficiently on standard multi-core CPUs. Prior literature reports benchmark F1 scores around 0.64 for small NLI models on domain datasets. Our work examines whether this compact local architecture can match or exceed lexical baselines and provide dependable safety guarantees on real clinical RAG generation without hardware acceleration.
