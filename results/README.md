# Results (`results/`)

This directory contains experimental outputs, timing benchmarks, evaluation metrics, statistical tests, and publication tables.

## Directory Layout

```text
results/
├── LATEST.json                   # Pointers to latest valid run_id for each experiment
├── thresholds.json               # Frozen decision thresholds tuned strictly on Exp 1 dev
├── figures/                      # Generated vector and PNG figures for the paper
├── pilot/                        # Phase 1 pilot verification checks and metrics.json
├── dev_tuning/                   # Dev split scoring outputs used for threshold tuning
├── exp1/
│   └── <run_id>/                 # Timestamped experiment run (e.g. 20260115-1430-a1b2)
│       ├── manifest.json         # Snapshot of config, git commit, prompt hashes, environment
│       ├── raw/                  # Raw predictions per verifier (.jsonl, git-ignored)
│       ├── metrics.json          # Precision, Recall, F1, FNR, FPR, McNemar p-value
│       └── tables/               # Formatted markdown/CSV tables of record
├── exp2/
│   └── <run_id>/                 # Phase 7 & 8 real RAG generation evaluations
├── cross/
│   └── <run_id>/                 # Phase 9 cross-experiment ranking, threshold transfer, and qualitative review
└── site/
    ├── numbers_of_record.json    # Published metrics consumed by website tiles
    └── README.md                 # Schema documentation
```

## Reproducibility Rules

- Every experiment run must write an immutable `manifest.json` containing the exact `git_commit`, `config_snapshot`, `prompt_hashes`, and `machine_info` (CPU model, RAM, OS, Python/Torch version) per Rule R4.3.
- Raw prediction files in `raw/` are git-ignored due to size; summary metrics and tables are committed.
- `src/site_export.py` collects validated metrics from `results/<exp>/<run_id>/` into `results/site/numbers_of_record.json`.

---
*Research prototype. Not for clinical use.*
