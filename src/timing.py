"""Timing protocol for latency, load time, and peak RAM measurement.

Phase 5b (Phase.md). Design.md §9. Rules §3.
Entry point:
    python -m src.timing --config configs/config.yaml --verifier <name> --split test --session <morning|evening> --confirm
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import sys
import time
from pathlib import Path

import numpy as np
import psutil

from src.common.config import Config, load_config
from src.common.io import Pair, read_jsonl
from src.common.logging_utils import setup_logging
from src.common.manifest import generate_run_id, get_machine_info
from src.filters.base import Verifier
from src.filters.baseline_rouge import RougeLVerifier
from src.filters.filter_api import APIJudgeVerifier
from src.filters.filter_nli import NLIVerifier

logger = logging.getLogger(__name__)

CHECKLIST = [
    "1. Laptop is connected to AC charger (performance power mode).",
    "2. Web browser, media players, and non-essential applications are closed.",
    "3. OS background updates and antivirus scans are paused (Windows).",
    "4. No other Python processes or background computational jobs are running.",
]


def print_checklist() -> None:
    """Print pre-run laptop timing checklist (Phase 5b / Rule R3.8)."""
    print("\n" + "=" * 65)
    print("PRE-RUN TIMING BENCHMARK CHECKLIST (Rules §3, Rule R3.8)")
    print("=" * 65)
    for item in CHECKLIST:
        print(f"  [X] {item}")
    print("=" * 65 + "\n")


def get_exp1_run_id(cfg: Config, explicit_run_id: str | None = None) -> str:
    """Retrieve existing exp1 run_id from LATEST.json or generate a new one."""
    if explicit_run_id:
        return explicit_run_id

    latest_path = Path(cfg.paths.results) / "LATEST.json"
    if latest_path.exists():
        try:
            with open(latest_path, encoding="utf-8") as f:
                data = json.load(f)
            if "exp1" in data and data["exp1"]:
                return str(data["exp1"])
        except Exception as e:
            logger.warning("Could not read LATEST.json: %s", e)

    run_id = generate_run_id()
    # Save pointer
    latest_path.parent.mkdir(parents=True, exist_ok=True)
    existing: dict[str, str] = {}
    if latest_path.exists():
        try:
            with open(latest_path, encoding="utf-8") as f:
                existing = json.load(f)
        except Exception:
            pass
    existing["exp1"] = run_id
    with open(latest_path, "w", encoding="utf-8") as f:
        json.dump(existing, f, indent=2)
    return run_id


def measure_verifier_timing(
    verifier: Verifier,
    pairs: list[Pair],
    cfg: Config,
    out_dir: Path,
    session: str = "morning",
    limit: int | None = None,
) -> dict:
    """Execute the standardized timing protocol on a verifier.

    Steps:
    1. Measure model load time and initial RAM.
    2. Execute 10 warm-up pairs and discard latencies (Rule R3.4).
    3. Measure per-pair latency with time.perf_counter() around score() only (Rule R3.5).
    4. Repeat twice (Rule R3.6).
    5. Track peak RAM using psutil (Rule R3.9).
    6. For Filter A, assert no cache hits (Rule R3.2).
    7. Output JSON and per-pair CSV (Design.md §9).
    """
    proc = psutil.Process()
    rss_before_mb = proc.memory_info().rss / (1024 * 1024)

    logger.info("Timing model load for verifier: %s", verifier.name)
    load_start = time.perf_counter()
    verifier.load()
    load_time_s = time.perf_counter() - load_start
    rss_after_load_mb = proc.memory_info().rss / (1024 * 1024)
    peak_rss_mb = max(rss_before_mb, rss_after_load_mb)
    logger.info(
        "Verifier %s loaded in %.4f s (RSS: %.1f MB -> %.1f MB)",
        verifier.name,
        load_time_s,
        rss_before_mb,
        rss_after_load_mb,
    )

    warmup_n = min(cfg.timing.warmup_pairs, len(pairs))
    warmup_pairs = pairs[:warmup_n]
    eval_pairs = pairs[warmup_n:]

    if limit is not None and limit > 0:
        eval_pairs = eval_pairs[:limit]
        logger.info("Limited evaluated timing pairs to %d", len(eval_pairs))

    if not eval_pairs:
        raise ValueError(f"No pairs available for timing after {warmup_n} warm-ups")

    # 1. Warm-up (Rule R3.4)
    logger.info("Executing %d warm-up pairs (discarding latencies)...", len(warmup_pairs))
    for p in warmup_pairs:
        if verifier.name == "filter_a":
            verifier.score(p.context, p.answer, pair_id=p.pair_id, mode="timing")  # type: ignore[call-arg]
        else:
            verifier.score(p.context, p.answer, pair_id=p.pair_id)

    # 2. Repeated inference passes (Rule R3.6)
    pass1_latencies: list[float] = []
    pass2_latencies: list[float] = []
    per_pair_rows: list[dict[str, str | int | float]] = []

    # Pass 1
    logger.info("Executing timing Pass 1 over %d pairs...", len(eval_pairs))
    for p in eval_pairs:
        t0 = time.perf_counter()
        if verifier.name == "filter_a":
            res = verifier.score(p.context, p.answer, pair_id=p.pair_id, mode="timing")  # type: ignore[call-arg]
            # Rule R3.2 assertion
            assert res.details.get("from_cache") is not True, "Cache hit detected during timing run (violates Rule R3.2)"
        else:
            res = verifier.score(p.context, p.answer, pair_id=p.pair_id)
        lat_ms = (time.perf_counter() - t0) * 1000.0
        pass1_latencies.append(lat_ms)
        per_pair_rows.append({"pair_id": p.pair_id, "pass": 1, "latency_ms": round(lat_ms, 3)})

        curr_rss = proc.memory_info().rss / (1024 * 1024)
        if curr_rss > peak_rss_mb:
            peak_rss_mb = curr_rss

    # Pass 2
    logger.info("Executing timing Pass 2 over %d pairs...", len(eval_pairs))
    for p in eval_pairs:
        t0 = time.perf_counter()
        if verifier.name == "filter_a":
            res = verifier.score(p.context, p.answer, pair_id=p.pair_id, mode="timing")  # type: ignore[call-arg]
            assert res.details.get("from_cache") is not True, "Cache hit detected during timing run (violates Rule R3.2)"
        else:
            res = verifier.score(p.context, p.answer, pair_id=p.pair_id)
        lat_ms = (time.perf_counter() - t0) * 1000.0
        pass2_latencies.append(lat_ms)
        per_pair_rows.append({"pair_id": p.pair_id, "pass": 2, "latency_ms": round(lat_ms, 3)})

        curr_rss = proc.memory_info().rss / (1024 * 1024)
        if curr_rss > peak_rss_mb:
            peak_rss_mb = curr_rss

    pooled_latencies = pass1_latencies + pass2_latencies

    machine_info = get_machine_info()
    machine_info["on_charger"] = True

    timing_result = {
        "verifier": verifier.name,
        "session": session,
        "machine_info": machine_info,
        "load_time_seconds": round(load_time_s, 4),
        "rss_initial_mb": round(rss_before_mb, 2),
        "rss_after_load_mb": round(rss_after_load_mb, 2),
        "peak_rss_mb": round(peak_rss_mb, 2),
        "warmup_pairs": warmup_n,
        "n_timed_pairs": len(eval_pairs),
        "pass1": {
            "median_ms": round(float(np.median(pass1_latencies)), 2),
            "p95_ms": round(float(np.percentile(pass1_latencies, 95)), 2),
            "mean_ms": round(float(np.mean(pass1_latencies)), 2),
            "min_ms": round(float(np.min(pass1_latencies)), 2),
            "max_ms": round(float(np.max(pass1_latencies)), 2),
            "n": len(pass1_latencies),
        },
        "pass2": {
            "median_ms": round(float(np.median(pass2_latencies)), 2),
            "p95_ms": round(float(np.percentile(pass2_latencies, 95)), 2),
            "mean_ms": round(float(np.mean(pass2_latencies)), 2),
            "min_ms": round(float(np.min(pass2_latencies)), 2),
            "max_ms": round(float(np.max(pass2_latencies)), 2),
            "n": len(pass2_latencies),
        },
        "pooled": {
            "median_ms": round(float(np.median(pooled_latencies)), 2),
            "p95_ms": round(float(np.percentile(pooled_latencies, 95)), 2),
            "mean_ms": round(float(np.mean(pooled_latencies)), 2),
            "min_ms": round(float(np.min(pooled_latencies)), 2),
            "max_ms": round(float(np.max(pooled_latencies)), 2),
            "n": len(pooled_latencies),
        },
    }

    # Save timing JSON for session
    session_json_path = out_dir / f"timing_{verifier.name}_{session}.json"
    with open(session_json_path, "w", encoding="utf-8") as f:
        json.dump(timing_result, f, indent=2)

    # Save per-pair CSV
    session_csv_path = out_dir / f"timing_{verifier.name}_{session}.csv"
    with open(session_csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["pair_id", "pass", "latency_ms"])
        writer.writeheader()
        writer.writerows(per_pair_rows)

    # Save consolidated timing JSON (e.g. timing_filter_b.json)
    cons_json_path = out_dir / f"timing_{verifier.name}.json"
    with open(cons_json_path, "w", encoding="utf-8") as f:
        json.dump(timing_result, f, indent=2)

    logger.info("Saved timing outputs to %s and %s", session_json_path, session_csv_path)

    # Update metrics.json with tile keys
    metrics_path = out_dir / "metrics.json"
    metrics_data: dict = {}
    if metrics_path.exists():
        try:
            with open(metrics_path, encoding="utf-8") as f:
                metrics_data = json.load(f)
        except Exception:
            pass

    tile_key = f"timing.{verifier.name}.median_ms"
    metrics_data[tile_key] = {
        "value": timing_result["pooled"]["median_ms"],
        "display": f"{timing_result['pooled']['median_ms']:.1f} ms",
        "source": str(cons_json_path.as_posix()),
    }
    with open(metrics_path, "w", encoding="utf-8") as f:
        json.dump(metrics_data, f, indent=2)

    return timing_result


def main() -> None:
    parser = argparse.ArgumentParser(description="Timing protocol for verifiers.")
    parser.add_argument("--config", default="configs/config.yaml", help="Path to config YAML")
    parser.add_argument(
        "--verifier",
        default="all",
        choices=["all", "rouge", "filter_b", "filter_a"],
        help="Which verifier to time (default: all)",
    )
    parser.add_argument(
        "--split",
        default="test",
        choices=["test", "dev"],
        help="Split to time on (default: test per Rule R3.1)",
    )
    parser.add_argument(
        "--session",
        default="morning",
        choices=["morning", "evening"],
        help="Timing session (morning/evening for Filter A per Rule R3.7)",
    )
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="Confirm pre-run laptop environment checklist",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional limit on pairs to time (after warm-up)",
    )
    parser.add_argument(
        "--run-id",
        default=None,
        help="Explicit run ID to associate timing with",
    )
    args = parser.parse_args()

    print_checklist()
    if not args.confirm:
        print("ERROR: Pre-run checklist must be confirmed with --confirm flag per Rule R3.8.")
        sys.exit(1)

    cfg = load_config(args.config)
    setup_logging(f"timing_{args.verifier}_{args.session}")

    # Load split pairs (Rule R3.1: Exp 1 test pairs only)
    split_file = Path(cfg.paths.data) / "exp1_medhallu" / f"{args.split}.jsonl"
    if not split_file.exists():
        raise FileNotFoundError(f"Split file not found: {split_file}")
    pairs = read_jsonl(split_file, Pair)
    logger.info("Loaded %d pairs from %s", len(pairs), split_file)

    run_id = get_exp1_run_id(cfg, args.run_id)
    out_dir = Path(cfg.paths.results) / "exp1" / run_id
    out_dir.mkdir(parents=True, exist_ok=True)
    logger.info("Timing output directory: %s", out_dir)

    verifiers_to_time: list[Verifier] = []
    if args.verifier in ("all", "rouge"):
        verifiers_to_time.append(RougeLVerifier(field=cfg.baseline.rouge_field))
    if args.verifier in ("all", "filter_b"):
        verifiers_to_time.append(
            NLIVerifier(
                model_id=cfg.models.nli_main,
                num_threads=cfg.filter_b.num_threads,
                batch_size=1,  # Rule R6.4: batch size 1 in timing runs
                max_length=cfg.filter_b.max_length,
            )
        )
    if args.verifier in ("all", "filter_a"):
        verifiers_to_time.append(APIJudgeVerifier(cfg=cfg))

    print("=" * 65)
    print(f"RUNNING TIMING BENCHMARKS: split={args.split}, session={args.session}")
    print(f"Run ID: {run_id}")
    print(f"Output directory: {out_dir}")
    print("=" * 65)

    for v in verifiers_to_time:
        print(f"\n---> Benchmarking {v.name.upper()} ({args.session} session)...")
        res = measure_verifier_timing(
            verifier=v,
            pairs=pairs,
            cfg=cfg,
            out_dir=out_dir,
            session=args.session,
            limit=args.limit,
        )
        print(f"     Load time:   {res['load_time_seconds']:.4f} s")
        print(f"     Peak RAM:    {res['peak_rss_mb']:.1f} MB")
        print(f"     Pass 1 p50:  {res['pass1']['median_ms']:.1f} ms | p95: {res['pass1']['p95_ms']:.1f} ms")
        print(f"     Pass 2 p50:  {res['pass2']['median_ms']:.1f} ms | p95: {res['pass2']['p95_ms']:.1f} ms")
        print(f"     POOLED p50:  {res['pooled']['median_ms']:.1f} ms | p95: {res['pooled']['p95_ms']:.1f} ms")

    print("\n" + "=" * 65)
    print("TIMING BENCHMARKS COMPLETED")
    print("=" * 65)


if __name__ == "__main__":
    main()
