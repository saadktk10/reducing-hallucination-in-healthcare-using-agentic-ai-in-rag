"""JSONL read/write and pydantic data schemas from Design.md §3.

Every JSONL record is validated on read and write (Rule R5.6).
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel, Field
from typing import Literal

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


# ---------------------------------------------------------------------------
# Schemas — Design.md §3
# ---------------------------------------------------------------------------

class Pair(BaseModel):
    """One (question, context, answer, label) record — §3.1."""

    pair_id: str
    question_id: str
    experiment: Literal["exp1", "exp2"]
    split: Literal["dev", "test", "rag"]
    question: str
    context: str
    answer: str
    label: Literal[0, 1] | None = None
    difficulty: str | None = None
    category: str | None = None
    condition: Literal["normal", "degraded"] | None = None
    source_doc_id: str | None = None


class Chunk(BaseModel):
    """A text chunk from a PubMedQA abstract — §3.2."""

    chunk_id: str
    doc_id: str
    text: str
    n_tokens: int


class Generated(BaseModel):
    """A RAG-generated answer — §3.3."""

    question_id: str
    condition: Literal["normal", "degraded"]
    retrieved_chunk_ids: list[str]
    retrieved_doc_ids: list[str]
    own_doc_in_context: bool
    context: str
    answer: str
    generator_model_id: str
    prompt_hash: str
    cache_key: str


class VerifierResult(BaseModel):
    """Output from any verifier — §3.4."""

    pair_id: str
    verifier: Literal["filter_a", "filter_b", "rouge", "filter_b_base"]
    score: float | None = None
    verdict: Literal[0, 1] | None = None
    confidence: float | None = None
    latency_ms: float | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    parse_failure: bool = False
    details: dict = Field(default_factory=dict)


class CacheRecord(BaseModel):
    """An API response cache entry — §3.5."""

    key: str
    provider: str
    model_id: str
    prompt_hash: str
    request_text: str
    response_text: str
    parsed: dict | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    latency_ms: float
    attempt: int
    mode: Literal["normal", "timing"]
    timestamp_utc: str


# ---------------------------------------------------------------------------
# JSONL I/O
# ---------------------------------------------------------------------------

def read_jsonl(path: str | Path, model: type[T]) -> list[T]:
    """Read a JSONL file and validate each record against a pydantic model.

    Args:
        path: Path to the JSONL file.
        model: The pydantic model class to validate against.

    Returns:
        A list of validated model instances.

    Raises:
        FileNotFoundError: If the file does not exist.
        pydantic.ValidationError: If any record fails validation.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"JSONL file not found: {path}")

    records: list[T] = []
    with open(path) as f:
        for line_num, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                raw = json.loads(line)
                records.append(model.model_validate(raw))
            except (json.JSONDecodeError, Exception) as exc:
                raise ValueError(
                    f"Invalid record at {path}:{line_num}: {exc}"
                ) from exc

    logger.info("Read %d records from %s", len(records), path)
    return records


def write_jsonl(path: str | Path, records: list[BaseModel], *, append: bool = False) -> None:
    """Write pydantic model instances to a JSONL file.

    Each record is serialized and validated before writing (Rule R5.6).

    Args:
        path: Output path.
        records: List of pydantic model instances.
        append: If True, append to existing file. Otherwise overwrite.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    mode = "a" if append else "w"
    with open(path, mode) as f:
        for record in records:
            f.write(record.model_dump_json() + "\n")

    logger.info("Wrote %d records to %s (append=%s)", len(records), path, append)


def append_jsonl(path: str | Path, record: BaseModel) -> None:
    """Append a single record to a JSONL file.

    Args:
        path: Output path (created if it does not exist).
        record: A pydantic model instance.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, "a") as f:
        f.write(record.model_dump_json() + "\n")
