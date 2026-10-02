# Discussion Digest

*Drafted in Phase 10 from empirical findings and clinical safety analysis (Design.md §1, Rules.md §7).*

## Clinical Safety, Threshold Transfer & Imbalance Dynamics

- Real RAG hallucination class imbalance ratio : 95.5% supported vs 4.5% hallucinated (n=200, `results/exp2/20261002-1129-cb0b4a7/metrics.json`) [meaning: extreme positive class scarcity severely penalizes precision and F1 in real RAG deployments]
- Safety critical metric (False Negative Rate) achieved by Filter B : 0.0000 across both Exp 1 and Exp 2 (`results/exp1/20260919-2151-bd5e507/metrics.json`, `results/exp2/20261002-1129-cb0b4a7/metrics.json`) [meaning: no unsupported answer escaped detection, prioritizing patient safety above false alarm rates]
- Threshold transfer penalty from synthetic dev to real RAG : 0.0048 F1 gap (`results/cross/20260919-2151-bd5e507_20261002-1129-cb0b4a7/cross_summary.md`) [meaning: using the frozen benchmark threshold without retuning costs less than half a percentage point of F1 relative to an oracle threshold]
- Lexical overlap failure mode in Exp 1 : 2 hallucinations missed by ROUGE-L (FNR = 0.0050) (n=400, `results/exp1/20260919-2151-bd5e507/metrics.json`) [meaning: superficial token overlap failed where semantic contradiction occurred with shared vocabulary]
- Edge compute resource footprint : 855.66 MB peak RSS (n=400, `results/exp1/20260919-2151-bd5e507/timing_filter_b.json`) [meaning: local NLI runs entirely on consumer hospital laptops without GPU infrastructure, cloud dependencies, or data transmission]
- Divergence case studies identified for clinical review : 3 pairs (`results/cross/20260919-2151-bd5e507_20261002-1129-cb0b4a7/qualitative_disagreements.csv`) [meaning: exactly three borderline medical QA cases where lexical overlap and NLI classification diverged]
