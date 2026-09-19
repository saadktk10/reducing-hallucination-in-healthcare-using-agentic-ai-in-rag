"""Run manifest and machine info utilities.

Every results folder includes a run_manifest.json linking the output to
exact code state, config, and environment (Rule R4.3).
"""

from __future__ import annotations

import json
import logging
import os
import platform
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path

import psutil

logger = logging.getLogger(__name__)


def find_git_binary() -> str:
    """Find git executable on PATH or via GitHub Desktop on Windows."""
    git_bin = shutil.which("git")
    if git_bin:
        return git_bin
    local_app = Path(os.path.expanduser(r"~\AppData\Local\GitHubDesktop"))
    if local_app.exists():
        matches = sorted(local_app.glob("app-*/resources/app/git/cmd/git.exe"))
        if matches:
            return str(matches[-1])
    return "git"


def _short_git_sha() -> str:
    """Get the short git SHA of HEAD, or 'nogit' if unavailable."""
    git_bin = find_git_binary()
    try:
        result = subprocess.run(
            [git_bin, "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
            timeout=5,
        )
        return result.stdout.strip()
    except Exception:
        return "nogit"


def generate_run_id() -> str:
    """Generate a run identifier: YYYYMMDD-HHMM-<short_git_sha>.

    Returns:
        A string like '20260115-1430-a1b2c3d'.
    """
    now = datetime.now(UTC)
    timestamp = now.strftime("%Y%m%d-%H%M")
    sha = _short_git_sha()
    return f"{timestamp}-{sha}"


def get_machine_info() -> dict:
    """Collect machine information for reproducibility.

    Returns:
        A dict with CPU, RAM, OS, Python, and optionally torch info.
    """
    info: dict = {
        "cpu": platform.processor() or platform.machine(),
        "cpu_count_logical": psutil.cpu_count(logical=True),
        "cpu_count_physical": psutil.cpu_count(logical=False),
        "ram_total_gb": round(psutil.virtual_memory().total / (1024**3), 2),
        "ram_available_gb": round(psutil.virtual_memory().available / (1024**3), 2),
        "os": f"{platform.system()} {platform.release()}",
        "python": platform.python_version(),
    }

    try:
        import torch

        info["torch_version"] = torch.__version__
        info["cuda_available"] = torch.cuda.is_available()
        info["torch_num_threads"] = torch.get_num_threads()
    except ImportError:
        info["torch_version"] = None

    return info


def write_manifest(
    run_dir: str | Path,
    *,
    config_snapshot: dict | None = None,
    prompt_hashes: dict[str, str] | None = None,
    model_ids: dict[str, str] | None = None,
    dataset_revision: str | None = None,
    extra: dict | None = None,
) -> Path:
    """Write a run_manifest.json to the given results directory.

    Args:
        run_dir: Directory to write the manifest into.
        config_snapshot: The full config dict at run time.
        prompt_hashes: Map of prompt name to SHA-256.
        model_ids: Map of role to model ID.
        dataset_revision: Pinned HF dataset revision.
        extra: Any additional metadata.

    Returns:
        Path to the written manifest file.
    """
    run_dir = Path(run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)

    manifest = {
        "run_id": run_dir.name,
        "git_commit": _short_git_sha(),
        "timestamp_utc": datetime.now(UTC).isoformat(),
        "machine_info": get_machine_info(),
        "config_snapshot": config_snapshot,
        "prompt_hashes": prompt_hashes or {},
        "model_ids": model_ids or {},
        "dataset_revision": dataset_revision,
    }
    if extra:
        manifest.update(extra)

    manifest_path = run_dir / "run_manifest.json"
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2, default=str)
        f.write("\n")

    logger.info("Wrote manifest to %s", manifest_path)
    return manifest_path
