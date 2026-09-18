# Source Code Package (`src/`)

This directory contains the Python implementation for data preparation, verifiers, RAG pipeline, evaluation, and website export.

## Package Architecture

```text
src/
├── common/              # Shared foundational utilities (IO, caching, config, text, prompts, manifests)
├── filters/             # Hallucination verifiers (Filter A Gemini judge, Filter B DeBERTa NLI, ROUGE baseline)
├── evaluation/          # Metrics, cost computation, and statistical significance tests
├── data_prep.py         # MedHallu ingestion, stratification, and split construction (Phase 2)
├── pilot.py             # Phase 1 pilot validation checks (Gate G1)
├── rag.py               # PubMedQA FAISS indexing and Degraded Generator (Phase 4)
├── run_verifiers.py     # Main verification execution loop with latency measurement (Phases 3, 5, 7)
└── site_export.py       # Exporter collecting metrics into results/site/numbers_of_record.json
```

## Conventions

- **Modular and Decoupled**: Each verifier implements the `Verifier` protocol in `src/filters/base.py`.
- **Fail Loudly**: No silent fallbacks, unexpected type coercion, or hidden defaults (Design.md §2).
- **Strict Typing**: Code uses explicit type annotations and passes `ruff check .` with zero errors.

---
*Research prototype. Not for clinical use.*
