# Session Handover (`handover.md`)

*Rule R9.14: Every agent or researcher session MUST start by reading this file, and MUST conclude by updating it.*

---

## Current State

- **Date**: 2026-09-19
- **Session**: 3 (Completed)
- **Active Branch**: `main`
- **Current Phase**: Phase 0 ✅ Done, Phase 0b ✅ Done, Phase 1 🟡 Partial (Awaiting human spot-check annotation for Gate G1), Phase 2 ✅ Done, Phase 3 🟡 In Progress.
- **Test Status**: 101 passed in `pytest -q`, 0 lint errors in `ruff check .`.
- **Site Build**: `mkdocs build --strict` passing with 0 warnings.
- **Live Documentation**: [https://saadktk10.github.io/reducing-hallucination-in-healthcare-using-agentic-ai-in-rag/](https://saadktk10.github.io/reducing-hallucination-in-healthcare-using-agentic-ai-in-rag/)

---

## Accomplishments (Session 3)

1. **API Keys Verification & Model Pinning (Phase 0 Task 7 & 8)**:
   - Validated all three keys from `.env`: `HF_TOKEN`, `GROQ_API_KEY`, `GEMINI_API_KEY`.
   - Pinned generator model: `qwen/qwen3.8-27b` (Groq provider).
   - Pinned judge model: `gemini-3.6-flash` (Gemini OpenAI endpoint, 15 RPM limit, `max_tokens=500` to budget reasoning tokens).
   - Implemented `scripts/smoke_apis.py` and successfully executed smoke calls cached to `data/cache/judge_gemini.jsonl` and `data/cache/generator_groq.jsonl`.
2. **Experiment 1 Dataset Construction (Phase 2)**:
   - Executed `src/build_exp1_pairs.py`: generated canonical 250 questions (500 pairs) stratified by difficulty.
   - Built `data/exp1_medhallu/dev.jsonl` (100 pairs / 50 questions) and `data/exp1_medhallu/test.jsonl` (400 pairs / 200 questions).
   - Verified strict disjointness (0 question overlap) and exact 50/50 label balance.
   - Verified that Phase 2 dev set matches Phase 1 pilot provisional dev set byte-identically.
3. **Verifier Implementation (Phase 3)**:
   - **Baseline ROUGE-L (`src/filters/baseline_rouge.py`)**: Implemented `RougeLVerifier` supporting precision, recall, and fmeasure variants.
   - **Filter B NLI (`src/filters/filter_nli.py`)**: Implemented `NLIVerifier` (`nli-deberta-v3-small`). Resolved PyTorch 2.2 / transformers dependency constraints, automated HF authentication, dynamic `id2label` entailment index resolution (Rule R5.5), and sentence-level min-of-max chunk aggregation.
   - **Filter A API Judge (`src/filters/filter_api.py`)**: Implemented `APIJudgeVerifier` with token bucket rate limiter (15 RPM), tenacity exponential backoff, robust JSON extraction, single retry on parse failure (Rule R2.6), and disk caching (Rule R2.5).
4. **Evaluation & Verification Framework (Phases 3 & 8)**:
   - Implemented `src/evaluation/metrics.py`: Precision, Recall, F1, FNR, FPR, AUROC, latency summaries, and shadow cost per 1k verifications.
   - Implemented `src/evaluation/stats.py`: exact McNemar test, percentile bootstrap confidence intervals, and Cohen's kappa.
   - Implemented `src/run_verifiers.py`: unified multi-split runner. Successfully ran dev scoring for ROUGE-L (100 pairs) and smoke runs for Filter A and Filter B.
   - Implemented `src/tune_thresholds.py`: dev-only F1 maximization with lower FNR tie-breaking.
5. **Testing & Code Quality**:
   - Added 31 new tests: `test_baseline_rouge.py`, `test_filter_nli.py`, `test_filter_api.py`, `test_metrics.py`, `test_stats.py`.
   - Total test suite expanded from 70 to 101 tests (100% passing).
   - Clean lint status (`ruff check .` passes).

---

## Key Technical Decisions

- **Transformers & PyTorch Compatibility**: `transformers 5.x` requires `torch >= 2.5`. Because macOS environment has CPU-only PyTorch 2.2.2, constrained `transformers>=4.42,<5.0` and `sentence-transformers>=3.0,<4.0` in `pyproject.toml`.
- **HuggingFace HTTP Streaming**: Removed `hf-xet` to avoid hung file lock operations on macOS, allowing fast and stable model downloads via standard HTTP fallback.
- **Gemini 3.x Flash Reasoning Tokens**: Gemini 3.x Flash models include thinking tokens in completion budgets. Increased `max_tokens` from 64 to 500 and set `reasoning_effort="low"` in `APIJudgeVerifier` to prevent truncated/empty completions.
- **Automatic `.env` Ingestion**: Added `load_dotenv()` directly to `src/common/config.py:load_config()` so all tools and HuggingFace API clients seamlessly authenticate.

---

## Blockers & Pending External Actions

1. **Human Spot-Check Annotation (Gate G1)**:
   - Researchers must open `data/pilot/spotcheck_50.csv` and annotate the `supported_yes_no` column (`yes` or `no`) for the 50 rows.
   - Per Rule R1.5, the AI agent is forbidden from generating or suggesting labels for these 50 rows.
   - Once filled, run `python -m src.pilot_checks --config configs/config.yaml --step report` to trigger Gate G1 evaluation.
2. **Gate G1 Decision (Plan 1 vs Plan 2)**:
   - Once the pilot report is generated, confirm the plan in `configs/config.yaml`.

---

## Immediate Next Tasks

1. **Researchers annotate `data/pilot/spotcheck_50.csv`**:
   - Fill 50 rows in `supported_yes_no` column.
   - Run `python -m src.pilot_checks --config configs/config.yaml --step report`.
2. **Complete Dev Tuning (Phase 3d)**:
   - Run `python -m src.run_verifiers --config configs/config.yaml --split dev --verifier filter_b`.
   - Run `python -m src.run_verifiers --config configs/config.yaml --split dev --verifier filter_a`.
   - Run `python -m src.tune_thresholds --config configs/config.yaml` to freeze thresholds in `results/thresholds.json`.
3. **Freeze Judge Prompt**:
   - Verify `prompts/judge_v1.txt` and freeze its SHA-256 in `prompts/FROZEN.json` via `freeze_prompt("judge_v1.txt")`.

---
*Research prototype. Not for clinical use.*
