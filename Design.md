# Design.md

Technical design: data schemas, interfaces, algorithms, and conventions. Code must match this file. If it cannot, update this file in the same commit (Rules R8.5).

## 1. Design Principles

1. **One verifier interface.** All three verifiers expose the same method and return the same result type, so every experiment, timing run, and metric treats them identically.
2. **Scores, then decisions.** Verifiers return a continuous `score` where possible. Turning a score into a label uses a threshold stored separately in `results/thresholds.json`.
3. **Append-only data.** Caches and results are never overwritten. New runs create new folders.
4. **Config over code.** Anything a researcher might change lives in `configs/config.yaml`.
5. **Fail loudly.** Schema violations, hash mismatches, and leakage raise errors. No silent fixes.

## 2. Configuration

`configs/config.yaml` (values marked `TBD` must be filled by researchers before the relevant phase):

```yaml
project: hallucination-verifier-c
seed: 42
plan: 1                          # set after Week 1 pilot: 1 or 2

paths:
  data: data
  cache: data/cache
  results: results
  prompts: prompts

datasets:
  medhallu:
    hf_id: UTAustin-AIHealth/MedHallu
    config: pqa_labeled
    revision: TBD                # pin HF commit hash
    columns:                     # confirm in Phase 1, update if different
      question: Question
      context: Knowledge
      ground_truth: Ground Truth
      hallucinated: Hallucinated Answer
      difficulty: Difficulty Level
      category: Category of Hallucination
  pubmedqa:
    hf_id: qiaojin/PubMedQA
    config: pqa_labeled
    revision: TBD

exp1:
  n_questions: 250
  dev_questions: 50
  test_questions: 200
  stratify_by: difficulty

exp2:
  n_normal: 50
  n_degraded: 50
  extra_degraded_max: 20         # used only if < 25% Hallucinated
  exclude_exp1_dev: true
  chunk_tokens: 250
  chunk_overlap: 30
  top_k: 3
  degraded_search_k: 20          # search wider, drop own doc, keep top_k

models:
  embedder: BAAI/bge-small-en-v1.5
  nli_main: cross-encoder/nli-deberta-v3-small
  nli_optional: cross-encoder/nli-deberta-v3-base
  generator:
    provider: groq
    model_id: TBD                # exact ID, logged
    temperature: 0
    max_tokens: 256
  judge:
    provider: gemini
    model_id: TBD                # exact Gemini Flash ID, logged
    base_url: https://generativelanguage.googleapis.com/v1beta/openai/
    temperature: 0
    max_tokens: 64
    rpm_limit: TBD               # from current free-tier docs

filter_b:
  num_threads: 6
  batch_size: 16
  max_length: 512
  sentence_splitter: pysbd

baseline:
  rouge_variant: rougeL
  rouge_field: precision         # confirm on dev; see section 6.3

timing:
  warmup_pairs: 10
  repeats: 2
  percentiles: [50, 95]

stats:
  bootstrap_resamples: 1000
  ci: 0.95
  bootstrap_unit: question       # resample questions, keep pairs together
```

`configs/pricing.yaml` is filled by humans from the official pricing page:

```yaml
judge:
  model_id: TBD
  input_per_million_usd: null
  output_per_million_usd: null
  checked_on: null               # YYYY-MM-DD
  source_url: null
```

## 3. Data Schemas

All JSONL records are validated with pydantic models in `src/common/io.py`.

### 3.1 Pair (Experiment 1 and Experiment 2 after labeling)

```python
class Pair(BaseModel):
    pair_id: str                 # "e1-<qid>-gt" | "e1-<qid>-hal" | "e2-<qid>"
    question_id: str             # links both answers of a question
    experiment: Literal["exp1", "exp2"]
    split: Literal["dev", "test", "rag"]
    question: str
    context: str                 # exact text the verifiers see
    answer: str
    label: Literal[0, 1] | None  # 0 Supported, 1 Hallucinated; None before annotation
    difficulty: str | None       # exp1: easy | medium | hard
    category: str | None         # exp1 hallucination category
    condition: Literal["normal", "degraded"] | None   # exp2 only
    source_doc_id: str | None    # PubMedQA PMID for the question
```

