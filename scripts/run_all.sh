#!/usr/bin/env bash
# Reproduce all reported results from cached API responses.
# Usage: bash scripts/run_all.sh
#
# Prerequisites:
#   - Environment set up via scripts/setup_env.sh
#   - data/cache/ populated with cached API responses
#   - Frozen prompts and thresholds in place
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"
source .venv/bin/activate

CONFIG="configs/config.yaml"

echo "=== Hallucination Verifier C — Full Pipeline ==="
echo "Config: $CONFIG"
echo ""

# Phase 2: Build Experiment 1 pairs and splits
# python -m src.build_exp1_pairs --config "$CONFIG"

# Phase 3: Run verifiers on dev (thresholds already frozen)
# python -m src.run_verifiers --config "$CONFIG" --split dev

# Phase 5: Run verifiers on test
# python -m src.run_verifiers --config "$CONFIG" --split test

# Phase 7: Run verifiers on RAG set
# python -m src.run_verifiers --config "$CONFIG" --split rag

# Phase 8: Evaluate
# python -m src.evaluate --config "$CONFIG" --exp exp1
# python -m src.evaluate --config "$CONFIG" --exp exp2

# Phase 9: Cross-experiment analysis
# python -m src.cross_experiment --config "$CONFIG"

# Phase 10: Generate figures
# python -m src.figures --config "$CONFIG"

echo "=== Pipeline steps are commented out. Uncomment as phases complete. ==="
