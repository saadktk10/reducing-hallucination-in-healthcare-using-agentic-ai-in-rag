# Prompts (`prompts/`)

This directory contains versioned prompts for LLM verification (Filter A) and generator queries.

## Files & Directories

| Path | Purpose |
| :--- | :--- |
| `judge_v1.txt` | Frozen LLM-as-a-judge evaluation prompt (Filter A). Evaluates evidence support and returns JSON verdict (`SUPPORTED` vs `UNSUPPORTED`). |
| `generator_v1.txt` | Frozen RAG answer generator prompt (Groq Qwen 3.8-27b). Prompts the model to synthesize 2–4 sentence answers strictly grounded in provided scientific context. |
| `FROZEN.json` | Hash registry mapping frozen prompt filenames to their SHA-256 digests (enforced by Rule R1.4). |
| `drafts/` | Unfrozen, experimental prompt templates under development. |

## Freezing & Hash Verification Protocol (Rule R4.4)

Prompts used for evaluation must be frozen before experimental execution:

1. **Freezing**: Compute SHA-256 hash and record in `FROZEN.json` via `src.common.prompts.freeze_prompt()`.
2. **Runtime Verification**: `verify_frozen()` ensures that the byte content on disk exactly matches the registered hash in `FROZEN.json`.
3. **Tampering Protection**: Modifying any frozen prompt without creating a new version (e.g., `judge_v2.txt`) raises `PromptHashMismatchError` and halts execution.
4. **Template Filling**: Always uses exact string substitution (`str.replace`), never `str.format()`, to avoid escaping JSON syntax braces (`{}`).

---
*Research prototype. Not for clinical use.*
