"""Annotation tooling for Experiment 2: export, kappa, disagreements, and merge.

Phase 6 (Phase.md). Design.md §3.6, §8.2.
Entry points:
    python -m src.annotation export [--config configs/config.yaml]
    python -m src.annotation kappa [--config configs/config.yaml] [--annotator-1 <path>] [--annotator-2 <path>]
    python -m src.annotation merge [--config configs/config.yaml] [--labeled <path>]
"""

from __future__ import annotations

import argparse
import csv
import logging
import random
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.metrics import cohen_kappa_score

from src.common.config import Config, load_config
from src.common.io import Generated, Pair, QuestionRecord, read_jsonl, write_jsonl
from src.common.logging_utils import setup_logging

logger = logging.getLogger(__name__)

SHEET_COLUMNS: list[str] = [
    "pair_id",
    "question",
    "retrieved_context",
    "answer",
    "label (Supported/Hallucinated)",
    "notes",
]

DISAGREEMENT_COLUMNS: list[str] = [
    "pair_id",
    "question",
    "retrieved_context",
    "answer",
    "annotator_1",
    "annotator_2",
    "notes_1",
    "notes_2",
    "final_label",
    "resolution_notes",
]

LABELED_COLUMNS: list[str] = [
    "pair_id",
    "annotator_1",
    "annotator_2",
    "final_label",
    "resolution_notes",
]


def parse_label(val: Any) -> int | None:
    """Normalize user input label string to 0 (Supported) or 1 (Hallucinated).

    Returns None if empty or unannotated.
    Raises ValueError if label text is invalid.
    """
    if val is None:
        return None
    s = str(val).strip().lower()
    if not s or s in ("none", "null", "nan", ""):
        return None
    if s in ("supported", "s", "0"):
        return 0
    if s in ("hallucinated", "h", "1", "unsupported"):
        return 1
    raise ValueError(
        f"Invalid label: '{val}'. Expected 'Supported' (0) or 'Hallucinated' (1)."
    )


def format_label(val: int | None) -> str:
    """Format integer label code back to canonical display string."""
    if val == 0:
        return "Supported"
    if val == 1:
        return "Hallucinated"
    return ""


