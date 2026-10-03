#!/usr/bin/env bash
# Reproduce all reported results from cached API responses and local verifiers.
# Usage: bash scripts/run_all.sh [--rerun-verifiers]
#
# Prerequisites:
#   - Environment set up via scripts/setup_env.sh
#   - data/cache/ populated with cached API responses
#   - Frozen prompts and thresholds in place
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

if [ -f .venv/bin/activate ]; then
  source .venv/bin/activate
elif [ -f .venv/Scripts/activate ]; then
  source .venv/Scripts/activate
fi

CONFIG="configs/config.yaml"

echo "=== Hallucination Verifier C — Full Pipeline Reproduction ==="
echo "Config: $CONFIG"
echo ""

# Optional: Re-run local verifiers on test and RAG splits if requested
if [ "${1:-}" = "--rerun-verifiers" ]; then
    echo "--- Re-running local verifiers on test and RAG splits ---"
    python -m src.run_verifiers --config "$CONFIG" --split test --verifier filter_b
    python -m src.run_verifiers --config "$CONFIG" --split test --verifier rouge
    python -m src.run_verifiers --config "$CONFIG" --split rag --verifier filter_b
    python -m src.run_verifiers --config "$CONFIG" --split rag --verifier rouge
fi

echo "--- 1. Evaluating Experiment 1 (MedHallu test, n=400) ---"
python -m src.evaluate --config "$CONFIG" --exp exp1

echo "--- 2. Evaluating Experiment 2 (PubMedQA RAG, n=200) ---"
python -m src.evaluate --config "$CONFIG" --exp exp2

echo "--- 3. Running Cross-Experiment Synthesis ---"
python -m src.cross_experiment --config "$CONFIG"

echo "--- 4. Generating Publication Figures (PNG & PDF) ---"
python -m src.figures --config "$CONFIG"

echo "--- 5. Exporting Numbers of Record for Documentation ---"
python -m src.site_export

echo ""
echo "=== Full reproduction completed successfully! ==="
