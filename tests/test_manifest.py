"""Tests for src/common/manifest.py — run ID and machine info."""

import json
import re
from pathlib import Path

from src.common.manifest import generate_run_id, get_machine_info, write_manifest


def test_run_id_format() -> None:
    """Run ID matches YYYYMMDD-HHMM-<sha> format."""
    run_id = generate_run_id()
    # Pattern: 8 digits, dash, 4 digits, dash, alphanumeric
    assert re.match(r"\d{8}-\d{4}-.+", run_id), f"Unexpected run_id format: {run_id}"


def test_machine_info_fields() -> None:
    """Machine info has required fields."""
    info = get_machine_info()
    assert "cpu" in info
    assert "ram_total_gb" in info
    assert "os" in info
    assert "python" in info
    assert isinstance(info["ram_total_gb"], float)


def test_write_manifest(tmp_path: Path) -> None:
    """Manifest is written as valid JSON with expected keys."""
    run_dir = tmp_path / "results" / "test-run"
    manifest_path = write_manifest(
        run_dir,
        config_snapshot={"seed": 42},
        prompt_hashes={"judge_v1.txt": "abc123"},
        model_ids={"judge": "gemini-flash"},
        dataset_revision="abc123",
    )

    assert manifest_path.exists()

    with open(manifest_path) as f:
        data = json.load(f)

    assert data["config_snapshot"]["seed"] == 42
    assert data["prompt_hashes"]["judge_v1.txt"] == "abc123"
    assert data["model_ids"]["judge"] == "gemini-flash"
    assert "machine_info" in data
    assert "timestamp_utc" in data
