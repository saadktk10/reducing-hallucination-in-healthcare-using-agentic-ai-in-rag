"""Filter A: API-based LLM judge (Gemini Flash via OpenAI-compatible endpoint).

Phase 3 (Phase.md). Design.md §5. Implements the Verifier protocol (§4).
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

from src.common.cache import JsonlCache, make_cache_key
from src.common.config import Config, load_config
from src.common.io import CacheRecord, Pair, VerifierResult
from src.common.prompts import compute_hash, load_prompt

logger = logging.getLogger(__name__)


class TokenBucketRateLimiter:
    """Token bucket rate limiter to respect free-tier API rate limits (Rule R2.9)."""

    def __init__(self, rpm: float) -> None:
        self.rpm = rpm
        self.interval = 60.0 / rpm if rpm > 0 else 0.0
        self.last_call = 0.0

    def acquire(self) -> None:
        """Wait until an API request slot is available."""
        if self.interval <= 0:
            return
        now = time.time()
        elapsed = now - self.last_call
        if elapsed < self.interval:
            sleep_time = self.interval - elapsed
            time.sleep(sleep_time)
        self.last_call = time.time()


class APIJudgeVerifier:
    """Filter A: LLM Judge verifier using Gemini Flash via OpenAI-compatible endpoint.

    Implements:
    - Retries on network/429 errors with exponential backoff (Rule R2.7)
    - Rate limiter respecting free-tier limits (Rule R2.9)
    - JSON extraction and validation (Design.md §5.3)
    - Exactly one retry on parse failure (Rule R2.6)
    - Response caching in data/cache/judge_gemini.jsonl (Rule R2.5)
    - Fresh calls in timing mode without reading cache (Rule R3.2)
    """

    name: str = "filter_a"

    def __init__(
        self,
        cfg: Config | None = None,
        prompt_name: str = "judge_v1.txt",
        cache_path: str | Path | None = None,
        client: Any = None,
    ) -> None:
        self.cfg = cfg or load_config()
        self.prompt_name = prompt_name
        self.cache_path = Path(
            cache_path or (Path(self.cfg.paths.cache) / "judge_gemini.jsonl")
        )
        self.client = client

        self.template: str = ""
        self.prompt_hash: str = ""
        self.cache: JsonlCache | None = None
        self.rate_limiter: TokenBucketRateLimiter | None = None

    def load(self) -> float:
        """Initialize client, load prompt template, and open cache."""
        t0 = time.perf_counter()

        # 1. Load prompt template
        self.template = load_prompt(self.prompt_name, base=self.cfg.paths.prompts)
        self.prompt_hash = compute_hash(self.template)

        # 2. Rate limiter
        rpm = self.cfg.models.judge.rpm_limit
        rpm_val = float(rpm) if isinstance(rpm, (int, float)) and rpm > 0 else 15.0
        self.rate_limiter = TokenBucketRateLimiter(rpm=rpm_val)

        # 3. Client
        if self.client is None:
            api_key = os.getenv("GEMINI_API_KEY")
            if not api_key:
                raise ValueError("GEMINI_API_KEY not found in environment (.env)")
            self.client = OpenAI(
                api_key=api_key,
                base_url=self.cfg.models.judge.base_url,
            )

        # 4. Cache
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        self.cache = JsonlCache(self.cache_path)

        load_time = time.perf_counter() - t0
        logger.info(
            "Loaded %s (model=%s, rpm=%.1f, cached_entries=%d) in %.4f s",
            self.name,
            self.cfg.models.judge.model_id,
            rpm_val,
            len(self.cache),
            load_time,
        )
        return load_time

    @staticmethod
    def parse_response(raw_text: str) -> dict[str, Any]:
        """Parse raw model output into validated verdict and confidence dictionary.

        Raises ValueError if format is invalid.
        """
        text = raw_text.strip()
        # Extract json code fences if present
        match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
        if match:
            text = match.group(1)
        else:
            start = text.find("{")
            end = text.rfind("}")
            if start != -1 and end != -1 and end > start:
                text = text[start : end + 1]

        data = json.loads(text)
        if not isinstance(data, dict):
            raise ValueError(f"Parsed JSON is not a dictionary: {type(data)}")

        verdict = data.get("verdict")
        if verdict not in ("SUPPORTED", "NOT_SUPPORTED"):
            raise ValueError(
                f"Invalid verdict {verdict!r}, must be SUPPORTED or NOT_SUPPORTED"
            )

        confidence = data.get("confidence")
        if confidence is None or not isinstance(confidence, (int, float)):
            raise ValueError(f"Invalid confidence {confidence!r}, must be a float")
        confidence = float(confidence)
        if not (0.0 <= confidence <= 1.0):
            raise ValueError(f"Confidence {confidence} out of range [0.0, 1.0]")

        return {
            "verdict": verdict,
            "confidence": confidence,
            "reason": str(data.get("reason", "")),
        }

    def _call_api(self, prompt_text: str) -> tuple[str, int | None, int | None, float]:
        """Execute chat completion with tenacity retry on network/429 errors (Rule R2.7)."""
        assert self.client is not None
        assert self.rate_limiter is not None

        @retry(
            wait=wait_exponential(multiplier=2, min=2, max=60),
            stop=stop_after_attempt(6),
            reraise=True,
        )
        def _execute() -> tuple[str, int | None, int | None, float]:
            self.rate_limiter.acquire()
            t_start = time.perf_counter()
            response = self.client.chat.completions.create(
                model=self.cfg.models.judge.model_id,
                messages=[{"role": "user", "content": prompt_text}],
                temperature=self.cfg.models.judge.temperature,
                reasoning_effort="low",
                max_tokens=self.cfg.models.judge.max_tokens,
            )
            # Rule R3.5: measure verifier call only
            lat_ms = (time.perf_counter() - t_start) * 1000.0
            content = response.choices[0].message.content or ""
            in_tok = response.usage.prompt_tokens if response.usage else None
            out_tok = response.usage.completion_tokens if response.usage else None
            return content, in_tok, out_tok, lat_ms

        return _execute()

    def score(
        self,
        context: str,
        answer: str,
        pair_id: str = "",
        mode: Literal["normal", "timing"] = "normal",
    ) -> VerifierResult:
        """Score a single context-answer pair using the LLM judge."""
        if self.cache is None or self.template == "":
            self.load()
            assert self.cache is not None

        # Exact string replacement per Rule R2.8 & Design.md §5.2
        prompt_text = self.template.replace("{context}", context).replace(
            "{answer}", answer
        )
        model_id = self.cfg.models.judge.model_id
        cache_key = make_cache_key(model_id, self.prompt_hash, context, answer)

        # Rule R3.2: Timing runs call API fresh; normal mode reads cache
        if mode == "normal" and cache_key in self.cache:
            record = self.cache.get(cache_key)
            if record is not None and record.parsed is not None:
                parsed = record.parsed
                verdict_str = parsed.get("verdict")
                conf = float(parsed.get("confidence", 1.0))
                verdict_code = (
                    0
                    if verdict_str == "SUPPORTED"
                    else (1 if verdict_str == "NOT_SUPPORTED" else None)
                )
                score_val = conf if verdict_str == "SUPPORTED" else 1.0 - conf
                return VerifierResult(
                    pair_id=pair_id,
                    verifier="filter_a",
                    score=score_val,
                    verdict=verdict_code,  # type: ignore[arg-type]
                    confidence=conf,
                    latency_ms=record.latency_ms,
                    input_tokens=record.input_tokens,
                    output_tokens=record.output_tokens,
                    parse_failure=False,
                    details={
                        "from_cache": True,
                        "raw_response": record.response_text,
                        "parsed": parsed,
                    },
                )

        # Call API
        raw_text, in_tok, out_tok, lat_ms = self._call_api(prompt_text)
        attempt = 1
        parsed = None
        parse_failure = False

        try:
            parsed = self.parse_response(raw_text)
        except Exception as e1:
            logger.warning(
                "Parse failure on attempt 1 for pair %s: %s. Retrying once (Rule R2.6)...",
                pair_id,
                e1,
            )
            # Rule R2.6: Retry an unparseable judge output exactly once
            attempt = 2
            raw_text, in_tok, out_tok, lat_ms_retry = self._call_api(prompt_text)
            lat_ms += lat_ms_retry
            try:
                parsed = self.parse_response(raw_text)
            except Exception as e2:
                logger.error(
                    "Parse failure on attempt 2 for pair %s: %s. Recorded as parse failure.",
                    pair_id,
                    e2,
                )
                parse_failure = True

        # Append to cache
        cache_rec = CacheRecord(
            key=cache_key,
            provider=self.cfg.models.judge.provider,
            model_id=model_id,
            prompt_hash=self.prompt_hash,
            request_text=prompt_text,
            response_text=raw_text,
            parsed=parsed,
            input_tokens=in_tok,
            output_tokens=out_tok,
            latency_ms=lat_ms,
            attempt=attempt,
            mode=mode,
            timestamp_utc=datetime.now(UTC).isoformat(),
        )
        self.cache.append(cache_rec)

        if parse_failure or parsed is None:
            return VerifierResult(
                pair_id=pair_id,
                verifier="filter_a",
                score=None,
                verdict=None,
                confidence=None,
                latency_ms=lat_ms,
                input_tokens=in_tok,
                output_tokens=out_tok,
                parse_failure=True,
                details={"from_cache": False, "raw_response": raw_text},
            )

        verdict_str = parsed.get("verdict")
        conf = float(parsed.get("confidence", 1.0))
        verdict_code = (
            0
            if verdict_str == "SUPPORTED"
            else (1 if verdict_str == "NOT_SUPPORTED" else None)
        )
        score_val = conf if verdict_str == "SUPPORTED" else 1.0 - conf

        return VerifierResult(
            pair_id=pair_id,
            verifier="filter_a",
            score=score_val,
            verdict=verdict_code,  # type: ignore[arg-type]
            confidence=conf,
            latency_ms=lat_ms,
            input_tokens=in_tok,
            output_tokens=out_tok,
            parse_failure=False,
            details={
                "from_cache": False,
                "raw_response": raw_text,
                "parsed": parsed,
                "attempt": attempt,
            },
        )

    def score_batch(self, pairs: list[Pair]) -> list[VerifierResult]:
        """Score a list of pairs sequentially with rate limiting."""
        if self.cache is None:
            self.load()

        results: list[VerifierResult] = []
        for p in pairs:
            res = self.score(context=p.context, answer=p.answer, pair_id=p.pair_id)
            results.append(res)
        return results
