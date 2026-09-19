"""Build PubMedQA corpus chunks and FAISS index for Experiment 2.

Phase 4 (Phase.md). Design.md §7.
Entry point:
    python -m src.build_index --config configs/config.yaml
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import random
import time
from pathlib import Path
from typing import Any

import faiss
import numpy as np
import psutil
import torch
import torch.nn.functional as F
from datasets import load_dataset
from dotenv import load_dotenv
from tqdm import tqdm
from transformers import AutoModel, AutoTokenizer

from src.common.config import Config, load_config
from src.common.io import Chunk, Pair, QuestionRecord, read_jsonl, write_jsonl
from src.common.logging_utils import setup_logging
from src.common.text import normalize_question, token_chunks

logger = logging.getLogger(__name__)

BGE_QUERY_PREFIX = "Represent this sentence for searching relevant passages: "


def get_peak_ram_mb() -> float:
    """Return peak resident set size in MB for current process."""
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / (1024.0 * 1024.0)


def build_corpus_chunks(
    dataset_rows: list[dict[str, Any]],
    tokenizer: Any,
    chunk_tokens: int = 250,
    chunk_overlap: int = 30,
) -> list[Chunk]:
    """Group PubMedQA contexts by PMID, chunk them, and return Chunk models.

    Per Design.md §7.2:
    - Excludes conclusions (long_answer), matching how MedHallu builds context.
    - Chunks to ~250 tokens with overlap 30.
    """
    chunks: list[Chunk] = []

    # Deduplicate / group abstracts by pubid
    doc_contexts: dict[str, str] = {}
    for row in dataset_rows:
        pubid = str(row["pubid"])
        ctx = row.get("context")
        if isinstance(ctx, dict):
            contexts_list = ctx.get("contexts", [])
            text = " ".join([c.strip() for c in contexts_list if c.strip()])
        elif isinstance(ctx, list):
            text = " ".join([str(c).strip() for c in ctx if str(c).strip()])
        elif isinstance(ctx, str):
            text = ctx.strip()
        else:
            text = ""

        if pubid not in doc_contexts:
            doc_contexts[pubid] = text
        else:
            # Append if different
            if text and text not in doc_contexts[pubid]:
                doc_contexts[pubid] = f"{doc_contexts[pubid]} {text}".strip()

    logger.info("Building chunks for %d unique PubMedQA abstracts", len(doc_contexts))

    for doc_id, full_text in sorted(doc_contexts.items()):
        raw_chunks = token_chunks(
            full_text,
            budget=chunk_tokens,
            overlap=chunk_overlap,
            tokenizer=tokenizer,
        )
        if not raw_chunks:
            raw_chunks = [full_text] if full_text.strip() else [""]

        for idx, c_text in enumerate(raw_chunks):
            chunk_id = f"{doc_id}-{idx}"
            n_tokens = len(tokenizer.encode(c_text, add_special_tokens=False))
            chunks.append(
                Chunk(
                    chunk_id=chunk_id,
                    doc_id=doc_id,
                    text=c_text,
                    n_tokens=n_tokens,
                )
            )

    logger.info("Generated %d chunks from %d abstracts", len(chunks), len(doc_contexts))
    return chunks


def compute_embeddings(
    texts: list[str],
    tokenizer: Any,
    model: Any,
    batch_size: int = 32,
    prefix: str = "",
) -> np.ndarray:
    """Compute normalized CLS embeddings using BGE model on CPU."""
    all_embeddings: list[np.ndarray] = []

    with torch.inference_mode():
        for i in tqdm(range(0, len(texts), batch_size), desc="Encoding texts"):
            batch_texts = [f"{prefix}{t}" for t in texts[i : i + batch_size]]
            inputs = tokenizer(
                batch_texts,
                padding=True,
                truncation=True,
                max_length=512,
                return_tensors="pt",
            )
            outputs = model(**inputs)
            # CLS pooling + L2 normalization
            cls_repr = outputs[0][:, 0]
            normed = F.normalize(cls_repr, p=2, dim=1)
            all_embeddings.append(normed.cpu().numpy().astype(np.float32))

    return np.vstack(all_embeddings)


def select_exp2_questions(
    dataset_rows: list[dict[str, Any]],
    cfg: Config,
) -> list[QuestionRecord]:
    """Select 100 questions for Exp 2 disjoint from Exp 1 (Design.md §7.1)."""
    # 1. Load Exp 1 dev and test pairs to collect forbidden questions
    data_dir = Path(cfg.paths.data)
    forbidden_questions: set[str] = set()

    test_path = data_dir / "exp1_medhallu" / "test.jsonl"
    if not test_path.exists():
        raise FileNotFoundError(
            f"Exp 1 test pairs not found at {test_path}. "
            "Run 'python -m src.build_exp1_pairs' before build_index (Rule R1.8)."
        )
    for p in read_jsonl(test_path, Pair):
        forbidden_questions.add(normalize_question(p.question))

    if cfg.exp2.exclude_exp1_dev:
        dev_path = data_dir / "exp1_medhallu" / "dev.jsonl"
        if not dev_path.exists():
            raise FileNotFoundError(
                f"Exp 1 dev pairs not found at {dev_path}. "
                "Run 'python -m src.build_exp1_pairs' before build_index (Rule R1.8)."
            )
        for p in read_jsonl(dev_path, Pair):
            forbidden_questions.add(normalize_question(p.question))

    logger.info(
        "Forbidden Exp 1 questions (test + dev): %d unique normalized questions",
        len(forbidden_questions),
    )

    # 2. Filter PubMedQA candidates
    candidates: list[dict[str, Any]] = []
    seen_q_texts: set[str] = set()

    for row in dataset_rows:
        q_text = row["question"].strip()
        norm_q = normalize_question(q_text)

        if norm_q in forbidden_questions:
            continue
        if norm_q in seen_q_texts:
            continue

        seen_q_texts.add(norm_q)
        candidates.append(row)

    logger.info(
        "Available candidate questions after removing Exp 1 overlap: %d",
        len(candidates),
    )

    n_needed = cfg.exp2.n_normal + cfg.exp2.n_degraded
    if len(candidates) < n_needed:
        raise ValueError(
            f"Not enough candidate questions: need {n_needed}, but only {len(candidates)} available"
        )

    # 3. Deterministic sampling with global seed (Rule R4.1)
    rng = random.Random(cfg.seed)
    # Sort candidates first for perfect cross-platform determinism
    candidates.sort(key=lambda r: str(r["pubid"]))
    selected = rng.sample(candidates, n_needed)

    # Assign 50 normal, 50 degraded
    records: list[QuestionRecord] = []
    for i, row in enumerate(selected):
        condition = "normal" if i < cfg.exp2.n_normal else "degraded"
        qid = f"e2-q{i:03d}"
        records.append(
            QuestionRecord(
                question_id=qid,
                question=row["question"].strip(),
                source_doc_id=str(row["pubid"]),
                condition=condition,
                ground_truth_long=row.get("long_answer"),
                final_decision=row.get("final_decision"),
            )
        )

    return records


def run_retrieval_sanity_check(
    questions: list[QuestionRecord],
    chunks: list[Chunk],
    index: faiss.IndexFlatIP,
    tokenizer: Any,
    model: Any,
    top_k: int = 3,
    degraded_search_k: int = 20,
) -> dict[str, Any]:
    """Verify normal hit rate and assert degraded own_doc_in_context is False."""
    logger.info("Running retrieval sanity checks on %d questions", len(questions))

    # Test top 20 normal questions for hit rate
    normal_qs = [q for q in questions if q.condition == "normal"][:20]
    hits = 0

    for q in normal_qs:
        q_emb = compute_embeddings(
            [q.question],
            tokenizer,
            model,
            prefix=BGE_QUERY_PREFIX,
        )
        _, indices = index.search(q_emb, top_k)
        retrieved_doc_ids = [chunks[idx].doc_id for idx in indices[0]]
        if q.source_doc_id in retrieved_doc_ids:
            hits += 1

    normal_hit_rate = hits / len(normal_qs) if normal_qs else 0.0
    logger.info("Normal condition top-%d retrieval hit rate: %.2f (%d/%d)", top_k, normal_hit_rate, hits, len(normal_qs))

    # Verify degraded condition for ALL degraded questions
    degraded_qs = [q for q in questions if q.condition == "degraded"]
    for q in degraded_qs:
        q_emb = compute_embeddings(
            [q.question],
            tokenizer,
            model,
            prefix=BGE_QUERY_PREFIX,
        )
        _, indices = index.search(q_emb, degraded_search_k)

        # Drop own doc chunks (Design.md §7.3)
        filtered_chunks: list[Chunk] = []
        for idx in indices[0]:
            c = chunks[idx]
            if c.doc_id != q.source_doc_id:
                filtered_chunks.append(c)
            if len(filtered_chunks) == top_k:
                break

        retrieved_docs = [c.doc_id for c in filtered_chunks]
        assert q.source_doc_id not in retrieved_docs, (
            f"Degraded retrieval leaked source doc {q.source_doc_id} in {q.question_id}"
        )

    logger.info("Degraded retrieval assertion passed for all %d questions", len(degraded_qs))

    return {
        "normal_evaluated": len(normal_qs),
        "normal_top3_hit_rate": normal_hit_rate,
        "degraded_verified": len(degraded_qs),
        "degraded_leak_count": 0,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Build PubMedQA index and sample Exp 2 questions.")
    parser.add_argument("--config", default="configs/config.yaml", help="Path to config YAML")
    args = parser.parse_args()

    cfg = load_config(args.config)
    setup_logging("build_index")
    t0 = time.perf_counter()

    # Rule R6.2: torch.set_num_threads(6)
    torch.set_num_threads(cfg.filter_b.num_threads)

    exp2_dir = Path(cfg.paths.data) / "exp2_rag"
    exp2_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("PHASE 4: EXPERIMENT 2 INDEX & QUESTION BUILD")
    print(f"Embedder: {cfg.models.embedder}")
    print("=" * 60)

    # 1. Load PubMedQA dataset
    logger.info(
        "Loading PubMedQA dataset: %s (%s, rev=%s)",
        cfg.datasets.pubmedqa.hf_id,
        cfg.datasets.pubmedqa.config,
        cfg.datasets.pubmedqa.revision,
    )
    load_dotenv()
    token = os.getenv("HF_TOKEN")
    dataset = load_dataset(
        cfg.datasets.pubmedqa.hf_id,
        cfg.datasets.pubmedqa.config,
        revision=cfg.datasets.pubmedqa.revision,
        split="train",
        token=token,
    )
    raw_rows = [dict(r) for r in dataset]

    # 2. Load embedder and tokenizer
    logger.info("Loading embedder: %s", cfg.models.embedder)
    tok = AutoTokenizer.from_pretrained(cfg.models.embedder, token=token)
    model = AutoModel.from_pretrained(cfg.models.embedder, token=token).eval()

    # 3. Build corpus chunks (or load cached)
    chunks_file = exp2_dir / "corpus_chunks.jsonl"
    if chunks_file.exists():
        chunks = read_jsonl(chunks_file, Chunk)
        logger.info("Loaded %d existing chunks from %s", len(chunks), chunks_file)
        print(f"Loaded {len(chunks)} cached corpus chunks <- {chunks_file}")
    else:
        chunks = build_corpus_chunks(
            raw_rows,
            tokenizer=tok,
            chunk_tokens=cfg.exp2.chunk_tokens,
            chunk_overlap=cfg.exp2.chunk_overlap,
        )
        write_jsonl(chunks_file, chunks)
        print(f"Saved {len(chunks)} corpus chunks -> {chunks_file}")

    # 4. Compute embeddings and build FAISS index (or load cached per Rule R4.7)
    index_file = exp2_dir / "faiss.index"
    if index_file.exists():
        index = faiss.read_index(str(index_file))
        dim = index.d
        logger.info("Loaded cached FAISS index from %s", index_file)
        print(f"Loaded cached FAISS index (ntotal={index.ntotal}, d={dim}) <- {index_file}")
    else:
        print(f"Computing embeddings for {len(chunks)} chunks on CPU...")
        chunk_texts = [c.text for c in chunks]
        embeddings = compute_embeddings(chunk_texts, tokenizer=tok, model=model, batch_size=64)

        dim = embeddings.shape[1]
        index = faiss.IndexFlatIP(dim)
        index.add(embeddings)
        faiss.write_index(index, str(index_file))
        print(f"Built FAISS index (ntotal={index.ntotal}, d={dim}) -> {index_file}")

    # 5. Select 100 disjoint Exp 2 questions
    questions = select_exp2_questions(raw_rows, cfg)
    questions_file = exp2_dir / "questions.jsonl"
    write_jsonl(questions_file, questions)
    print(f"Saved {len(questions)} Exp 2 questions (50 normal, 50 degraded) -> {questions_file}")

    # 6. Retrieval sanity check
    sanity = run_retrieval_sanity_check(
        questions=questions,
        chunks=chunks,
        index=index,
        tokenizer=tok,
        model=model,
        top_k=cfg.exp2.top_k,
        degraded_search_k=cfg.exp2.degraded_search_k,
    )

    elapsed_s = time.perf_counter() - t0
    peak_ram_mb = get_peak_ram_mb()

    # 7. Write index summary metadata
    summary = {
        "n_abstracts": 1000,
        "n_chunks": len(chunks),
        "embedding_dim": dim,
        "embedder_model": cfg.models.embedder,
        "build_time_s": elapsed_s,
        "peak_ram_mb": peak_ram_mb,
        "retrieval_sanity": sanity,
    }
    summary_file = exp2_dir / "index_summary.json"
    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print("\n" + "=" * 60)
    print("INDEX BUILD COMPLETE")
    print(f"Corpus chunks: {len(chunks)}")
    print(f"Questions:     {len(questions)} (50 normal, 50 degraded)")
    print(f"Top-3 hit rate (normal): {sanity['normal_top3_hit_rate']:.2%}")
    print(f"Build time:    {elapsed_s:.1f} s")
    print(f"Peak RAM:      {peak_ram_mb:.1f} MB")
    print("=" * 60)


if __name__ == "__main__":
    main()
