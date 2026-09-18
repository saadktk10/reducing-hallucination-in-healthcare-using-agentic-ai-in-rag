# Architecture.md

System architecture for the hallucination verifier study. Diagrams use Mermaid (renders in GitHub, VS Code, and Antigravity markdown preview).

## 1. System Overview

Two data sources feed one shared verification layer. Everything downstream (evaluation, statistics, figures) is shared too, so both experiments are measured the same way.

```mermaid
flowchart TB
    subgraph SRC["Data sources (Hugging Face)"]
        MH["MedHallu<br/>pqa_labeled"]
        PQ["PubMedQA<br/>pqa_labeled abstracts"]
    end

    subgraph E1["Experiment 1: Benchmark"]
        P1["build_exp1_pairs<br/>250 questions to 500 pairs"]
        SPL["Split by question<br/>dev 100 / test 400"]
    end

    subgraph E2["Experiment 2: RAG validation"]
        IDX["build_index<br/>chunk, embed, FAISS"]
        GEN["generate_rag<br/>normal + degraded retrieval<br/>Groq, temp 0"]
        ANN["Human annotation<br/>2 annotators, kappa"]
    end

    subgraph VER["Verification layer (shared)"]
        FA["Filter A<br/>Gemini Flash judge"]
        FB["Filter B<br/>DeBERTa-v3-small NLI"]
        BL["Baseline<br/>ROUGE-L"]
    end

    subgraph EVAL["Evaluation layer (shared)"]
        MET["Metrics<br/>P, R, F1, FNR, FPR, AUROC"]
        STAT["Statistics<br/>McNemar, bootstrap CI, kappa"]
        TIME["Timing<br/>latency, RAM, shadow cost"]
        XEXP["Cross-experiment<br/>comparison"]
        FIG["Figures"]
    end

    MH --> P1 --> SPL --> VER
    PQ --> IDX --> GEN --> ANN --> VER
    MH -. "exclude test questions" .-> GEN
    VER --> MET --> STAT --> XEXP --> FIG
    VER --> TIME --> FIG
    CACHE[("data/cache<br/>API JSONL")] <--> FA
    CACHE <--> GEN
```

## 2. Week 1 Decision Gate

The pilot decides which experiment carries the headline results. The code must support both plans through config (`plan: 1` or `plan: 2`).

```mermaid
flowchart TD
    A["Load MedHallu pqa_labeled<br/>inspect fields on 20 rows"] --> B["Human spot-check 50 rows:<br/>is ground truth supported by context?"]
    B --> C["ROUGE-L on 100 dev pairs<br/>compute AUROC"]
    C --> D{"Unsupported GT under 10%<br/>AND ROUGE-L AUROC under 0.95?"}
    D -- "Yes" --> P1["Plan 1 (default)<br/>Exp 1 = main results<br/>Exp 2 = 100-pair validation"]
    D -- "No" --> P2["Plan 2 (fallback)<br/>Exp 2 = main results, grow to 200 pairs<br/>Exp 1 = secondary, with caveats"]
```

## 3. Experiment 1 Data Flow

```mermaid
flowchart LR
    R["MedHallu row"] --> S["context + ground-truth answer<br/>label 0 Supported"]
    R --> H["context + hallucinated answer<br/>label 1 Hallucinated"]
    S --> Q{"Stratified sample 250 questions<br/>by difficulty, then split by question"}
    H --> Q
    Q --> DEV["dev.jsonl<br/>50 questions, 100 pairs"]
    Q --> TEST["test.jsonl<br/>200 questions, 400 pairs"]
```

## 4. Experiment 2 RAG Pipeline

```mermaid
flowchart TB
    C["PubMedQA pqa_labeled abstracts<br/>about 1,000 documents"] --> CH["Chunk about 250 tokens<br/>keep doc_id per chunk"]
    CH --> EM["Embed on laptop<br/>BAAI/bge-small-en-v1.5"]
    EM --> FX[("FAISS IndexFlatIP<br/>normalized vectors")]
    QS["100 questions<br/>not in Exp 1 test"] --> COND{"Condition"}
    COND -- "50 normal" --> RN["Retrieve top-3"]
    COND -- "50 degraded" --> RD["Retrieve top-k, drop chunks<br/>from own source doc, keep top-3"]
    FX --> RN
    FX --> RD
    RN --> G["Groq generator<br/>generator_v1 prompt, temp 0"]
    RD --> G
    G --> OUT["generated.jsonl"]
    OUT --> SHEET["annotation sheet<br/>annotator_1.csv / annotator_2.csv"]
    SHEET --> K["kappa + disagreement list"]
    K --> LAB["labeled.jsonl<br/>final human labels"]
```

## 5. Verifier Design

