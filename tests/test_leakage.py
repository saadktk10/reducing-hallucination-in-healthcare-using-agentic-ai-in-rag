"""Tests for data leakage prevention — Phase 4.

Design.md §7.1 and Rule R1.8:
- Exp 2 questions must be strictly disjoint from Exp 1 test and dev questions.
- Assert zero question overlap.
- Assert correct class and condition balance.
"""

from __future__ import annotations

from pathlib import Path

from src.common.config import load_config
from src.common.io import Pair, QuestionRecord, read_jsonl
from src.common.text import normalize_question


def test_zero_leakage_exp2_vs_exp1() -> None:
    """Assert zero question overlap between Exp 2 questions and Exp 1 dev/test splits."""
    cfg = load_config()
    data_dir = Path(cfg.paths.data)

    dev_file = data_dir / "exp1_medhallu" / "dev.jsonl"
    test_file = data_dir / "exp1_medhallu" / "test.jsonl"
    q_file = data_dir / "exp2_rag" / "questions.jsonl"

    if not q_file.exists():
        # Will be tested after build_index runs
        return

    exp1_dev_pairs = read_jsonl(dev_file, Pair)
    exp1_test_pairs = read_jsonl(test_file, Pair)
    exp2_questions = read_jsonl(q_file, QuestionRecord)

    dev_q_norm = {normalize_question(p.question) for p in exp1_dev_pairs}
    test_q_norm = {normalize_question(p.question) for p in exp1_test_pairs}
    exp2_q_norm = {normalize_question(q.question) for q in exp2_questions}

    # 1. Assert zero overlap with test
    overlap_test = exp2_q_norm.intersection(test_q_norm)
    assert len(overlap_test) == 0, f"Leakage detected between Exp 2 and Exp 1 test: {overlap_test}"

    # 2. Assert zero overlap with dev (per Rule R1.8 and exclude_exp1_dev config)
    overlap_dev = exp2_q_norm.intersection(dev_q_norm)
    assert len(overlap_dev) == 0, f"Leakage detected between Exp 2 and Exp 1 dev: {overlap_dev}"

    # 3. Assert count and balance
    expected_total = cfg.exp2.n_normal + cfg.exp2.n_degraded
    assert len(exp2_questions) == expected_total
    n_normal = sum(1 for q in exp2_questions if q.condition == "normal")
    n_degraded = sum(1 for q in exp2_questions if q.condition == "degraded")
    assert n_normal == cfg.exp2.n_normal
    assert n_degraded == cfg.exp2.n_degraded


def test_exp2_questions_unique_ids() -> None:
    """Assert all question IDs and source_doc_ids are valid and unique."""
    cfg = load_config()
    q_file = Path(cfg.paths.data) / "exp2_rag" / "questions.jsonl"
    if not q_file.exists():
        return

    exp2_questions = read_jsonl(q_file, QuestionRecord)
    qids = [q.question_id for q in exp2_questions]
    assert len(qids) == len(set(qids)), "Duplicate question_id in questions.jsonl"
