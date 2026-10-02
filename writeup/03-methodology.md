# Methodology Digest

*Drafted in Phase 10 from study design, data collection, and experimental specifications (Design.md §2-§8, Architecture.md §3-§7).*

## Experimental Setup & Architecture

- Experiment 1 total questions sampled : 250 questions (`configs/config.yaml`, `data/exp1_medhallu/split_summary.json`) [meaning: 250 distinct medical questions drawn from MedHallu]
- Experiment 1 total evaluation pairs : 500 pairs (`data/exp1_medhallu/split_summary.json`) [meaning: each question yields 1 supported and 1 hallucinated pair, ensuring exact 50/50 balance]
- Experiment 1 split stratification : 100 dev pairs (50 questions), 400 test pairs (200 questions) (`data/exp1_medhallu/split_summary.json`) [meaning: splits separated by question to eliminate data leakage across dev and test]
- Experiment 2 PubMedQA retrieval corpus size : 1,790 chunks (`data/exp2_rag/corpus_chunks.jsonl`) [meaning: abstract corpus chunked into 250-token segments with 30-token overlap]
- Embedding model for FAISS vector index : `BAAI/bge-small-en-v1.5` (`configs/config.yaml`) [meaning: 384-dimensional dense semantic representations computed locally on CPU]
- FAISS vector index peak RAM usage : 451.8 MB (`data/exp2_rag/index_summary.json`) [meaning: retrieval index easily fits within laptop memory constraints]
- Normal retrieval top-k hit rate : 100.0% (`data/exp2_rag/index_summary.json`) [meaning: target document ranked in top 3 retrieved chunks for all 100 normal questions]
- Degraded retrieval condition formulation : exclude ground-truth document, retrieve top-3 distractor chunks (`configs/config.yaml`) [meaning: simulates noisy clinical retrieval to stress-test generator hallucination resistance]
- Human annotation scale and design : 200 pairs blindly reviewed by 2 independent annotators (`data/exp2_rag/annotation/annotation_guide.md`) [meaning: 100 normal and 100 degraded RAG answers labeled for clinical hallucination]
- Inter-annotator agreement (Cohen's Kappa) : 1.0000 (n=200, `results/exp2/20261002-1129-cb0b4a7/metrics.json`) [meaning: 100.00% raw agreement across all 200 pairs, 0 disagreements to arbitrate]
- Frozen Filter B decision threshold : 1.000000 (`results/thresholds.json`) [meaning: dev-tuned threshold frozen prior to test and RAG evaluation per Rule R1.3]
- Frozen Baseline ROUGE-L decision threshold : 0.300000 (`results/thresholds.json`) [meaning: dev-tuned ROUGE threshold frozen per Rule R1.3]
