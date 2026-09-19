# Common Utilities (`src/common/`)

Foundational utilities shared across all phases of the project.

## Modules

| Module | Responsibility |
| :--- | :--- |
| `config.py` | Validated Pydantic configuration schemas matching `configs/config.yaml`. |
| `io.py` | Pydantic data schemas (`Pair`, `Chunk`, `QuestionRecord`, `VerifierResult`, `CacheRecord`) and robust JSONL read/write utilities. |
| `cache.py` | Append-only, SHA-256 keyed cache (`JsonlCache`) for API requests and model responses (Rule R5.2). |
| `text.py` | Sentence splitting (`pysbd`), sliding-window token chunking with overlap, and question normalization. |
| `prompts.py` | Prompt loading, SHA-256 hash freezing, and tampering detection against `prompts/FROZEN.json`. |
| `manifest.py` | Cross-platform git discovery (`find_git_binary`), unique run ID generator (`YYYYMMDD-HHMM-<sha>`), and immutable `manifest.json` metadata recording. |
| `logging_utils.py` | Formatted logging configuration routing to stderr and timestamped log files in `logs/` (Rule R5.7). |

## Invariants

- Never use raw `print()` for logging; always use `logging.getLogger()`.
- Never use `str.format()` on prompt templates containing JSON formatting.
- The cache key is strictly deterministic: `sha256(model_id | prompt_hash | context | answer)`.

---
*Research prototype. Not for clinical use.*
