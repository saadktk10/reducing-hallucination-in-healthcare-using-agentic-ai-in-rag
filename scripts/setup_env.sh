#!/usr/bin/env bash
# Phase 0: Environment setup script.
# Usage: bash scripts/setup_env.sh
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

echo "=== Hallucination Verifier C — Environment Setup ==="
echo "Repo root: $REPO_ROOT"

# 1. Check Python version
PYTHON_VERSION=$(python3 --version 2>&1)
echo "Python: $PYTHON_VERSION"

# 2. Create virtual environment with uv if available, else venv
if command -v uv &> /dev/null; then
    echo "Using uv for environment setup..."
    uv venv .venv --python 3.12
    source .venv/bin/activate

    # Install CPU-only PyTorch first
    uv pip install torch --index-url https://download.pytorch.org/whl/cpu

    # Install project with dev dependencies
    uv pip install -e ".[dev]"

    # Lock dependencies
    uv lock 2>/dev/null || echo "uv lock skipped (may need pyproject adjustments)"
else
    echo "uv not found, falling back to python venv..."
    python3 -m venv .venv
    source .venv/bin/activate

    pip install --upgrade pip

    # Install CPU-only PyTorch first
    pip install torch --index-url https://download.pytorch.org/whl/cpu

    # Install project with dev dependencies
    pip install -e ".[dev]"
fi

# 3. Create data directories (git-ignored)
mkdir -p data/raw data/pilot data/exp1_medhallu data/exp2_rag/annotation data/cache
mkdir -p results/pilot results/figures
mkdir -p logs
mkdir -p notebooks

echo ""
echo "=== Verification ==="

# 4. Check torch is CPU-only
python3 -c "import torch; print(f'torch {torch.__version__}, CUDA available: {torch.cuda.is_available()}')"

# 5. Run tests and linting
echo ""
echo "--- pytest ---"
python3 -m pytest -q

echo ""
echo "--- ruff ---"
python3 -m ruff check .

echo ""
echo "=== Setup complete ==="
