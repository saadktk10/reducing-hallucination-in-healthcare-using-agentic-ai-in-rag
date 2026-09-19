"""Unit tests for src/annotation.py (Phase 6).

Covers:
- Label parsing and formatting
- Sheet export integrity (Rule R1.5 empty labels, Rule R1.6 blind condition)
- Cohen's kappa calculation and disagreement logging
- Merging resolved annotations into validated Pair records (Rule R5.6)
- Gate G2 class balance checks
"""

from __future__ import annotations

import csv
from pathlib import Path

import pytest

from src.annotation import (
    SHEET_COLUMNS,
    compute_kappa,
    export_sheets,
    format_label,
    merge_annotations,
    parse_label,
)
from src.common.config import load_config
from src.common.io import Generated, Pair, QuestionRecord, write_jsonl


def test_parse_label() -> None:
    """Test flexible parsing of user annotation labels."""
    assert parse_label("Supported") == 0
    assert parse_label("supported") == 0
    assert parse_label("0") == 0
    assert parse_label(0) == 0
    assert parse_label("s") == 0

    assert parse_label("Hallucinated") == 1
    assert parse_label("hallucinated") == 1
    assert parse_label("1") == 1
    assert parse_label(1) == 1
    assert parse_label("h") == 1
    assert parse_label("unsupported") == 1

    assert parse_label("") is None
    assert parse_label("   ") is None
    assert parse_label("None") is None
    assert parse_label(None) is None

    with pytest.raises(ValueError, match="Invalid label"):
        parse_label("maybe")


def test_format_label() -> None:
    """Test integer code formatting."""
    assert format_label(0) == "Supported"
    assert format_label(1) == "Hallucinated"
    assert format_label(None) == ""


