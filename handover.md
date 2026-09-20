# Session Handover (`handover.md`)

*Rule R9.14: Every agent or researcher session MUST start by reading this file, and MUST conclude by updating it.*

---

## Current State

- **Date**: 2026-09-21
- **Session**: 9 (Completed)
- **Active Branch**: `main`
- **Current Phase**:
  - Phase 0 ✅ Done (Python 3.12, PyTorch CPU, pinned models)
  - Phase 0b ✅ Done (Live documentation site, strict build, CI)
  - Phase 1 ✅ Done (Gate G1 resolved to Plan 2)
  - Phase 2 ✅ Done (MedHallu 500 pairs generated, 100 dev / 400 test)
  - Phase 3 ✅ Done (Verifiers implemented, frozen thresholds & prompts)
  - Phase 4 ✅ Done (PubMedQA FAISS index, 200 RAG answers generated via Groq at temp 0)
  - Phase 5 🟡 Partial (Filter B & Baseline accuracy runs, timing benchmarks, shadow cost computed; Filter A deferred)
  - Phase 6 🟡 Partial (Annotation CSVs re-exported and validated with RFC 4180 compliance; awaiting independent human labeling for Gate G2)
  - Phase 7 🔲 Planned (Verifiers on RAG set, ready post-G2)
  - Phase 8 🟡 Partial (`src/evaluate.py` implemented; Exp 1 evaluated on 400 test pairs: main tables, question bootstrap CIs, McNemar test, breakdowns, `summary.md`; site tiles live; Exp 2 pending G2)
  - Phase 9 🟡 Partial (`src/cross_experiment.py` implemented; Exp 1 ranking & 3 qualitative disagreements exported; Exp 2 transfer check pending G2)
  - Phase 10 🟡 Partial (`src/figures.py` implemented; all 6 paper figures generated in 300 dpi PNG & vector PDF)
  - Phase 11 🔲 Planned
