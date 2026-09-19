"""Filter B: Local NLI cross-encoder (DeBERTa-v3-small).

Phase 3 (Phase.md). Design.md §6. Implements the Verifier protocol (§4).
"""

from __future__ import annotations

import logging
import os
import time
from typing import Any

import torch
from dotenv import load_dotenv
from transformers import AutoModelForSequenceClassification, AutoTokenizer

from src.common.io import Pair, VerifierResult
from src.common.text import split_sentences, token_chunks

logger = logging.getLogger(__name__)


class NLIVerifier:
    """Filter B: Local NLI Cross-Encoder verifier.

    Evaluates entailment between context chunks (premise) and answer sentences (hypothesis).
    Aggregates: min over sentences of max over context chunks (Design.md §6.2).
    """

    name: str = "filter_b"

    def __init__(
        self,
        model_id: str = "cross-encoder/nli-deberta-v3-small",
        num_threads: int = 6,
        batch_size: int = 16,
        max_length: int = 512,
    ) -> None:
        self.model_id = model_id
        self.num_threads = num_threads
        self.batch_size = batch_size
        self.max_length = max_length

        self.tokenizer: Any = None
        self.model: Any = None
        self.ent_idx: int = 1  # Will be resolved from model.config.id2label

    def load(self) -> float:
        """Load tokenizer and model weights on CPU. Returns load time in seconds."""
        load_dotenv()
        token = os.getenv("HF_TOKEN")
        t0 = time.perf_counter()
        torch.set_num_threads(self.num_threads)

        logger.info("Loading NLI tokenizer: %s", self.model_id)
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_id, token=token)

        logger.info("Loading NLI model: %s", self.model_id)
        self.model = AutoModelForSequenceClassification.from_pretrained(
            self.model_id, token=token
        ).eval()

        # Rule R5.5: MUST read NLI label order from model.config.id2label. NEVER assume index 1 is entailment.
        id2label = {k: v.lower() for k, v in self.model.config.id2label.items()}
        label2id = {v: k for k, v in id2label.items()}

        if "entailment" not in label2id:
            raise ValueError(
                f"Model {self.model_id} config.id2label does not contain 'entailment'. "
                f"Available labels: {id2label}"
            )
        self.ent_idx = int(label2id["entailment"])
        load_time = time.perf_counter() - t0
        logger.info(
            "Loaded %s (entailment_idx=%d, id2label=%s) in %.3f s",
            self.model_id,
            self.ent_idx,
            id2label,
            load_time,
        )
        return load_time

    def _predict_pairs(self, premise_hypo_pairs: list[tuple[str, str]]) -> list[float]:
        """Compute entailment probabilities for a list of (premise, hypothesis) pairs."""
        if not premise_hypo_pairs:
            return []

        assert self.tokenizer is not None
        assert self.model is not None

        scores: list[float] = []
        # Rule R6.2: MUST wrap inference in torch.inference_mode()
        with torch.inference_mode():
            for i in range(0, len(premise_hypo_pairs), self.batch_size):
                batch = premise_hypo_pairs[i : i + self.batch_size]
                premises = [p[0] for p in batch]
                hypotheses = [p[1] for p in batch]

                inputs = self.tokenizer(
                    premises,
                    hypotheses,
                    padding=True,
                    truncation=True,
                    max_length=self.max_length,
                    return_tensors="pt",
                )

                outputs = self.model(**inputs)
                probs = torch.softmax(outputs.logits, dim=-1)
                entail_probs = probs[:, self.ent_idx].tolist()
                scores.extend(entail_probs)

        return scores

    def score(self, context: str, answer: str, pair_id: str = "") -> VerifierResult:
        """Score a single context-answer pair using NLI cross-encoder."""
        if self.model is None or self.tokenizer is None:
            self.load()

        t0 = time.perf_counter()
        sentences = split_sentences(answer)
        if not sentences:
            latency_ms = (time.perf_counter() - t0) * 1000.0
            return VerifierResult(
                pair_id=pair_id,
                verifier="filter_b",
                score=0.0,
                verdict=None,
                confidence=0.0,
                latency_ms=latency_ms,
                details={"sentence_scores": {}, "note": "empty_answer"},
            )

        # Token budget for context chunks: max_length - max_sentence_tokens - 3
        # Calculate max sentence tokens
        sent_token_lens = [
            len(self.tokenizer.encode(s, add_special_tokens=False)) for s in sentences
        ]
        max_sent_tok = max(sent_token_lens) if sent_token_lens else 50
        chunk_budget = max(64, self.max_length - max_sent_tok - 3)

        chunks = token_chunks(context, budget=chunk_budget, tokenizer=self.tokenizer)
        if not chunks:
            chunks = [context] if context.strip() else [""]

        # Build cross-product of (chunk, sentence)
        pairs_to_score: list[tuple[str, str]] = []
        for s in sentences:
            for c in chunks:
                pairs_to_score.append((c, s))

        probs = self._predict_pairs(pairs_to_score)

        # Aggregate: min_s (max_c p[s][c])
        idx = 0
        sentence_scores: dict[str, float] = {}
        for s in sentences:
            c_probs = probs[idx : idx + len(chunks)]
            idx += len(chunks)
            sentence_scores[s] = max(c_probs) if c_probs else 0.0

        answer_score = min(sentence_scores.values()) if sentence_scores else 0.0
        latency_ms = (time.perf_counter() - t0) * 1000.0

        return VerifierResult(
            pair_id=pair_id,
            verifier="filter_b",
            score=float(answer_score),
            verdict=None,
            confidence=float(answer_score),
            latency_ms=latency_ms,
            details={
                "sentence_scores": sentence_scores,
                "n_chunks": len(chunks),
                "n_sentences": len(sentences),
            },
        )

    def score_batch(self, pairs: list[Pair]) -> list[VerifierResult]:
        """Score a batch of pairs."""
        if self.model is None or self.tokenizer is None:
            self.load()

        results: list[VerifierResult] = []
        for p in pairs:
            res = self.score(context=p.context, answer=p.answer, pair_id=p.pair_id)
            results.append(res)
        return results
