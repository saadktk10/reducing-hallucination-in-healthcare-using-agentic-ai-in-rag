# Configs (`configs/`)

This directory contains the declarative configuration files for the benchmark pipeline.

## Files

| File | Purpose | Loaded By |
| :--- | :--- | :--- |
| `config.yaml` | Primary research configuration: dataset identifiers, split sizes, seeds, model names, retrieval parameters, and filter thresholds. | `src.common.config.load_config()` |
| `pricing.yaml` | Provider pricing rates (input/output cost per 1M tokens) for computing shadow financial costs (Filter A). | `src.evaluation.cost` |

## Design Principles

- **Config over Code**: Every tunable hyperparameter, dataset identifier, random seed, and model string is declared here, never hardcoded in scripts (Design.md §2).
- **Validation**: All YAML files are validated upon loading using Pydantic models in `src/common/config.py`. Missing required fields or invalid types will fail loudly at startup.
- **Reproducibility**: Experiments record the exact `config_snapshot` in their `manifest.json`.

---
*Research prototype. Not for clinical use.*
