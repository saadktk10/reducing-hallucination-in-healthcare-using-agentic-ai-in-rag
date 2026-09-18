# Phase.md

Detailed implementation plan over 10 weeks. Each phase lists goal, owner, tasks, files, commands, acceptance criteria, and human gates. The agent does not start a phase until the previous gate is passed or the phase is marked parallel.

**Owners.** R1 = researcher leading Experiment 1. R2 = researcher leading Experiment 2. Both = both researchers. Agent = Antigravity.

## Timeline at a Glance

```mermaid
gantt
    title Methodology C: 10-week implementation
    dateFormat  YYYY-MM-DD
    axisFormat  W%W
    section Setup
    P0 Environment and scaffold        :p0, 2026-01-05, 4d
    P1 Pilot checks                    :p1, after p0, 3d
    Decision gate G1                   :milestone, g1, after p1, 0d
    section Experiment 1
    P2 Build pairs and splits          :p2, after g1, 3d
    P3 Verifiers + dev tuning          :p3, after p2, 8d
    P5 Test runs and timing            :p5, after p3, 7d
    section Experiment 2
    P4 Index + generation              :p4, after g1, 10d
    P6 Two-annotator labeling          :p6, after p4, 7d
    P7 Verifiers on RAG set            :p7, after p6, 3d
    section Analysis
    P8 Metrics and statistics          :p8, after p7, 6d
    P9 Cross-experiment + extras       :p9, after p8, 5d
    section Writing
    P10 Figures and draft support      :p10, after p9, 7d
    P11 Revision and release           :p11, after p10, 7d
```

(Dates are placeholders. Replace the start date with the real Week 1 Monday.)

| Week | Phases | R1 | R2 |
| --- | --- | --- | --- |
| 1 | P0, P1, G1 | Environment, pilot | Environment, pilot |
| 2 | P2, P3 start, P4 start | Pairs, prompt drafts | Corpus, index |
| 3 | P3, P4 | Dev tuning, freeze | Generation |
| 4 | P5, P6 | Test runs, timing | Annotation (both label) |
| 5 | P6 end, P7 | Annotation | Annotation, run verifiers on RAG |
| 6 | P8 | Metrics, stats | Metrics, stats |
| 7 | P9 | Cross-experiment | Qualitative review |
| 8 | P10 | Figures | Draft |
| 9 to 10 | P11 | Revision | Revision |

---

## Phase 0: Environment and Scaffold

**Week 1, days 1 to 4. Owner: Agent, Both verify.**

**Goal.** A clean repo that installs in one command, with shared utilities tested, before any research code.

### Tasks

1. Create the directory structure from `Architecture.md` section 9 (empty modules with docstrings).
2. `pyproject.toml` with Python 3.12 and dependencies:
   - Core: `pandas numpy pyyaml pydantic python-dotenv tqdm`
   - HF: `datasets huggingface_hub transformers sentence-transformers`
   - Torch: CPU build (`--index-url https://download.pytorch.org/whl/cpu`)
   - Retrieval: `faiss-cpu`
   - APIs: `openai groq tenacity`
   - Text: `pysbd nltk rouge-score`
   - Eval: `scikit-learn statsmodels scipy`
   - Plots: `matplotlib seaborn`
   - System: `psutil`
   - Dev: `pytest ruff jupyterlab`
3. Lock dependencies (`uv lock`). Write `scripts/setup_env.sh`.
4. `.env.example`, `.gitignore`, `README.md` with the not-for-clinical-use notice.
5. Implement `src/common/`: `config.py`, `io.py` (schemas from Design.md section 3), `cache.py`, `manifest.py`, `prompts.py`, `text.py`, `logging_utils.py`.
6. Tests for all of `src/common/`.
7. Smoke-check APIs: one Groq call and one Gemini call with `--limit 1`, cached. Record the exact model IDs returned.
8. Check free-tier rate limits for both providers from current docs; researchers enter `rpm_limit`.

### Acceptance criteria

