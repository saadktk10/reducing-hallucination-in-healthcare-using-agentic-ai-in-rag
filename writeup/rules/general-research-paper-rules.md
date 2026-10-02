# General Research Paper Rules

*Guidelines and hard constraints for writing the empirical paper (Phase 10, Task 5; Rules.md §1 & §9).*

---

## 1. Number Integrity & Ground Truth (Rules R1.10, R9.5)

1. **Exact Numbers Only:** Never round loosely or alter numbers in prose or tables. All figures, metrics, confidence intervals, and $p$-values must trace directly to a verified JSON or CSV file in `results/`.
2. **Confidence Intervals:** Always report bootstrap 95% confidence intervals alongside point estimates where applicable (e.g., $F_1 = 0.6667 \text{ [0.6667, 0.6667]}$ for Exp 1; $F_1 = 0.0861 \text{ [0.0392, 0.1395]}$ for Exp 2).
3. **No Retuning on Evaluation Sets (Rule R1.3):** Never retroactively alter decision thresholds to make test or RAG performance appear higher. Report frozen dev thresholds as primary, and any oracle post-hoc analysis as strictly diagnostic.
4. **Transparent Sample Accounting (Rule R1.9):** Every pilot finding, failed parse, excluded case, and discordance must be explicitly accounted for in the text. No data points are silently omitted.

---

## 2. Structure and Terminology

1. **Standard IMRaD Sections:** The manuscript follows standard biomedical informatics structure:
   - **00-Abstract:** Structured background, objective, methods, results, and conclusion.
   - **01-Introduction:** Motivation (agentic RAG in healthcare, hallucination hazards, cost/latency limits of API judges, local verification hypothesis).
   - **02-Related Work:** NLI for factuality, LLM-as-a-judge, medical hallucination benchmarks, edge NLP in healthcare.
   - **03-Methodology:** Pipeline architecture, benchmark construction, PubMedQA FAISS retrieval, human annotation protocol, verifier definitions, evaluation statistics.
   - **04-Results:** Empirically verified findings across Exp 1, Exp 2, latency profiling, and cross-experiment transfer.
   - **05-Discussion:** Clinical implications, safety considerations, class imbalance effect, threshold transfer cost, limitations, and future work.
   - **06-Conclusion:** Core takeaway and recommendations for healthcare RAG deployment.
2. **Explicit Label Definitions:** Consistently adhere to the canonical hallucination definition: an answer containing unsupported assertions, contradictions, or ungrounded clinical claims relative to the retrieved context.
3. **Clinical Safety Focus:** Prioritize False Negative Rate ($\text{FNR}$) as the chief safety metric, as a false negative represents a hallucination silently delivered to a healthcare stakeholder.

---

## 3. Visuals and Tables

1. **Colorblind-Safe Palettes:** All plots must use Okabe-Ito colorblind-accessible palettes with consistent color mapping:
   - Filter B (DeBERTa): Orange `#E69F00`
   - Baseline (ROUGE-L): Sky Blue `#56B4E9`
   - Filter A (Gemini): Bluish Green `#009E73`
2. **Dual Formats:** All figures must be exported in both high-resolution bitmap (300 dpi PNG) and vector graphics (PDF).
3. **Reproducible Tables:** Tables must correspond to machine-readable CSVs in the respective `results/` directories.

---

## 4. Ethical Declarations (Rules R7.1, R7.2)

1. **Research Prototype Notice:** All drafts and releases must prominently state:
   > *Research prototype — not for clinical use. This study is an academic investigation of hallucination verification architectures and is not validated for patient care or diagnostic decision-making.*
2. **Data Privacy:** Only publicly available, de-identified research literature (PubMedQA, MedHallu) is used. No protected health information (PHI) is processed.
