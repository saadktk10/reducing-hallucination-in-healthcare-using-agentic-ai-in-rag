# Introduction Digest

*Drafted in Phase 10 from problem formulation and study motivation (Architecture.md §1, Design.md §1).*

## Motivation & Background Facts

- Benchmark hallucination dataset explored : MedHallu `pqa_labeled` (`configs/config.yaml`, revision `515060458a945c633debc6fd5baac7764416b724`) [meaning: study grounds its benchmark on standard MedHallu medical QA subset]
- Pilot ground truth unsupported rate in MedHallu : 46.0% (n=50, `results/pilot/metrics.json`) [meaning: 46% of sampled benchmark rows showed context-evidence inconsistencies during human audit, leading to Plan 2 adoption]
- ROUGE-L lexical baseline AUROC on pilot sample : 0.4894 (n=100, `results/pilot/metrics.json`) [meaning: simple lexical overlap fails to discriminate hallucinations better than random guessing on benchmark pairs]
- Local CPU verifier model explored : `cross-encoder/nli-deberta-v3-small` (`configs/config.yaml`) [meaning: lightweight 44M parameter cross-encoder running purely on CPU]
- Generative model deployed for healthcare RAG : `qwen/qwen3.8-27b` via Groq at temperature 0 (`configs/config.yaml`) [meaning: state-of-the-art open-weights model used to generate medical answers]
- Generator and judge provider separation : Groq (generator) vs Google Gemini (judge) (`Rules.md` R2.3) [meaning: avoids self-evaluation bias by using different model families for generation and judging]
- Local hardware deployment target : AMD Ryzen 5 7450U CPU, 8 GB RAM (`Architecture.md` §10) [meaning: designed to operate locally on standard clinical workstation laptops without discrete GPUs]
