# Prompts (`prompts/`)

This directory contains versioned prompts for LLM verification (Filter A) and generator queries.

## Files & Directories

| Path | Purpose |
| :--- | :--- |
| `*.txt` | Active frozen prompt templates (e.g. `judge_v1.txt`). Templates use placeholder tags like `{context}` and `{answer}`. |
| `FROZEN.json` | Hash registry mapping prompt filenames to their SHA-256 digests. |
| `drafts/` | Unfrozen, experimental prompt templates under development. |

## Freezing & Hash Verification Protocol (Rule R4.4)

Prompts used for evaluation must be frozen before experimental execution:

1. **Freezing**: Compute SHA-256 hash and record in `FROZEN.json` via `src.common.prompts.freeze_prompt()`.
2. **Runtime Verification**: `verify_frozen()` ensures that the byte content on disk exactly matches the registered hash in `FROZEN.json`.
3. **Tampering Protection**: Modifying any frozen prompt without creating a new version (e.g., `judge_v2.txt`) raises `PromptHashMismatchError` and halts execution.
4. **Template Filling**: Always uses exact string substitution (`str.replace`), never `str.format()`, to avoid escaping JSON syntax braces (`{}`).

---
*Research prototype. Not for clinical use.*
