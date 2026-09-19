"""Smoke test for Gemini (Judge) and Groq (Generator) APIs — Phase 0 Task 7.

Validates API connectivity, records latency, creates validated CacheRecord entries
in data/cache/judge_gemini.jsonl and data/cache/generator_groq.jsonl, and logs exact model IDs.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from datetime import UTC, datetime
from pathlib import Path

from groq import Groq
from openai import OpenAI

from src.common.config import load_config
from src.common.io import CacheRecord, append_jsonl
from src.common.logging_utils import setup_logging

logger = logging.getLogger(__name__)


def make_cache_key(model_id: str, prompt_hash: str, context: str, answer: str) -> str:
    payload = f"{model_id}|{prompt_hash}|{context}|{answer}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def smoke_gemini(cfg) -> CacheRecord:
    """Execute one smoke call to Gemini via OpenAI endpoint and return a CacheRecord."""
    gemini_key = os.getenv("GEMINI_API_KEY")
    if not gemini_key:
        raise ValueError("GEMINI_API_KEY not found in environment")

    client = OpenAI(
        api_key=gemini_key,
        base_url=cfg.models.judge.base_url,
    )
    model_id = cfg.models.judge.model_id
    prompt_text = (
        'Evaluate if the answer is supported by the context.\n'
        'Context: Aspirin is used to treat mild to moderate pain and reduce fever.\n'
        'Answer: Aspirin can help relieve minor aches.\n'
        'Return JSON: {"verdict": "SUPPORTED", "confidence": 1.0, "reason": "Consistent with context"}'
    )
    prompt_hash = hashlib.sha256(prompt_text.encode("utf-8")).hexdigest()

    t0 = time.perf_counter()
    response = client.chat.completions.create(
        model=model_id,
        messages=[{"role": "user", "content": prompt_text}],
        temperature=cfg.models.judge.temperature,
        reasoning_effort="low",
        max_tokens=cfg.models.judge.max_tokens,
    )
    latency_ms = (time.perf_counter() - t0) * 1000.0

    content = response.choices[0].message.content or ""
    returned_model = response.model or model_id

    # Parse JSON if possible
    parsed = None
    try:
        clean = content.strip().strip("`").removeprefix("json").strip()
        parsed = json.loads(clean)
    except Exception:
        pass

    in_tokens = response.usage.prompt_tokens if response.usage else None
    out_tokens = response.usage.completion_tokens if response.usage else None

    key = make_cache_key(returned_model, prompt_hash, "Aspirin is used...", "Aspirin can help...")
    record = CacheRecord(
        key=key,
        provider=cfg.models.judge.provider,
        model_id=returned_model,
        prompt_hash=prompt_hash,
        request_text=prompt_text,
        response_text=content,
        parsed=parsed,
        input_tokens=in_tokens,
        output_tokens=out_tokens,
        latency_ms=latency_ms,
        attempt=1,
        mode="normal",
        timestamp_utc=datetime.now(UTC).isoformat(),
    )
    return record


def smoke_groq(cfg) -> CacheRecord:
    """Execute one smoke call to Groq generator and return a CacheRecord."""
    groq_key = os.getenv("GROQ_API_KEY")
    if not groq_key:
        raise ValueError("GROQ_API_KEY not found in environment")

    client = Groq(api_key=groq_key)
    model_id = cfg.models.generator.model_id
    prompt_text = (
        "Question: Is paracetamol indicated for pain relief?\n"
        "Context: Paracetamol (acetaminophen) is widely used for pain relief and fever reduction.\n"
        "Answer in 2 sentences based on the evidence."
    )
    prompt_hash = hashlib.sha256(prompt_text.encode("utf-8")).hexdigest()

    t0 = time.perf_counter()
    response = client.chat.completions.create(
        model=model_id,
        messages=[{"role": "user", "content": prompt_text}],
        temperature=cfg.models.generator.temperature,
        max_tokens=cfg.models.generator.max_tokens,
    )
    latency_ms = (time.perf_counter() - t0) * 1000.0

    content = response.choices[0].message.content or ""
    returned_model = response.model or model_id
    in_tokens = response.usage.prompt_tokens if response.usage else None
    out_tokens = response.usage.completion_tokens if response.usage else None

    key = make_cache_key(returned_model, prompt_hash, "Paracetamol is widely used...", "")
    record = CacheRecord(
        key=key,
        provider=cfg.models.generator.provider,
        model_id=returned_model,
        prompt_hash=prompt_hash,
        request_text=prompt_text,
        response_text=content,
        parsed=None,
        input_tokens=in_tokens,
        output_tokens=out_tokens,
        latency_ms=latency_ms,
        attempt=1,
        mode="normal",
        timestamp_utc=datetime.now(UTC).isoformat(),
    )
    return record


def main() -> None:
    setup_logging("smoke_apis")
    cfg = load_config()

    cache_dir = Path(cfg.paths.cache)
    cache_dir.mkdir(parents=True, exist_ok=True)

    judge_cache_file = cache_dir / "judge_gemini.jsonl"
    gen_cache_file = cache_dir / "generator_groq.jsonl"

    print("=" * 60)
    print("API SMOKE TESTS (Phase 0 Task 7)")
    print("=" * 60)

    # 1. Smoke test Gemini judge
    print(f"1. Calling Gemini Judge ({cfg.models.judge.model_id})...")
    gemini_record = smoke_gemini(cfg)
    append_jsonl(judge_cache_file, gemini_record)
    print(f"   Model returned: {gemini_record.model_id}")
    print(f"   Latency:        {gemini_record.latency_ms:.1f} ms")
    print(f"   Tokens:         in={gemini_record.input_tokens}, out={gemini_record.output_tokens}")
    print(f"   Cached to:      {judge_cache_file}")

    # 2. Smoke test Groq generator
    print(f"\n2. Calling Groq Generator ({cfg.models.generator.model_id})...")
    groq_record = smoke_groq(cfg)
    append_jsonl(gen_cache_file, groq_record)
    print(f"   Model returned: {groq_record.model_id}")
    print(f"   Latency:        {groq_record.latency_ms:.1f} ms")
    print(f"   Tokens:         in={groq_record.input_tokens}, out={groq_record.output_tokens}")
    print(f"   Cached to:      {gen_cache_file}")

    print("=" * 60)
    print("ALL API SMOKE CALLS SUCCEEDED AND CACHED")
    print("=" * 60)


if __name__ == "__main__":
    main()
