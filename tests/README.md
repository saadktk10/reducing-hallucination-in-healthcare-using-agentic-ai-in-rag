# Test Suite (`tests/`)

This directory contains automated unit, integration, and regression tests executed by `pytest`.

## Test Modules

| Test File | Target | Scope |
| :--- | :--- | :--- |
| `test_config.py` | `src/common/config.py` | Loading, validation, default parameters, and error handling for bad configs. |
| `test_io.py` | `src/common/io.py` | Pydantic schema validation (`Pair`, `Chunk`, `VerifierResult`, `CacheRecord`) and JSONL reading/writing. |
| `test_cache.py` | `src/common/cache.py` | SHA-256 key determinism, cache hit/miss behavior, and JSONL persistence. |
| `test_text.py` | `src/common/text.py` | Sentence splitting, token-aware sliding window chunking with overlap, and question normalization. |
| `test_prompts.py` | `src/common/prompts.py` | Template loading, hash freezing, and tampering detection against `prompts/FROZEN.json`. |
| `test_manifest.py` | `src/common/manifest.py` | Run ID timestamp format and machine environment metadata capture. |
| `test_website.py` | `hooks/*.py`, `src/site_export.py` | Snapshot table parsing, missing tile handling, populated tiles, tile pairs, and site export logic. |
| `test_pilot.py` | `src/pilot_checks.py` | Gate G1 decision logic, ROUGE-L AUROC hand-computed checks, spot-check CSV formatting, dev-set properties (Phase 1). |
| `test_split.py` | `src/build_exp1_pairs.py` | Dev/test question ID disjointness, label balance, stratification, and disk artifact validation (Phase 2). |
| `test_baseline_rouge.py` | `src/filters/baseline_rouge.py` | Baseline ROUGE-L precision/recall/fmeasure on toy pairs and protocol conformance (Phase 3a). |
| `test_filter_nli.py` | `src/filters/filter_nli.py` | Cross-encoder dynamic label indexing, missing label error, and min-of-max aggregation (Phase 3b). |
| `test_filter_api.py` | `src/filters/filter_api.py` | Gemini JSON fence parsing, single retry logic, double parse failure, frozen prompt hash verification, and timing mode (Phase 3c). |
| `test_metrics.py` | `src/evaluation/metrics.py` | Hand-computed metric tests (Precision, Recall, F1, FNR, FPR, AUROC, shadow cost) (Phase 8). |
| `test_stats.py` | `src/evaluation/stats.py` | McNemar test matrix calculations, bootstrap confidence intervals, and Cohen's kappa (Phase 8). |
| `test_timing.py` | `src/timing.py` | Standardized timing benchmark protocol, warm-up discard, repeat passes, cache hit assertions (Phase 5b). |
| `test_leakage.py` | `src/build_index.py`, `src/generate_rag.py` | Assert zero question ID overlap between Experiment 1 and Experiment 2 (Phase 4). |

## Running Tests

```bash
# Run all tests
pytest -v

# Run quick tests with short output
pytest -q
```

---
*Research prototype. Not for clinical use.*
