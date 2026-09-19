"""Load and validate configs/config.yaml.

Provides a typed Config model matching all fields from Design.md §2.
Every configurable value lives here — no magic numbers in code (Rule R5.4).
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Sub-models
# ---------------------------------------------------------------------------


class PathsConfig(BaseModel):
    data: str = "data"
    cache: str = "data/cache"
    results: str = "results"
    prompts: str = "prompts"


class DatasetColumnsConfig(BaseModel):
    question: str = "Question"
    context: str = "Knowledge"
    ground_truth: str = "Ground Truth"
    hallucinated: str = "Hallucinated Answer"
    difficulty: str = "Difficulty Level"
    category: str = "Category of Hallucination"


class DatasetConfig(BaseModel):
    hf_id: str
    config: str
    revision: str = "TBD"
    columns: DatasetColumnsConfig | None = None


class DatasetsConfig(BaseModel):
    medhallu: DatasetConfig
    pubmedqa: DatasetConfig


class Exp1Config(BaseModel):
    n_questions: int = 250
    dev_questions: int = 50
    test_questions: int = 200
    stratify_by: str = "difficulty"


class PilotConfig(BaseModel):
    spotcheck_n: int = 50
    fields_n: int = 20
    rouge_dev_questions: int = 50


class Exp2Config(BaseModel):
    n_normal: int = 50
    n_degraded: int = 50
    extra_degraded_max: int = 20
    exclude_exp1_dev: bool = True
    chunk_tokens: int = 250
    chunk_overlap: int = 30
    top_k: int = 3
    degraded_search_k: int = 20


class GeneratorModelConfig(BaseModel):
    provider: str = "groq"
    model_id: str = "TBD"
    temperature: int = 0
    max_tokens: int = 256


class JudgeModelConfig(BaseModel):
    provider: str = "gemini"
    model_id: str = "TBD"
    base_url: str = "https://generativelanguage.googleapis.com/v1beta/openai/"
    temperature: int = 0
    max_tokens: int = 64
    rpm_limit: int | str = "TBD"


class ModelsConfig(BaseModel):
    embedder: str = "BAAI/bge-small-en-v1.5"
    nli_main: str = "cross-encoder/nli-deberta-v3-small"
    nli_optional: str = "cross-encoder/nli-deberta-v3-base"
    generator: GeneratorModelConfig = Field(default_factory=GeneratorModelConfig)
    judge: JudgeModelConfig = Field(default_factory=JudgeModelConfig)


class FilterBConfig(BaseModel):
    num_threads: int = 6
    batch_size: int = 16
    max_length: int = 512
    sentence_splitter: str = "pysbd"


class BaselineConfig(BaseModel):
    rouge_variant: str = "rougeL"
    rouge_field: str = "precision"


class TimingConfig(BaseModel):
    warmup_pairs: int = 10
    repeats: int = 2
    percentiles: list[int] = Field(default_factory=lambda: [50, 95])


class StatsConfig(BaseModel):
    bootstrap_resamples: int = 1000
    ci: float = 0.95
    bootstrap_unit: str = "question"


# ---------------------------------------------------------------------------
# Top-level config
# ---------------------------------------------------------------------------


class Config(BaseModel):
    """Top-level project configuration."""

    project: str = "hallucination-verifier-c"
    seed: int = 42
    plan: int = 1

    paths: PathsConfig = Field(default_factory=PathsConfig)
    datasets: DatasetsConfig
    pilot: PilotConfig = Field(default_factory=PilotConfig)
    exp1: Exp1Config = Field(default_factory=Exp1Config)
    exp2: Exp2Config = Field(default_factory=Exp2Config)
    models: ModelsConfig = Field(default_factory=ModelsConfig)
    filter_b: FilterBConfig = Field(default_factory=FilterBConfig)
    baseline: BaselineConfig = Field(default_factory=BaselineConfig)
    timing: TimingConfig = Field(default_factory=TimingConfig)
    stats: StatsConfig = Field(default_factory=StatsConfig)


# ---------------------------------------------------------------------------
# Loader
# ---------------------------------------------------------------------------


def load_config(path: str | Path = "configs/config.yaml") -> Config:
    """Load and validate the project configuration.

    Args:
        path: Path to the YAML config file.

    Returns:
        A validated Config instance.

    Raises:
        FileNotFoundError: If the config file does not exist.
        pydantic.ValidationError: If the config is invalid.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")

    load_dotenv()

    with open(path, encoding="utf-8") as f:
        raw: dict[str, Any] = yaml.safe_load(f)

    cfg = Config(**raw)
    logger.info("Loaded config from %s (project=%s, plan=%d)", path, cfg.project, cfg.plan)
    return cfg
