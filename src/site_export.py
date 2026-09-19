"""Site export script: collects metrics from experiment results into results/site/numbers_of_record.json.

Per Website_Prompt.md §7:
- Reads only committed summary tables/metrics from the latest valid run folder of each experiment
  (the run ID recorded in results/LATEST.json or per-experiment latest pointers).
- Never recomputes metrics.
- Populates numbers_of_record.json following the defined schema.
"""

from __future__ import annotations

import json
import os
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from src.common.logging_utils import get_logger

logger = get_logger(__name__)

TILE_REGISTRY: dict[str, str] = {
    "pilot.unsupported_rate": "Phase 1",
    "pilot.rouge_auroc": "Phase 1",
    "exp1.filter_a.f1": "Phase 8",
    "exp1.filter_b.f1": "Phase 8",
    "exp1.rouge.f1": "Phase 8",
    "exp1.filter_a.fnr": "Phase 8",
    "exp1.filter_b.fnr": "Phase 8",
    "exp1.mcnemar_ab.p": "Phase 8",
    "timing.filter_b.median_ms": "Phase 5",
    "timing.filter_a.median_ms": "Phase 5",
    "cost.filter_a.per_1k_usd": "Phase 5",
    "exp2.kappa": "Phase 6",
    "exp2.filter_a.f1": "Phase 8",
    "exp2.filter_b.f1": "Phase 8",
    "cross.ranking_agrees": "Phase 9",
}


def get_git_sha() -> str:
    """Get short git SHA."""
    sha = os.environ.get("GITHUB_SHA", "")
    if sha:
        return sha[:7]
    try:
        res = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
            timeout=5,
        )
        return res.stdout.strip()
    except Exception:
        return "unknown"


def export_site_numbers(
    results_dir: Path = Path("results"),
    output_path: Path = Path("results/site/numbers_of_record.json"),
) -> dict[str, Any]:
    """Collect available metrics from results into numbers_of_record.json."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    latest_pointer = results_dir / "LATEST.json"

    latest_runs: dict[str, str] = {}
    if latest_pointer.exists():
        try:
            with open(latest_pointer, encoding="utf-8") as f:
                latest_runs = json.load(f)
        except Exception as e:
            logger.warning("Failed to read %s: %s", latest_pointer, e)

    numbers: dict[str, Any] = {}

    # Check for pilot metrics (Phase 1)
    pilot_metrics_file = results_dir / "pilot" / "metrics.json"
    if pilot_metrics_file.exists():
        try:
            with open(pilot_metrics_file, encoding="utf-8") as f:
                pilot_data = json.load(f)
            for k in ["pilot.unsupported_rate", "pilot.rouge_auroc"]:
                if k in pilot_data:
                    val = pilot_data[k]
                    if isinstance(val, dict):
                        numbers[k] = val
                    else:
                        numbers[k] = {
                            "value": val,
                            "display": f"{val:.4f}" if isinstance(val, float) else str(val),
                            "source": str(pilot_metrics_file),
                        }
        except Exception as e:
            logger.warning("Failed to read %s: %s", pilot_metrics_file, e)

    # Check for exp1 metrics (Phases 5, 8)
    exp1_run_id = latest_runs.get("exp1")
    if exp1_run_id:
        exp1_metrics_file = results_dir / "exp1" / exp1_run_id / "metrics.json"
        if exp1_metrics_file.exists():
            try:
                with open(exp1_metrics_file, encoding="utf-8") as f:
                    exp1_data = json.load(f)
                for k, v in exp1_data.items():
                    if k in TILE_REGISTRY:
                        numbers[k] = v
            except Exception as e:
                logger.warning("Failed to read %s: %s", exp1_metrics_file, e)

    # Check for exp2 metrics (Phases 6, 8)
    exp2_run_id = latest_runs.get("exp2")
    if exp2_run_id:
        exp2_metrics_file = results_dir / "exp2" / exp2_run_id / "metrics.json"
        if exp2_metrics_file.exists():
            try:
                with open(exp2_metrics_file, encoding="utf-8") as f:
                    exp2_data = json.load(f)
                for k, v in exp2_data.items():
                    if k in TILE_REGISTRY:
                        numbers[k] = v
            except Exception as e:
                logger.warning("Failed to read %s: %s", exp2_metrics_file, e)

    record = {
        "generated_at": datetime.now(UTC).isoformat(),
        "git_sha": get_git_sha(),
        "numbers": numbers,
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(record, f, indent=2)

    logger.info("Exported %d numbers to %s", len(numbers), output_path)
    return record


if __name__ == "__main__":
    export_site_numbers()