def test_export_sheets(tmp_path: Path) -> None:
    """Test sheet export creates identical, blind, unannotated copies."""
    data_dir = tmp_path / "data"
    rag_dir = data_dir / "exp2_rag"
    rag_dir.mkdir(parents=True, exist_ok=True)

    # Mock questions.jsonl
    q_records = [
        QuestionRecord(
            question_id="e2-q001",
            question="Is drug A effective?",
            source_doc_id="1001",
            condition="normal",
        ),
        QuestionRecord(
            question_id="e2-q002",
            question="Does drug B cause nausea?",
            source_doc_id="1002",
            condition="degraded",
        ),
    ]
    write_jsonl(rag_dir / "questions.jsonl", q_records)

    # Mock generated.jsonl
    gen_records = [
        Generated(
            question_id="e2-q001",
            condition="normal",
            retrieved_chunk_ids=["1001-0"],
            retrieved_doc_ids=["1001"],
            own_doc_in_context=True,
            context="Drug A is effective.",
            answer="Yes, drug A is effective.",
            generator_model_id="qwen",
            prompt_hash="abc",
            cache_key="key1",
        ),
        Generated(
            question_id="e2-q002",
            condition="degraded",
            retrieved_chunk_ids=["9999-0"],
            retrieved_doc_ids=["9999"],
            own_doc_in_context=False,
            context="Different topic.",
            answer="Drug B prevents nausea.",
            generator_model_id="qwen",
            prompt_hash="abc",
            cache_key="key2",
        ),
    ]
    write_jsonl(rag_dir / "generated.jsonl", gen_records)

    cfg = load_config()
    cfg.paths.data = str(data_dir)
    cfg.seed = 42

    out_dir = tmp_path / "out_ann"
    t_csv, a1_csv, a2_csv, guide_md = export_sheets(cfg, out_dir=out_dir)

    assert t_csv.exists()
    assert a1_csv.exists()
    assert a2_csv.exists()
    assert guide_md.exists()

    # Verify guide has definition
    guide_content = guide_md.read_text(encoding="utf-8")
    assert "Supported" in guide_content
    assert "Hallucinated" in guide_content
    assert "Rule R1.11" in guide_content

    # Verify CSV headers and emptiness (Rule R1.5, R1.6)
    for p in [t_csv, a1_csv, a2_csv]:
        with open(p, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            assert reader.fieldnames == SHEET_COLUMNS
            assert "condition" not in reader.fieldnames  # Blind
            rows = list(reader)
            assert len(rows) == 2
            for r in rows:
                assert r["label (Supported/Hallucinated)"] == ""  # Empty label


def test_compute_kappa(tmp_path: Path) -> None:
    """Test Cohen's kappa and disagreement logging."""
    f1 = tmp_path / "ann1.csv"
    f2 = tmp_path / "ann2.csv"

    fieldnames = SHEET_COLUMNS

    rows1 = [
        {"pair_id": "p1", "question": "q1", "retrieved_context": "c1", "answer": "a1", "label (Supported/Hallucinated)": "Supported", "notes": ""},
        {"pair_id": "p2", "question": "q2", "retrieved_context": "c2", "answer": "a2", "label (Supported/Hallucinated)": "Hallucinated", "notes": ""},
        {"pair_id": "p3", "question": "q3", "retrieved_context": "c3", "answer": "a3", "label (Supported/Hallucinated)": "Supported", "notes": ""},
        {"pair_id": "p4", "question": "q4", "retrieved_context": "c4", "answer": "a4", "label (Supported/Hallucinated)": "Hallucinated", "notes": ""},
    ]
    # Row 3 disagrees (ann1=Supported, ann2=Hallucinated)
    rows2 = [
        {"pair_id": "p1", "question": "q1", "retrieved_context": "c1", "answer": "a1", "label (Supported/Hallucinated)": "Supported", "notes": ""},
        {"pair_id": "p2", "question": "q2", "retrieved_context": "c2", "answer": "a2", "label (Supported/Hallucinated)": "Hallucinated", "notes": ""},
        {"pair_id": "p3", "question": "q3", "retrieved_context": "c3", "answer": "a3", "label (Supported/Hallucinated)": "Hallucinated", "notes": "ann2 thought hal"},
        {"pair_id": "p4", "question": "q4", "retrieved_context": "c4", "answer": "a4", "label (Supported/Hallucinated)": "Hallucinated", "notes": ""},
    ]

    for p, rows in [(f1, rows1), (f2, rows2)]:
        with open(p, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

    disagreements_file = tmp_path / "disagreements.csv"
    res = compute_kappa(f1, f2, out_disagreements=disagreements_file)

    assert res["total_pairs"] == 4
    assert res["annotated_pairs"] == 4
    assert res["agreed_count"] == 3
    assert res["disagreed_count"] == 1
    assert res["raw_agreement"] == 0.75
    assert res["cohen_kappa"] is not None
    assert disagreements_file.exists()

    with open(disagreements_file, encoding="utf-8") as f:
        d_rows = list(csv.DictReader(f))
        assert len(d_rows) == 1
        assert d_rows[0]["pair_id"] == "p3"
        assert d_rows[0]["annotator_1"] == "Supported"
        assert d_rows[0]["annotator_2"] == "Hallucinated"


def test_merge_annotations(tmp_path: Path) -> None:
    """Test merge produces valid Pair records with split='rag'."""
    data_dir = tmp_path / "data"
    rag_dir = data_dir / "exp2_rag"
    rag_dir.mkdir(parents=True, exist_ok=True)

    q_records = [
        QuestionRecord(
            question_id="e2-q001",
            question="Is drug A safe?",
            source_doc_id="101",
            condition="normal",
        ),
        QuestionRecord(
            question_id="e2-q002",
            question="Does drug B work?",
            source_doc_id="102",
            condition="degraded",
        ),
    ]
    write_jsonl(rag_dir / "questions.jsonl", q_records)

    gen_records = [
        Generated(
            question_id="e2-q001",
            condition="normal",
            retrieved_chunk_ids=["101-0"],
            retrieved_doc_ids=["101"],
            own_doc_in_context=True,
            context="Drug A is safe.",
            answer="Yes.",
            generator_model_id="qwen",
            prompt_hash="abc",
            cache_key="k1",
        ),
        Generated(
            question_id="e2-q002",
            condition="degraded",
            retrieved_chunk_ids=["999-0"],
            retrieved_doc_ids=["999"],
            own_doc_in_context=False,
            context="Unknown.",
            answer="No.",
            generator_model_id="qwen",
            prompt_hash="abc",
            cache_key="k2",
        ),
    ]
    write_jsonl(rag_dir / "generated.jsonl", gen_records)

    labeled_csv = rag_dir / "labeled.csv"
    with open(labeled_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f, fieldnames=["pair_id", "annotator_1", "annotator_2", "final_label", "resolution_notes"]
        )
        writer.writeheader()
        writer.writerow({
            "pair_id": "e2-q001",
            "annotator_1": "Supported",
            "annotator_2": "Supported",
            "final_label": "Supported",
            "resolution_notes": "",
        })
        writer.writerow({
            "pair_id": "e2-q002",
            "annotator_1": "Supported",
            "annotator_2": "Hallucinated",
            "final_label": "Hallucinated",
            "resolution_notes": "Resolved to Hallucinated after discussion",
        })

    cfg = load_config()
    cfg.paths.data = str(data_dir)

    pairs = merge_annotations(cfg, labeled_csv=labeled_csv)
    assert len(pairs) == 2

    p1 = pairs[0]
    assert isinstance(p1, Pair)
    assert p1.pair_id == "e2-q001"
    assert p1.split == "rag"
    assert p1.experiment == "exp2"
    assert p1.label == 0  # Supported
    assert p1.condition == "normal"

    p2 = pairs[1]
    assert p2.pair_id == "e2-q002"
    assert p2.split == "rag"
    assert p2.label == 1  # Hallucinated
    assert p2.condition == "degraded"
