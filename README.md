# MedVerify-C (Hallucination Verifier C)

**Local NLI Cross-Encoder vs API-Based LLM-as-a-Judge for Hallucination Verification in Healthcare Agentic RAG**

> ⚠️ **Research prototype — not for clinical use.** This is an academic research project. It is not validated for medical decision-making and must not be used in any clinical or patient-facing setting.

---

## Overview

This research repository evaluates whether a lightweight, local natural language inference (NLI) cross-encoder running purely on consumer laptop CPU hardware can reliably verify medical answer faithfulness in healthcare Agentic Retrieval-Augmented Generation (RAG) pipelines, matching the clinical safety profile of commercial cloud LLM judges.

The system evaluates two primary verifiers against a lexical overlap baseline:
- **Filter B (Local NLI Cross-Encoder):** `cross-encoder/nli-deberta-v3-small` (44M parameters) executing locally on CPU.
- **Filter A (API LLM Judge):** `gemini-3.6-flash` prompted at temperature 0 with structured output JSON.
- **Baseline (Lexical Overlap):** Sentence-level ROUGE-L overlap (`rouge-score`).

---

## Researchers & Institution

- **Researchers:** Muhammad Saad, Rabia Qaiser — University of Engineering and Technology (UET) Peshawar, Jalozai Campus
- **Supervisor:** Dr. Laeeq Ahmed
- **Project Timeline:** September 18, 2026 – October 3, 2026

---

## Key Experimental Findings

1. **Zero False Negative Rate ($\text{FNR} = 0.0000$):** Filter B intercepted 100% of hallucinations across both the 400-pair MedHallu benchmark ($n=400$, 200 questions) and the 200-pair real PubMedQA RAG evaluation ($n=200$, 100 normal, 100 degraded).
2. **Inter-Annotator Agreement (Gate G2):** Two independent human reviewers blindly evaluated all 200 RAG pairs, achieving 100.00% raw agreement and Cohen's $\kappa = 1.0000$ (9 / 200 = 4.5% real-world hallucination prevalence).
3. **Cross-Experiment Ranking & Threshold Transfer:** Verifier performance ranking held strictly across both domains ($\text{Filter B} \ge \text{ROUGE-L}$). Calibrated dev thresholds transferred from benchmark to real RAG with an $F_1$ gap of only **0.0048**.
4. **Edge Computational Efficiency:** Filter B achieved a median inference latency of **332.1 ms** ($p_{95} = 378.4\text{ ms}$) and **855.7 MB peak RAM** on an AMD Ryzen 5 7450U CPU, completely avoiding the **$0.0575 / 1,000 query** shadow cost and privacy risks of commercial APIs.

---

## Pinned Models and Dataset Revisions

To ensure strict scientific reproducibility (Rules R2.1, R4.4), all model identifiers and dataset commit hashes are pinned:

### Models
- **Embedder:** `BAAI/bge-small-en-v1.5`
- **NLI Cross-Encoder:** `cross-encoder/nli-deberta-v3-small` (44M parameters, PyTorch CPU, 6 threads)
- **Generator:** `qwen/qwen3.8-27b` (via Groq at temperature 0, `max_tokens: 256`)
- **API Judge:** `gemini-3.6-flash` (via Google AI Studio at temperature 0, `max_tokens: 1000`)

### Datasets
- **MedHallu:** `UTAustin-AIHealth/MedHallu` (`pqa_labeled` split) pinned at commit `515060458a945c633debc6fd5baac7764416b724`
- **PubMedQA:** `qiaojin/PubMedQA` (`pqa_labeled` split) pinned at commit `9001f2853fb87cab8d220904e0de81ac6973b318`

---

## Hardware Requirements

- **Processor:** AMD Ryzen 5 7450U CPU (6 physical cores, 12 threads) or equivalent x86_64 CPU
- **Memory:** 8 GB RAM (peak process RAM observed: 855.7 MB)
- **Hardware Acceleration:** No GPU required (CPU-only PyTorch build)
- **Operating System:** Windows 11 / Ubuntu 22.04 LTS / macOS 13+

---

## Environment Setup

```bash
# 1. Clone the repository
git clone https://github.com/saadktk10/reducing-hallucination-in-healthcare-using-agentic-ai-in-rag.git
cd reducing-hallucination-in-healthcare-using-agentic-ai-in-rag

# 2. Set up virtual environment and dependencies (Linux / macOS)
bash scripts/setup_env.sh

# 3. Configure API keys (optional if reproducing purely from cached artifacts)
cp .env.example .env
# Fill GROQ_API_KEY, GEMINI_API_KEY, HF_TOKEN if running fresh API calls

# 4. Verify test suite and static analysis
pytest -q
ruff check .
python -c "import torch; print(torch.__version__, torch.cuda.is_available())"
# Expected output: 2.2.x+cpu, False
```

---

## Full Pipeline Reproduction

All reported results, evaluation tables, cross-experiment statistics, and publication figures can be reproduced in a single command using cached artifacts:

### Linux / macOS / Git Bash
```bash
bash scripts/run_all.sh
```

To also re-run local CPU inference for Filter B and ROUGE-L on the test and RAG splits before evaluation:
```bash
bash scripts/run_all.sh --rerun-verifiers
```

### Windows PowerShell
```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run_all.ps1
```

To re-run local CPU verifiers on Windows:
```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run_all.ps1 -RerunVerifiers
```

Each run directory under `results/` includes a cryptographic `run_manifest.json` recording the exact git commit, configuration snapshot, prompt hashes, and model IDs used.

---

## Documentation Website

The project includes an interactive, living documentation website styled after AdaptiShield, built with MkDocs Material:

```bash
python -m mkdocs build --strict
python -m mkdocs serve
```

Live website: [https://saadktk10.github.io/reducing-hallucination-in-healthcare-using-agentic-ai-in-rag/](https://saadktk10.github.io/reducing-hallucination-in-healthcare-using-agentic-ai-in-rag/)

---

## Study Limitations

1. **Synthetic Mutation Artifacts (MedHallu):** Synthetic entity substitutions in benchmark datasets introduce lexical dissimilarity, allowing lexical baselines like ROUGE-L to achieve artificially high performance.
2. **Class Imbalance in Real RAG:** Frontier foundation models (Qwen3.8-27b) prompted with authoritative context at temperature 0 produce unsupported statements in only 4.5% of cases. In low-prevalence regimes, $F_1$ is heavily depressed even when safety recall is 100%.
3. **Conservative Decision Thresholds:** Maximizing $F_1$ on dev yields a threshold ($\tau_B = 1.0$) that drives false alarms ($\text{FPR} = 1.0$) in real RAG. Filter B is therefore optimized as a high-sensitivity triage tripwire that routes flagged cases to human review or secondary agents.
4. **Domain Scope:** Evaluation is restricted to English-language biomedical literature.

---

## Dataset Licenses and Data Governance

- **PubMedQA:** Distributed under the [MIT License](https://github.com/pubmedqa/pubmedqa/blob/master/LICENSE). Permitted for open academic research and redistribution.
- **MedHallu:** Derived from open medical literature under [CC BY-NC 4.0](https://creativecommons.org/licenses/by-nc/4.0/) (Attribution-NonCommercial).
- **Codebase:** Distributed under the MIT License.
- In compliance with Rule R7.1 and R5.8, no protected health information (PHI) or patient records are used in this study. Large artifacts, cached responses, and vector indices are managed locally and excluded from version control via `.gitignore`.

---
*Research prototype. Not for clinical use.*