For Exp 2, `context` is the three retrieved chunks joined with `"\n\n"` in rank order. The joined string is stored, so every verifier sees byte-identical input.

### 3.2 Chunk

```python
class Chunk(BaseModel):
    chunk_id: str                # "<doc_id>-<n>"
    doc_id: str                  # PMID
    text: str
    n_tokens: int
```

### 3.3 Generated answer

```python
class Generated(BaseModel):
    question_id: str
    condition: Literal["normal", "degraded"]
    retrieved_chunk_ids: list[str]
    retrieved_doc_ids: list[str]
    own_doc_in_context: bool     # must be False for degraded
    context: str
    answer: str
    generator_model_id: str
    prompt_hash: str
    cache_key: str
```

### 3.4 Verifier result

```python
class VerifierResult(BaseModel):
    pair_id: str
    verifier: Literal["filter_a", "filter_b", "rouge", "filter_b_base"]
    score: float | None          # higher = more supported; None for parse failure
    verdict: Literal[0, 1] | None   # after threshold (A: direct from JSON)
    confidence: float | None     # Filter A only
    latency_ms: float | None
    input_tokens: int | None     # Filter A only
    output_tokens: int | None
    parse_failure: bool = False
    details: dict = {}           # e.g. per-sentence scores for Filter B
```

**Score direction convention:** `score` is always "support" (high means supported). For AUROC and PR curves with Hallucinated as positive, use `1 - score` for Filter B and baseline.

### 3.5 Cache record

```python
class CacheRecord(BaseModel):
    key: str                     # sha256 of model_id|prompt_hash|context|answer (or question)
    provider: str
    model_id: str
    prompt_hash: str
    request_text: str
    response_text: str
    parsed: dict | None
    input_tokens: int | None
    output_tokens: int | None
    latency_ms: float
    attempt: int                 # 1 or 2 (parse retry)
    mode: Literal["normal", "timing"]
    timestamp_utc: str
```

### 3.6 Annotation sheet columns

`pair_id, question, retrieved_context, answer, label (Supported/Hallucinated), notes`

Each annotator gets an identical copy with empty `label` and `notes`. Rows are shuffled with the same seed so condition order does not leak. The `condition` column is **not** included in annotator copies (blind annotation).

`labeled.csv` columns: `pair_id, annotator_1, annotator_2, final_label, resolution_notes`.

## 4. Verifier Interface

```python
# src/filters/base.py
class Verifier(Protocol):
    name: str
    def load(self) -> float: ...                    # returns load time in seconds
    def score(self, context: str, answer: str) -> VerifierResult: ...
    def score_batch(self, pairs: list[Pair]) -> list[VerifierResult]: ...
```

`run_verifiers.py` applies thresholds after scoring:

```
verdict = 1 if score < threshold else 0     # Filter B, ROUGE
verdict = 1 if parsed["verdict"] == "NOT_SUPPORTED" else 0   # Filter A
```

## 5. Filter A: API LLM Judge

### 5.1 Client

- OpenAI Python client pointed at the Gemini OpenAI-compatible endpoint (`base_url` from config). If the endpoint behaves differently, the native `google-genai` SDK is an acceptable swap; log which one was used.
- Rate limiter: token bucket at `rpm_limit`.
- `tenacity`: retry on connection errors, timeouts, HTTP 429 and 5xx; exponential backoff 2 s to 60 s, max 6 attempts. Never switch model.

### 5.2 Prompt

Loaded from `prompts/judge_v1.txt`, filled with `str.replace("{context}", ...)` and `str.replace("{answer}", ...)` (not `str.format`, since the prompt contains literal JSON braces). Hash checked against `FROZEN.json` on every load once frozen.

### 5.3 Parsing

