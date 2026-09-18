# Verifiers / Filters (`src/filters/`)

This directory contains the implementations of the hallucination verifiers compared in the study.

## Modules

| Module | Verifier | Description |
| :--- | :--- | :--- |
| `base.py` | `Verifier` (Protocol) | Abstract protocol defining `name`, `load() -> float`, `score(context, answer) -> VerifierResult`, and `score_batch()`. |
| `filter_a.py` | Filter A (API Judge) | Gemini Flash LLM judge with structured JSON output parsing and single retry logic (Rule R5.1). |
| `filter_b.py` | Filter B (NLI Large) | Local cross-encoder `deberta-v3-large` fine-tuned on NLI. Entailment probability scoring with sentence-level min-of-max aggregation (Rule R5.5). |
| `filter_b_base.py` | Filter B Base (NLI Base) | Lightweight `deberta-v3-base` NLI comparison model for resource-constrained edge deployments. |
| `rouge.py` | ROUGE Baseline | Lexical overlap baseline computing ROUGE-L F1 between context and answer. |

## Protocol & Conventions

All verifiers adhere to the `Verifier` protocol in `base.py`:
- `score` returns a `VerifierResult` where `score` is a float (higher = more supported / less hallucinated).
- In Filter B, the entailment label index is dynamically retrieved from `model.config.id2label` (never hardcoded, Rule R5.5).

---
*Research prototype. Not for clinical use.*