- [ ] `bash scripts/setup_env.sh && pytest -q` passes on the laptop.
- [ ] `python -c "import torch; print(torch.__version__, torch.cuda.is_available())"` shows CPU build, `False`.
- [ ] Both API smoke calls succeed and appear in `data/cache/`.
- [ ] Model IDs for generator and judge written into `config.yaml`.
- [ ] Idle RAM with Python loaded noted in README.

---

## Phase 1: Pilot Checks

**Week 1, days 4 to 5. Owner: Agent builds, Both judge.**

**Goal.** Test MedHallu for the two known risks before investing in it.

### Tasks

1. `pilot_checks.py --step fields`: load MedHallu pqa_labeled at a pinned revision, print column names, types, and 20 rows to `data/pilot/fields_20.json`. **Confirm column names and update `config.yaml` if they differ.**
2. `pilot_checks.py --step spotcheck`: sample 50 rows (seeded), export `data/pilot/spotcheck_50.csv` with columns `row_id, question, context, ground_truth, supported_yes_no, notes`. `supported_yes_no` left empty.
3. **Human task:** both researchers fill `supported_yes_no` (Risk 1: unsupported correct answers).
4. `pilot_checks.py --step rouge`: build a provisional 100-pair dev set (same logic as Phase 2, same seed so it matches), compute ROUGE-L scores and AUROC (Risk 2: lexical shortcut). Also report AUROC for precision, recall, and F-measure variants.
5. `pilot_checks.py --step report`: write `data/pilot/pilot_report.json` and `results/pilot/pilot_report.md` with: unsupported rate and count, ROUGE-L AUROC per variant, the decision rule, and which plan the rule points to.

### Gate G1: Plan decision (human)

| Condition | Plan |
| --- | --- |
| Unsupported ground truth under 10% **and** ROUGE-L AUROC under 0.95 | **Plan 1**: Exp 1 main, Exp 2 is 100-pair validation |
| Otherwise | **Plan 2**: Exp 2 main, grow to 200 pairs, Exp 1 secondary with caveats |

Researchers set `plan:` in config and commit with message `G1: plan N, unsupported=X%, auroc=Y`. All pilot numbers go in the paper regardless.

### Acceptance criteria

- [ ] Column names confirmed and in config.
- [ ] Spot-check CSV filled by humans, not by the agent.
- [ ] Pilot report generated from code, numbers reproducible.
- [ ] `plan` set in config.

---

## Phase 2: Experiment 1 Pairs and Splits

**Week 2, days 1 to 3. Owner: Agent, R1 verifies.**

**Goal.** Build 500 labeled pairs with a leak-free dev/test split.

### Tasks

1. `build_exp1_pairs.py`:
   - Load MedHallu at pinned revision.
   - Stratified sample of 250 questions by difficulty (seeded). If a stratum is too small, sample proportionally and log it.
   - For each question, create two `Pair` records: ground truth (label 0) and hallucinated (label 1), same `question_id`, same `context`.
   - Split by question: 50 questions to dev, 200 to test, stratified by difficulty.
   - Write `data/exp1_medhallu/dev.jsonl` and `test.jsonl`.
2. Write `data/exp1_medhallu/split_summary.json`: counts per split, per difficulty, per category.
3. Tests: `test_split.py` (no overlap, correct counts, balanced labels).

### Acceptance criteria

- [ ] Dev = 100 pairs, test = 400 pairs, 50/50 label balance in each.
- [ ] Zero question IDs shared between dev and test.
- [ ] Rerunning produces byte-identical files.
- [ ] Provisional pilot dev set equals final dev set (same seed and logic), or the difference is documented.

---

## Phase 3: Verifiers and Dev Tuning

**Weeks 2 to 3. Owner: Agent implements, R1 owns prompt and freeze.**

**Goal.** Three working verifiers, a frozen judge prompt, and frozen thresholds, all from dev data only.

### 3a. Baseline ROUGE-L

1. Implement `filters/baseline_rouge.py` per Design.md 6.3.
2. Unit tests with toy strings.

### 3b. Filter B: NLI cross-encoder

