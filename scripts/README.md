# Operational Scripts (`scripts/`)

This directory contains utility shell scripts for environment provisioning, pipeline execution, and local development.

## Scripts

| Script | Purpose | Usage |
| :--- | :--- | :--- |
| `setup_env.sh` | Provisions the local Python 3.12 virtual environment, installs CPU-only PyTorch, installs project dependencies, and verifies imports. | `bash scripts/setup_env.sh` |
| `run_pipeline.sh` | Orchestrates the end-to-end evaluation pipeline with timing and manifests. | `bash scripts/run_pipeline.sh [args]` |

## Notes

- Shell scripts use `set -euo pipefail` to fail loudly on any error.
- All scripts are executed from the repository root.

---
*Research prototype. Not for clinical use.*