def generate_guide_text() -> str:
    """Generate markdown text for annotation_guide.md per Rule R1.11 & Phase 6."""
    return """# Experiment 2: Human Annotation Guide

*Hallucination Verification in Healthcare Agentic RAG*
*Rule R1.11: Hallucination definition must be identical across all prompts, code, and guides.*

---

## 1. Hallucination Definition

The verifiers and annotators check **faithfulness to the provided context**, NOT general medical truth.

| Label | Code | Meaning |
| :--- | :--- | :--- |
| **Supported** | `0` | Every claim in the answer is entailed by the provided context. |
| **Hallucinated** | `1` | At least one claim is contradicted by, or absent from, the provided context. |

> **IMPORTANT**:
> - **Faithfulness over Prior Knowledge**: An answer that is factually or medically correct according to clinical textbooks, but makes claims **not supported by the retrieved context**, MUST be labeled **`Hallucinated`**.
> - **Partial Support is Hallucinated**: If an answer makes three claims, and two are supported but one is unsupported or contradicted, the answer is **`Hallucinated`**.
> - **Positive Class**: In this study, `Hallucinated` is the positive class (`1`), and `Supported` is the negative class (`0`).

---

## 2. Worked Examples

### Example 1: Supported (Entailed by Context)
- **Question**: Is amlodipine effective for systolic blood pressure reduction?
- **Retrieved Context**: A randomized controlled trial of 150 patients with mild-to-moderate hypertension showed that daily administration of 10 mg amlodipine reduced mean systolic blood pressure by 14 mmHg over 12 weeks.
- **Generated Answer**: Daily treatment with 10 mg amlodipine lowers systolic blood pressure in patients with mild-to-moderate hypertension.
- **Label**: **`Supported`** (`0`)
- **Rationale**: Every statement made in the answer is explicitly stated and entailed by the retrieved context.

### Example 2: Hallucinated (Extrinsic / Unsupported Claim)
- **Question**: What are the clinical indications and outcomes of metformin in type 2 diabetes?
- **Retrieved Context**: Metformin is the first-line oral hypoglycemic agent for type 2 diabetes mellitus, improving insulin sensitivity and reducing hepatic gluconeogenesis.
- **Generated Answer**: Metformin is the first-line therapy for type 2 diabetes and additionally reduces all-cause mortality in diabetic neuropathy by 25%.
- **Label**: **`Hallucinated`** (`1`)
- **Rationale**: The first clause is supported by the context. However, the claim regarding a "25% reduction in all-cause mortality in diabetic neuropathy" is completely absent from the provided context. Even if medically plausible, it is unsupported by the evidence and must be labeled `Hallucinated`.

### Example 3: Hallucinated (Intrinsic / Direct Contradiction)
- **Question**: Is routine antibiotic prophylaxis recommended for clean laparoscopic cholecystectomy?
- **Retrieved Context**: A systematic review of prospective trials revealed that routine antibiotic prophylaxis did not reduce surgical site infection rates in patients undergoing elective clean laparoscopic cholecystectomy.
- **Generated Answer**: Routine antibiotic prophylaxis is strongly recommended to prevent surgical site infections during elective clean laparoscopic cholecystectomy.
- **Label**: **`Hallucinated`** (`1`)
- **Rationale**: The answer directly contradicts the findings presented in the retrieved context.

---

## 3. Labeling Instructions

1. Fill the **`label (Supported/Hallucinated)`** column in your assigned file (`annotator_1.csv` or `annotator_2.csv`) with either **`Supported`** (or `0`) or **`Hallucinated`** (or `1`).
2. Optional: use the **`notes`** column to record brief reasoning or note specific clauses that were unsupported.
3. Work independently: **do not share or view the other annotator's file until all pairs are completed** (Rule R1.6).
4. After both annotators complete labeling, the disagreement analysis will be run via `python -m src.annotation kappa`.
"""


def export_sheets(
    cfg: Config,
    out_dir: Path | None = None,
) -> tuple[Path, Path, Path, Path]:
    """Export blind annotation templates and guide for Experiment 2.

    Creates:
    - template.csv
    - annotator_1.csv
    - annotator_2.csv
    - annotation_guide.md

    Enforces:
    - Rule R1.5: labels stay empty
    - Rule R1.6: condition column omitted (blind)
    - Rule R4.1: reproducible shuffle with global seed
    """
    data_dir = Path(cfg.paths.data) / "exp2_rag"
    gen_path = data_dir / "generated.jsonl"
    q_path = data_dir / "questions.jsonl"

    if not gen_path.exists():
        raise FileNotFoundError(f"Generated answers not found at {gen_path}")
    if not q_path.exists():
        raise FileNotFoundError(f"Questions not found at {q_path}")

    generated_records = read_jsonl(gen_path, Generated)
    question_records = read_jsonl(q_path, QuestionRecord)
    q_map = {q.question_id: q for q in question_records}

    rows: list[dict[str, str]] = []
    for gen in generated_records:
        q = q_map.get(gen.question_id)
        q_text = q.question if q else ""
        pair_id = gen.question_id  # In Exp 2, pair_id == question_id (Design.md §3.1)

        row = {
            "pair_id": pair_id,
            "question": q_text,
            "retrieved_context": gen.context,
            "answer": gen.answer,
            "label (Supported/Hallucinated)": "",  # Rule R1.5: empty
            "notes": "",
        }
        rows.append(row)

    # Shuffle rows reproducibly per Rule R4.1
    rng = random.Random(cfg.seed)
    rng.shuffle(rows)

    target_dir = out_dir or (data_dir / "annotation")
    target_dir.mkdir(parents=True, exist_ok=True)

    template_path = target_dir / "template.csv"
    ann1_path = target_dir / "annotator_1.csv"
    ann2_path = target_dir / "annotator_2.csv"
    guide_path = target_dir / "annotation_guide.md"

    def write_csv(path: Path, data: list[dict[str, str]]) -> None:
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=SHEET_COLUMNS)
            writer.writeheader()
            for r in data:
                writer.writerow(r)

    write_csv(template_path, rows)
    write_csv(ann1_path, rows)
    write_csv(ann2_path, rows)

    guide_path.write_text(generate_guide_text(), encoding="utf-8")

    logger.info(
        "Exported %d annotation rows to:\n  - %s\n  - %s\n  - %s\n  - %s",
        len(rows),
        template_path,
        ann1_path,
        ann2_path,
        guide_path,
    )
    return template_path, ann1_path, ann2_path, guide_path


