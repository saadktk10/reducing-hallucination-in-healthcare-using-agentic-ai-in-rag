# Operational Scripts (`scripts/`)

This directory contains utility shell scripts for environment provisioning, pipeline execution, and local development.

## Scripts

| Script | Purpose | Usage |
| :--- | :--- | :--- |
| `setup_env.sh` | Provisions the local Python 3.12 virtual environment, installs CPU-only PyTorch, installs project dependencies, and verifies imports. | `bash scripts/setup_env.sh` |
| `smoke_apis.py` | Phase 0 Task 7 API smoke testing: verifies Gemini judge and Groq generator, measures latency, and populates `data/cache/`. | `python -m scripts.smoke_apis` |
| `run_all.sh` | Orchestrates the end-to-end evaluation pipeline with timing and manifests. | `bash scripts/run_all.sh [args]` |
| `generate_architecture_drawio.py` | Compiles the full end-to-end research architecture diagram in draw.io XML format adhering to the AdaptiShield v3 specification. | `python scripts/generate_architecture_drawio.py` |

## Notes

- Shell scripts use `set -euo pipefail` to fail loudly on any error.
- All scripts are executed from the repository root.

---
*Research prototype. Not for clinical use.*
