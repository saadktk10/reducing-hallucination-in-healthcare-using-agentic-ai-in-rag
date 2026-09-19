# Verifiers / Filters (`src/filters/`)

This directory contains the implementations of the hallucination verifiers compared in the study.

## Modules

| Module | Verifier | Description |
| :--- | :--- | :--- |
| `base.py` | `Verifier` (Protocol) | Abstract protocol defining `name`, `load() -> float`, `score(context, answer) -> VerifierResult`, and `score_batch()`. |
| `filter_api.py` | `APIJudgeVerifier` (Filter A) | Gemini Flash LLM judge with structured JSON output parsing, frozen prompt hash verification (`prompts/FROZEN.json`), token bucket rate limiter, tenacity retry, and single retry logic (Design.md §5, Rule R1.4, Rule R2.6). |
| `filter_nli.py` | `NLIVerifier` (Filter B) | Local cross-encoder `nli-deberta-v3-small`. Entailment probability scoring with token-aware chunking and sentence-level min-of-max aggregation (Design.md §6, Rule R5.5). |
| `baseline_rouge.py` | `RougeLVerifier` (Baseline) | Lexical overlap baseline computing ROUGE-L precision (default) between context and answer (Design.md §6.3). |

## Protocol & Conventions

All verifiers adhere to the `Verifier` protocol in `base.py`:
- `score` returns a `VerifierResult` where `score` is a float (higher = more supported / less hallucinated).
- In Filter B, the entailment label index is dynamically retrieved from `model.config.id2label` (never hardcoded, Rule R5.5).

---
*Research prototype. Not for clinical use.*
