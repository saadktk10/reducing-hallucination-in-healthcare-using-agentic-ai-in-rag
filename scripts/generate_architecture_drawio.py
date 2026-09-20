"""
Script to generate the complete end-to-end Architecture Diagram for the study:
'Reducing Hallucination in HealthCare using Agentic AI in RAG'

Outputs:
  - docs/assets/architecture.drawio
  - architecture.drawio (in repository root)

Generates clean, valid draw.io XML (diagrams.net compatible) with:
  - 5 horizontal layers (Left-to-Right dataflow)
  - Color-coded modern tech palette
  - Clear model/tool badges (Groq, Gemini, DeBERTa, BGE, FAISS, ROUGE)
  - Solid boxes for built components
  - Dotted boxes (dashed stroke) for planned / in-progress components
  - Orthogonal edge routing connecting the complete pipeline
"""

import html
import os
import xml.etree.ElementTree as ET


def create_diagram_xml() -> str:
    # Canvas dimensions
    CANVAS_WIDTH = 2600
    CANVAS_HEIGHT = 1480

    xml_parts = []
    xml_parts.append('<?xml version="1.0" encoding="UTF-8"?>')
    xml_parts.append('<mxfile host="app.diagrams.net" modified="2026-09-20T17:45:00.000Z" agent="Antigravity/2.0" version="24.0.0" type="device">')
    xml_parts.append('  <diagram id="hallucination-verifier-architecture" name="System Architecture (End-to-End)">')
    xml_parts.append(
        f'    <mxGraphModel dx="2600" dy="1600" grid="1" gridSize="10" guides="1" tooltips="1" '
        f'connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="{CANVAS_WIDTH}" '
        f'pageHeight="{CANVAS_HEIGHT}" background="#F8FAFC" math="0" shadow="0">'
    )
    xml_parts.append('      <root>')
    xml_parts.append('        <mxCell id="0" />')
    xml_parts.append('        <mxCell id="1" parent="0" />')

    # Helper function to add a cell
    def add_cell(cell_id, value, style, x, y, width, height, vertex=1, parent="1"):
        escaped_val = html.escape(value, quote=True)
        xml_parts.append(
            f'        <mxCell id="{cell_id}" value="{escaped_val}" style="{style}" vertex="{vertex}" parent="{parent}">'
        )
        xml_parts.append(f'          <mxGeometry x="{x}" y="{y}" width="{width}" height="{height}" as="geometry" />')
        xml_parts.append('        </mxCell>')

    # Helper function to add an edge
    def add_edge(edge_id, source_id, target_id, label="", style=""):
        escaped_lbl = html.escape(label, quote=True)
        default_style = (
            "edgeStyle=orthogonalEdgeStyle;rounded=1;orthogonalLoop=1;jettySize=auto;html=1;"
            "strokeColor=#64748B;strokeWidth=2;endArrow=classic;fontSize=10;fontColor=#475569;"
        )
        final_style = default_style + style
        xml_parts.append(
            f'        <mxCell id="{edge_id}" value="{escaped_lbl}" style="{final_style}" edge="1" parent="1" '
            f'source="{source_id}" target="{target_id}">'
        )
        xml_parts.append('          <mxGeometry relative="1" as="geometry" />')
        xml_parts.append('        </mxCell>')

    # 1. Top Header Banner
    header_html = (
        '<div style="font-size: 18px; font-weight: bold; color: #0F172A; line-height: 1.3;">'
        'System Architecture: Reducing Hallucination in Healthcare via Agentic AI &amp; Verification'
        '</div>'
        '<div style="font-size: 12px; color: #475569; margin-top: 4px;">'
        'A Comparative Evaluation of LLM-as-Judge (Gemini Flash) vs Local NLI (DeBERTa-v3) &amp; Lexical Baselines across Synthetic Benchmark (Exp 1) &amp; Realistic Healthcare RAG (Exp 2)'
        '</div>'
    )
    header_style = (
        "rounded=1;whiteSpace=wrap;html=1;fillColor=#FFFFFF;strokeColor=#CBD5E1;strokeWidth=1.5;"
        "align=left;spacingLeft=25;shadow=1;"
    )
    add_cell("HEADER", header_html, header_style, 40, 20, 1600, 75)

    # 1b. Legend Banner (Top Right)
    legend_html = (
        '<div style="font-size: 11px; font-weight: bold; color: #1E293B; margin-bottom: 2px;">ARCHITECTURE LEGEND</div>'
        '<div style="display: flex; gap: 12px; font-size: 10px;">'
        '<span style="display: inline-block; padding: 2px 6px; background: #ECFDF5; border: 1.5px solid #10B981; border-radius: 4px; color: #065F46; font-weight: 600;">■ Solid: Built / Active</span> '
        '<span style="display: inline-block; padding: 2px 6px; background: #FEF2F2; border: 1.5px dashed #EF4444; border-radius: 4px; color: #991B1B; font-weight: 600;">- - Dotted: Planned / Later Phase</span> '
        '<span style="display: inline-block; padding: 2px 6px; background: #FFF7ED; border: 1px solid #EA580C; border-radius: 4px; color: #C2410C;">⚡ Groq API</span> '
        '<span style="display: inline-block; padding: 2px 6px; background: #EFF6FF; border: 1px solid #2563EB; border-radius: 4px; color: #1D4ED8;">☁ Gemini API</span> '
        '<span style="display: inline-block; padding: 2px 6px; background: #F3E8FF; border: 1px solid #9333EA; border-radius: 4px; color: #6B21A8;">💻 Local CPU</span>'
        '</div>'
    )
    legend_style = (
        "rounded=1;whiteSpace=wrap;html=1;fillColor=#FFFFFF;strokeColor=#CBD5E1;strokeWidth=1.5;"
        "align=left;spacingLeft=15;shadow=1;"
    )
    add_cell("LEGEND", legend_html, legend_style, 1660, 20, 880, 75)

    # 2. Swimlanes / Layer Backgrounds (Left to Right)
    layers = [
        ("L1_BG", "LAYER 1: DATA SOURCES & INGESTION", "#EFF6FF", "#3B82F6", 40, 110, 460, 1340),
        ("L2_BG", "LAYER 2: EXPERIMENT DATA PREP & RAG GENERATION", "#FFFBEB", "#F59E0B", 530, 110, 480, 1340),
        ("L3_BG", "LAYER 3: VERIFICATION LAYER (SHARED MULTI-VERIFIER)", "#F0FDF4", "#10B981", 1040, 110, 490, 1340),
        ("L4_BG", "LAYER 4: EVALUATION, STATISTICS & PROFILING", "#FAF5FF", "#8B5CF6", 1560, 110, 480, 1340),
        ("L5_BG", "LAYER 5: PRESENTATION, WEB & DISSEMINATION", "#FFF1F2", "#F43F5E", 2070, 110, 470, 1340),
    ]

    for lid, title, fill, stroke, lx, ly, lw, lh in layers:
        style = (
            f"swimlane;startSize=36;rounded=1;arcSize=3;fontColor=#0F172A;fillColor={fill};"
            f"strokeColor={stroke};strokeWidth=2;fontSize=13;fontStyle=1;align=center;collapsible=0;"
        )
        add_cell(lid, title, style, lx, ly, lw, lh)

    # Helper styling templates
    def solid_box_style(fill, stroke, font="#0F172A", stroke_w="1.5"):
        return (
            f"rounded=1;arcSize=6;whiteSpace=wrap;html=1;fillColor={fill};strokeColor={stroke};"
            f"strokeWidth={stroke_w};fontColor={font};fontSize=11;align=left;spacingLeft=12;spacingRight=12;shadow=1;"
        )

    def dotted_box_style(fill="#FEF2F2", stroke="#DC2626", font="#991B1B"):
        return (
            f"rounded=1;arcSize=6;whiteSpace=wrap;html=1;fillColor={fill};strokeColor={stroke};"
            f"strokeWidth=2;dashed=1;dashPattern=6 4;fontColor={font};fontSize=11;align=left;spacingLeft=12;spacingRight=12;shadow=0;"
        )

    # =========================================================================
    # LAYER 1: DATA SOURCES & INGESTION (X: 60, Width: 420)
    # =========================================================================
    add_cell(
        "L1_MEDHALLU",
        '<div style="font-weight: bold; color: #1E3A8A; font-size: 12px;">HuggingFace: MedHallu (pqa_labeled)</div>'
        '<div style="font-size: 10px; color: #2563EB; font-weight: 600; margin-bottom: 4px;">DATA SOURCE | HF: UTAustin-AIHealth/MedHallu</div>'
        '<div style="font-size: 10.5px; color: #334155;">'
        '• Pinned Commit: <b>51506045...</b> (Rule R4.4)<br/>'
        '• 500 clinical QA pairs derived from PubMed abstracts<br/>'
        '• Synthetic hallucinations injected at sentence level<br/>'
        '• Schema: Question, Knowledge, Ground Truth, Hallucinated Answer, Difficulty, Category'
        '</div>',
        solid_box_style("#FFFFFF", "#3B82F6"),
        60, 165, 420, 125
    )

    add_cell(
        "L1_PUBMEDQA",
        '<div style="font-weight: bold; color: #1E3A8A; font-size: 12px;">HuggingFace: PubMedQA (pqa_labeled)</div>'
        '<div style="font-size: 10px; color: #2563EB; font-weight: 600; margin-bottom: 4px;">CORPUS SOURCE | HF: qiaojin/PubMedQA</div>'
        '<div style="font-size: 10.5px; color: #334155;">'
        '• Pinned Commit: <b>9001f285...</b> (Rule R4.4)<br/>'
        '• ~1,000 real PubMed biomedical research abstracts<br/>'
        '• Unmodified medical literature serving as the retrieval corpus for Experiment 2 RAG'
        '</div>',
        solid_box_style("#FFFFFF", "#3B82F6"),
        60, 310, 420, 115
    )

    add_cell(
        "L1_PILOT",
        '<div style="font-weight: bold; color: #1E3A8A; font-size: 12px;">Pilot Inspection &amp; Spot-Check</div>'
        '<div style="font-size: 10px; color: #1D4ED8; font-weight: 600; margin-bottom: 4px;">PHASE 1 | src/pilot_checks.py</div>'
        '<div style="font-size: 10.5px; color: #334155;">'
        '• <b>Risk 1:</b> Human spotcheck (n=50) uncovered <b>46.0%</b> unsupported ground-truth answers in MedHallu<br/>'
        '• <b>Risk 2:</b> Lexical shortcut test on 100 dev pairs yielded ROUGE-L AUROC = <b>0.4894</b> (&lt; 0.95 rule pass)'
        '</div>',
        solid_box_style("#EFF6FF", "#2563EB"),
        60, 445, 420, 125
    )

    add_cell(
        "L1_GATE_G1",
        '<div style="font-weight: bold; color: #B45309; font-size: 12px;">Gate G1 Decision: Plan 2 Activation</div>'
        '<div style="font-size: 10px; color: #D97706; font-weight: 600; margin-bottom: 4px;">DECISION GATE | Human Sign-off</div>'
        '<div style="font-size: 10.5px; color: #334155;">'
        '• High unsupported rate (&gt; 10%) triggered protocol fallback to <b>Plan 2</b><br/>'
        '• <b>Experiment 2 (RAG):</b> Upgraded to Primary Headline Study (200 pairs)<br/>'
        '• <b>Experiment 1 (MedHallu):</b> Retained as Secondary Benchmark'
        '</div>',
        solid_box_style("#FEF3C7", "#D97706", stroke_w="2"),
        60, 590, 420, 130
    )

    add_cell(
        "L1_CACHE",
        '<div style="font-weight: bold; color: #0F172A; font-size: 12px;">Cache &amp; Provenance Infrastructure</div>'
        '<div style="font-size: 10px; color: #475569; font-weight: 600; margin-bottom: 4px;">PERSISTENCE | data/cache/ &amp; manifests</div>'
        '<div style="font-size: 10.5px; color: #334155;">'
        '• <b>JsonlCache:</b> Deterministic hashing &amp; offline storage of API responses<br/>'
        '• <b>FROZEN.json:</b> Pinned prompt hashes (generator_v1, judge_v1)<br/>'
        '• SHA-256 manifests tracking data, configs, and seeds (seed=42)'
        '</div>',
        solid_box_style("#F1F5F9", "#64748B"),
        60, 740, 420, 120
    )

    # =========================================================================
    # LAYER 2: EXPERIMENT DATA PREP & RAG GENERATION (X: 550, Width: 440)
    # =========================================================================
    add_cell(
        "L2_E1_PAIRS",
        '<div style="font-weight: bold; color: #9A3412; font-size: 12px;">Exp 1 Pair Generator (src/build_exp1_pairs.py)</div>'
        '<div style="font-size: 10px; color: #EA580C; font-weight: 600; margin-bottom: 4px;">PHASE 2 | BENCHMARK DATASET GENERATION</div>'
        '<div style="font-size: 10.5px; color: #334155;">'
        '• Samples 250 questions from MedHallu, stratified by clinical difficulty<br/>'
        '• Expands to 500 balanced (context, answer) evaluation pairs:<br/>'
        '&nbsp;&nbsp;- 250 Ground Truth (Supported, Label 0)<br/>'
        '&nbsp;&nbsp;- 250 Hallucinated Answer (Hallucinated, Label 1)'
        '</div>',
        solid_box_style("#FFFFFF", "#EA580C"),
        550, 165, 440, 125
    )

    add_cell(
        "L2_E1_SPLIT",
        '<div style="font-weight: bold; color: #9A3412; font-size: 12px;">Question-Level Stratified Splitter</div>'
        '<div style="font-size: 10px; color: #EA580C; font-weight: 600; margin-bottom: 4px;">SPLIT ENGINE | 0 QUESTION LEAKAGE</div>'
        '<div style="font-size: 10.5px; color: #334155;">'
        '• Splits strictly by question (both GT &amp; Hallucinated stay together):<br/>'
        '&nbsp;&nbsp;→ <b>Dev Set:</b> 50 questions / 100 pairs (for threshold tuning)<br/>'
        '&nbsp;&nbsp;→ <b>Test Set:</b> 200 questions / 400 pairs (for evaluation)'
        '</div>',
        solid_box_style("#FFF7ED", "#EA580C"),
        550, 310, 440, 105
    )

    add_cell(
        "L2_E1_FILES",
        '<div style="font-weight: bold; color: #9A3412; font-size: 12px;">Exp 1 Dev &amp; Test Stores</div>'
        '<div style="font-size: 10px; color: #EA580C; font-weight: 600; margin-bottom: 4px;">STORAGE | data/exp1/dev.jsonl &amp; test.jsonl</div>'
        '<div style="font-size: 10.5px; color: #334155;">'
        '• Immutable JSONL test partitions with verified 50/50 balance<br/>'
        '• Test questions explicitly excluded from Experiment 2 selection'
        '</div>',
        solid_box_style("#FFFFFF", "#F97316"),
        550, 435, 440, 85
    )

    add_cell(
        "L2_E2_CHUNK",
        '<div style="font-weight: bold; color: #9A3412; font-size: 12px;">PubMedQA Abstract Chunker (src/build_index.py)</div>'
        '<div style="font-size: 10px; color: #D97706; font-weight: 600; margin-bottom: 4px;">PHASE 4 | RETRIEVAL INDEX PREPARATION</div>'
        '<div style="font-size: 10.5px; color: #334155;">'
        '• Chunks 1,000 PubMedQA abstracts into ~250 token segments (30 overlap)<br/>'
        '• Generated 1,790 clean chunks tracking source document metadata'
        '</div>',
        solid_box_style("#FFFBEB", "#D97706"),
        550, 540, 440, 95
    )

    add_cell(
        "L2_E2_FAISS",
        '<div style="font-weight: bold; color: #9A3412; font-size: 12px;">Local Embedding &amp; FAISS Vector Index</div>'
        '<div style="font-size: 10px; color: #B45309; font-weight: 600; margin-bottom: 4px;">'
        '💻 TOOL: Local CPU | Model: BAAI/bge-small-en-v1.5 | faiss-cpu'
        '</div>'
        '<div style="font-size: 10.5px; color: #334155;">'
        '• 384-dimensional normalized dense vectors embedded locally<br/>'
        '• <b>FAISS IndexFlatIP:</b> Exact inner-product cosine similarity retrieval<br/>'
        '• Highly efficient: <b>451.8 MB peak RAM</b> footprint on laptop CPU'
        '</div>',
        solid_box_style("#FEF3C7", "#D97706", stroke_w="2"),
        550, 655, 440, 115
    )

    add_cell(
        "L2_E2_RETRIEVAL",
        '<div style="font-weight: bold; color: #9A3412; font-size: 12px;">Dual-Condition Retrieval Engine</div>'
        '<div style="font-size: 10px; color: #EA580C; font-weight: 600; margin-bottom: 4px;">RETRIEVAL | 100 Normal + 100 Degraded</div>'
        '<div style="font-size: 10.5px; color: #334155;">'
        '• <b>Normal Condition (n=100):</b> Top-3 nearest chunks retrieved (100% hit)<br/>'
        '• <b>Degraded Condition (n=100):</b> Retrieve top-20, drop source document chunks, retain top-3 distractors to induce realistic hallucinations'
        '</div>',
        solid_box_style("#FFF7ED", "#EA580C"),
        550, 790, 440, 115
    )

    add_cell(
        "L2_E2_GROQ",
        '<div style="font-weight: bold; color: #9A3412; font-size: 12px;">RAG Generator: Groq Cloud API</div>'
        '<div style="font-size: 10px; color: #C2410C; font-weight: 600; margin-bottom: 4px;">'
        '⚡ TOOL: Groq API | Model: qwen/qwen3.8-27b | temp=0'
        '</div>'
        '<div style="font-size: 10.5px; color: #334155;">'
        '• Generates clinical answers conditioned on retrieved context chunks<br/>'
        '• Prompt: generator_v1 (frozen in FROZEN.json) | max_tokens=256<br/>'
        '• Outputs 200 answers stored in data/exp2_rag/generated.jsonl'
        '</div>',
        solid_box_style("#FFEDD5", "#C2410C", stroke_w="2"),
        550, 925, 440, 115
    )

    add_cell(
        "L2_E2_ANN_EXPORT",
        '<div style="font-weight: bold; color: #9A3412; font-size: 12px;">Annotation Preparation (src/annotation.py)</div>'
        '<div style="font-size: 10px; color: #D97706; font-weight: 600; margin-bottom: 4px;">PHASE 6 | RFC 4180 CSV SHEETS</div>'
        '<div style="font-size: 10.5px; color: #334155;">'
        '• Generates clean RFC 4180 CSV annotation sheets with seed=42 shuffle<br/>'
        '• Exports: annotator_1.csv, annotator_2.csv, template.csv, guide<br/>'
        '• Degraded/normal conditions completely blinded to annotators'
        '</div>',
        solid_box_style("#FFFBEB", "#D97706"),
        550, 1060, 440, 105
    )

    add_cell(
        "L2_E2_GATE_G2",
        '<div style="font-weight: bold; color: #B91C1C; font-size: 12px;">[PLANNED] Gate G2: Human Annotation &amp; Adjudication</div>'
        '<div style="font-size: 10px; color: #DC2626; font-weight: 600; margin-bottom: 4px;">STATUS: IN PROGRESS / BLOCKED | DOTTED BOX</div>'
        '<div style="font-size: 10.5px; color: #450A0A;">'
        '• <b>Independent Human Labeling (Rule R1.5):</b><br/>'
        '&nbsp;&nbsp;Annotator 1: Muhammad Saad | Annotator 2: Rabia Qaiser (200 pairs)<br/>'
        '• Inter-annotator agreement: Cohen\'s Kappa κ computation<br/>'
        '• Adjudication of disagreements → labeled.csv → pairs.jsonl ground truth'
        '</div>',
        dotted_box_style("#FEF2F2", "#DC2626", font="#7F1D1D"),
        550, 1185, 440, 130
    )

    # =========================================================================
    # LAYER 3: VERIFICATION LAYER (SHARED MULTI-VERIFIER) (X: 1065, Width: 440)
    # =========================================================================
    add_cell(
        "L3_COORDINATOR",
        '<div style="font-weight: bold; color: #065F46; font-size: 12px;">Shared Verifier Coordinator (src/run_verifiers.py)</div>'
        '<div style="font-size: 10px; color: #059669; font-weight: 600; margin-bottom: 4px;">SHARED PIPELINE | filters/base.py</div>'
        '<div style="font-size: 10.5px; color: #334155;">'
        '• Abstract BaseVerifier interface establishing unified JSONL schema<br/>'
        '• Evaluates Exp 1 and Exp 2 pairs with identical verification code'
        '</div>',
        solid_box_style("#ECFDF5", "#10B981"),
        1065, 165, 440, 95
    )

    add_cell(
        "L3_TUNING",
        '<div style="font-weight: bold; color: #065F46; font-size: 12px;">Threshold Optimizer (src/tune_thresholds.py)</div>'
        '<div style="font-size: 10px; color: #047857; font-weight: 600; margin-bottom: 4px;">PHASE 3 | TUNED ON EXP 1 DEV (100 PAIRS)</div>'
        '<div style="font-size: 10.5px; color: #334155;">'
        '• Grid-searches optimal classification thresholds maximizing F1<br/>'
        '• <b>Frozen in results/thresholds.json:</b><br/>'
        '&nbsp;&nbsp;- ROUGE-L threshold = <b>0.1741</b> (Dev F1 = 0.6667)<br/>'
        '&nbsp;&nbsp;- Filter B threshold = <b>0.0039</b> (Dev F1 = 0.6667)'
        '</div>',
        solid_box_style("#D1FAE5", "#059669", stroke_w="2"),
        1065, 280, 440, 125
    )

    add_cell(
        "L3_ROUGE",
        '<div style="font-weight: bold; color: #334155; font-size: 12px;">Baseline Filter: ROUGE-L Precision</div>'
        '<div style="font-size: 10px; color: #475569; font-weight: 600; margin-bottom: 4px;">'
        '💻 TOOL: Local CPU | Library: rouge-score'
        '</div>'
        '<div style="font-size: 10.5px; color: #334155;">'
        '• Measures longest common subsequence precision: answer vs context<br/>'
        '• Rule: score &lt; 0.1741 → Hallucinated (1), else Supported (0)<br/>'
        '• Ultra-fast lexical baseline: <b>median latency 2.5 ms</b> on CPU'
        '</div>',
        solid_box_style("#F1F5F9", "#64748B"),
        1065, 425, 440, 115
    )

    add_cell(
        "L3_FILTER_B",
        '<div style="font-weight: bold; color: #581C87; font-size: 12px;">Filter B: Local NLI Cross-Encoder</div>'
        '<div style="font-size: 10px; color: #7E22CE; font-weight: 600; margin-bottom: 4px;">'
        '💻 TOOL: PyTorch CPU | Model: cross-encoder/nli-deberta-v3-small'
        '</div>'
        '<div style="font-size: 10.5px; color: #334155;">'
        '• Sentence Splitter: <b>pysbd</b> (biomedical rule-based segmentation)<br/>'
        '• Sentence × Chunk entailment probability matrix (max 512 tokens)<br/>'
        '• Formula: <i>score = min<sub>s</sub>(max<sub>c</sub>(P(entailment)))</i><br/>'
        '• Rule: score &lt; 0.0039 → Hallucinated (1) | 6 CPU threads, batch=16'
        '</div>',
        solid_box_style("#F3E8FF", "#9333EA", stroke_w="2"),
        1065, 560, 440, 140
    )

    add_cell(
        "L3_FILTER_B_OPT",
        '<div style="font-weight: bold; color: #6B21A8; font-size: 12px;">[PLANNED] Filter B Optional Base Model</div>'
        '<div style="font-size: 10px; color: #9333EA; font-weight: 600; margin-bottom: 4px;">STATUS: OPTIONAL ABLATION | DOTTED BOX</div>'
        '<div style="font-size: 10.5px; color: #4A044E;">'
        '• Model: cross-encoder/nli-deberta-v3-base<br/>'
        '• Tests parameter scaling vs latency trade-off on laptop CPU'
        '</div>',
        dotted_box_style("#FAF5FF", "#A855F7", font="#581C87"),
        1065, 715, 440, 85
    )

    add_cell(
        "L3_FILTER_A",
        '<div style="font-weight: bold; color: #0C4A6E; font-size: 12px;">Filter A: API LLM Judge (Gemini Flash)</div>'
        '<div style="font-size: 10px; color: #0284C7; font-weight: 600; margin-bottom: 4px;">'
        '☁ TOOL: Google Gemini API | Model: gemini-3.6-flash | temp=0'
        '</div>'
        '<div style="font-size: 10.5px; color: #334155;">'
        '• Frozen Prompt: judge_v1 (clinical verification instructions)<br/>'
        '• Structured JSON output: verdict (0/1), confidence (1-5), rationale<br/>'
        '• Resilience: JsonlCache caching, rate limiting (10 RPM), tenacity retry'
        '</div>',
        solid_box_style("#E0F2FE", "#0284C7", stroke_w="2"),
        1065, 820, 440, 125
    )

    add_cell(
        "L3_FILTER_A_FULL",
        '<div style="font-weight: bold; color: #991B1B; font-size: 12px;">[PLANNED] Full Exp 1 &amp; Exp 2 Filter A Run</div>'
        '<div style="font-size: 10px; color: #DC2626; font-weight: 600; margin-bottom: 4px;">STATUS: DEFERRED (RATE LIMIT) | DOTTED BOX</div>'
        '<div style="font-size: 10.5px; color: #450A0A;">'
        '• Scaffolding &amp; smoke tests verified; deferred due to 20 RPD free tier<br/>'
        '• Awaiting batch quota / key upgrade to score 400 Exp 1 + 200 Exp 2 pairs'
        '</div>',
        dotted_box_style("#FEF2F2", "#EF4444", font="#7F1D1D"),
        1065, 965, 440, 95
    )

    add_cell(
        "L3_E1_EXEC",
        '<div style="font-weight: bold; color: #065F46; font-size: 12px;">Exp 1 Test Scored Runs (Phase 5)</div>'
        '<div style="font-size: 10px; color: #059669; font-weight: 600; margin-bottom: 4px;">PHASE 5 | COMPLETED TEST EVALUATION</div>'
        '<div style="font-size: 10.5px; color: #334155;">'
        '• 400 test pairs evaluated by Filter B &amp; Baseline ROUGE-L<br/>'
        '• Output: results/exp1/20260919-2151-bd5e507/metrics.json'
        '</div>',
        solid_box_style("#ECFDF5", "#059669"),
        1065, 1080, 440, 95
    )

    add_cell(
        "L3_E2_EXEC",
        '<div style="font-weight: bold; color: #991B1B; font-size: 12px;">[PLANNED] Phase 7: RAG Verification Run</div>'
        '<div style="font-size: 10px; color: #DC2626; font-weight: 600; margin-bottom: 4px;">STATUS: PLANNED (AWAITS GATE G2) | DOTTED BOX</div>'
        '<div style="font-size: 10.5px; color: #450A0A;">'
        '• Command: python -m src.run_verifiers --config configs/config.yaml --split rag<br/>'
        '• Run Filter B, Baseline ROUGE, and Filter A on 200 ground-truth RAG pairs'
        '</div>',
        dotted_box_style("#FEF2F2", "#DC2626", font="#7F1D1D"),
        1065, 1195, 440, 110
    )

    # =========================================================================
    # LAYER 4: EVALUATION, STATISTICS & PROFILING (X: 1585, Width: 430)
    # =========================================================================
    add_cell(
        "L4_METRICS",
        '<div style="font-weight: bold; color: #4C1D95; font-size: 12px;">Evaluation Engine (src/evaluate.py)</div>'
        '<div style="font-size: 10px; color: #6D28D9; font-weight: 600; margin-bottom: 4px;">PHASE 8 | CORE CLASSIFICATION METRICS</div>'
        '<div style="font-size: 10.5px; color: #334155;">'
        '• Precision, Recall, F1-Score, FPR, AUROC<br/>'
        '• <b>Safety-Critical Metric: False Negative Rate (FNR)</b><br/>'
        '&nbsp;&nbsp;Measures dangerous uncaught medical hallucinations<br/>'
        '• Exp 1 Test: Filter B F1=<b>0.6667</b>, FNR=0.0; ROUGE F1=<b>0.6667</b>, FNR=0.0'
        '</div>',
        solid_box_style("#FAF5FF", "#7C3AED", stroke_w="2"),
        1585, 165, 430, 130
    )

    add_cell(
        "L4_STATS",
        '<div style="font-weight: bold; color: #4C1D95; font-size: 12px;">Statistical Inference Suite (src/evaluation/stats.py)</div>'
        '<div style="font-size: 10px; color: #6D28D9; font-weight: 600; margin-bottom: 4px;">STATISTICAL RIGOR | BOOTSTRAP &amp; McNEMAR</div>'
        '<div style="font-size: 10.5px; color: #334155;">'
        '• <b>Question Block Bootstrap (1,000 resamples):</b> 95% CIs resampling questions to respect clustered test pair variance<br/>'
        '• <b>McNemar Paired Chi-Squared Test:</b> With continuity correction<br/>'
        '• Exp 1 Test: Filter B vs ROUGE McNemar <i>p = 1.0000</i>'
        '</div>',
        solid_box_style("#F5F3FF", "#6D28D9"),
        1585, 315, 430, 135
    )

    add_cell(
        "L4_BREAKDOWNS",
        '<div style="font-weight: bold; color: #4C1D95; font-size: 12px;">Granular Breakdown Analyzers</div>'
        '<div style="font-size: 10px; color: #7C3AED; font-weight: 600; margin-bottom: 4px;">SUBGROUP ANALYSIS | EXPORTED CSV TABLES</div>'
        '<div style="font-size: 10.5px; color: #334155;">'
        '• <b>Difficulty Breakdown:</b> Easy / Medium / Hard questions<br/>'
        '• <b>Category Breakdown:</b> Entity, Relation, Fact, Contradiction<br/>'
        '• Confirms whether filters fail on specific medical domain types'
        '</div>',
        solid_box_style("#FAF5FF", "#8B5CF6"),
        1585, 470, 430, 110
    )

    add_cell(
        "L4_TIMING",
        '<div style="font-weight: bold; color: #1E293B; font-size: 12px;">Resource &amp; Efficiency Profiler (src/timing.py)</div>'
        '<div style="font-size: 10px; color: #475569; font-weight: 600; margin-bottom: 4px;">'
        '💻 TOOL: psutil &amp; monotonic clock | SYSTEM EFFICIENCY'
        '</div>'
        '<div style="font-size: 10.5px; color: #334155;">'
        '• Wall-clock latency (p50/p95): Filter B median <b>332.1 ms</b>, ROUGE <b>2.5 ms</b><br/>'
        '• Peak RAM tracking (Under 8 GB laptop memory budget)<br/>'
        '• Shadow Financial Cost: Filter A estimated at <b>$0.0575 / 1k queries</b>'
        '</div>',
        solid_box_style("#F8FAFC", "#64748B"),
        1585, 600, 430, 125
    )

    add_cell(
        "L4_CROSS",
        '<div style="font-weight: bold; color: #4C1D95; font-size: 12px;">Cross-Experiment Analysis (src/cross_experiment.py)</div>'
        '<div style="font-size: 10px; color: #7C3AED; font-weight: 600; margin-bottom: 4px;">PHASE 9 | RANKING &amp; DISAGREEMENT MINING</div>'
        '<div style="font-size: 10.5px; color: #334155;">'
        '• Verifier ranking agreement across datasets (Kendall\'s τ, Spearman\'s ρ)<br/>'
        '• Qualitative Disagreement Analyzer: 3 divergent test pairs exported for clinical inspection'
        '</div>',
        solid_box_style("#FAF5FF", "#7C3AED"),
        1585, 745, 430, 115
    )

    add_cell(
        "L4_E2_EVAL",
        '<div style="font-weight: bold; color: #991B1B; font-size: 12px;">[PLANNED] Phase 8 Exp 2 RAG Evaluation</div>'
        '<div style="font-size: 10px; color: #DC2626; font-weight: 600; margin-bottom: 4px;">STATUS: PLANNED | DOTTED BOX</div>'
        '<div style="font-size: 10.5px; color: #450A0A;">'
        '• Scored on 200 realistic human-annotated RAG pairs<br/>'
        '• Confusion matrices, 95% bootstrap CIs, safety-critical FNR analysis'
        '</div>',
        dotted_box_style("#FEF2F2", "#DC2626", font="#7F1D1D"),
        1585, 880, 430, 100
    )

    add_cell(
        "L4_E2_TRANSFER",
        '<div style="font-weight: bold; color: #991B1B; font-size: 12px;">[PLANNED] Phase 9 Domain Shift &amp; Transfer</div>'
        '<div style="font-size: 10px; color: #DC2626; font-weight: 600; margin-bottom: 4px;">STATUS: PLANNED | DOTTED BOX</div>'
        '<div style="font-size: 10.5px; color: #450A0A;">'
        '• Zero-shot transfer of Exp 1 thresholds to Exp 2 RAG pairs<br/>'
        '• Quantifies performance degradation under distribution shift'
        '</div>',
        dotted_box_style("#FEF2F2", "#DC2626", font="#7F1D1D"),
        1585, 1000, 430, 100
    )

    add_cell(
        "L4_E2_HYPOTHESIS",
        '<div style="font-weight: bold; color: #991B1B; font-size: 12px;">[PLANNED] Formal Hypothesis Tests (H1 &amp; H2)</div>'
        '<div style="font-size: 10px; color: #DC2626; font-weight: 600; margin-bottom: 4px;">STATUS: PLANNED | DOTTED BOX</div>'
        '<div style="font-size: 10.5px; color: #450A0A;">'
        '• H1: Filter B local NLI non-inferior to Filter A Gemini judge<br/>'
        '• H2: Verifier performance degrades under realistic RAG distribution shift'
        '</div>',
        dotted_box_style("#FEF2F2", "#DC2626", font="#7F1D1D"),
        1585, 1120, 430, 105
    )

    # =========================================================================
    # LAYER 5: PRESENTATION, WEB & DISSEMINATION (X: 2095, Width: 420)
    # =========================================================================
    add_cell(
        "L5_SSOT",
        '<div style="font-weight: bold; color: #881337; font-size: 12px;">Numbers of Record (Single Source of Truth)</div>'
        '<div style="font-size: 10px; color: #BE123C; font-weight: 600; margin-bottom: 4px;">CANONICAL STORE | results/site/numbers_of_record.json</div>'
        '<div style="font-size: 10.5px; color: #334155;">'
        '• Central repository for all verified numbers, CIs, p-values, timings<br/>'
        '• Strictly prevents hard-coding; guarantees zero divergence across docs'
        '</div>',
        solid_box_style("#FFF1F2", "#E11D48", stroke_w="2"),
        2095, 165, 420, 115
    )

    add_cell(
        "L5_FIGURES",
        '<div style="font-weight: bold; color: #881337; font-size: 12px;">Publication Figures Engine (src/figures.py)</div>'
        '<div style="font-size: 10px; color: #BE123C; font-weight: 600; margin-bottom: 4px;">'
        '🎨 TOOL: matplotlib &amp; seaborn | 6 PUBLICATION FIGURES'
        '</div>'
        '<div style="font-size: 10.5px; color: #334155;">'
        '• <b>Fig 1:</b> Confusion Matrix &nbsp;&nbsp;• <b>Fig 2:</b> Filter B PR Curve<br/>'
        '• <b>Fig 3:</b> Latency CDF &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;• <b>Fig 4:</b> Pareto Front<br/>'
        '• <b>Fig 5:</b> Category Breakdown &nbsp;• <b>Fig 6:</b> Cross-Exp Comparison<br/>'
        '• High-res output: 300 DPI PNG &amp; Vector PDF in results/figures/'
        '</div>',
        solid_box_style("#FFE4E6", "#E11D48", stroke_w="2"),
        2095, 300, 420, 150
    )

    add_cell(
        "L5_SITE_EXPORT",
        '<div style="font-weight: bold; color: #881337; font-size: 12px;">Site Exporter Engine (src/site_export.py)</div>'
        '<div style="font-size: 10px; color: #9F1239; font-weight: 600; margin-bottom: 4px;">SESSION CLOSE ENGINE | Rule R9.2</div>'
        '<div style="font-size: 10.5px; color: #334155;">'
        '• Replaces template macros with canonical numbers of record<br/>'
        '• Synchronizes Phase.md Snapshot Progress Board<br/>'
        '• Validates all 14 interactive metric tiles on the website'
        '</div>',
        solid_box_style("#FFF1F2", "#BE123C"),
        2095, 470, 420, 115
    )

    add_cell(
        "L5_MKDOCS",
        '<div style="font-weight: bold; color: #881337; font-size: 12px;">Project Website (Material for MkDocs)</div>'
        '<div style="font-size: 10px; color: #9F1239; font-weight: 600; margin-bottom: 4px;">DOCUMENTATION PORTAL | mkdocs build --strict</div>'
        '<div style="font-size: 10.5px; color: #334155;">'
        '• 4 custom Python hooks (numbers, progress, citations, claim)<br/>'
        '• Interactive web presentation of Architecture, Write-up, &amp; Progress'
        '</div>',
        solid_box_style("#FFE4E6", "#BE123C"),
        2095, 605, 420, 115
    )

    add_cell(
        "L5_CICD",
        '<div style="font-weight: bold; color: #0F172A; font-size: 12px;">Automated CI/CD (GitHub Actions)</div>'
        '<div style="font-size: 10px; color: #334155; font-weight: 600; margin-bottom: 4px;">AUTOMATION | .github/workflows/</div>'
        '<div style="font-size: 10.5px; color: #334155;">'
        '• <b>ci.yml:</b> Automated pytest (122 passing tests) &amp; ruff linting<br/>'
        '• <b>pages.yml:</b> Continuous deployment to GitHub Pages on git push'
        '</div>',
        solid_box_style("#F1F5F9", "#475569"),
        2095, 740, 420, 110
    )

    add_cell(
        "L5_PAPER",
        '<div style="font-weight: bold; color: #991B1B; font-size: 12px;">[PLANNED] Academic Manuscript &amp; LaTeX Assets</div>'
        '<div style="font-size: 10px; color: #DC2626; font-weight: 600; margin-bottom: 4px;">STATUS: PLANNED | DOTTED BOX | paper/</div>'
        '<div style="font-size: 10.5px; color: #450A0A;">'
        '• Automated LaTeX table generation directly from numbers_of_record.json<br/>'
        '• Camera-ready clinical paper draft adhering to health AI guidelines'
        '</div>',
        dotted_box_style("#FEF2F2", "#DC2626", font="#7F1D1D"),
        2095, 870, 420, 115
    )

    add_cell(
        "L5_RELEASE",
        '<div style="font-weight: bold; color: #991B1B; font-size: 12px;">[PLANNED] Open Science Release &amp; Archival</div>'
        '<div style="font-size: 10px; color: #DC2626; font-weight: 600; margin-bottom: 4px;">STATUS: PLANNED (PHASE 11) | DOTTED BOX</div>'
        '<div style="font-size: 10.5px; color: #450A0A;">'
        '• Permanent Zenodo DOI code and data archival<br/>'
        '• Reproducible one-click execution bundle (scripts/run_all.sh)'
        '</div>',
        dotted_box_style("#FEF2F2", "#DC2626", font="#7F1D1D"),
        2095, 1005, 420, 115
    )

    # =========================================================================
    # EDGES & DATAFLOW CONNECTIONS
    # =========================================================================
    # Layer 1 internal & to Layer 2
    add_edge("E_M_PILOT", "L1_MEDHALLU", "L1_PILOT", "Sample 50 rows")
    add_edge("E_P_PILOT", "L1_PILOT", "L1_GATE_G1", "46% unsupported GT")
    add_edge("E_G1_E1", "L1_GATE_G1", "L2_E1_PAIRS", "Plan 2: Secondary Benchmark")
    add_edge("E_G1_E2", "L1_GATE_G1", "L2_E2_CHUNK", "Plan 2: Primary Headline RAG")
    add_edge("E_M_E1", "L1_MEDHALLU", "L2_E1_PAIRS", "250 questions")
    add_edge("E_P_E2", "L1_PUBMEDQA", "L2_E2_CHUNK", "1,000 abstracts")

    # Layer 2 internal
    add_edge("E_E1_P_S", "L2_E1_PAIRS", "L2_E1_SPLIT", "500 pairs")
    add_edge("E_E1_S_F", "L2_E1_SPLIT", "L2_E1_FILES", "100 dev / 400 test")
    add_edge("E_E2_C_F", "L2_E2_CHUNK", "L2_E2_FAISS", "1,790 chunks")
    add_edge("E_E2_F_R", "L2_E2_FAISS", "L2_E2_RETRIEVAL", "IndexFlatIP vectors")
    add_edge("E_E2_R_G", "L2_E2_RETRIEVAL", "L2_E2_GROQ", "Top-3 chunks (normal/degraded)")
    add_edge("E_E2_G_A", "L2_E2_GROQ", "L2_E2_ANN_EXPORT", "200 generated answers")
    add_edge("E_E2_A_G2", "L2_E2_ANN_EXPORT", "L2_E2_GATE_G2", "annotator_1.csv & annotator_2.csv", style="dashed=1;")

    # Layer 2 to Layer 3
    add_edge("E_E1_DEV_TUNE", "L2_E1_FILES", "L3_TUNING", "Dev 100 pairs")
    add_edge("E_E1_TEST_COORD", "L2_E1_FILES", "L3_COORDINATOR", "Test 400 pairs")
    add_edge("E_E2_G2_COORD", "L2_E2_GATE_G2", "L3_E2_EXEC", "Reconciled pairs.jsonl", style="dashed=1;")

    # Layer 3 internal
    add_edge("E_TUNE_ROUGE", "L3_TUNING", "L3_ROUGE", "Freeze thresh: 0.1741")
    add_edge("E_TUNE_NLI", "L3_TUNING", "L3_FILTER_B", "Freeze thresh: 0.0039")
    add_edge("E_COORD_ROUGE", "L3_COORDINATOR", "L3_ROUGE", "Evaluate")
    add_edge("E_COORD_NLI", "L3_COORDINATOR", "L3_FILTER_B", "Evaluate")
    add_edge("E_COORD_API", "L3_COORDINATOR", "L3_FILTER_A", "Evaluate (smoke verified)")
    add_edge("E_COORD_E1_EXEC", "L3_COORDINATOR", "L3_E1_EXEC", "Score 400 pairs")
    add_edge("E_API_FULL", "L3_FILTER_A", "L3_FILTER_A_FULL", "Deferred", style="dashed=1;")
    add_edge("E_NLI_OPT", "L3_FILTER_B", "L3_FILTER_B_OPT", "Model ablation", style="dashed=1;")
    add_edge("E_COORD_E2_EXEC", "L3_COORDINATOR", "L3_E2_EXEC", "Phase 7 RAG run", style="dashed=1;")

    # Layer 3 to Layer 4
    add_edge("E_E1_EXEC_METRICS", "L3_E1_EXEC", "L4_METRICS", "Exp 1 scored pairs")
    add_edge("E_E1_EXEC_TIMING", "L3_E1_EXEC", "L4_TIMING", "Latencies & RAM")
    add_edge("E_E2_EXEC_EVAL", "L3_E2_EXEC", "L4_E2_EVAL", "Exp 2 scored pairs", style="dashed=1;")
    add_edge("E_E2_EXEC_TRANS", "L3_E2_EXEC", "L4_E2_TRANSFER", "Threshold transfer", style="dashed=1;")

    # Layer 4 internal
    add_edge("E_METRICS_STATS", "L4_METRICS", "L4_STATS", "Question Bootstrap & McNemar")
    add_edge("E_METRICS_BREAK", "L4_METRICS", "L4_BREAKDOWN", "Subgroups")
    add_edge("E_METRICS_CROSS", "L4_METRICS", "L4_CROSS", "Rank agreement")
    add_edge("E_E2_EVAL_HYP", "L4_E2_EVAL", "L4_E2_HYPOTHESIS", "Hypothesis H1 & H2", style="dashed=1;")
    add_edge("E_E2_TRANS_HYP", "L4_E2_TRANSFER", "L4_E2_HYPOTHESIS", "Domain shift impact", style="dashed=1;")

    # Layer 4 to Layer 5
    add_edge("E_METRICS_SSOT", "L4_METRICS", "L5_SSOT", "F1, FNR, P, R")
    add_edge("E_STATS_SSOT", "L4_STATS", "L5_SSOT", "Bootstrap 95% CIs & p-values")
    add_edge("E_TIMING_SSOT", "L4_TIMING", "L5_SSOT", "Latency p50/p95 & costs")
    add_edge("E_SSOT_FIG", "L5_SSOT", "L5_FIGURES", "Exact canonical metrics")
    add_edge("E_SSOT_SITE", "L5_SSOT", "L5_SITE_EXPORT", "Numbers synchronization")
    add_edge("E_FIG_WEB", "L5_FIGURES", "L5_MKDOCS", "Figures 1 to 6 (PNG/PDF)")
    add_edge("E_SITE_WEB", "L5_SITE_EXPORT", "L5_MKDOCS", "Populated Markdown")
    add_edge("E_CICD_WEB", "L5_CICD", "L5_MKDOCS", "Automated deployment")
    add_edge("E_SSOT_PAPER", "L5_SSOT", "L5_PAPER", "LaTeX tables export", style="dashed=1;")
    add_edge("E_WEB_RELEASE", "L5_MKDOCS", "L5_RELEASE", "Reproducible package", style="dashed=1;")

    xml_parts.append('      </root>')
    xml_parts.append('    </mxGraphModel>')
    xml_parts.append('  </diagram>')
    xml_parts.append('</mxfile>')

    return '\n'.join(xml_parts)

def main():
    content = create_diagram_xml()

    # Validate XML syntax
    try:
        ET.fromstring(content)
        print("XML Syntax Validation: SUCCESS (Valid XML)")
    except ET.ParseError as e:
        print(f"XML Syntax Error: {e}")
        return 1

    # Output paths
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
