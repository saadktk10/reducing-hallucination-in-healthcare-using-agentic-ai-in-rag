# Hallucination Verifier C

**Local NLI Cross-Encoder vs API-Based LLM-as-a-Judge for Hallucination Verification in Healthcare Agentic RAG**

> ⚠️ **Research prototype — not for clinical use.** This is an academic research project. It is not validated for medical decision-making and must not be used in any clinical or patient-facing setting.

## Overview

This research codebase compares two approaches to verifying whether a medical answer is faithfully supported by its evidence:

- **Filter A:** An API-based LLM judge (Gemini Flash via Google AI Studio)
- **Filter B:** A local NLI cross-encoder (`cross-encoder/nli-deberta-v3-small`) running on CPU

A **ROUGE-L baseline** tests whether either filter outperforms simple word overlap.

Two experiments evaluate these verifiers:
- **Experiment 1:** 500 MedHallu pairs with external ground-truth labels
- **Experiment 2:** ~100 RAG-generated answers with independent human annotation

## Researchers

- Muhammad Saad, Rabia Qaiser — UET Peshawar, Jalozai Campus
- Supervisor: Dr. Laeeq Ahmed

## Hardware Requirements

- CPU: AMD Ryzen 5 7450U (or comparable)
- RAM: 8 GB (≈5 GB free during runs)
- GPU: Not required (CPU-only PyTorch)

## Setup

```bash
# 1. Clone the repository
git clone <repo-url> && cd hallucination-verifier-c

# 2. Create environment and install
bash scripts/setup_env.sh

# 3. Copy and fill API keys
cp .env.example .env
# Edit .env with your GROQ_API_KEY, GEMINI_API_KEY, HF_TOKEN

# 4. Verify installation
pytest -q
ruff check .
python -c "import torch; print(torch.__version__, torch.cuda.is_available())"
# Expected: torch version, False (CPU build)
```

## Reproduction

All reported results can be regenerated from cached API responses:

```bash
bash scripts/run_all.sh
```

Each results folder includes a `run_manifest.json` linking to the exact config, model IDs, prompt hashes, and git commit used.

## Project Structure

See `Architecture.md` for the full module dependency graph and directory layout.

## License

Check dataset licenses (MedHallu, PubMedQA) before redistributing any labeled data.