```mermaid
flowchart TB
    IN["Pair: context + answer"] --> FA1
    IN --> FB1
    IN --> FB2
    IN --> BL1

    subgraph A["Filter A: API LLM judge"]
        FA1["Frozen judge_v1 prompt<br/>temperature 0"] --> FA2["Parse JSON<br/>verdict + confidence"]
        FA2 -- "parse fail" --> FA3["Retry once, else<br/>record parse_failure"]
    end

    subgraph B["Filter B: local NLI cross-encoder"]
        FB1["Chunk context<br/>under 512 tokens with hypothesis"]
        FB2["Split answer into sentences<br/>pysbd"]
        FB1 --> FB3["P(entailment) for every<br/>sentence x chunk"]
        FB2 --> FB3
        FB3 --> FB4["sentence score = max over chunks<br/>answer score = min over sentences"]
        FB4 --> FB5{"score below<br/>dev threshold?"}
    end

    subgraph R["Baseline: ROUGE-L"]
        BL1["ROUGE-L answer vs context"] --> BL2{"score below<br/>dev threshold?"}
    end

    FA2 --> OUTV["Supported 0 / Hallucinated 1"]
    FB5 --> OUTV
    BL2 --> OUTV
```

## 6. Filter A Call Sequence (Cache and Retry)

```mermaid
sequenceDiagram
    participant R as run_verifier
    participant J as filter_api.JudgeClient
    participant C as cache.JsonlCache
    participant G as Gemini API

    R->>J: verify(pair, mode)
    J->>J: check prompt hash vs FROZEN.json
    alt mode = normal and cache hit
        J->>C: get(key)
        C-->>J: cached record
    else mode = timing or cache miss
        J->>G: request (rate limited, tenacity backoff)
        G-->>J: raw text + usage
        J->>J: parse JSON
        opt parse failed
            J->>G: retry once
            G-->>J: raw text
        end
        J->>C: append(record with latency, tokens)
    end
    J-->>R: VerifierResult
```

## 7. Module Dependency Graph

Arrows mean "imports". `common/` has no project imports, so it can be tested alone.

```mermaid
flowchart BT
    subgraph common["src/common"]
        CFG["config.py"]
        IO["io.py (JSONL, schemas)"]
        CA["cache.py"]
        LOG["logging_utils.py"]
        MAN["manifest.py"]
        TXT["text.py (sentences, chunking)"]
    end

    PIL["pilot_checks.py"] --> IO & CFG
    B1["build_exp1_pairs.py"] --> IO & CFG
    BI["build_index.py"] --> TXT & IO & CFG
    GR["generate_rag.py"] --> CA & IO & CFG
    AN["annotation.py"] --> IO & CFG
    FAPI["filters/filter_api.py"] --> CA & CFG
    FNLI["filters/filter_nli.py"] --> TXT & CFG
    FR["filters/baseline_rouge.py"] --> CFG
    BASE["filters/base.py"]
    FAPI --> BASE
    FNLI --> BASE
    FR --> BASE
    TUNE["tune_thresholds.py"] --> FNLI & FR & MET
    RUN["run_verifiers.py"] --> FAPI & FNLI & FR & MAN
    TIM["timing.py"] --> FAPI & FNLI & FR & MAN
    MET["evaluation/metrics.py"]
    ST["evaluation/stats.py"]
    EV["evaluate.py"] --> MET & ST & IO
    XE["cross_experiment.py"] --> MET & IO
    FG["figures.py"] --> IO
```

## 8. Runtime Memory Budget (8 GB)

Approximate peak for Exp 2 retrieval plus Filter B, taken from the methodology.

```mermaid
pie showData
    title Peak RAM (GB), retrieval + Filter B
    "OS + light desktop" : 1.2
    "Python + PyTorch" : 0.7
    "DeBERTa-v3-small" : 0.6
    "bge-small + FAISS" : 0.25
    "Data + results" : 0.25
    "Free headroom" : 5.0
```

Filter A and the generator run over the network, so no large model is ever loaded locally.

## 9. Directory Structure

Extends the structure in Methodology C section 10. Original file names are kept; filters, evaluation, and shared utilities are grouped into subpackages.

