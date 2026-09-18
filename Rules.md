# Rules.md

Hard rules for this repository. **MUST** and **NEVER** rules are not negotiable; breaking one can invalidate the study. **SHOULD** rules can be relaxed only with a written reason in the commit message. If two rules conflict, stop and ask the researchers.

## 1. Research Integrity

| ID | Rule | Reason |
| --- | --- | --- |
| R1.1 | **NEVER** use test split data (Exp 1 test, or any Exp 2 pair) to choose a prompt, threshold, chunk size, or any other setting. | Test results must be unbiased. |
| R1.2 | **MUST** tune Filter B and ROUGE-L thresholds on Exp 1 dev only, by maximum F1 with Hallucinated as positive. | Methodology section 6. |
| R1.3 | **NEVER** retune thresholds for Exp 2. Apply the Exp 1 dev thresholds unchanged. A "best possible threshold on RAG set" may be computed **only** for the threshold transfer check and must be reported as such. | Tests whether thresholds transfer. |
| R1.4 | **MUST** freeze `prompts/judge_v1.txt` and `prompts/generator_v1.txt` after dev work. Store their SHA-256 in `prompts/FROZEN.json`. Every run checks the hash and aborts on mismatch. | Frozen prompt rule. |
| R1.5 | **NEVER** generate, suggest, or fill labels for Experiment 2 or for the 50-row pilot spot-check. Annotation columns stay empty until humans fill them. | Labels must be human and independent. |
| R1.6 | **NEVER** show one annotator's labels to the other. Keep `annotator_1.csv` and `annotator_2.csv` as separate files until both are complete. | Kappa is meaningless otherwise. |
| R1.7 | **MUST** split Exp 1 by question, so both answers of a question land in the same split. | Prevents leakage. |
| R1.8 | **MUST** keep Exp 2 questions disjoint from Exp 1 test questions. **SHOULD** also exclude Exp 1 dev questions. | Keeps experiments independent. |
| R1.9 | **MUST** report every pilot result, failed parse, retry, and excluded pair. Nothing is silently dropped. | Transparency. |
| R1.10 | **NEVER** invent numbers, API prices, citations, or model IDs. Missing values stay `null` and are flagged. | Integrity. |
| R1.11 | **MUST** use the same hallucination definition (Agent.md section 3) in all code, prompts, and annotation guides. | Consistency across experiments. |

## 2. Models and APIs

| ID | Rule |
| --- | --- |
| R2.1 | **MUST** pin exact model IDs in `configs/config.yaml` (generator, judge, NLI, embedder) and log them with every result. |
| R2.2 | **NEVER** use multi-provider gateways or libraries that switch models on rate limits or errors. On a limit, wait and retry the same model. |
| R2.3 | **MUST** keep generator (Groq) and judge (Gemini) from different model families. |
| R2.4 | **MUST** use temperature 0 for both generator and judge. |
| R2.5 | **MUST** cache every API response to JSONL in `data/cache/` with: cache key, model ID, prompt hash, input tokens, output tokens, latency in ms, UTC timestamp, raw text, parsed result. |
| R2.6 | **MUST** retry an unparseable judge output exactly once, then record it as a parse failure. Parse failures are counted and reported, not guessed. |
| R2.7 | **MUST** use `tenacity` with exponential backoff for network errors and HTTP 429. Retries on network errors do not count as the "one parse retry". |
| R2.8 | **MUST** load keys from `.env` via `python-dotenv`. **NEVER** hardcode, print, or log keys. `.env` is in `.gitignore`. |
| R2.9 | **SHOULD** respect free-tier limits with a configurable rate limiter (requests per minute) instead of relying on 429 errors. |

## 3. Timing and Measurement

