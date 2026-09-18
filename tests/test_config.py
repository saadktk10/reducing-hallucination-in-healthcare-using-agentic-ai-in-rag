"""Tests for src/common/config.py — config loading and validation."""

from pathlib import Path

import pytest
import yaml

from src.common.config import Config, load_config


FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def sample_config_path(tmp_path: Path) -> Path:
    """Write a minimal valid config to a temp file."""
    cfg = {
        "project": "test-project",
        "seed": 42,
        "plan": 1,
        "paths": {"data": "data", "cache": "data/cache", "results": "results", "prompts": "prompts"},
        "datasets": {
            "medhallu": {
                "hf_id": "UTAustin-AIHealth/MedHallu",
                "config": "pqa_labeled",
                "revision": "TBD",
                "columns": {
                    "question": "Question",
                    "context": "Knowledge",
                    "ground_truth": "Ground Truth",
                    "hallucinated": "Hallucinated Answer",
                    "difficulty": "Difficulty Level",
                    "category": "Category of Hallucination",
                },
            },
            "pubmedqa": {
                "hf_id": "qiaojin/PubMedQA",
                "config": "pqa_labeled",
                "revision": "TBD",
            },
        },
    }
    path = tmp_path / "config.yaml"
    with open(path, "w") as f:
        yaml.dump(cfg, f)
    return path


def test_load_config_valid(sample_config_path: Path) -> None:
    """Valid config loads without error and has correct values."""
    cfg = load_config(sample_config_path)
    assert cfg.project == "test-project"
    assert cfg.seed == 42
    assert cfg.plan == 1
    assert cfg.datasets.medhallu.hf_id == "UTAustin-AIHealth/MedHallu"
    assert cfg.exp1.n_questions == 250  # default value


def test_load_config_missing_file() -> None:
    """Missing config file raises FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        load_config("nonexistent.yaml")


def test_load_config_invalid_yaml(tmp_path: Path) -> None:
    """Config missing required fields raises ValidationError."""
    path = tmp_path / "bad.yaml"
    path.write_text("project: test\n")
    with pytest.raises(Exception):  # pydantic.ValidationError
        load_config(path)


def test_config_defaults() -> None:
    """Config model applies defaults for optional fields."""
    minimal = {
        "datasets": {
            "medhallu": {"hf_id": "test", "config": "test"},
            "pubmedqa": {"hf_id": "test", "config": "test"},
        },
    }
    cfg = Config(**minimal)
    assert cfg.seed == 42
    assert cfg.plan == 1
    assert cfg.exp1.dev_questions == 50
    assert cfg.filter_b.num_threads == 6
    assert cfg.timing.warmup_pairs == 10


def test_load_real_config() -> None:
    """The actual configs/config.yaml loads without error."""
    real_path = Path("configs/config.yaml")
    if real_path.exists():
        cfg = load_config(real_path)
        assert cfg.project == "hallucination-verifier-c"
