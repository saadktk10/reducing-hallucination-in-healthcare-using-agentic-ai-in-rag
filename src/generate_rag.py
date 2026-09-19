"""Generate RAG answers for Experiment 2 using Groq.

Phase 4 (Phase.md). Design.md §7.5.
Entry point: python -m src.generate_rag --config configs/config.yaml

Flow:
  1. Load corpus_chunks.jsonl and questions.jsonl from data/exp2_rag/
  2. Load FAISS index and BGE embedder
  3. For each question: retrieve top-k chunks (degraded: drop own doc), build
     context string, call Groq at temperature 0, cache response, write Generated
  4. Log per-condition answer length stats
  5. Write run_manifest.json (Rule R4.3)

Rules enforced:
  R1.4  prompt hash checked against FROZEN.json before any generation
  R2.4  temperature 0
  R2.5  every API response cached to data/cache/
  R2.7  tenacity retry on transient errors
  R2.8  GROQ_API_KEY loaded from .env
  R4.1  seed 42 (sampling already done in build_index)
  R4.3  run_manifest.json written to results folder
  R4.7  idempotent: skips already-cached responses
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import faiss
import numpy as np
import torch
import torch.nn.functional as F
from dotenv import load_dotenv
from groq import Groq
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)
from transformers import AutoModel, AutoTokenizer

from src.common.config import Config, load_config
from src.common.io import (
    CacheRecord,
    Chunk,
    Generated,
    QuestionRecord,
    append_jsonl,
    read_jsonl,
)
from src.common.logging_utils import setup_logging

logger = logging.getLogger(__name__)

BGE_QUERY_PREFIX = "Represent this sentence for searching relevant passages: "


# ---------------------------------------------------------------------------
# Prompt helpers (Rule R1.4)
# ---------------------------------------------------------------------------


def load_frozen_prompt(prompts_dir: Path, name: str) -> tuple[str, str]:
    """Load a prompt file and verify its SHA-256 against FROZEN.json.

    Returns:
        (prompt_text, hex_hash)

    Raises:
        FileNotFoundError: if the prompt or FROZEN.json is missing.
        ValueError: if the hash does not match.
    """
    frozen_path = prompts_dir / "FROZEN.json"
    if not frozen_path.exists():
        raise FileNotFoundError(f"FROZEN.json not found at {frozen_path}")

    with open(frozen_path, encoding="utf-8") as f:
        frozen: dict[str, str] = json.load(f)

    prompt_path = prompts_dir / name
    if not prompt_path.exists():
        raise FileNotFoundError(f"Prompt file not found: {prompt_path}")

    text = prompt_path.read_text(encoding="utf-8")
    actual_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()

    if name not in frozen:
        raise ValueError(f"{name} not in FROZEN.json — freeze it before generating.")

    expected_hash = frozen[name]
    if actual_hash != expected_hash:
        raise ValueError(
            f"Prompt hash mismatch for {name}!\n"
            f"  expected: {expected_hash}\n"
            f"  actual:   {actual_hash}\n"
            "The prompt has been modified. Create a new version (v2) per Rule R8.4."
        )

    logger.info("Prompt %s hash verified: %s", name, actual_hash[:12])
    return text, actual_hash


# ---------------------------------------------------------------------------
# Embedder helpers
# ---------------------------------------------------------------------------


def compute_query_embedding(
    question: str,
    tokenizer: Any,
    model: Any,
) -> np.ndarray:
    """Compute a single normalized BGE query embedding."""
    prefixed = f"{BGE_QUERY_PREFIX}{question}"
    with torch.inference_mode():
        inputs = tokenizer(
            [prefixed],
            padding=True,
            truncation=True,
            max_length=512,
            return_tensors="pt",
        )
        outputs = model(**inputs)
        cls_repr = outputs[0][:, 0]
        normed = F.normalize(cls_repr, p=2, dim=1)
    return normed.cpu().numpy().astype(np.float32)


# ---------------------------------------------------------------------------
# Retrieval
# ---------------------------------------------------------------------------


def retrieve_chunks(
    question: QuestionRecord,
    chunks: list[Chunk],
    index: faiss.IndexFlatIP,
    tokenizer: Any,
    model: Any,
    top_k: int,
    degraded_search_k: int,
) -> tuple[list[Chunk], bool]:
    """Retrieve context chunks for a question.

    For normal condition: return top_k chunks (may include own doc).
    For degraded condition: search top degraded_search_k, drop own doc, keep top_k.

    Returns:
        (retrieved_chunks, own_doc_in_context)
    """
    q_emb = compute_query_embedding(question.question, tokenizer, model)

    if question.condition == "normal":
        _, indices = index.search(q_emb, top_k)
        retrieved = [chunks[i] for i in indices[0] if i < len(chunks)]
        own_doc = any(c.doc_id == question.source_doc_id for c in retrieved)
        return retrieved, own_doc

    else:  # degraded
        _, indices = index.search(q_emb, degraded_search_k)
        filtered: list[Chunk] = []
        for i in indices[0]:
            if i >= len(chunks):
                continue
            c = chunks[i]
            if c.doc_id != question.source_doc_id:
                filtered.append(c)
            if len(filtered) == top_k:
                break

        # Design.md §7.3: degraded must never contain own doc
        own_doc = any(c.doc_id == question.source_doc_id for c in filtered)
        assert not own_doc, (
            f"Degraded retrieval leaked own doc {question.source_doc_id} "
            f"for {question.question_id}"
        )
        return filtered, False


# ---------------------------------------------------------------------------
# Groq client with tenacity retry (Rule R2.7)
# ---------------------------------------------------------------------------


def make_groq_client() -> Groq:
    """Create a Groq client from GROQ_API_KEY in environment (Rule R2.8)."""
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise OSError(
            "GROQ_API_KEY not set. Add it to your .env file (Rule R2.8)."
        )
    return Groq(api_key=api_key)


@retry(
    retry=retry_if_exception_type(Exception),
    wait=wait_exponential(multiplier=2, min=2, max=60),
    stop=stop_after_attempt(6),
    reraise=True,
)
def call_groq(
    client: Groq,
    model_id: str,
    prompt_text: str,
    temperature: int,
    max_tokens: int,
) -> tuple[str, int, int, float]:
    """Call Groq chat completion with tenacity retry.

    Returns:
        (answer_text, input_tokens, output_tokens, latency_ms)
    """
    t0 = time.perf_counter()
    response = client.chat.completions.create(
        model=model_id,
        messages=[{"role": "user", "content": prompt_text}],
        temperature=temperature,
        max_tokens=max_tokens,
    )
    latency_ms = (time.perf_counter() - t0) * 1000.0

    answer = response.choices[0].message.content or ""
    usage = response.usage
    in_tok = usage.prompt_tokens if usage else 0
    out_tok = usage.completion_tokens if usage else 0

    return answer, in_tok, out_tok, latency_ms


# ---------------------------------------------------------------------------
# Cache (Rule R2.5)
# ---------------------------------------------------------------------------


def make_cache_key(question_id: str, prompt_hash: str, model_id: str) -> str:
    """Deterministic cache key from question ID + prompt hash + model ID."""
    raw = f"{question_id}|{prompt_hash}|{model_id}"
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


def load_cache_index(cache_dir: Path) -> dict[str, str]:
    """Return {cache_key: answer_text} from existing cache JSONL files."""
    index: dict[str, str] = {}
    for fpath in cache_dir.glob("generate_rag_*.jsonl"):
        try:
            records = read_jsonl(fpath, CacheRecord)
            for r in records:
                index[r.key] = r.response_text
        except Exception as exc:
            logger.warning("Could not read cache file %s: %s", fpath, exc)
    return index


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate RAG answers for Experiment 2."
    )
    parser.add_argument(
        "--config", default="configs/config.yaml", help="Path to config YAML"
    )
    args = parser.parse_args()

    load_dotenv()
    cfg: Config = load_config(args.config)
    run_id = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    setup_logging(f"generate_rag_{run_id}")
    t0_wall = time.perf_counter()

    # Rule R6.2
    torch.set_num_threads(cfg.filter_b.num_threads)

    print("=" * 60)
    print("PHASE 4: EXPERIMENT 2 RAG GENERATION")
    print(f"Run ID:    {run_id}")
    print(f"Generator: {cfg.models.generator.provider}/{cfg.models.generator.model_id}")
    print("=" * 60)

    # ---- 1. Verify generator prompt hash (Rule R1.4) ----------------------
    prompts_dir = Path(cfg.paths.prompts)
    prompt_template, prompt_hash = load_frozen_prompt(prompts_dir, "generator_v1.txt")
    print(f"Prompt hash verified: {prompt_hash[:16]}...")

    # ---- 2. Load chunks and questions -------------------------------------
    exp2_dir = Path(cfg.paths.data) / "exp2_rag"
    chunks_file = exp2_dir / "corpus_chunks.jsonl"
    questions_file = exp2_dir / "questions.jsonl"
    index_file = exp2_dir / "faiss.index"

    if not chunks_file.exists():
        raise FileNotFoundError(
            f"{chunks_file} not found. Run build_index first:\n"
            "  python -m src.build_index --config configs/config.yaml"
        )

    chunks = read_jsonl(chunks_file, Chunk)
    questions = read_jsonl(questions_file, QuestionRecord)
    logger.info("Loaded %d chunks and %d questions", len(chunks), len(questions))
    print(f"Loaded {len(chunks)} corpus chunks, {len(questions)} questions")

    # ---- 3. Load FAISS index and embedder ---------------------------------
    if not index_file.exists():
        raise FileNotFoundError(f"{index_file} not found. Run build_index first.")

    index = faiss.read_index(str(index_file))
    logger.info("Loaded FAISS index (ntotal=%d)", index.ntotal)

    token = os.getenv("HF_TOKEN")
    logger.info("Loading embedder: %s", cfg.models.embedder)
    tok = AutoTokenizer.from_pretrained(cfg.models.embedder, token=token)
    emb_model = AutoModel.from_pretrained(cfg.models.embedder, token=token).eval()
    print(f"Embedder ready: {cfg.models.embedder}")

    # ---- 4. Groq client ---------------------------------------------------
    client = make_groq_client()
    gen_cfg = cfg.models.generator

    # ---- 5. Cache init (Rule R2.5) ----------------------------------------
    cache_dir = Path(cfg.paths.cache)
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_file = cache_dir / f"generate_rag_{run_id}.jsonl"
    existing_cache = load_cache_index(cache_dir)
    logger.info("Found %d existing cached responses", len(existing_cache))

    # ---- 6. Output file ---------------------------------------------------
    generated_file = exp2_dir / "generated.jsonl"
    # Load already-generated records for idempotency (Rule R4.7)
    already_done: set[str] = set()
    if generated_file.exists():
        try:
            prev = read_jsonl(generated_file, Generated)
            already_done = {r.question_id for r in prev}
            logger.info("Resuming: %d questions already generated", len(already_done))
            print(f"Resuming: {len(already_done)}/{len(questions)} already done")
        except Exception as exc:
            logger.warning("Could not load existing generated.jsonl: %s", exc)

    # ---- 7. Generate loop -------------------------------------------------
    normal_lengths: list[int] = []
    degraded_lengths: list[int] = []
    total_in_tok = 0
    total_out_tok = 0

    for i, q in enumerate(questions):
        if q.question_id in already_done:
            logger.debug("Skipping %s (already done)", q.question_id)
            continue

        # Retrieve context
        retrieved_chunks, own_doc_in_ctx = retrieve_chunks(
            question=q,
            chunks=chunks,
            index=index,
            tokenizer=tok,
            model=emb_model,
            top_k=cfg.exp2.top_k,
            degraded_search_k=cfg.exp2.degraded_search_k,
        )

        context_text = "\n\n".join(c.text for c in retrieved_chunks)
        retrieved_ids = [c.chunk_id for c in retrieved_chunks]
        retrieved_doc_ids = [c.doc_id for c in retrieved_chunks]

        # Fill prompt (Design.md §5.2: str.replace, not str.format)
        filled_prompt = (
            prompt_template
            .replace("{context}", context_text)
            .replace("{question}", q.question)
        )

        # Cache lookup
        cache_key = make_cache_key(q.question_id, prompt_hash, gen_cfg.model_id)
        if cache_key in existing_cache:
            answer = existing_cache[cache_key]
            in_tok = out_tok = 0
            latency_ms = 0.0
            logger.debug("Cache hit for %s", q.question_id)
        else:
            # Call Groq (Rule R2.4 temperature=0, Rule R2.7 tenacity)
            answer, in_tok, out_tok, latency_ms = call_groq(
                client=client,
                model_id=gen_cfg.model_id,
                prompt_text=filled_prompt,
                temperature=gen_cfg.temperature,
                max_tokens=gen_cfg.max_tokens,
            )
            total_in_tok += in_tok
            total_out_tok += out_tok

            # Write to cache (Rule R2.5)
            cache_rec = CacheRecord(
                key=cache_key,
                provider=gen_cfg.provider,
                model_id=gen_cfg.model_id,
                prompt_hash=prompt_hash,
                request_text=filled_prompt,
                response_text=answer,
                parsed=None,
                input_tokens=in_tok,
                output_tokens=out_tok,
                latency_ms=latency_ms,
                attempt=1,
                mode="normal",
                timestamp_utc=datetime.now(UTC).isoformat(),
            )
            append_jsonl(cache_file, cache_rec)
            existing_cache[cache_key] = answer
            time.sleep(2.0)  # Respect free-tier rate limits (Rule R2.9)

        # Accumulate length stats
        word_count = len(answer.split())
        if q.condition == "normal":
            normal_lengths.append(word_count)
        else:
            degraded_lengths.append(word_count)

        # Write Generated record
        gen_record = Generated(
            question_id=q.question_id,
            condition=q.condition,
            retrieved_chunk_ids=retrieved_ids,
            retrieved_doc_ids=retrieved_doc_ids,
            own_doc_in_context=own_doc_in_ctx,
            context=context_text,
            answer=answer,
            generator_model_id=gen_cfg.model_id,
            prompt_hash=prompt_hash,
            cache_key=cache_key,
        )
        append_jsonl(generated_file, gen_record)
        already_done.add(q.question_id)

        if (i + 1) % 10 == 0 or (i + 1) == len(questions):
            print(
                f"  [{i + 1:3d}/{len(questions)}] {q.question_id} "
                f"({q.condition}) | {word_count} words | "
                f"{latency_ms:.0f} ms"
            )

    # ---- 8. Per-condition length stats ------------------------------------
    def _stats(lengths: list[int]) -> dict[str, float]:
        if not lengths:
            return {"n": 0, "mean": 0.0, "min": 0.0, "max": 0.0}
        return {
            "n": len(lengths),
            "mean": sum(lengths) / len(lengths),
            "min": float(min(lengths)),
            "max": float(max(lengths)),
        }

    length_stats = {
        "normal": _stats(normal_lengths),
        "degraded": _stats(degraded_lengths),
    }

    # ---- 9. Run manifest (Rule R4.3) --------------------------------------
    git_sha = "unknown"
    try:
        import subprocess

        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            git_sha = result.stdout.strip()
    except Exception:
        pass

    elapsed_s = time.perf_counter() - t0_wall
    manifest = {
        "run_id": run_id,
        "phase": "4",
        "script": "src.generate_rag",
        "git_sha": git_sha,
        "config_snapshot": {
            "generator": gen_cfg.model_dict() if hasattr(gen_cfg, "model_dict") else gen_cfg.model_dump(),
            "exp2": cfg.exp2.model_dump(),
            "seed": cfg.seed,
        },
        "prompt_name": "generator_v1.txt",
        "prompt_hash": prompt_hash,
        "embedder_model": cfg.models.embedder,
        "dataset_revision": cfg.datasets.pubmedqa.revision,
        "questions_total": len(questions),
        "questions_generated": len(already_done),
        "total_input_tokens": total_in_tok,
        "total_output_tokens": total_out_tok,
        "length_stats_words": length_stats,
        "elapsed_s": elapsed_s,
        "timestamp_utc": datetime.now(UTC).isoformat(),
    }

    manifest_file = exp2_dir / "run_manifest_generate.json"
    with open(manifest_file, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    # ---- 10. Summary -------------------------------------------------------
    total_gen = len(already_done)
    print("\n" + "=" * 60)
    print("GENERATION COMPLETE")
    print(f"Generated:   {total_gen} answers ({len(questions)} questions total)")
    print(f"Output:      {generated_file}")
    print(f"Cache:       {cache_file}")
    print(f"Elapsed:     {elapsed_s:.1f} s")
    print("\nAnswer length stats (words):")
    for cond, s in length_stats.items():
        print(f"  {cond}: n={s['n']}, mean={s['mean']:.1f}, min={s['min']:.0f}, max={s['max']:.0f}")
    print("=" * 60)

    logger.info(
        "Generation complete: %d answers, elapsed=%.1f s",
        total_gen,
        elapsed_s,
    )


if __name__ == "__main__":
    main()
