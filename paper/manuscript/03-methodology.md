---
status: final
---

# 3. Methodology

We designed a two-stage empirical study comparing local CPU-based NLI cross-encoders against lexical overlap baselines and cloud API judges across both benchmark and live RAG conditions.

## 3.1 Verification Architectures

We evaluated three verification mechanisms under identical interfaces:

1. **Filter B (Local NLI Cross-Encoder):** Uses `cross-encoder/nli-deberta-v3-small` (44M parameters) deployed locally on CPU. Generated answers are segmented into sentences using `pysbd`. For each sentence $s_i$, the cross-encoder computes softmax probabilities over $[P(\text{contradiction}), P(\text{neutral}), P(\text{entailment})]$ using the retrieved context as premise. The sentence score is $1 - P(\text{entailment})$. The overall answer score is the maximum sentence score: $\max_i (1 - P(\text{entailment}_i))$. An answer is classified as Hallucinated ($y=1$) if the score exceeds threshold $\tau_B$.
2. **Baseline (Lexical Overlap):** Computes sentence-level ROUGE-L recall against the evidence context using `rouge-score`. The score is defined as $1 - \min_i \text{ROUGE-L}(s_i, \text{context})$. If the score exceeds $\tau_{\text{rouge}}$, the answer is flagged as Hallucinated.
3. **Filter A (API LLM Judge):** Prompts `gemini-3.6-flash` at temperature 0 via structured JSON output using a frozen rubric (`prompts/judge_v1.txt`). Evaluated via token consumption and shadow cost profiling ($0.10/1M prompt, $0.40/1M completion tokens).

## 3.2 Experiment 1: Synthetic Benchmark Evaluation (MedHallu)

From the pinned Hugging Face revision of MedHallu (`pqa_labeled`, revision `515060458a`), we sampled 250 clinical questions stratified across difficulty tiers (Easy, Medium, Hard). Each question provides both a supported Ground Truth answer and a synthetically mutated Hallucinated Answer, yielding 500 total evaluation pairs.

To prevent data leakage, splitting was performed strictly at the question level:
- **Dev Set:** 50 questions (100 pairs) used exclusively for tuning decision thresholds $\tau_B$ and $\tau_{\text{rouge}}$ to maximize $F_1$ with Hallucinated as the positive class.
- **Test Set:** 200 questions (400 pairs, 200 supported, 200 hallucinated) reserved for unbiased evaluation.

Decision thresholds were frozen in `results/thresholds.json` ($\tau_B = 1.000000$, $\tau_{\text{rouge}} = 0.300000$) prior to test evaluation and never retuned.

## 3.3 Experiment 2: Live Medical RAG Evaluation (PubMedQA)

To evaluate real-world generation, we constructed an end-to-end RAG system:
- **Corpus & Index:** 1,790 chunked passages (250 tokens, 30 token overlap) from PubMedQA abstracts indexed with `BAAI/bge-small-en-v1.5` embeddings into a flat CPU FAISS vector index (peak RAM: 451.8 MB).
- **Retrieval Conditions:** 100 questions evaluated under **Normal Retrieval** (top-3 chunks retrieved, 100% ground-truth document recall), and 100 questions evaluated under **Degraded Retrieval** (ground-truth document excluded, top-3 distractor chunks retrieved) to stress-test generator resilience.
- **Answer Generation:** Groq-hosted `qwen/qwen3.8-27b` executed at temperature 0 with frozen prompt `prompts/generator_v1.txt`.
- **Double-Blind Human Annotation (Gate G2):** Two independent clinical reviewers evaluated all 200 generated answers against their retrieved evidence using a standardized four-tier rubric (Supported, Partially Supported, Unsupported, Contradicted). Reviewers achieved **100.00% raw agreement** (Cohen's $\kappa = 1.0000$, 0 disagreements). Merged ground truth yielded 191 Supported (95.5%) and 9 Hallucinated (4.5%) answers.

## 3.4 Hardware and Profiling Setup

All local inference and timing benchmarks were conducted on a dedicated laptop workstation:
- **Processor:** AMD Ryzen 5 7450U CPU (6 physical cores, 12 threads)
- **Memory:** 8 GB DDR5 RAM
- **Software Stack:** Windows 11, Python 3.12.14, PyTorch 2.2 CPU-only build (`torch.set_num_threads(6)`)
- **Latency Protocol:** Ten warm-up pairs discarded; inference times recorded per pair with `time.perf_counter()` across two independent runs; median and 95th percentile ($p_{95}$) reported.