1. Strip whitespace and markdown fences (```` ```json ````).
2. Extract the first `{...}` block.
3. `json.loads`, then validate: `verdict` in {`SUPPORTED`, `NOT_SUPPORTED`}, `confidence` a number in [0, 1].
4. On failure: one retry with the same prompt. Second failure sets `parse_failure=True`, `verdict=None`.

Parse failures are excluded from F1 and reported as a count and rate. A secondary table treats them as Hallucinated (conservative) for the safety view.

### 5.4 Score for Filter A

`score = confidence if verdict == SUPPORTED else 1 - confidence`. Used only for optional analyses; reported Filter A metrics use the binary verdict.

## 6. Filter B: Local NLI Cross-Encoder

### 6.1 Loading

```python
torch.set_num_threads(cfg.filter_b.num_threads)
tok = AutoTokenizer.from_pretrained(model_id)
model = AutoModelForSequenceClassification.from_pretrained(model_id).eval()
ent_idx = {v.lower(): k for k, v in model.config.id2label.items()}["entailment"]
```

Load time measured separately (Rules R3.3).

### 6.2 Scoring algorithm

```
sentences = pysbd.split(answer)                       # drop empty strings
chunks    = token_chunks(context, budget = 512 - max_sentence_tokens - 3)
for s in sentences:
    for c in chunks:
        p[s][c] = softmax(model(premise=c, hypothesis=s))[ent_idx]
    sentence_score[s] = max_c p[s][c]
answer_score = min_s sentence_score[s]
```

- Premise is the context chunk, hypothesis is the answer sentence.
- Context chunks split on sentence boundaries where possible, with small overlap, so a supporting sentence is not cut in half.
- Store per-sentence scores in `details` for the qualitative review.
- For one-sentence MedHallu answers this reduces to max over chunks.

### 6.3 Baseline: ROUGE-L

`rouge_score.RougeScorer(["rougeL"], use_stemmer=True)`, `score(target=context, prediction=answer)`. ROUGE-L **precision** is the default, because it measures how much of the answer is covered by the context, which matches the faithfulness question. Recall and F-measure are also stored. The variant used for thresholding is chosen on dev only and recorded in `thresholds.json`.

### 6.4 Threshold tuning (dev only)

For each continuous verifier, sweep every unique score on dev as a candidate threshold, pick the one with maximum F1 (Hallucinated positive). Ties broken by lower FNR. Write:

```json
{
  "filter_b": {"threshold": 0.0, "dev_f1": 0.0, "model_id": "...", "tuned_on": "exp1_dev", "date": "..."},
  "rouge": {"threshold": 0.0, "variant": "precision", "dev_f1": 0.0, "tuned_on": "exp1_dev", "date": "..."}
}
```

`thresholds.json` is committed and treated as frozen.

## 7. Experiment 2 Details

### 7.1 Question selection

From PubMedQA pqa_labeled, remove every question whose PMID appears in Exp 1 test (and dev if `exclude_exp1_dev`). Sample 100 with the global seed, assign 50 normal and 50 degraded, write `questions.jsonl`. If MedHallu has no PMID column, match questions by normalized question text (lowercase, collapsed whitespace, stripped punctuation) and log any near-duplicates for human review. `tests/test_leakage.py` asserts zero overlap.

### 7.2 Corpus and index

- Corpus: all PubMedQA pqa_labeled contexts (about 1,000 abstracts), joined per PMID. Conclusions (`LONG_ANSWER`) are **excluded**, matching how MedHallu builds context.
- Chunk to about 250 tokens (bge tokenizer), overlap 30.
- Embed with bge-small, L2-normalize, `faiss.IndexFlatIP`. Queries use bge's query instruction prefix per model card.

### 7.3 Degraded retrieval

Search `degraded_search_k` results, drop every chunk whose `doc_id` equals the question's own PMID, keep the first `top_k`. This is equivalent to removing the source abstract from the index without rebuilding it. Assert `own_doc_in_context == False`.

### 7.4 Generator prompt

`prompts/generator_v1.txt` asks for an answer based on the evidence in two to four sentences. It does **not** instruct the model to refuse when evidence is weak (methodology 5.2). Frozen before the first generation run.

## 8. Evaluation

### 8.1 Metrics (`src/evaluation/metrics.py`)

| Function | Definition |
| --- | --- |
| `precision, recall, f1` | sklearn, `pos_label=1` |
| `fnr` | FN / (FN + TP) |
| `fpr` | FP / (FP + TN) |
| `auroc` | sklearn `roc_auc_score(y, 1 - score)` |
| `latency_summary` | median, p95, mean, n |
| `shadow_cost_per_1k` | `1000 * (avg_in * in_price + avg_out * out_price) / 1_000_000` |

### 8.2 Statistics (`src/evaluation/stats.py`)

| Question | Implementation |
| --- | --- |
| A vs B on same pairs | 2x2 table of per-pair correctness, `statsmodels.stats.contingency_tables.mcnemar(table, exact=True)`. Also A vs baseline and B vs baseline. |
| F1 uncertainty | Bootstrap, 1,000 resamples, 95% percentile CI. Exp 1 resamples question IDs (both pairs together). Exp 2 resamples pairs. |
| Annotator agreement | `sklearn.metrics.cohen_kappa_score` on raw annotator labels before resolution |

Pairs with a Filter A parse failure are excluded from the paired McNemar test for comparisons that involve Filter A; the count is reported.

### 8.3 Breakdowns

- Exp 1: F1 by difficulty, F1 by hallucination category (hallucinated pairs carry the category; supported pairs are grouped with their question's category for per-question analysis, and this choice is noted).
- Exp 2: F1 and label balance by condition (normal vs degraded).

### 8.4 Cross-experiment

- **Ranking check:** order the three verifiers by F1 and by FNR in each experiment; report whether the order matches, with CIs.
- **Threshold transfer:** Filter B F1 on Exp 2 with the frozen dev threshold vs the oracle best threshold on Exp 2. The gap is the transfer cost. The oracle is labeled "not a valid result, diagnostic only".

## 9. Timing Design

`src/timing.py --verifier {filter_a,filter_b,rouge} --split test --session {morning,evening}`

1. Write machine info (CPU, RAM, OS, Python, torch, threads, on_charger flag entered by user).
2. Load model, record `load_seconds` and RSS after load.
3. Run 10 warm-up pairs, discard.
4. Time each remaining pair with `perf_counter` around `score()` only, batch size 1.
5. Track peak RSS with `psutil` in a background sampler (every 50 ms).
6. Repeat the full pass twice. Report per-pass and pooled median and p95.
7. Filter A: `mode="timing"` bypasses cache reads; run once per session at two different times of day.

Output: `results/exp1/<run_id>/timing_<verifier>_<session>.json` plus per-pair CSV.

## 10. Figures

| Figure | Source data | Library | Notes |
| --- | --- | --- | --- |
| Confusion matrices, both experiments | predictions | seaborn | 2 x 3 grid |
| F1 with 95% CI, experiments side by side | bootstrap output | matplotlib | grouped bars with error bars |
| Latency box plot | timing CSVs | matplotlib | log y-axis |
| F1 vs cost per 1k | metrics + pricing | matplotlib | Filter B cost shown as 0 API cost, annotated |
| F1 by difficulty | exp1 breakdown | seaborn | |
| PR curve, Filter B | scores | sklearn + matplotlib | both experiments on one plot |

Style: one consistent color per verifier across all figures (Filter A, Filter B, ROUGE-L), colorblind-safe palette (Okabe-Ito), 300 dpi PNG and vector PDF, font size readable at single-column width, no chart titles inside images (captions go in the paper).

## 11. CLI Conventions

Every entry point:

```
python -m src.<module> --config configs/config.yaml [--split dev|test|rag] [--dry-run] [--limit N]
```

- `--limit N` runs on the first N records for smoke tests.
- `--dry-run` validates inputs and prints the plan without API calls.
- Exit code non-zero on any validation error.

## 12. Testing Strategy

| Test | Checks |
| --- | --- |
| `test_split.py` | No question ID in both dev and test; counts are 100 and 400; difficulty strata present |
| `test_leakage.py` | Exp 2 questions do not overlap Exp 1 test (and dev if configured) |
| `test_filter_nli.py` | Label index read from config; min-of-max aggregation on a fake score matrix; chunking stays under 512 tokens |
| `test_filter_api.py` | Parser handles fences, extra text, bad JSON; one retry only; cache key stable; timing mode skips cache reads (mocked client) |
| `test_metrics.py` | Hand-computed P, R, F1, FNR, FPR, cost formula |
| `test_stats.py` | McNemar on a known table; bootstrap reproducible with seed |
| `test_prompts.py` | Hash mismatch raises |

Tests never call real APIs or download models; use fixtures and mocks. A separate `--limit 5` smoke run exercises the real stack.
