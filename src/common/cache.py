"""Append-only JSONL cache with SHA-256 keys.

Caches API responses so that identical requests are not repeated (Rule R2.5).
Cache is append-only — records are never overwritten (Design principle 3).
"""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path

from src.common.io import CacheRecord, append_jsonl, read_jsonl

logger = logging.getLogger(__name__)


def make_cache_key(model_id: str, prompt_hash: str, context: str, answer: str) -> str:
    """Create a deterministic cache key from request parameters.

    Key = sha256(model_id|prompt_hash|context|answer) — Design.md §3.5.

    Args:
        model_id: The model identifier.
        prompt_hash: SHA-256 of the prompt template.
        context: The context text.
        answer: The answer (or question for generator).

    Returns:
        A hex-encoded SHA-256 hash string.
    """
    payload = f"{model_id}|{prompt_hash}|{context}|{answer}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class JsonlCache:
    """Append-only JSONL cache backed by a file on disk.

    Records are indexed in memory by key for O(1) lookup.
    New records are appended to the file without rewriting.
    """

    def __init__(self, path: str | Path) -> None:
        """Initialize the cache.

        Args:
            path: Path to the JSONL cache file. Created on first append.
        """
        self.path = Path(path)
        self._index: dict[str, CacheRecord] = {}
        self._load()

    def _load(self) -> None:
        """Load existing cache records into the in-memory index."""
        if not self.path.exists():
            logger.info("Cache file does not exist yet: %s", self.path)
            return

        records = read_jsonl(self.path, CacheRecord)
        for record in records:
            self._index[record.key] = record

        logger.info("Loaded %d cached records from %s", len(self._index), self.path)

    def get(self, key: str) -> CacheRecord | None:
        """Look up a cached record by key.

        Args:
            key: The cache key (SHA-256 hex string).

        Returns:
            The cached record, or None if not found.
        """
        return self._index.get(key)

    def append(self, record: CacheRecord) -> None:
        """Append a record to the cache file and in-memory index.

        Args:
            record: A validated CacheRecord instance.
        """
        append_jsonl(self.path, record)
        self._index[record.key] = record
        logger.debug("Cached record with key %s", record.key[:12])

    def __len__(self) -> int:
        return len(self._index)

    def __contains__(self, key: str) -> bool:
        return key in self._index
