"""
Script to generate the complete end-to-end Architecture Diagram for:
'Reducing Hallucination in HealthCare using Agentic AI in RAG'

Styling adheres to the exact AdaptiShield v3 architecture standard:
  - Dark mode background (#0D0D0D)
  - Rich jewel-toned container headers (Layer 0, Layer 1, Layer 2, Layer 3, Layer 4, Layer 5, Governance/Pilot)
  - Jet-black inner component cards (#111111) with crisp borders (#AAAAAA, #20BEFF, #9333EA, #EA580C)
  - Explicit tool and model badges:
      * ⚡ Groq Cloud API: qwen/qwen3.8-27b
      * ☁ Google Gemini API: gemini-3.6-flash
      * 💻 Local PyTorch CPU: cross-encoder/nli-deberta-v3-small
      * 💻 Local Embedding: BAAI/bge-small-en-v1.5
      * 💻 Local Vector Store: faiss-cpu IndexFlatIP
      * 💻 Local Lexical Baseline: rouge-score
      * 💻 Biomedical Sentence Segmenter: pysbd
  - Solid boxes for built & active components
  - Dotted boxes (dashed=1;) for planned / later components
  - Clean orthogonal edge routing with colored feedback/dataflow paths

Outputs:
  - docs/assets/architecture.drawio
  - architecture.drawio (in repository root)
"""

import html
import os
import xml.etree.ElementTree as ET


