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
| `test_website.py` | `hooks/*.py`, `src/site_export.py` | Snapshot table parsing, missing tile handling, tile pairs, and site export logic. |
| `test_pilot.py` | `src/pilot_checks.py` | Gate G1 decision logic, ROUGE-L AUROC hand-computed checks, spot-check CSV formatting, dev-set properties (Phase 1). |
| `test_split.py` | `src/data_prep.py` | Dev/test question ID disjointness and label balance (Phase 2). |
| `test_filter_nli.py` | `src/filters/filter_b.py` | Cross-encoder dynamic label indexing and min-of-max chunk aggregation (Phase 3). |
| `test_filter_api.py` | `src/filters/filter_a.py` | Gemini JSON fence parsing, single retry logic, and timing mode (Phase 3). |
| `test_metrics.py` | `src/evaluation/metrics.py` | Hand-computed metric tests (Precision, Recall, F1, FNR, shadow cost) (Phase 8). |
| `test_stats.py` | `src/evaluation/stats.py` | McNemar test matrix calculations and bootstrap confidence intervals (Phase 8). |
| `test_leakage.py` | `src/rag.py` | Assert zero question ID overlap between Experiment 1 and Experiment 2 (Phase 4). |

## Running Tests

```bash
# Run all tests
pytest -v

# Run quick tests with short output
pytest -q
```

---
*Research prototype. Not for clinical use.*