- **Test Status**: 127 passed in `pytest -q`, 0 lint errors in `ruff check .`.
- **Site Build**: `mkdocs build --strict` passing with 0 warnings in 1.1s.
- **Live Documentation**: [https://saadktk10.github.io/reducing-hallucination-in-healthcare-using-agentic-ai-in-rag/](https://saadktk10.github.io/reducing-hallucination-in-healthcare-using-agentic-ai-in-rag/)

---

## Accomplishments (Session 9)

1. **Clarified Diagram Architecture Specifications**:
   - Polled user via interactive clarification questions for layout orientation (horizontal Left-to-Right dataflow), scope (full end-to-end research architecture), file locations (`docs/assets/architecture.drawio` and repository root `architecture.drawio`), and visual theme (modern tech palette with distinct badges and dotted boxes for planned components).
2. **Generated Comprehensive draw.io Architecture Diagram**:
   - Structured the complete research system into 5 horizontal layers with clear orthogonal dataflow:
     - **Layer 1: Data Sources & Ingestion**: MedHallu (`UTAustin-AIHealth/MedHallu:pqa_labeled`), PubMedQA (`qiaojin/PubMedQA:pqa_labeled`), Pilot inspection/spot-check (46% unsupported rate), Gate G1 decision (Plan 2 activation), Local cache & provenance store.
     - **Layer 2: Experiment Data Prep & RAG Generation**: Exp 1 pair generator (250 Qs / 500 pairs) & question-level splitter (100 dev / 400 test), PubMedQA abstract chunker (1,790 chunks), local CPU embedding (`BAAI/bge-small-en-v1.5`), local FAISS vector store (`IndexFlatIP`, 451.8 MB peak RAM), dual retrieval engine (normal top-3 vs degraded top-3 distractors), Groq Cloud API generator (`qwen/qwen3.8-27b` @ temp 0, 256 tokens), Phase 6 annotation sheets (`annotator_1.csv`, `annotator_2.csv`), and Gate G2 human adjudication (dotted box).
     - **Layer 3: Verification Layer (Shared Multi-Verifier)**: Shared verifier coordinator (`src/run_verifiers.py`), dev threshold tuner (`src/tune_thresholds.py`), Baseline ROUGE-L precision (threshold 0.1741, 2.5 ms median), Filter B Local NLI cross-encoder (`cross-encoder/nli-deberta-v3-small` on 6 CPU threads, batch 16, `pysbd` sentence segmentation, threshold 0.0039), Filter A API LLM judge (`gemini-3.6-flash`, structured JSON, `JsonlCache`), Exp 1 test scored runs, and planned Phase 7 RAG run / Filter A full runs (dotted boxes).
     - **Layer 4: Evaluation, Statistics & Profiling**: Core metrics engine (`evaluate.py`: F1, FNR, FPR, AUROC), statistical inference suite (1,000-resample question block bootstrap 95% CIs, McNemar test), difficulty and hallucination category breakdown analyzers, system profiler (`src/timing.py`: p50/p95 latency, RAM, shadow financial cost), cross-experiment comparator (`cross_experiment.py`: ranking agreement & qualitative disagreement mining), and planned Exp 2 RAG evaluation & threshold transfer (dotted boxes).
     - **Layer 5: Presentation, Web & Dissemination**: Numbers of Record canonical store (`results/site/numbers_of_record.json`), 6 publication figures in 300 DPI PNG & vector PDF (`src/figures.py`), site exporter (`site_export.py`), project website (Material for MkDocs with 4 custom hooks), GitHub Actions CI/CD workflows, and planned LaTeX manuscript exporter & Zenodo open science release (dotted boxes).
3. **Automated draw.io Diagram Generator & Test Coverage**:
   - Implemented `scripts/generate_architecture_drawio.py` to compile and validate the XML document.
   - Generated both `docs/assets/architecture.drawio` and `architecture.drawio` in repository root.
   - Added unit tests in `tests/test_architecture_drawio.py` validating XML syntax, the 5 layers, explicit model/tool badges, and dotted boxes for planned components.
   - Test suite expanded from 122 to 127 tests (all passing).
4. **Documentation & Site Synchronization**:
   - Updated `Architecture.md` with links and directory structure entries for `architecture.drawio`.
   - Verified strict MkDocs documentation build (`mkdocs build --strict` passing in 1.1s with 0 warnings).

---

## Immediate Next Tasks (Phase 6 Human Labeling & Gate G2)

1. **Independent Human Labeling (Rule R1.5, R1.6)**:
   - Researcher 1 (Muhammad Saad) opens and labels `data/exp2_rag/annotation/annotator_1.csv`.
   - Researcher 2 (Rabia Qaiser) opens and labels `data/exp2_rag/annotation/annotator_2.csv`.
   - Both annotators refer to `data/exp2_rag/annotation/annotation_guide.md` for definitions and examples.
   - For each row, set `label (Supported/Hallucinated)` to `Supported` (or `0`) or `Hallucinated` (or `1`).
   - Do not share or view each other's labels until all 200 rows are complete.
2. **Compute Inter-Annotator Agreement**:
   - Run `python -m src.annotation kappa` to compute Cohen's kappa and generate `data/exp2_rag/annotation/disagreements.csv`.
3. **Resolve Disagreements (Gate G2)**:
   - Researchers discuss disagreements in `disagreements.csv` and fill `final_label` in `data/exp2_rag/labeled.csv`.
4. **Merge Ground Truth Dataset**:
   - Run `python -m src.annotation merge --config configs/config.yaml` to create `data/exp2_rag/pairs.jsonl`.
   - Check Gate G2 condition class balance (>= 25% Hallucinated).
5. **Execute Phase 7 (Verifiers on RAG set)**:
   - Run `python -m src.run_verifiers --config configs/config.yaml --split rag`.

---
*Research prototype. Not for clinical use.*
