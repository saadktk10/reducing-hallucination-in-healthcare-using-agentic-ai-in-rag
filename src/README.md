# Source Code Package (`src/`)

This directory contains the Python implementation for data preparation, verifiers, RAG pipeline, evaluation, and website export.

## Package Architecture

```text
src/
├── common/              # Shared foundational utilities (IO, caching, config, text, prompts, manifests)
├── filters/             # Hallucination verifiers (Filter A Gemini judge, Filter B DeBERTa NLI, ROUGE baseline)
├── evaluation/          # Metrics, cost computation, and statistical significance tests
├── pilot_checks.py      # Phase 1 pilot validation checks (Gate G1) ← implemented
├── build_exp1_pairs.py  # MedHallu ingestion, stratification, and split construction (Phase 2) ← implemented
├── build_index.py       # PubMedQA context chunking & FAISS indexing (Phase 4) ← implemented
├── generate_rag.py      # Degraded/normal RAG generation (Phase 4)
├── annotation.py        # Annotation template export, kappa, disagreements (Phase 6)
├── run_verifiers.py     # Main verification execution loop (Phases 3, 5, 7) ← implemented
├── timing.py            # Latency measurement protocol (Phase 5)
├── tune_thresholds.py   # Dev-only threshold optimization (Phase 3) ← implemented
├── evaluate.py          # Per-experiment tables and breakdowns (Phase 8)
├── cross_experiment.py  # Cross-experiment ranking check (Phase 9)
├── figures.py           # Paper figures generation (Phase 10)
└── site_export.py       # Exporter collecting metrics into results/site/numbers_of_record.json ← implemented
```

## Conventions

- **Modular and Decoupled**: Each verifier implements the `Verifier` protocol in `src/filters/base.py`.
- **Fail Loudly**: No silent fallbacks, unexpected type coercion, or hidden defaults (Design.md §2).
- **Strict Typing**: Code uses explicit type annotations and passes `ruff check .` with zero errors.

---
*Research prototype. Not for clinical use.*
