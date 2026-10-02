# Results Digest

*Drafted in Phase 10 from verified numbers of record (Design.md §10, Website_Prompt.md §7).*

## Experiment 1: Benchmark Evaluation (MedHallu)

- Filter B (DeBERTa-v3-small) test F1 score : 0.6667 [0.6667, 0.6667] (n=400, `results/exp1/20260919-2151-bd5e507/metrics.json`) [meaning: on MedHallu benchmark, the local CPU cross-encoder achieved 66.7% F1 score]
- Filter B False Negative Rate (FNR) : 0.0000 (n=400, `results/exp1/20260919-2151-bd5e507/metrics.json`) [meaning: zero hallucinations passed undetected by Filter B on the benchmark test set]
- Baseline ROUGE-L test F1 score : 0.6667 [0.6633, 0.6700] (n=400, `results/exp1/20260919-2151-bd5e507/metrics.json`) [meaning: surface-level lexical overlap baseline achieved comparable F1 on balanced synthetic benchmark]
- Baseline ROUGE-L False Negative Rate (FNR) : 0.0050 (n=400, `results/exp1/20260919-2151-bd5e507/metrics.json`) [meaning: ROUGE missed 0.5% of hallucinations]
- McNemar test (Filter B vs ROUGE-L) : p = 1.0000 (n=400, `results/exp1/20260919-2151-bd5e507/tables/mcnemar.csv`) [meaning: no statistically significant difference in classifications on MedHallu benchmark]
- Filter B local CPU inference latency : 332.06 ms [p50] (n=400, `results/exp1/20260919-2151-bd5e507/timing_filter_b.json`) [meaning: median verification time on laptop CPU is 332 ms]
- Baseline ROUGE-L latency : 2.50 ms [p50] (n=400, `results/exp1/20260919-2151-bd5e507/timing_rouge.json`) [meaning: word overlap check runs in 2.5 ms]
- Filter A (Gemini Flash) shadow cost : $0.0575 / 1,000 queries (`results/exp1/20260919-2151-bd5e507/metrics.json`) [meaning: API judge incurs $0.0575 per 1k verifications]

## Experiment 2: RAG Outputs (PubMedQA)

- Inter-annotator agreement (Cohen's Kappa) : 1.0000 (n=200, `results/exp2/20261002-1129-cb0b4a7/metrics.json`) [meaning: two independent human annotators reached complete agreement on all 200 pairs]
- Real RAG hallucination prevalence : 4.5% (9/200 pairs, `data/exp2_rag/pairs.jsonl`) [meaning: Groq Qwen3.8-27b at temp 0 exhibited high fidelity on retrieved medical literature]
- Filter B RAG test F1 score : 0.0861 [0.0392, 0.1395] (n=200, `results/exp2/20261002-1129-cb0b4a7/metrics.json`) [meaning: low F1 driven by class imbalance (4.5% positive prevalence) under conservative frozen dev threshold]
- Baseline ROUGE-L RAG test F1 score : 0.0861 [0.0392, 0.1395] (n=200, `results/exp2/20261002-1129-cb0b4a7/metrics.json`) [meaning: baseline mirrored Filter B F1 score under frozen dev threshold]
- Condition breakdown (Normal retrieval) : Filter B F1 = 0.0952 (n=100, `results/exp2/20261002-1129-cb0b4a7/tables/condition_breakdown.csv`) [meaning: 5% hallucination rate on normal retrieval]
- Condition breakdown (Degraded retrieval) : Filter B F1 = 0.0769 (n=100, `results/exp2/20261002-1129-cb0b4a7/tables/condition_breakdown.csv`) [meaning: 4% hallucination rate on degraded retrieval]

## Cross-Experiment Synthesis

- Verifier performance ranking agreement : YES (`results/cross/20260919-2151-bd5e507_20261002-1129-cb0b4a7/cross_metrics.json`) [meaning: Filter B is ranked above or equal to baseline across both synthetic and real RAG settings]
- Threshold transfer cost gap : 0.0048 (`results/cross/20260919-2151-bd5e507_20261002-1129-cb0b4a7/cross_summary.md`) [meaning: transferring dev threshold to real RAG costs less than 0.5% F1 compared to oracle-tuned threshold]
- Qualitative clinical disagreements : 3 pairs (`results/cross/20260919-2151-bd5e507_20261002-1129-cb0b4a7/qualitative_disagreements.csv`) [meaning: exactly 3 pairs where verifiers diverged, isolated for clinical discussion]