1. Implement `filters/filter_nli.py` per Design.md 6.
2. Implement token-aware context chunking in `common/text.py`.
3. Tests: label index from config, aggregation (min over sentences of max over chunks), chunk token budget.
4. Run on dev with `--limit 10`, inspect per-sentence details by hand.
5. Record load time and peak RAM once as a sanity check (not the reported timing).

### 3c. Filter A: API judge

1. Implement `filters/filter_api.py` per Design.md 5: client, rate limiter, tenacity, cache, parser, one retry.
2. Tests with a mocked client.
3. R1 writes `prompts/judge_v1.txt` (starting from the methodology prompt). Iterate **on dev only**. Keep each attempt as `prompts/drafts/judge_draft_N.txt` with its dev F1 and parse-failure rate logged to `results/dev_prompt_log.csv`.
4. When R1 is satisfied: copy the chosen draft to `judge_v1.txt`, write its hash into `FROZEN.json`, commit `freeze: judge_v1`.

### 3d. Threshold tuning

1. `run_verifiers.py --split dev` for all three verifiers.
2. `tune_thresholds.py` per Design.md 6.4. Writes `results/thresholds.json`.
3. Report dev P, R, F1, AUROC for each verifier (these are **not** paper results, only tuning context).
4. Commit `freeze: thresholds`.

### 3e. Optional: DeBERTa-base

If time allows, tune a separate threshold for `nli_optional` on dev. Never loaded together with small.

### Acceptance criteria

- [ ] All three verifiers pass unit tests and a `--limit 5` smoke run.
- [ ] `judge_v1.txt` hash in `FROZEN.json`; loading a modified prompt raises.
- [ ] `thresholds.json` committed with dev F1, variant, model ID, date.
- [ ] No test file was read during this phase (check logs; `run_verifiers` logs every file it opens).
- [ ] Filter A dev parse-failure rate recorded.

---

## Phase 4: Experiment 2 Index and Generation

**Weeks 2 to 3, parallel with Phase 3. Owner: Agent, R2 verifies.**

**Goal.** About 100 RAG answers, half from degraded retrieval, ready for blind annotation.

### Tasks

1. `build_index.py`:
   - Load PubMedQA pqa_labeled contexts (no conclusions), group by PMID.
   - Chunk (~250 tokens, overlap 30), write `corpus_chunks.jsonl`.
   - Embed with bge-small on CPU, normalize, build `faiss.index`.
   - Log build time and peak RAM.
2. Select questions per Design.md 7.1. Write `questions.jsonl` with condition assigned. Run `test_leakage.py`.
3. Retrieval sanity check: for 20 normal-condition questions, report how often the own source doc appears in top-3 (retrieval hit rate). For degraded, assert it never does.
4. R2 writes `prompts/generator_v1.txt` (answer based on evidence, 2 to 4 sentences, no forced refusal). Test on 5 **dev-excluded, non-selected** questions, then freeze and commit.
5. `generate_rag.py`: retrieve, build context string, call Groq at temperature 0, cache, write `generated.jsonl`.
6. Record per-condition answer length stats.

### Acceptance criteria

- [ ] `faiss.index` rebuilds deterministically from `corpus_chunks.jsonl`.
- [ ] 100 generated answers (50 normal, 50 degraded), all with `own_doc_in_context == False` for degraded.
- [ ] `test_leakage.py` passes.
- [ ] `generator_v1.txt` frozen before the first real generation.
- [ ] Peak RAM of index build logged.

---

## Phase 5: Experiment 1 Test Runs and Timing

**Weeks 3 to 4. Owner: Agent runs, R1 supervises the laptop.**

**Goal.** Headline accuracy, latency, and cost numbers on the 400 test pairs.

### 5a. Accuracy runs

1. `run_verifiers.py --split test` for Filter A, Filter B, ROUGE-L using frozen prompt and thresholds.
2. Save predictions to `results/exp1/<run_id>/predictions_<verifier>.jsonl` with manifest.
3. Record Filter A parse failures and retries.

### 5b. Timing runs (laptop only, Rules section 3)