def compute_kappa(
    file1: Path,
    file2: Path,
    out_disagreements: Path | None = None,
) -> dict[str, Any]:
    """Compute Cohen's kappa and export disagreements between two annotator files."""
    if not file1.exists():
        raise FileNotFoundError(f"Annotator 1 file not found: {file1}")
    if not file2.exists():
        raise FileNotFoundError(f"Annotator 2 file not found: {file2}")

    with open(file1, newline="", encoding="utf-8") as f:
        rows1 = list(csv.DictReader(f))
    with open(file2, newline="", encoding="utf-8") as f:
        rows2 = list(csv.DictReader(f))

    if len(rows1) != len(rows2):
        raise ValueError(
            f"Row count mismatch between annotators: {len(rows1)} vs {len(rows2)}"
        )

    pairs1 = [r.get("pair_id") for r in rows1]
    pairs2 = [r.get("pair_id") for r in rows2]
    if pairs1 != pairs2:
        raise ValueError("pair_id sequence does not match between annotators")

    labels1: list[int] = []
    labels2: list[int] = []
    missing_indices: list[int] = []

    disagreements: list[dict[str, str]] = []

    for idx, (r1, r2) in enumerate(zip(rows1, rows2, strict=False)):
        raw_label1 = r1.get("label (Supported/Hallucinated)") or r1.get("label")
        raw_label2 = r2.get("label (Supported/Hallucinated)") or r2.get("label")

        val1 = parse_label(raw_label1)
        val2 = parse_label(raw_label2)

        if val1 is None or val2 is None:
            missing_indices.append(idx)
            continue

        labels1.append(val1)
        labels2.append(val2)

        if val1 != val2:
            disagreements.append(
                {
                    "pair_id": r1.get("pair_id", ""),
                    "question": r1.get("question", ""),
                    "retrieved_context": r1.get("retrieved_context", ""),
                    "answer": r1.get("answer", ""),
                    "annotator_1": format_label(val1),
                    "annotator_2": format_label(val2),
                    "notes_1": r1.get("notes", ""),
                    "notes_2": r2.get("notes", ""),
                    "final_label": "",
                    "resolution_notes": "",
                }
            )

    if missing_indices:
        logger.warning(
            "Found %d pairs with missing annotations (indices: %s)",
            len(missing_indices),
            missing_indices[:10],
        )

    n_complete = len(labels1)
    if n_complete == 0:
        logger.error("No complete annotations found to compute kappa.")
        return {
            "total_pairs": len(rows1),
            "annotated_pairs": 0,
            "agreed_count": 0,
            "disagreed_count": 0,
            "raw_agreement": 0.0,
            "cohen_kappa": None,
        }

    agreed_count = sum(1 for a, b in zip(labels1, labels2, strict=False) if a == b)
    raw_agreement = agreed_count / n_complete

    # If all items agree or single class, cohen_kappa_score might raise or return NaN
    try:
        kappa_val = float(cohen_kappa_score(labels1, labels2))
        if np.isnan(kappa_val):
            kappa_val = 1.0 if raw_agreement == 1.0 else 0.0
    except Exception:
        kappa_val = 1.0 if raw_agreement == 1.0 else 0.0

    disagreements_path = (
        out_disagreements or file1.parent / "disagreements.csv"
    )
    with open(disagreements_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=DISAGREEMENT_COLUMNS)
        writer.writeheader()
        for d in disagreements:
            writer.writerow(d)

    logger.info(
        "Kappa Results (n=%d): Raw Agreement = %.2f%% (%d/%d), Cohen's Kappa = %.4f. Disagreements written to %s",
        n_complete,
        raw_agreement * 100.0,
        agreed_count,
        n_complete,
        kappa_val,
        disagreements_path,
    )

    if kappa_val < 0.6:
        logger.warning(
            "Cohen's kappa (%.4f) is below the 0.60 threshold (Phase.md Acceptance Criteria). Discussion required.",
            kappa_val,
        )

    return {
        "total_pairs": len(rows1),
        "annotated_pairs": n_complete,
        "agreed_count": agreed_count,
        "disagreed_count": len(disagreements),
        "raw_agreement": raw_agreement,
        "cohen_kappa": kappa_val,
        "disagreements_file": str(disagreements_path),
    }