```text
hallucination-verifier-c/
├── Agent.md                      # agent instructions (this doc set)
├── Rules.md
├── Architecture.md
├── Design.md
├── Phase.md
├── README.md                     # setup, how to reproduce, "not for clinical use"
├── pyproject.toml
├── uv.lock
├── .env.example                  # GROQ_API_KEY=, GEMINI_API_KEY=, HF_TOKEN=
├── .gitignore                    # .env, data/, results/*/raw/, *.index, logs/
│
├── configs/
│   ├── config.yaml               # all paths, model IDs, seeds, sizes, thresholds file
│   └── pricing.yaml              # judge prices + checked_on date (filled by humans)
│
├── prompts/
│   ├── judge_v1.txt              # Filter A prompt (frozen after dev)
│   ├── generator_v1.txt          # Exp 2 generator prompt (frozen before generation)
│   └── FROZEN.json               # {"judge_v1.txt": "<sha256>", ...}
│
├── data/                         # git-ignored
│   ├── raw/                      # HF snapshots at pinned revisions
│   ├── pilot/
│   │   ├── fields_20.json
│   │   ├── spotcheck_50.csv      # humans fill supported_yes_no
│   │   └── pilot_report.json
│   ├── exp1_medhallu/
│   │   ├── dev.jsonl
│   │   └── test.jsonl
│   ├── exp2_rag/
│   │   ├── questions.jsonl       # 100 questions + condition
│   │   ├── corpus_chunks.jsonl
│   │   ├── faiss.index
│   │   ├── generated.jsonl
│   │   ├── annotation/
│   │   │   ├── template.csv
│   │   │   ├── annotator_1.csv
│   │   │   ├── annotator_2.csv
│   │   │   └── disagreements.csv
│   │   ├── labeled.csv           # final resolved labels (human)
│   │   └── labeled.jsonl         # validated conversion of labeled.csv
│   └── cache/
│       ├── judge_gemini.jsonl
│       └── generator_groq.jsonl
│
├── src/
│   ├── __init__.py
│   ├── common/
│   │   ├── config.py             # load + validate config.yaml
│   │   ├── io.py                 # JSONL read/write, pydantic schemas
│   │   ├── cache.py              # append-only JSONL cache with keys
│   │   ├── text.py               # sentence split, token-aware chunking
│   │   ├── manifest.py           # run_id, run_manifest.json, machine info
│   │   ├── prompts.py            # load prompt, verify hash vs FROZEN.json
│   │   └── logging_utils.py
│   ├── pilot_checks.py
│   ├── build_exp1_pairs.py
│   ├── build_index.py
│   ├── generate_rag.py
│   ├── annotation.py             # template export, kappa, disagreements, merge
│   ├── filters/
│   │   ├── base.py               # Verifier protocol + VerifierResult
│   │   ├── filter_api.py         # Filter A
│   │   ├── filter_nli.py         # Filter B
│   │   └── baseline_rouge.py     # Baseline
│   ├── tune_thresholds.py        # dev only, writes thresholds.json
│   ├── run_verifiers.py          # scores a split with all verifiers
│   ├── timing.py                 # latency, load time, peak RAM protocol
│   ├── evaluation/
│   │   ├── metrics.py            # P, R, F1, FNR, FPR, AUROC, cost
│   │   └── stats.py              # McNemar, bootstrap CI, kappa
│   ├── evaluate.py               # per-experiment tables + breakdowns
│   ├── cross_experiment.py       # ranking check + threshold transfer
│   └── figures.py                # all paper figures
│
├── results/
│   ├── thresholds.json           # frozen after dev tuning
│   ├── pilot/
│   ├── exp1/<run_id>/            # predictions, metrics, timing, manifest
│   ├── exp2/<run_id>/
│   ├── cross/<run_id>/
│   └── figures/                  # PNG + PDF, 300 dpi
│
├── notebooks/                    # exploration only, never source of reported numbers
│   └── 00_explore_medhallu.ipynb
│
├── tests/
│   ├── fixtures/                 # 10-row toy datasets
│   ├── test_io.py
│   ├── test_split.py             # no question in both splits
│   ├── test_text.py
│   ├── test_filter_nli.py        # max/min aggregation, label order
│   ├── test_filter_api.py        # JSON parsing, retry, mocked client
│   ├── test_metrics.py           # hand-computed examples
│   ├── test_stats.py
│   └── test_leakage.py           # Exp 2 vs Exp 1 test overlap = 0
│
├── scripts/
│   ├── setup_env.sh
│   └── run_all.sh                # full pipeline from cache
│
└── logs/                         # git-ignored
```

## 10. Layer Responsibilities

| Layer | Modules | Owns | Must not |
| --- | --- | --- | --- |
| Common | `src/common/*` | Config, schemas, cache, text utils, manifests | Import any other project module |
| Data build | `pilot_checks`, `build_exp1_pairs`, `build_index`, `generate_rag`, `annotation` | Creating validated JSONL datasets | Compute metrics |
| Verification | `filters/*`, `run_verifiers`, `tune_thresholds`, `timing` | Producing scores and verdicts | Read labels (except `tune_thresholds` on dev) |
| Evaluation | `evaluation/*`, `evaluate`, `cross_experiment` | Metrics, statistics, comparisons | Call any API or model |
| Presentation | `figures` | Plots | Compute new metrics |

The key separation: **verifiers never see labels during scoring**, and **evaluation never calls models**. This makes leakage structurally hard.
