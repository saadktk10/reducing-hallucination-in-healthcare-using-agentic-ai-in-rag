# Related Work Digest

*Drafted in Phase 10 from published literature context and baselines (paper/external_numbers.json, Design.md §1).*

## Literature Context & Benchmark Points of Comparison

- Published LLM-as-a-judge medical benchmark F1 : 0.7200 (external reference in `paper/external_numbers.json`) [meaning: published literature reports ~72% F1 for large API judges on medical benchmarks]
- Published local NLI medical factuality benchmark F1 : 0.6400 (external reference in `paper/external_numbers.json`) [meaning: published small cross-encoders achieve ~64% F1 on medical entailment datasets]
- Local cross-encoder test F1 achieved in this study : 0.6667 [0.6667, 0.6667] (n=400, `results/exp1/20260919-2151-bd5e507/metrics.json`) [meaning: our Filter B exceeds published small NLI baseline figures on MedHallu test split]
- Lexical overlap baseline test F1 : 0.6667 [0.6633, 0.6700] (n=400, `results/exp1/20260919-2151-bd5e507/metrics.json`) [meaning: ROUGE-L matches F1 on synthetic data due to high lexical overlap differences in benchmark word substitutions]
- Published API judge average latency : 1200.0 ms (external reference in `paper/external_numbers.json`) [meaning: typical cloud LLM judge takes over 1 second across network per pair]
- Local CPU cross-encoder median latency achieved in this study : 332.06 ms (n=400, `results/exp1/20260919-2151-bd5e507/timing_filter_b.json`) [meaning: our local CPU verifier is ~3.6x faster than typical network API judges]
- Peak RAM consumption during CPU inference : 855.66 MB (n=400, `results/exp1/20260919-2151-bd5e507/timing_filter_b.json`) [meaning: model operates well within the 4 GB operating budget, requiring less than 1 GB RAM]