def merge_annotations(
    cfg: Config,
    labeled_csv: Path | None = None,
    out_jsonl: Path | None = None,
) -> list[Pair]:
    """Merge human-resolved annotations into validated Pair records with split='rag'.

    Validates:
    - Every row has a valid final_label (0 or 1)
    - Metadata reconstructed from generated.jsonl & questions.jsonl
    - Rule R5.6 schema validation
    - Gate G2 class balance check
    """
    data_dir = Path(cfg.paths.data) / "exp2_rag"
    csv_path = labeled_csv or (data_dir / "labeled.csv")

    if not csv_path.exists():
        # Check if inside annotation folder
        alt_path = data_dir / "annotation" / "labeled.csv"
        if alt_path.exists():
            csv_path = alt_path
        else:
            raise FileNotFoundError(
                f"Resolved labeled CSV not found at {csv_path} or {alt_path}"
            )

    gen_path = data_dir / "generated.jsonl"
    q_path = data_dir / "questions.jsonl"
    if not gen_path.exists() or not q_path.exists():
        raise FileNotFoundError("Missing exp2_rag generated.jsonl or questions.jsonl")

    generated_records = {g.question_id: g for g in read_jsonl(gen_path, Generated)}
    question_records = {q.question_id: q for q in read_jsonl(q_path, QuestionRecord)}

    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        csv_rows = list(reader)

    pairs: list[Pair] = []
    missing_labels: list[str] = []

    for r in csv_rows:
        pair_id = r.get("pair_id", "").strip()
        raw_final = r.get("final_label") or r.get("label (Supported/Hallucinated)") or r.get("label")
        final_code = parse_label(raw_final)

        if final_code is None:
            missing_labels.append(pair_id)
            continue

        gen = generated_records.get(pair_id)
        q = question_records.get(pair_id)
        if gen is None or q is None:
            raise ValueError(
                f"pair_id '{pair_id}' from {csv_path} not found in generated or questions dataset."
            )

        pair = Pair(
            pair_id=pair_id,
            question_id=pair_id,
            experiment="exp2",
            split="rag",
            question=q.question,
            context=gen.context,
            answer=gen.answer,
            label=final_code,  # type: ignore[arg-type]
            condition=gen.condition,
            source_doc_id=q.source_doc_id,
        )
        pairs.append(pair)

    if missing_labels:
        raise ValueError(
            f"Cannot merge annotations: {len(missing_labels)} pairs missing final_label. Example IDs: {missing_labels[:5]}"
        )

    # Output paths
    target_jsonl = out_jsonl or (data_dir / "labeled.jsonl")
    target_pairs = data_dir / "pairs.jsonl"

    write_jsonl(target_jsonl, pairs)
    write_jsonl(target_pairs, pairs)

    # Class balance and Gate G2
    n_total = len(pairs)
    n_hal = sum(1 for p in pairs if p.label == 1)
    n_sup = sum(1 for p in pairs if p.label == 0)
    hal_rate = n_hal / n_total if n_total > 0 else 0.0

    normal_pairs = [p for p in pairs if p.condition == "normal"]
    degraded_pairs = [p for p in pairs if p.condition == "degraded"]

    norm_hal = sum(1 for p in normal_pairs if p.label == 1)
    deg_hal = sum(1 for p in degraded_pairs if p.label == 1)

    norm_rate = norm_hal / len(normal_pairs) if normal_pairs else 0.0
    deg_rate = deg_hal / len(degraded_pairs) if degraded_pairs else 0.0

    logger.info(
        "Merged %d pairs into %s and %s:\n"
        "  - Total: %d pairs (Supported=%d [%.1f%%], Hallucinated=%d [%.1f%%])\n"
        "  - Normal condition: %d pairs (Hallucinated=%d [%.1f%%])\n"
        "  - Degraded condition: %d pairs (Hallucinated=%d [%.1f%%])",
        n_total,
        target_jsonl,
        target_pairs,
        n_total,
        n_sup,
        (n_sup / n_total) * 100.0 if n_total else 0.0,
        n_hal,
        hal_rate * 100.0,
        len(normal_pairs),
        norm_hal,
        norm_rate * 100.0,
        len(degraded_pairs),
        deg_hal,
        deg_rate * 100.0,
    )

    if hal_rate < 0.25:
        logger.warning(
            "Gate G2 Alert: Hallucination rate is %.1f%% (< 25%%). "
            "Researchers may authorize up to 20 extra degraded questions per Gate G2 (Phase.md).",
            hal_rate * 100.0,
        )
    else:
        logger.info(
            "Gate G2 Target Satisfied: Hallucination rate is %.1f%% (>= 25%%).",
            hal_rate * 100.0,
        )

    return pairs