Pre-run checklist (print it at script start and require `--confirm`):

- [ ] On charger, performance power mode
- [ ] Browser and other apps closed
- [ ] OS updates and antivirus scans paused (Windows)
- [ ] No other Python processes

Runs:

| Run | Sessions | Notes |
| --- | --- | --- |
| Filter B timing | 1 session, 2 repeats | Load time and peak RAM recorded |
| ROUGE-L timing | 1 session, 2 repeats | |
| Filter A timing | Morning and evening sessions, 2 repeats each | Cache reads bypassed |

Timing outputs go to `results/exp1/<run_id>/timing_*.json`.

### 5c. Cost

Once humans fill `pricing.yaml`, compute shadow cost per 1,000 verifications from logged tokens. Optional paid run: same model with billing enabled on a small subset to confirm real cost and latency; tagged `mode: paid` in the manifest.

### 5d. Optional self-consistency

Filter A, 5 calls on 50 test pairs (250 calls). Because temperature is 0, this measures API nondeterminism; report agreement rate. Cache key includes a `repeat_idx` for this run only.

### Acceptance criteria

- [ ] Predictions for all 400 pairs per verifier (parse failures counted).
- [ ] Timing JSON has machine info, load time, warm-up count, per-pass and pooled median and p95.
- [ ] Filter A timed in two sessions at different times of day.
- [ ] No latency value comes from a cache hit (asserted in code).
- [ ] Shadow cost computed with `checked_on` date, or left `null` and flagged.

---

## Phase 6: Two-Annotator Labeling (Human)

**Weeks 4 to 5. Owner: Both. Agent builds tooling only.**

**Goal.** Human ground truth for Experiment 2 with measured agreement.

### Tasks

1. Agent: `annotation.py export` creates `template.csv` and two identical, shuffled, condition-blind copies (`annotator_1.csv`, `annotator_2.csv`). Also generates `annotation_guide.md` containing only the Section 2 definition and three worked examples written by the researchers.
2. **Human:** each researcher labels independently, without seeing the other file.
3. Agent: `annotation.py kappa` computes Cohen's kappa on raw labels and writes `disagreements.csv`.
4. **Human:** resolve disagreements by discussion, fill `labeled.csv`.
5. Agent: `annotation.py merge` validates `labeled.csv` and writes `labeled.jsonl` as `Pair` records with `split="rag"`.
6. Agent reports the class balance by condition.

### Gate G2: Class balance

If fewer than 25% of answers are Hallucinated, researchers may authorize up to 20 extra degraded questions. Agent then reruns Phase 4 step 5 for those questions only and returns to step 1 of this phase for the new rows. Final balance is reported.

Under **Plan 2**, this phase targets 200 pairs; Phase 4 is extended accordingly.

### Optional

Clinician or medical student reviews 20 to 30 pairs; their labels are stored separately and reported as an agreement check, not used to overwrite ground truth.

### Acceptance criteria

- [ ] Kappa computed and above 0.6, or the shortfall discussed in the paper.
- [ ] Every row in `labeled.jsonl` has a human `final_label`.
- [ ] Class balance per condition reported.
- [ ] No agent-generated label anywhere in the annotation files (checked by reviewing git history).

---

## Phase 7: Verifiers on the RAG Set

**Week 5. Owner: Agent, R2 verifies.**

### Tasks

1. `run_verifiers.py --split rag` with the frozen judge prompt and the **unchanged** Exp 1 dev thresholds.
2. Save predictions to `results/exp2/<run_id>/`.
3. No timing runs on Exp 2 (too small for stable timing).

### Acceptance criteria

- [ ] `thresholds.json` and `FROZEN.json` hashes in the manifest match the Phase 3 versions.
- [ ] Predictions for every labeled RAG pair.

---

## Phase 8: Metrics and Statistics

**Week 6. Owner: Agent computes, Both review.**

### Tasks

