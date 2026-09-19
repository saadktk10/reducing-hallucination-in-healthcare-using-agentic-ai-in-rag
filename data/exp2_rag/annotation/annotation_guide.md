# Experiment 2: Human Annotation Guide

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
