# Session Handover (`handover.md`)

*Rule R9.14: Every agent or researcher session MUST start by reading this file, and MUST conclude by updating it.*

---

## Current State

- **Date**: 2026-09-20
- **Session**: 6 (Completed)
- **Active Branch**: `main`
- **Current Phase**: Phase 0 ✅ Done, Phase 0b ✅ Done, Phase 1 ✅ Done (Gate G1 resolved to Plan 2), Phase 2 ✅ Done, Phase 3 ✅ Done, Phase 4 ✅ Done, Phase 5 🟡 Partial (Filter B & ROUGE-L accuracy runs done on 400 test pairs, laptop CPU timing benchmarks done, shadow cost computed, Filter A rate limit flagged).
- **Test Status**: 107 passed in `pytest -q`, 0 lint errors in `ruff check .`.
- **Site Build**: `mkdocs build --strict` passing with 0 warnings.
- **Live Documentation**: [https://saadktk10.github.io/reducing-hallucination-in-healthcare-using-agentic-ai-in-rag/](https://saadktk10.github.io/reducing-hallucination-in-healthcare-using-agentic-ai-in-rag/)

---

## Accomplishments (Session 6)

1. **Standardized Timing Protocol Implemented (`src/timing.py`, `tests/test_timing.py`)**:
   - Implemented `measure_verifier_timing()` enforcing Rules §3: pre-run checklist (`--confirm`), separate model load timing and memory tracking, 10 warm-up pairs discarded, two repeat passes measuring latency with `time.perf_counter()` around inference only (batch size 1), peak RAM sampling via `psutil`, and strict assertion that no timing latency comes from cache hits (Rule R3.2).
   - Created `tests/test_timing.py` covering mock timing runs, metrics reporting, and cache hit violation detection (all 107 tests passing).
2. **Pricing Configuration & Shadow Cost Model (Phase 5c)**:
   - Added `PricingConfig` and `load_pricing()` to `src/common/config.py`.
   - Updated `configs/pricing.yaml` with Gemini Flash rates ($0.10/1M input tokens, $0.40/1M output tokens, `checked_on: "2026-09-20"`).
   - Computed shadow cost: `$0.0575` per 1,000 verifications, saved in `results/exp1/20260919-2151-bd5e507/metrics.json`.
3. **Phase 5a Accuracy Runs Executed for Baseline ROUGE-L & Filter B**:
   - Enhanced `src/run_verifiers.py` with dynamic run folder resolution (`results/exp1/<run_id>/`), standard prediction filenames (`predictions_<verifier>.jsonl`), manifest creation via `write_manifest()`, and automated classification metrics computation.
   - Evaluated Baseline ROUGE-L on all 400 test pairs: F1 = **0.6667**, Precision = 0.5013, Recall = 0.9950, FNR = 0.0050, FPR = 0.9900, AUROC = 0.4058.
   - Evaluated Filter B (`nli-deberta-v3-small`) on all 400 test pairs on CPU: F1 = **0.6667**, Precision = 0.5000, Recall = 1.0000, FNR = 0.0000, FPR = 1.0000, AUROC = 0.5492.
4. **Phase 5b Laptop Timing Benchmarks Executed**:
   - ROUGE-L benchmark on laptop CPU: Load time = 0.0001 s, Peak RAM = 355.4 MB, Warm-up = 10 discarded, Pass 1 p50 = 2.5 ms (p95 = 4.3 ms), Pass 2 p50 = 2.5 ms (p95 = 4.1 ms), **POOLED p50 = 2.5 ms (p95 = 4.3 ms)**.
   - Filter B benchmark on laptop CPU: Load time = 3.5990 s, Peak RAM = **855.7 MB** (well within the 4 GB limit of Rule R6.3), Warm-up = 10 discarded, Pass 1 p50 = 334.3 ms (p95 = 969.1 ms), Pass 2 p50 = 326.7 ms (p95 = 982.1 ms), **POOLED p50 = 332.1 ms (p95 = 978.0 ms)**.
   - Stored structured timing logs and per-pair latency CSVs in `results/exp1/20260919-2151-bd5e507/`.
5. **Living Documentation & Website Synchronized**:
   - `src/site_export.py` updated `results/site/numbers_of_record.json` with `timing.filter_b.median_ms = 332.1 ms` and `cost.filter_a.per_1k_usd = $0.0575`.
   - `mkdocs build --strict` verified in 0.55s with 0 warnings.
   - Updated `Phase.md`, `Architecture.md`, `src/README.md`, `tests/README.md`.

---

## Key Technical Findings & Critical Blocker

- **Filter A Free-Tier Quota Constraint (Rule R8.1 & Risk Register)**:
  - During test scoring, Google AI Studio returned `429 RESOURCE_EXHAUSTED` with violation:
    `quotaId: GenerateRequestsPerDayPerProjectPerModel-FreeTier`, `quotaValue: 20` for `gemini-3.6-flash`.
  - On Google AI Studio's Free Tier, `gemini-3.6-flash` is strictly capped at **20 requests per day**. Evaluating 400 test pairs would require 20 days on this free tier.
  - Per Rule R8.1 ("MUST stop and ask when a rule blocks progress, instead of working around it") and the Risk Register ("Model ID deprecated mid-study | Any | Stop, report, researchers decide; never auto-switch"), this is flagged for researcher decision.
- **Researcher Options for Filter A**:
  - **Option 1 (Recommended)**: Enable Google AI Studio Pay-as-you-go (Tier 1) on the project. This lifts the rate limit to 1,000 RPM. For 400 test pairs, the total cost will be approximately **$0.17** (17 cents) and will complete in ~3 minutes.
  - **Option 2**: Switch the judge model to an active production model with standard free-tier quotas (e.g., `gemini-3.8-flash` which has a 5 RPM free tier, or `gemini-3.5-flash-lite`), update `configs/config.yaml`, and re-freeze prompts if necessary.

---

## Immediate Next Tasks

1. **Researcher Decision on Filter A Quota**:
   - Choose Option 1 (enable AI Studio billing) or Option 2 (approve model ID switch).
   - Once resolved, run `python -m src.run_verifiers --split test --verifier filter_a` to complete the Filter A test evaluation.
2. **Phase 6: Two-Annotator Blind Labeling Preparation**:
   - Implement `src/annotation.py export` to generate blind annotation CSVs (`annotator_1.csv`, `annotator_2.csv`) and `annotation_guide.md` from the 200 RAG answers.

---
*Research prototype. Not for clinical use.*