1. Implement `evaluation/metrics.py` and `evaluation/stats.py` per Design.md 8, with hand-computed tests.
2. `evaluate.py --exp exp1` and `--exp exp2`:
   - Main table per verifier: P, R, F1, FNR, FPR, AUROC (B and baseline), n, parse failures.
   - Bootstrap 95% CI for F1 (question-level resampling for Exp 1).
   - McNemar exact: A vs B, A vs baseline, B vs baseline.
   - Exp 1 only: latency (median, p95), load time, peak RAM, shadow cost per 1k.
3. Breakdowns: F1 by difficulty and category (Exp 1), by condition (Exp 2).
4. Precision-recall curve data for Filter B (both experiments).
5. Write `results/<exp>/<run_id>/tables/*.csv` and a `summary.md` that states numbers only, no interpretation.

### Acceptance criteria

- [ ] All metric tests pass against hand-computed values.
- [ ] Every number in `summary.md` traces to a CSV in the same run folder.
- [ ] Exp 2 CIs reported, and `summary.md` notes that Exp 2 is for direction of findings.

---

## Phase 9: Cross-Experiment and Additional Analyses

**Week 7. Owner: Agent computes, Both interpret.**

### Tasks

1. `cross_experiment.py`:
   - Ranking check by F1 and by FNR in both experiments, with CIs.
   - Threshold transfer check: Filter B F1 on Exp 2 with dev threshold vs oracle threshold (diagnostic only).
   - Output `results/cross/<run_id>/cross_summary.md` with a yes/no on ranking agreement.
2. Qualitative review export: 20 to 30 pairs where A and B disagree (both experiments), with context, answer, label, both verdicts, and Filter B per-sentence scores. **Humans** write the qualitative notes.
3. Optional: DeBERTa small vs base comparison on Exp 1 test.
4. Optional: negation subset. Tag Exp 1 test pairs where hallucinated and ground-truth answers differ mainly by a negation cue, report Filter B accuracy on that subset (the literature review flags negation as a known NLI weak point). Only if researchers approve adding it.

### Acceptance criteria

- [ ] Cross summary states whether the benchmark ranking holds on RAG output.
- [ ] Disagreement export ready for human review.

---

## Phase 10: Figures and Draft Support

**Week 8. Owner: Agent, Both write.**

### Tasks

1. `figures.py` produces all six figures in Design.md section 10 from the latest run folders, PNG and PDF, 300 dpi.
2. Export result tables as LaTeX (`booktabs`) and CSV.
3. Generate a `results/REPORT.md` index linking each figure and table to the run ID that produced it.

### Acceptance criteria

- [ ] `python -m src.figures` regenerates every figure from cached results with no API calls.
- [ ] Consistent verifier colors across all figures.

---

## Phase 11: Revision and Release

**Weeks 9 to 10. Owner: Both, Agent assists.**

### Tasks

1. Apply supervisor feedback. Any change to a frozen artifact requires a new version and a rerun of all dependent phases, noted in the paper.
2. `scripts/run_all.sh` reproduces all tables and figures from cache in one command. Test it on a fresh clone.
3. README: setup, reproduction steps, model IDs, dataset revisions, dates, limitations, not-for-clinical-use notice.
4. Check dataset licenses before publishing labeled Exp 2 data.
5. Tag release `v1.0-paper`.

### Acceptance criteria

- [ ] Fresh clone plus cache reproduces every reported number.
- [ ] All five docs match the final code.

---

## Risk Register

| Risk | Phase | Response |
| --- | --- | --- |
| MedHallu column names differ | P1 | Update config, rerun, no code rewrite |
| Pilot fails thresholds | G1 | Switch to Plan 2 |
| Free-tier rate limits slow Filter A | P3, P5 | Rate limiter, run overnight, cache everything |
| Model ID deprecated mid-study | Any | Stop, report, researchers decide; never auto-switch |
| Too few hallucinated RAG answers | G2 | Up to 20 extra degraded questions |
| Low kappa | P6 | Refine guide on a fresh sample, relabel, report both |
| RAM pressure | P3, P4 | Load one model at a time, lower batch size |
| Laptop timing noise | P5 | Checklist, warm-up, two repeats, median and p95 |
