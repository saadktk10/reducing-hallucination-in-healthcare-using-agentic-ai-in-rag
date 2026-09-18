"""Verifier protocol and shared types — Design.md §4.

All three verifiers (Filter A, Filter B, ROUGE-L) implement the Verifier
protocol so the rest of the codebase treats them identically.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from src.common.io import Pair, VerifierResult


@runtime_checkable
class Verifier(Protocol):
    """Protocol that all verifiers must satisfy."""

    name: str

    def load(self) -> float:
        """Load model/resources. Returns load time in seconds."""
        ...

    def score(self, context: str, answer: str) -> VerifierResult:
        """Score a single context-answer pair."""
        ...

    def score_batch(self, pairs: list[Pair]) -> list[VerifierResult]:
        """Score a batch of pairs."""
        ...