def main() -> None:
    """CLI entry point for Phase 6 annotation workflows."""
    setup_logging("annotation")
    parser = argparse.ArgumentParser(
        description="Phase 6 human annotation tooling for Experiment 2"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # export
    p_export = subparsers.add_parser("export", help="Export blind annotation CSVs and guide")
    p_export.add_argument("--config", default="configs/config.yaml", help="Path to config")
    p_export.add_argument("--out-dir", default=None, help="Output directory for annotation files")

    # kappa
    p_kappa = subparsers.add_parser("kappa", help="Compute Cohen's kappa and export disagreements")
    p_kappa.add_argument(
        "--annotator-1",
        default="data/exp2_rag/annotation/annotator_1.csv",
        help="Path to annotator 1 CSV",
    )
    p_kappa.add_argument(
        "--annotator-2",
        default="data/exp2_rag/annotation/annotator_2.csv",
        help="Path to annotator 2 CSV",
    )
    p_kappa.add_argument(
        "--out-disagreements",
        default=None,
        help="Output path for disagreements.csv",
    )

    # merge
    p_merge = subparsers.add_parser("merge", help="Merge resolved annotations into labeled.jsonl")
    p_merge.add_argument("--config", default="configs/config.yaml", help="Path to config")
    p_merge.add_argument("--labeled", default=None, help="Path to labeled.csv")
    p_merge.add_argument("--out-jsonl", default=None, help="Output path for labeled.jsonl")

    args = parser.parse_args()

    if args.command == "export":
        cfg = load_config(args.config)
        out_dir = Path(args.out_dir) if args.out_dir else None
        export_sheets(cfg, out_dir=out_dir)

    elif args.command == "kappa":
        f1 = Path(args.annotator_1)
        f2 = Path(args.annotator_2)
        out_d = Path(args.out_disagreements) if args.out_disagreements else None
        res = compute_kappa(f1, f2, out_disagreements=out_d)
        print("\n--- Cohen's Kappa Summary ---")
        print(f"Total pairs: {res['total_pairs']}")
        print(f"Annotated pairs: {res['annotated_pairs']}")
        print(f"Agreed count: {res['agreed_count']}")
        print(f"Disagreed count: {res['disagreed_count']}")
        print(f"Raw Agreement: {res['raw_agreement'] * 100.0:.2f}%")
        print(f"Cohen's Kappa: {res['cohen_kappa']}")

    elif args.command == "merge":
        cfg = load_config(args.config)
        labeled_path = Path(args.labeled) if args.labeled else None
        out_path = Path(args.out_jsonl) if args.out_jsonl else None
        merge_annotations(cfg, labeled_csv=labeled_path, out_jsonl=out_path)


if __name__ == "__main__":
    main()