def create_diagram_xml() -> str:
    CANVAS_WIDTH = 2100
    CANVAS_HEIGHT = 1200

    xml_parts = []
    xml_parts.append('<?xml version="1.0" encoding="UTF-8"?>')
    xml_parts.append('<mxfile host="app.diagrams.net" agent="Healthcare-RAG-Architecture">')
    xml_parts.append('  <diagram name="Healthcare RAG &amp; Verifier Architecture v3" id="healthcare-rag-v3">')
    xml_parts.append(
        f'    <mxGraphModel dx="1200" dy="700" grid="0" gridSize="10" guides="1" tooltips="1" '
        f'connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="{CANVAS_WIDTH}" '
        f'pageHeight="{CANVAS_HEIGHT}" background="#0D0D0D" math="0" shadow="0">'
    )
    xml_parts.append('      <root>')
    xml_parts.append('        <mxCell id="0" />')
    xml_parts.append('        <mxCell id="1" parent="0" />')

    def add_cell(cell_id, parent, style, value, x, y, width, height, vertex=1):
        escaped_val = html.escape(value, quote=True)
        xml_parts.append(
            f'        <mxCell id="{cell_id}" parent="{parent}" style="{style}" value="{escaped_val}" vertex="{vertex}">'
        )
        xml_parts.append(f'          <mxGeometry height="{height}" width="{width}" x="{x}" y="{y}" as="geometry" />')
        xml_parts.append('        </mxCell>')

    def add_edge(edge_id, parent, source, target, value="", style="", points=None):
        escaped_lbl = html.escape(value, quote=True)
        default_style = (
            "edgeStyle=orthogonalEdgeStyle;rounded=1;html=1;strokeColor=#FFFFFF;"
            "fontColor=light-dark(#DDDDDD,#FFFFFF);fontSize=10;"
        )
        final_style = default_style + style
        xml_parts.append(
            f'        <mxCell id="{edge_id}" edge="1" parent="{parent}" source="{source}" target="{target}" '
            f'style="{final_style}" value="{escaped_lbl}">'
        )
        if points:
            xml_parts.append('          <mxGeometry relative="1" as="geometry">')
            xml_parts.append('            <Array as="points">')
            for px, py in points:
                xml_parts.append(f'              <mxPoint x="{px}" y="{py}" />')
            xml_parts.append('            </Array>')
            xml_parts.append('          </mxGeometry>')
        else:
            xml_parts.append('          <mxGeometry relative="1" as="geometry" />')
        xml_parts.append('        </mxCell>')

    # 1. Top Title & Legend
    title_text = "Healthcare RAG & Verifier Architecture — Mitigating Hallucination via Agentic Verification"
    title_style = "text;html=1;align=left;verticalAlign=middle;fontSize=20;fontColor=#FFFFFF;fontStyle=1"
    add_cell("title", "1", title_style, title_text, 140, 24, 1300, 30)

    legend_text = (
        "Solid boxes = built & validated  ·  Dotted boxes = planned / next phase  ·  "
        "⚡ Groq API (qwen/qwen3.8-27b)  ·  ☁ Gemini API (gemini-3.6-flash)  ·  "
        "💻 Local CPU (DeBERTa-v3, BGE, FAISS, ROUGE)"
    )
    legend_style = "text;html=1;align=left;verticalAlign=middle;fontSize=11;fontColor=#BBBBBB"
    add_cell("legend", "1", legend_style, legend_text, 140, 56, 1500, 20)

    # Actor: Clinician / User
    actor_style = (
        "shape=umlActor;verticalLabelPosition=bottom;html=1;verticalAlign=top;outlineConnect=0;"
        "fillColor=#FFFFFF;strokeColor=#FFFFFF;fontColor=#FFFFFF;fontSize=11"
    )
    add_cell("actor_user", "1", actor_style, "Clinician / Query", 50, 200, 30, 60)

    # =========================================================================
    # LAYER 0: Clinical Knowledge & Corpus Sources
    # =========================================================================
    l0_style = (
        "rounded=1;whiteSpace=wrap;html=1;verticalAlign=top;fillColor=#8B4A1F;strokeColor=#D98A4A;"
        "fontColor=#FFFFFF;fontSize=12;fontStyle=1;container=1;collapsible=0;arcSize=8"
    )
    add_cell("layer0", "1", l0_style, "Layer 0 — Clinical Knowledge & Corpus Sources", 140, 100, 220, 360)

    card_style = "rounded=1;whiteSpace=wrap;html=1;fillColor=#111111;strokeColor=#AAAAAA;fontColor=#FFFFFF;fontSize=11;arcSize=12"
    card_cyan = "rounded=1;whiteSpace=wrap;html=1;fillColor=#111111;strokeColor=#20BEFF;strokeWidth=2;fontColor=#FFFFFF;fontSize=11;arcSize=12"
    card_dotted = "rounded=1;whiteSpace=wrap;html=1;fillColor=#111111;strokeColor=#888888;fontColor=#CCCCCC;fontSize=11;dashed=1;arcSize=12"

    l0_medhallu_val = (
        "<b>MedHallu Benchmark</b><br>"
        '<font style="font-size:9px">HF: UTAustin-AIHealth/MedHallu<br>'
        "config: pqa_labeled (rev 515060...)<br>"
        "500 clinical QA pairs with synthetic sentence-level hallucinations</font>"
    )
    add_cell("l0_medhallu", "layer0", card_style, l0_medhallu_val, 15, 45, 190, 85)

    l0_pubmedqa_val = (
        "<b>PubMedQA Corpus</b><br>"
        '<font style="font-size:9px">HF: qiaojin/PubMedQA<br>'
        "config: pqa_labeled (rev 9001f2...)<br>"
        "~1,000 biomedical research abstracts for Experiment 2 RAG retrieval</font>"
    )
    add_cell("l0_pubmedqa", "layer0", card_style, l0_pubmedqa_val, 15, 145, 190, 85)

    l0_prov_val = (
        "<b>Provenance & Integrity</b><br>"
        '<font style="font-size:9px">SHA-256 manifests per run<br>'
        "Pinned commits (Rule R4.4)<br>"
        "Fixed seed: 42 (reproducible)<br>"
        "Not for clinical use notice</font>"
    )
    add_cell("l0_provenance", "layer0", card_style, l0_prov_val, 15, 245, 190, 95)

    # =========================================================================
    # LAYER 1: Data Preparation & Stratification
    # =========================================================================
    l1_style = (
        "rounded=1;whiteSpace=wrap;html=1;verticalAlign=top;fillColor=#3F3F9E;strokeColor=#8A86E0;"
        "fontColor=#FFFFFF;fontSize=12;fontStyle=1;container=1;collapsible=0;arcSize=8"
    )
    add_cell("layer1", "1", l1_style, "Layer 1 — Data Preparation & Stratification", 385, 100, 220, 360)

    l1_builder_val = (
        "<b>Exp 1 Pair Generator</b><br>"
        '<font style="font-size:9px">src/build_exp1_pairs.py<br>'
        "250 questions sampled & stratified by clinical difficulty<br>"
        "→ 500 balanced (50/50) pairs</font>"
    )
    add_cell("l1_builder", "layer1", card_style, l1_builder_val, 15, 45, 190, 85)

    l1_splitter_val = (
        "<b>Question-Level Splitter</b><br>"
        '<font style="font-size:9px">Split by question (0 leakage)<br>'
        "Dev: 50 Qs (100 pairs) for tuning<br>"
        "Test: 200 Qs (400 pairs) for eval<br>"
        "data/exp1/dev.jsonl & test.jsonl</font>"
    )
    add_cell("l1_splitter", "layer1", card_style, l1_splitter_val, 15, 145, 190, 95)

    l1_leakage_val = (
        "<b>Leakage Guard</b><br>"
        '<font style="font-size:9px">test_leakage.py CI gate<br>'
        "Exp 1 test questions excluded from Exp 2 candidate pool<br>"
        "Zero overlap guaranteed</font>"
    )
    add_cell("l1_leakage", "layer1", card_style, l1_leakage_val, 15, 255, 190, 85)

    # Storage cylinder across bottom of L0 & L1
    store_style = (
        "shape=cylinder3;boundedLbl=1;backgroundOutline=1;size=12;whiteSpace=wrap;html=1;"
        "fillColor=#111111;strokeColor=#4FA3C7;fontColor=#FFFFFF;fontSize=11"
    )
    store_val = (
        "<b>data/cache/ & data/pilot/</b><br>"
        '<font style="font-size:9px">JsonlCache append-only API response store<br>'
        "FROZEN.json prompt hashes (judge_v1, generator_v1)</font>"
    )
    add_cell("store_cache", "1", store_style, store_val, 140, 475, 465, 75)

    # =========================================================================
    # PROTOCOL GOVERNANCE & PILOT STUDY (Gate G1)
    # =========================================================================
    pilot_style = (
        "rounded=1;whiteSpace=wrap;html=1;verticalAlign=top;fillColor=#5A1A1A;strokeColor=#C05A5A;"
        "fontColor=#FFFFFF;fontSize=12;fontStyle=1;container=1;collapsible=0;arcSize=8"
    )
    add_cell("layer_pilot", "1", pilot_style, "Protocol Governance & Pilot Study (Gate G1)", 140, 565, 465, 525)

    p_spot_val = (
        "<b>Human Spot-Check (n=50)</b><br>"
        '<font style="font-size:9px">spotcheck_50.csv evaluated<br>'
        "<b>46.0%</b> unsupported GT rate!<br>"
        "Risk 1 (unsupported correct) confirmed in MedHallu</font>"
    )
    add_cell("p_spotcheck", "layer_pilot", card_style, p_spot_val, 20, 42, 205, 85)

    p_rouge_val = (
        "<b>ROUGE-L Dev AUROC</b><br>"
        '<font style="font-size:9px">100 provisional dev pairs<br>'
        "AUROC = <b>0.4894</b> (&lt; 0.95)<br>"
        "Risk 2 (lexical shortcut) rejected; MedHallu not trivial</font>"
    )
    add_cell("p_rouge_auroc", "layer_pilot", card_style, p_rouge_val, 240, 42, 205, 85)

    p_gate_val = (
        "<b>Gate G1 Decision: Fallback to Plan 2</b><br>"
        '<font style="font-size:9px">Unsupported GT (&gt;10%) triggers Plan 2 protocol:<br>'
        "• <b>Experiment 2 (Healthcare RAG):</b> Primary headline study (200 pairs)<br>"
        "• <b>Experiment 1 (MedHallu):</b> Secondary benchmark (with caveats)</font>"
    )
    p_gate_style = "rounded=1;whiteSpace=wrap;html=1;fillColor=#3A1010;strokeColor=#C05A5A;fontColor=#EEEEEE;fontSize=10;arcSize=12"
    add_cell("p_gate_g1", "layer_pilot", p_gate_style, p_gate_val, 20, 140, 425, 85)

    p_rules_val = (
        "<b>Integrity & Governance Safeguards</b><br>"
        '<font style="font-size:9px">'
        "• <b>Rule R1.5:</b> AI assistant NEVER generates or guesses labels; human judgments only<br>"
        "• <b>Rule R1.6:</b> Progress past Gates G1-G6 requires explicit human sign-off in handover.md<br>"
        "• <b>Rule R4.1:</b> Master seed 42 for all stratified sampling and shuffling<br>"
        "• <b>Rule R9.2:</b> Mandatory session close: pytest + ruff + site_export + docs + git</font>"
    )
    add_cell("p_rules", "layer_pilot", card_cyan, p_rules_val, 20, 240, 425, 115)

    p_report_val = (
        "<b>Pilot Report & Artifacts</b><br>"
        '<font style="font-size:9px">'
        "• data/pilot/pilot_report.json & results/pilot/pilot_report.md<br>"
        "• results/pilot/metrics.json: pilot.unsupported_rate=0.46, pilot.rouge_auroc=0.4894<br>"
        "• Populates live website tiles automatically via results/site/numbers_of_record.json</font>"
    )
    add_cell("p_report", "layer_pilot", card_style, p_report_val, 20, 370, 425, 135)

    # =========================================================================
    # LAYER 2: Healthcare RAG Generation Plane (Exp 2)
    # =========================================================================
    l2_style = (
        "rounded=1;whiteSpace=wrap;html=1;verticalAlign=top;fillColor=#2E2EA8;strokeColor=#8A86E0;"
        "fontColor=#FFFFFF;fontSize=12;fontStyle=1;container=1;collapsible=0;arcSize=6"
    )
    add_cell("layer2", "1", l2_style, "Layer 2 — Healthcare RAG Generation Plane (Experiment 2)", 625, 100, 650, 595)

    l2_chunk_val = (
        "<b>PubMed Chunker</b><br>"
        '<font style="font-size:9px">src/build_index.py<br>'
        "~250 token chunks (30 overlap)<br>"
        "1,790 chunks tracking doc_ids</font>"
    )
    add_cell("l2_chunker", "layer2", card_style, l2_chunk_val, 20, 45, 190, 65)

    l2_faiss_val = (
        "<b>Embedding & Vector DB</b><br>"
        '<font style="font-size:9px">💻 <b>BAAI/bge-small-en-v1.5</b><br>'
        "💻 <b>faiss-cpu</b> IndexFlatIP (384-d)<br>"
        "Peak RAM: <b>451.8 MB</b> (under 8GB)</font>"
    )
    add_cell("l2_faiss", "layer2", card_cyan, l2_faiss_val, 225, 45, 200, 65)

    l2_ret_val = (
        "<b>Dual Retriever</b><br>"
        '<font style="font-size:9px">• Normal (n=100): top-3 chunks<br>'
        "• Degraded (n=100): drop source doc chunks, keep 3 distractors</font>"
    )
    add_cell("l2_retriever", "layer2", card_style, l2_ret_val, 440, 45, 190, 65)

    card_groq = "rounded=1;whiteSpace=wrap;html=1;fillColor=#111111;strokeColor=#EA580C;strokeWidth=2;fontColor=#FFFFFF;fontSize=11;arcSize=12"
    l2_gen_val = (
        "<b>RAG Generator: Groq Cloud API</b>  ·  ⚡ <b>Model: qwen/qwen3.8-27b</b><br>"
        '<font style="font-size:9px">Frozen prompt: generator_v1.txt · temp: 0.0 · max_tokens: 256 · '
        "Generates 200 clinical answers (100 normal + 100 degraded) into data/exp2_rag/generated.jsonl</font>"
    )
    add_cell("l2_generator", "layer2", card_groq, l2_gen_val, 20, 125, 610, 65)

    # Sublayer inside Layer 2: Annotation & Adjudication Sub-layer
    sub_style = (
        "rounded=1;whiteSpace=wrap;html=1;verticalAlign=top;fillColor=#6E6EDC;strokeColor=#C9C6F5;"
        "fontColor=#FFFFFF;fontSize=12;fontStyle=1;container=1;collapsible=0;arcSize=6"
    )
    add_cell(
        "sublayer_ann",
        "layer2",
        sub_style,
        "Annotation, Agreement & Adjudication Sub-layer (Gate G2)",
        20,
        205,
        610,
        370,
    )

    sl_exp_val = (
        "<b>Phase 6 CSV Exporter</b><br>"
        '<font style="font-size:9px">src/annotation.py export<br>'
        "RFC 4180 CSV export · seed 42 shuffle<br>"
        "annotator_1.csv & annotator_2.csv<br>"
        "Conditions (normal/degraded) blinded</font>"
    )
    add_cell("sl_export", "sublayer_ann", card_style, sl_exp_val, 20, 40, 270, 75)

    sl_gate2_val = (
        "<b>[PLANNED] Gate G2: Human Annotation</b><br>"
        '<font style="font-size:9px"><i>(Awaiting Independent Human Labels)</i><br>'
        "Annotator 1: Muhammad Saad (200 pairs)<br>"
        "Annotator 2: Rabia Qaiser (200 pairs)<br>"
        "Strict compliance with Rule R1.5</font>"
    )
    add_cell("sl_gate2_label", "sublayer_ann", card_dotted, sl_gate2_val, 310, 40, 280, 75)

    sl_kap_val = (
        "<b>Agreement & Cohen's Kappa</b><br>"
        '<font style="font-size:9px"><i>[PLANNED POST-LABELING]</i><br>'
        'python -m src.annotation kappa<br>'
        "Computes Cohen's κ on 200 pairs<br>"
        "Exports disagreements.csv</font>"
    )
    add_cell("sl_kappa", "sublayer_ann", card_dotted, sl_kap_val, 20, 130, 270, 75)

    sl_adj_val = (
        "<b>Consensus Adjudication</b><br>"
        '<font style="font-size:9px"><i>[PLANNED POST-LABELING]</i><br>'
        "Researchers reconcile disagreements<br>"
        "Populates data/exp2_rag/labeled.csv<br>"
        "Rule R1.6 sign-off required</font>"
    )
    add_cell("sl_adjudication", "sublayer_ann", card_dotted, sl_adj_val, 310, 130, 280, 75)

    sl_merge_val = (
        "<b>Ground Truth Dataset Merge (src/annotation.py merge)</b><br>"
        '<font style="font-size:9px"><i>[PLANNED]</i> Validates labeled dataset and generates <b>data/exp2_rag/pairs.jsonl</b><br>'
        "Verifies Gate G2 class balance check (≥ 25% Hallucinated in RAG corpus; triggers extra degraded if &lt;25%)</font>"
    )
    add_cell("sl_merge", "sublayer_ann", card_dotted, sl_merge_val, 20, 220, 570, 65)

    sl_note_style = (
        "rounded=1;whiteSpace=wrap;html=1;fillColor=#4A4AC4;strokeColor=#C9C6F5;fontColor=#FFFFFF;fontSize=10;arcSize=12"
    )
    sl_note_val = (
        '<font style="font-size:9px; color: #FFFFFF"><b>Soundness Principle:</b> '
        "Generator condition is blinded to human annotators. RAG hallucinations arise naturally from retrieval "
        "distractors rather than synthetic perturbation, providing an ecologically valid test of clinical verifier generalizability.</font>"
    )
    add_cell("sl_note", "sublayer_ann", sl_note_style, sl_note_val, 20, 295, 570, 60)

    # =========================================================================
    # LAYER 3: Multi-Verifier Verification Plane (Shared Pipeline)
    # =========================================================================
    l3_style = (
        "rounded=1;whiteSpace=wrap;html=1;verticalAlign=top;fillColor=#153D1E;strokeColor=#4E9A5F;"
        "fontColor=#FFFFFF;fontSize=12;fontStyle=1;container=1;collapsible=0;arcSize=6"
    )
    add_cell("layer3", "1", l3_style, "Layer 3 — Multi-Verifier Verification Plane (Shared Pipeline)", 1295, 100, 680, 595)

    l3_coord_val = (
        "<b>Verifier Coordinator</b><br>"
        '<font style="font-size:9px">src/run_verifiers.py & filters/base.py<br>'
        "Unified JSONL contract across Exp 1 & Exp 2<br>"
        "Latency timing & token accounting</font>"
    )
    add_cell("l3_coord", "layer3", card_style, l3_coord_val, 20, 42, 305, 65)

    l3_tune_val = (
        "<b>Dev Threshold Optimizer</b><br>"
        '<font style="font-size:9px">src/tune_thresholds.py on Exp 1 Dev (100 pairs)<br>'
        "Frozen in results/thresholds.json:<br>"
        "Filter B thresh: <b>0.0039</b> · ROUGE thresh: <b>0.1741</b></font>"
    )
    add_cell("l3_tune", "layer3", card_cyan, l3_tune_val, 345, 42, 315, 65)

    l3_rouge_val = (
        "<b>Baseline: ROUGE-L Precision</b>  ·  💻 <b>Tool: rouge-score (Local CPU)</b><br>"
        '<font style="font-size:9px">Lexical LCS overlap between context & answer · Thresh: 0.1741 · Dev F1: 0.6667 · Test F1: 0.6667 · '
        "<b>Median latency: 2.5 ms</b> (CPU)</font>"
    )
    add_cell("l3_rouge", "layer3", card_style, l3_rouge_val, 20, 120, 640, 65)

    card_nli = "rounded=1;whiteSpace=wrap;html=1;fillColor=#111111;strokeColor=#9333EA;strokeWidth=2;fontColor=#FFFFFF;fontSize=11;arcSize=12"
    l3_nli_val = (
        "<b>Filter B: Local NLI Cross-Encoder</b><br>"
        "💻 <b>Tool: PyTorch CPU</b> · <b>cross-encoder/nli-deberta-v3-small</b><br>"
        '<font style="font-size:9px">Sentence splitter: <b>pysbd</b> (biomedical rule-based)<br>'
        "Matrix: sentences × context chunks (max 512 tokens)<br>"
        "Score = min_s(max_c(P(entailment))) · Thresh: 0.0039<br>"
        "6 CPU threads, batch=16 · <b>Median latency: 332.1 ms</b></font>"
    )
    add_cell("l3_filter_b", "layer3", card_nli, l3_nli_val, 20, 198, 410, 95)

    l3_nli_opt_val = (
        "<b>Filter B Base Model</b><br>"
        '<font style="font-size:9px"><i>[DOTTED: OPTIONAL ABLATION]</i><br>'
        "Model: nli-deberta-v3-base<br>"
        "Evaluates parameter scale vs latency on CPU</font>"
    )
    add_cell("l3_filter_b_opt", "layer3", card_dotted, l3_nli_opt_val, 445, 198, 215, 95)

    card_gemini = "rounded=1;whiteSpace=wrap;html=1;fillColor=#111111;strokeColor=#2563EB;strokeWidth=2;fontColor=#FFFFFF;fontSize=11;arcSize=12"
    l3_gemini_val = (
        "<b>Filter A: API LLM Judge</b><br>"
        "☁ <b>Tool: Google Gemini API</b> · <b>gemini-3.6-flash</b><br>"
        '<font style="font-size:9px">Prompt: judge_v1 (frozen in FROZEN.json) · temp: 0.0 · max_tokens: 1000<br>'
        "Extracts structured JSON: verdict (0/1), confidence (1-5), rationale<br>"
        "Robustness: JsonlCache request caching, RPM limit: 10, tenacity retry</font>"
    )
    add_cell("l3_filter_a", "layer3", card_gemini, l3_gemini_val, 20, 305, 410, 95)

    l3_gemini_runs_val = (
        "<b>Filter A Full Runs</b><br>"
        '<font style="font-size:9px"><i>[DOTTED: DEFERRED]</i><br>'
        "Deferred due to 20 RPD free tier<br>"
        "Awaits batch key / tier upgrade to evaluate 400 Exp 1 + 200 Exp 2 pairs</font>"
    )
    add_cell("l3_filter_a_runs", "layer3", card_dotted, l3_gemini_runs_val, 445, 305, 215, 95)

    l3_e1_val = (
        "<b>Exp 1 Test Evaluation Execution (Phase 5 Completed)</b><br>"
        '<font style="font-size:9px">Evaluated 400 test pairs with Filter B & Baseline ROUGE-L · Output: results/exp1/20260919-2151-bd5e507/metrics.json<br>'
        "Both achieve test F1 = 0.6667 [0.6667, 0.6667], FNR = 0.0000 · Shadow cost: $0.0575 / 1k queries</font>"
    )
    card_green = "rounded=1;whiteSpace=wrap;html=1;fillColor=#12301E;strokeColor=#4FA96B;fontColor=#FFFFFF;fontSize=11;arcSize=12"
    add_cell("l3_e1_exec", "layer3", card_green, l3_e1_val, 20, 412, 640, 75)

    l3_e2_val = (
        "<b>[PLANNED] Phase 7: RAG Verification Run</b><br>"
        '<font style="font-size:9px"><i>[DOTTED: PLANNED POST-GATE G2]</i><br>'
        "Command: python -m src.run_verifiers --config configs/config.yaml --split rag<br>"
        "Evaluates Filter B, ROUGE-L, and Filter A on the 200 human-adjudicated healthcare RAG pairs</font>"
    )
    add_cell("l3_e2_exec", "layer3", card_dotted, l3_e2_val, 20, 500, 640, 80)

    # =========================================================================
    # LAYER 4: Evaluation, Statistics & Efficiency Profiling
    # =========================================================================
    l4_style = (
        "rounded=1;whiteSpace=wrap;html=1;verticalAlign=top;fillColor=#1E3A4C;strokeColor=#5A9AB8;"
        "fontColor=#FFFFFF;fontSize=12;fontStyle=1;container=1;collapsible=0;arcSize=8"
    )
    add_cell(
        "layer4",
        "1",
        l4_style,
        "Layer 4 — Evaluation, Statistics & Efficiency Profiling",
        625,
        710,
        650,
        380,
    )

    l4_eval_val = (
        "<b>Evaluation Engine</b><br>"
        '<font style="font-size:9px">src/evaluate.py<br>'
        "P, R, F1, FPR, AUROC<br>"
        "<b>Safety Metric: FNR</b> (uncaught)</font>"
    )
    add_cell("l4_eval", "layer4", card_style, l4_eval_val, 20, 42, 195, 70)

    l4_stats_val = (
        "<b>Bootstrap & McNemar</b><br>"
        '<font style="font-size:9px">src/evaluation/stats.py<br>'
        "1,000 question block resamples<br>"
        "McNemar exact test (p=1.000)</font>"
    )
    add_cell("l4_stats", "layer4", card_style, l4_stats_val, 225, 42, 200, 70)

    l4_break_val = (
        "<b>Subgroup Breakdowns</b><br>"
        '<font style="font-size:9px">Difficulty (Easy/Med/Hard)<br>'
        "Category (Entity/Fact/etc.)<br>"
        "difficulty_breakdown.csv</font>"
    )
    add_cell("l4_breakdowns", "layer4", card_style, l4_break_val, 435, 42, 195, 70)

    l4_timing_val = (
        "<b>Resource & Efficiency Profiler</b><br>"
        '<font style="font-size:9px">src/timing.py (psutil & monotonic clock)<br>'
        "Wall-clock p50/p95 latency (Filter B: 332ms, ROUGE: 2.5ms)<br>"
        "RAM tracking & shadow cost ($0.0575 / 1k queries)</font>"
    )
    add_cell("l4_timing", "layer4", card_cyan, l4_timing_val, 20, 125, 300, 75)

    l4_cross_val = (
        "<b>Cross-Experiment Analysis</b><br>"
        '<font style="font-size:9px">src/cross_experiment.py<br>'
        "Verifier ranking agreement (Kendall's τ, Spearman's ρ)<br>"
        "Qualitative disagreement mining: 3 pairs exported</font>"
    )
    add_cell("l4_cross", "layer4", card_style, l4_cross_val, 330, 125, 300, 75)

    l4_e2_eval_val = (
        "<b>[PLANNED] Phase 8 Exp 2 RAG Evaluation</b><br>"
        '<font style="font-size:9px"><i>[DOTTED: PLANNED]</i><br>'
        "Evaluate verifiers on 200 RAG pairs post-Gate G2</font>"
    )
    add_cell("l4_e2_eval", "layer4", card_dotted, l4_e2_eval_val, 20, 210, 195, 75)

    l4_e2_trans_val = (
        "<b>[PLANNED] Phase 9 Domain Shift</b><br>"
        '<font style="font-size:9px"><i>[DOTTED: PLANNED]</i><br>'
        "Zero-shot transfer of Exp 1 thresholds directly to Exp 2</font>"
    )
    add_cell("l4_e2_transfer", "layer4", card_dotted, l4_e2_trans_val, 225, 210, 200, 75)

    l4_hyp_val = (
        "<b>Hypothesis Testing</b><br>"
        '<font style="font-size:9px"><i>[DOTTED: PLANNED]</i><br>'
        "H1: Filter B non-inferiority<br>"
        "H2: Shift degradation</font>"
    )
    add_cell("l4_hypotheses", "layer4", card_dotted, l4_hyp_val, 435, 210, 195, 75)

    l4_banner_style = (
        "rounded=1;whiteSpace=wrap;html=1;fillColor=#12293A;strokeColor=#5A9AB8;fontColor=#EEEEEE;fontSize=10;arcSize=12"
    )
    l4_banner_val = (
        '<font style="font-size:9px; color: #EEEEEE"><b>Statistical Integrity Rule R8.2:</b> '
        "Question-level block bootstrap (1,000 resamples) keeps positive and negative pair halves coupled to reflect genuine "
        "clustered variance. All confidence intervals and p-values are programmatically exported to results/site/numbers_of_record.json.</font>"
    )
    add_cell("l4_banner", "layer4", l4_banner_style, l4_banner_val, 20, 298, 610, 65)

    # =========================================================================
    # LAYER 5: Dissemination, Observability & Web Infrastructure
    # =========================================================================
    l5_style = (
        "rounded=1;whiteSpace=wrap;html=1;verticalAlign=top;fillColor=#5B4416;strokeColor=#C9A24A;"
        "fontColor=#FFFFFF;fontSize=12;fontStyle=1;container=1;collapsible=0;arcSize=8"
    )
    add_cell(
        "layer5",
        "1",
        l5_style,
        "Layer 5 — Dissemination, Observability & Web Infrastructure",
        1295,
        710,
        680,
        380,
    )

    l5_ssot_val = (
        "<b>Numbers of Record (Single Source of Truth)</b><br>"
        '<font style="font-size:9px">results/site/numbers_of_record.json<br>'
        "Programmatic single source of truth for all verified numbers, CIs, timings, and costs · Zero hand-typed numbers</font>"
    )
    add_cell("l5_ssot", "layer5", card_cyan, l5_ssot_val, 20, 42, 305, 75)

    l5_fig_val = (
        "<b>Publication Figures Engine (src/figures.py)</b><br>"
        '<font style="font-size:9px">🎨 6 publication figures in 300 DPI PNG & Vector PDF:<br>'
        "Fig 1: CM · Fig 2: PR Curve · Fig 3: Latency CDF<br>"
        "Fig 4: Pareto Front · Fig 5: Category · Fig 6: Cross-Exp</font>"
    )
    add_cell("l5_figures", "layer5", card_style, l5_fig_val, 335, 42, 325, 75)

    l5_exp_val = (
        "<b>Site Exporter (src/site_export.py)</b><br>"
        '<font style="font-size:9px">Replaces template macros with numbers of record<br>'
        "Updates Phase.md Snapshot Progress Board<br>"
        "Validates 14 interactive website metric tiles</font>"
    )
    add_cell("l5_export", "layer5", card_style, l5_exp_val, 20, 125, 305, 75)

    l5_web_val = (
        "<b>Project Documentation Site (MkDocs)</b><br>"
        '<font style="font-size:9px">Material for MkDocs · strict build (--strict)<br>'
        "4 custom Python hooks (numbers, progress, citations, claim)<br>"
        "Hosted live on GitHub Pages</font>"
    )
    add_cell("l5_web", "layer5", card_style, l5_web_val, 335, 125, 325, 75)

    l5_cicd_val = (
        "<b>CI/CD Automation (GitHub Actions)</b><br>"
        '<font style="font-size:9px">ci.yml: Automated pytest (127 tests) & ruff linting<br>'
        "pages.yml: Automatic MkDocs strict build & deployment<br>"
        "Enforces reproducible environment & zero drift</font>"
    )
    add_cell("l5_cicd", "layer5", card_style, l5_cicd_val, 20, 210, 305, 75)

    l5_paper_val = (
        "<b>[PLANNED] Academic Manuscript</b><br>"
        '<font style="font-size:9px"><i>[DOTTED: PLANNED]</i><br>'
        "Phase 10: paper/ draft<br>"
        "LaTeX tables from JSON</font>"
    )
    add_cell("l5_paper", "layer5", card_dotted, l5_paper_val, 335, 210, 155, 75)

    l5_rel_val = (
        "<b>[PLANNED] Open Science Release</b><br>"
        '<font style="font-size:9px"><i>[DOTTED: PLANNED]</i><br>'
        "Phase 11: Permanent DOI<br>"
        "One-click reproduction</font>"
    )
    add_cell("l5_release", "layer5", card_dotted, l5_rel_val, 500, 210, 160, 75)

    l5_note_style = (
        "rounded=1;whiteSpace=wrap;html=1;fillColor=#3D2E0E;strokeColor=#C9A24A;fontColor=#FFFFFF;fontSize=10;arcSize=12"
    )
    l5_note_val = (
        '<font style="font-size:9px; color: #E0C77A"><b>Reproducibility Guarantee:</b> '
        "Every number appearing on the website or manuscript is derived via programmatic export from execution "
        "manifests. Neither the agent nor researchers may manually edit metric values, guaranteeing absolute synchronization across papers, tables, and website.</font>"
    )
    add_cell("l5_note", "layer5", l5_note_style, l5_note_val, 20, 298, 640, 65)

    # =========================================================================
    # ORTHOGONAL EDGES & DATAFLOW
    # =========================================================================
    add_edge("e1", "1", "actor_user", "l0_medhallu", "clinical query", points=[(100, 230), (100, 185)])
    add_edge("e2", "1", "l0_medhallu", "l1_builder", "250 questions")
    add_edge("e3", "1", "l1_builder", "l1_splitter", "500 pairs")
    add_edge("e4", "1", "l1_splitter", "l1_leakage", "leakage check")
    add_edge("e5", "1", "l0_medhallu", "p_spotcheck", "sample 50 rows", points=[(250, 240), (250, 607)])
    add_edge("e6", "1", "p_spotcheck", "p_gate_g1", "46% unsupported")
    add_edge("e7", "1", "p_rouge_auroc", "p_gate_g1", "AUROC=0.4894")
    add_edge("e8", "1", "p_gate_g1", "l1_builder", "Plan 2: Secondary Benchmark", points=[(615, 747), (615, 207)])
    add_edge("e9", "1", "p_gate_g1", "l2_chunker", "Plan 2: Primary Headline RAG", points=[(620, 747), (620, 177)])
    add_edge("e10", "1", "l0_pubmedqa", "l2_chunker", "1,000 abstracts", points=[(365, 285), (635, 285), (635, 177)])
    add_edge("e11", "1", "l2_chunker", "l2_faiss", "1,790 chunks")
    add_edge("e12", "1", "l2_faiss", "l2_retriever", "IndexFlatIP vectors")
    add_edge("e13", "1", "l2_retriever", "l2_generator", "top-3 chunks (normal/degraded)", points=[(1160, 210), (1160, 230), (930, 230)])
    add_edge("e14", "1", "l2_generator", "sl_export", "200 generated answers", points=[(930, 290), (780, 290)])
    add_edge("e15", "1", "sl_export", "sl_gate2_label", "annotator_1.csv / annotator_2.csv", style="strokeColor=#20BEFF;dashed=1;")
    add_edge("e16", "1", "sl_gate2_label", "sl_kappa", "200 labeled pairs", style="strokeColor=#20BEFF;dashed=1;", points=[(1075, 380), (1075, 410), (780, 410)])
    add_edge("e17", "1", "sl_kappa", "sl_adjudication", "disagreements.csv", style="strokeColor=#20BEFF;dashed=1;")
    add_edge("e18", "1", "sl_adjudication", "sl_merge", "resolved labels", style="strokeColor=#20BEFF;dashed=1;", points=[(1075, 455), (1075, 525)])
    add_edge("e19", "1", "sl_merge", "l3_e2_exec", "pairs.jsonl (Ground Truth)", style="strokeColor=#20BEFF;strokeWidth=2;dashed=1;", points=[(1245, 555), (1305, 555), (1305, 635)])

    # Edges from Layer 1 & 2 into Layer 3
    add_edge("e20", "1", "l1_splitter", "l3_tune", "Dev 100 pairs", points=[(615, 290), (1290, 290), (1290, 172)])
    add_edge("e21", "1", "l1_splitter", "l3_coord", "Test 400 pairs", points=[(615, 300), (1285, 300), (1285, 172)])
    add_edge("e22", "1", "l3_tune", "l3_rouge", "threshold: 0.1741", points=[(1785, 207), (1785, 220), (1635, 220)])
    add_edge("e23", "1", "l3_tune", "l3_filter_b", "threshold: 0.0039", points=[(1785, 207), (1785, 345), (1520, 345)])
    add_edge("e24", "1", "l3_coord", "l3_rouge", "evaluate")
    add_edge("e25", "1", "l3_coord", "l3_filter_b", "evaluate")
    add_edge("e26", "1", "l3_coord", "l3_filter_a", "evaluate (smoke verified)", points=[(1467, 207), (1467, 450), (1520, 450)])
    add_edge("e27", "1", "l3_filter_b", "l3_filter_b_opt", "model scale ablation", style="strokeColor=#888888;dashed=1;")
    add_edge("e28", "1", "l3_filter_a", "l3_filter_a_runs", "deferred (free tier 20 RPD)", style="strokeColor=#888888;dashed=1;")
    add_edge("e29", "1", "l3_coord", "l3_e1_exec", "score 400 pairs", points=[(1400, 207), (1400, 545)])

    # Edges from Layer 3 into Layer 4
    add_edge("e30", "1", "l3_e1_exec", "l4_eval", "Exp 1 test results", points=[(1635, 612), (1635, 700), (742, 700), (742, 752)])
    add_edge("e31", "1", "l3_e1_exec", "l4_timing", "latencies & memory", points=[(1635, 612), (1635, 700), (775, 700), (775, 835)])
    add_edge("e32", "1", "l3_e2_exec", "l4_e2_eval", "Exp 2 RAG results", style="strokeColor=#20BEFF;dashed=1;", points=[(1635, 700), (1285, 700), (1285, 960), (840, 960)])
    add_edge("e33", "1", "l3_e2_exec", "l4_e2_transfer", "Exp 1 → Exp 2 transfer", style="strokeColor=#20BEFF;dashed=1;", points=[(1635, 700), (1285, 700), (1285, 960), (1050, 960)])

    # Internal Layer 4
    add_edge("e34", "1", "l4_eval", "l4_stats", "bootstrap & McNemar")
    add_edge("e35", "1", "l4_eval", "l4_breakdowns", "subgroups")
    add_edge("e36", "1", "l4_eval", "l4_cross", "ranking check")

    # Layer 4 into Layer 5
    add_edge("e37", "1", "l4_eval", "l5_ssot", "F1, FNR, P, R", points=[(722, 782), (722, 695), (1467, 695), (1467, 752)])
    add_edge("e38", "1", "l4_stats", "l5_ssot", "95% CIs & p-values", points=[(945, 782), (945, 695), (1467, 695), (1467, 752)])
    add_edge("e39", "1", "l4_timing", "l5_ssot", "timing & shadow costs", points=[(945, 872), (1285, 872), (1285, 789)])
    add_edge("e40", "1", "l5_ssot", "l5_figures", "exact metric values")
    add_edge("e41", "1", "l5_ssot", "l5_export", "numbers synchronization")
    add_edge("e42", "1", "l5_figures", "l5_web", "figures 1-6 (PNG/PDF)")
    add_edge("e43", "1", "l5_export", "l5_web", "rendered tables & board")
    add_edge("e44", "1", "l5_cicd", "l5_web", "automated deploy on push")
    add_edge("e45", "1", "l5_ssot", "l5_paper", "LaTeX tables export", style="strokeColor=#888888;dashed=1;", points=[(1467, 827), (1467, 957), (1680, 957)])
    add_edge("e46", "1", "l5_web", "l5_release", "reproducible package", style="strokeColor=#888888;dashed=1;", points=[(1802, 910), (1875, 910), (1875, 957)])

    # Cache feedback edges
    add_edge("e47", "1", "store_cache", "l2_generator", "offline cache", style="strokeColor=#4FA3C7;dashed=1;", points=[(605, 512), (620, 512), (620, 257), (645, 257)])
    add_edge("e48", "1", "store_cache", "l3_filter_a", "offline cache", style="strokeColor=#4FA3C7;dashed=1;", points=[(605, 512), (620, 512), (620, 60), (1520, 60), (1520, 405)])

    xml_parts.append('      </root>')
    xml_parts.append('    </mxGraphModel>')
    xml_parts.append('  </diagram>')
    xml_parts.append('</mxfile>')

    return '\n'.join(xml_parts)


def main():
    content = create_diagram_xml()

    try:
        ET.fromstring(content)
        print("XML Syntax Validation: SUCCESS (Valid XML)")
    except ET.ParseError as e:
        print(f"XML Syntax Error: {e}")
        return 1

    paths = [
        os.path.abspath("docs/assets/architecture.drawio"),
        os.path.abspath("architecture.drawio"),
    ]

    for p in paths:
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"Generated draw.io file: {p} ({len(content)} bytes)")

    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