| ID | Rule |
| --- | --- |
| R3.1 | **MUST** measure latency on Exp 1 test pairs only. |
| R3.2 | **NEVER** count cache hits in latency. Timing runs call the API fresh (cache is written, not read). |
| R3.3 | **MUST** time model load separately from per-pair inference. |
| R3.4 | **MUST** discard 10 warm-up pairs before timing. |
| R3.5 | **MUST** use `time.perf_counter()` around the verifier call only (not file I/O or logging). |
| R3.6 | **MUST** repeat each timing run twice and report median and p95. |
| R3.7 | **MUST** run Filter A timing at two different times of day and record both. |
| R3.8 | **NEVER** report latency from Colab or Kaggle. Laptop only, on charger, performance mode, browser and other apps closed. |
| R3.9 | **MUST** record peak RAM with `psutil` for Filter B and write a machine info block (CPU, RAM, OS, Python, torch version, thread count) with every timing result. |

## 4. Reproducibility

| ID | Rule |
| --- | --- |
| R4.1 | **MUST** set a single global seed (`seed: 42` in config) for sampling, splitting, bootstrap, and any shuffling. |
| R4.2 | **MUST** make every script runnable from the repo root as `python -m src.<module>` with config-driven paths. |
| R4.3 | **MUST** write a `run_manifest.json` next to every results folder: git commit, config snapshot, model IDs, prompt hashes, dataset revision, date. |
| R4.4 | **MUST** pin the dataset revision (Hugging Face commit hash) for MedHallu and PubMedQA. |
| R4.5 | **NEVER** overwrite a results folder. Use `results/<exp>/<run_id>/` where `run_id = YYYYMMDD-HHMM-<short_git_sha>`. |
| R4.6 | **MUST** lock dependencies (`uv.lock` or `requirements.lock`). |
| R4.7 | **SHOULD** make every step idempotent: rerunning skips work already cached and produces identical outputs. |

## 5. Code Quality

| ID | Rule |
| --- | --- |
| R5.1 | **MUST** pass `ruff check .` and `pytest -q` before a task is called done. |
| R5.2 | **MUST** type-hint all public functions. |
| R5.3 | **MUST** test every metric function against a hand-computed example. |
| R5.4 | **MUST** keep one responsibility per module (see Architecture.md). No 800-line scripts. |
| R5.5 | **MUST** read NLI label order from `model.config.id2label`. **NEVER** assume index 1 is entailment. |
| R5.6 | **MUST** validate every JSONL record against the schemas in Design.md on read and write. |
| R5.7 | **SHOULD** log with the standard `logging` module to `logs/<script>_<run_id>.log`, not `print`. |
| R5.8 | **NEVER** commit large or derived files: `data/`, `results/*/raw/`, model weights, `faiss.index`. Commit code, configs, prompts, small CSV summaries, and figures. |

## 6. Resource Limits (8 GB Laptop)

| ID | Rule |
| --- | --- |
| R6.1 | **MUST** install the CPU-only PyTorch build. |
| R6.2 | **MUST** call `torch.set_num_threads(6)` and wrap inference in `torch.inference_mode()`. |
| R6.3 | **SHOULD** keep peak RAM under 4 GB for any single script. |
| R6.4 | **SHOULD** batch NLI inference (default batch size 16) outside timing runs. Timing runs use batch size 1 per pair so latency is per verification. |
| R6.5 | **NEVER** load DeBERTa-base and DeBERTa-small at the same time. |

## 7. Ethics

| ID | Rule |
| --- | --- |
| R7.1 | Use only public, de-identified research abstracts. No patient data. |
| R7.2 | README and any demo must state: research prototype, not for clinical use. |
| R7.3 | Check dataset licenses before publishing any labeled data. |

## 8. Agent Behavior

| ID | Rule |
| --- | --- |
| R8.1 | **MUST** stop and ask when a rule blocks progress, instead of working around it. |
| R8.2 | **MUST** state assumptions explicitly in the task report. |
| R8.3 | **NEVER** delete cache files, results, or annotation files without explicit permission. |
| R8.4 | **NEVER** modify `prompts/*_v1.txt` after freezing. A change means a new version (`v2`) and a researcher decision. |
| R8.5 | **MUST** keep these five docs (`Agent.md`, `Rules.md`, `Architecture.md`, `Design.md`, `Phase.md`) in sync with code. If code must diverge, update the doc in the same commit and say so.
