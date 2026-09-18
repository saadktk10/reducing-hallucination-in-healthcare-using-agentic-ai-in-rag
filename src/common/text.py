"""Text utilities: sentence splitting and token-aware chunking.

Used by Filter B (Design.md §6.2) and index building (§7.2).
"""

from __future__ import annotations

import logging
import re

import pysbd

logger = logging.getLogger(__name__)

# Module-level sentence segmenter (English).
_SEGMENTER = pysbd.Segmenter(language="en", clean=False)


def split_sentences(text: str) -> list[str]:
    """Split text into sentences using pysbd.

    Drops empty strings per Design.md §6.2.

    Args:
        text: The input text.

    Returns:
        A list of non-empty sentence strings.
    """
    sentences = _SEGMENTER.segment(text)
    return [s.strip() for s in sentences if s.strip()]


def token_chunks(
    text: str,
    budget: int,
    overlap: int = 30,
    tokenizer: object | None = None,
) -> list[str]:
    """Split text into token-budget-aware chunks with overlap.

    Chunks split on sentence boundaries where possible, so a supporting
    sentence is not cut in half (Design.md §6.2).

    If no tokenizer is provided, a simple whitespace-based word count is used
    as a proxy (1 word ≈ 1.3 tokens). For accurate chunking, pass a
    HuggingFace tokenizer.

    Args:
        text: The input text to chunk.
        budget: Maximum tokens per chunk.
        overlap: Token overlap between consecutive chunks.
        tokenizer: Optional HuggingFace tokenizer with an ``encode`` method.

    Returns:
        A list of text chunks, each within the token budget.
    """
    sentences = split_sentences(text)
    if not sentences:
        return [text] if text.strip() else []

    def count_tokens(s: str) -> int:
        if tokenizer is not None:
            return len(tokenizer.encode(s, add_special_tokens=False))  # type: ignore[union-attr]
        # Rough proxy: split on whitespace.
        return len(s.split())

    chunks: list[str] = []
    current_sentences: list[str] = []
    current_tokens = 0

    for sent in sentences:
        sent_tokens = count_tokens(sent)

        # If a single sentence exceeds the budget, split it into word-level sub-chunks.
        if sent_tokens > budget:
            if current_sentences:
                chunks.append(" ".join(current_sentences))
                current_sentences = []
                current_tokens = 0
            words = sent.split()
            sub_words: list[str] = []
            sub_tokens = 0
            for w in words:
                w_tok = count_tokens(w)
                if sub_words and (sub_tokens + w_tok > budget):
                    chunks.append(" ".join(sub_words))
                    sub_words = [w]
                    sub_tokens = w_tok
                else:
                    sub_words.append(w)
                    sub_tokens += w_tok
            if sub_words:
                chunks.append(" ".join(sub_words))
            continue

        if current_tokens + sent_tokens > budget:
            # Flush current chunk.
            chunks.append(" ".join(current_sentences))

            # Overlap: keep trailing sentences that fit within overlap budget.
            overlap_sentences: list[str] = []
            overlap_tokens = 0
            for s in reversed(current_sentences):
                s_tok = count_tokens(s)
                if overlap_tokens + s_tok > overlap:
                    break
                overlap_sentences.insert(0, s)
                overlap_tokens += s_tok

            current_sentences = overlap_sentences + [sent]
            current_tokens = overlap_tokens + sent_tokens
        else:
            current_sentences.append(sent)
            current_tokens += sent_tokens

    if current_sentences:
        chunks.append(" ".join(current_sentences))

    return chunks


def normalize_question(text: str) -> str:
    """Normalize a question for deduplication.

    Lowercase, collapse whitespace, strip punctuation (Design.md §7.1).

    Args:
        text: The question text.

    Returns:
        Normalized string for comparison.
    """
    text = text.lower().strip()
    text = re.sub(r"[^\w\s]", "", text)
    text = re.sub(r"\s+", " ", text)
    return text
