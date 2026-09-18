# Draft Prompts (`prompts/drafts/`)

This directory is reserved for candidate and experimental prompt templates that have not yet been evaluated or frozen.

## Workflow

1. Prototype candidate prompts here (e.g. testing alternative chain-of-thought or judge rubrics).
2. When ready to run benchmark evaluations, move the prompt template to `prompts/<name>_v<N>.txt`.
3. Freeze the prompt using `src.common.prompts.freeze_prompt("<name>_v<N>.txt")` to register its SHA-256 hash in `prompts/FROZEN.json` (Rule R4.4).

---
*Research prototype. Not for clinical use.*
