"""Baseline: ROUGE-L verifier.

Phase 3 (Phase.md). Design.md §6.3. Implements the Verifier protocol (§4).
"""

from __future__ import annotations

import logging
import time
from typing import Literal

from rouge_score import rouge_scorer

from src.common.io import Pair, VerifierResult

logger = logging.getLogger(__name__)


class RougeLVerifier:
    """Baseline ROUGE-L verifier.

    Computes ROUGE-L between target=context and prediction=answer.
    Defaults to precision as primary score (faithfulness proxy).
    """

    name: str = "rouge"

    def __init__(self, field: Literal["precision", "recall", "fmeasure"] = "precision") -> None:
        self.field = field
        self._scorer: rouge_scorer.RougeScorer | None = None

    def load(self) -> float:
        """Initialize the RougeScorer. Returns load time in seconds."""
        t0 = time.perf_counter()
        self._scorer = rouge_scorer.RougeScorer(["rougeL"], use_stemmer=True)
        load_time = time.perf_counter() - t0
        logger.info("Loaded %s verifier in %.4f s", self.name, load_time)
        return load_time

    def score(self, context: str, answer: str, pair_id: str = "") -> VerifierResult:
        """Score a single context-answer pair using ROUGE-L."""
        if self._scorer is None:
            self.load()
            assert self._scorer is not None

        t0 = time.perf_counter()
        scores = self._scorer.score(target=context, prediction=answer)
        latency_ms = (time.perf_counter() - t0) * 1000.0

        rouge_l = scores["rougeL"]
        score_val = getattr(rouge_l, self.field)

        return VerifierResult(
            pair_id=pair_id,
            verifier="rouge",
            score=float(score_val),
            verdict=None,  # Threshold applied in run_verifiers or evaluate
            confidence=float(score_val),
            latency_ms=latency_ms,
            details={
                "rougeL_precision": float(rouge_l.precision),
                "rougeL_recall": float(rouge_l.recall),
                "rougeL_fmeasure": float(rouge_l.fmeasure),
                "field": self.field,
            },
        )

    def score_batch(self, pairs: list[Pair]) -> list[VerifierResult]:
        """Score a batch of pairs."""
        if self._scorer is None:
            self.load()

        results: list[VerifierResult] = []
        for p in pairs:
            res = self.score(context=p.context, answer=p.answer, pair_id=p.pair_id)
            results.append(res)
        return results
