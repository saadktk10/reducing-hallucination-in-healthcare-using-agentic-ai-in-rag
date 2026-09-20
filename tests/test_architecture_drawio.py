"""
Unit tests for architecture draw.io diagram generator and XML validity.
"""

import os
import xml.etree.ElementTree as ET

from scripts.generate_architecture_drawio import create_diagram_xml


def test_drawio_xml_validity():
    """Verify that the generated diagram XML is well-formed and valid."""
    content = create_diagram_xml()
    assert content.startswith("<?xml version=\"1.0\" encoding=\"UTF-8\"?>")
    root = ET.fromstring(content)
    assert root.tag == "mxfile"
    diagram = root.find("diagram")
    assert diagram is not None
    assert diagram.get("name") == "System Architecture (End-to-End)"
    graph_model = diagram.find("mxGraphModel")
    assert graph_model is not None


def test_drawio_five_layers_present():
    """Verify that all 5 required left-to-right layers are present."""
    content = create_diagram_xml()
    expected_layers = [
        "LAYER 1: DATA SOURCES &amp; INGESTION",
        "LAYER 2: EXPERIMENT DATA PREP &amp; RAG GENERATION",
        "LAYER 3: VERIFICATION LAYER (SHARED MULTI-VERIFIER)",
        "LAYER 4: EVALUATION, STATISTICS &amp; PROFILING",
        "LAYER 5: PRESENTATION, WEB &amp; DISSEMINATION",
    ]
    for layer in expected_layers:
        assert layer in content, f"Missing layer in diagram XML: {layer}"


def test_drawio_model_tool_badges():
    """Verify that all key models and tools are explicitly tagged and present."""
    content = create_diagram_xml()
    expected_tools = [
        "qwen/qwen3.8-27b",
        "gemini-3.6-flash",
        "cross-encoder/nli-deberta-v3-small",
        "BAAI/bge-small-en-v1.5",
        "faiss-cpu",
        "rouge-score",
        "pysbd",
    ]
    for tool in expected_tools:
        assert tool in content, f"Missing model or tool badge in diagram: {tool}"


def test_drawio_dotted_boxes_for_planned_components():
    """Verify that planned/future components use dotted/dashed styling."""
    content = create_diagram_xml()
    assert "dashed=1" in content
    assert "dashPattern=6 4" in content
    root = ET.fromstring(content)
    all_values = " ".join(cell.get("value", "") for cell in root.iter("mxCell"))
    planned_markers = [
        "[PLANNED] Gate G2: Human Annotation",
        "[PLANNED] Phase 7: RAG Verification Run",
        "[PLANNED] Phase 8 Exp 2 RAG Evaluation",
        "[PLANNED] Phase 9 Domain Shift",
        "[PLANNED] Academic Manuscript",
        "[PLANNED] Open Science Release",
    ]
    for marker in planned_markers:
        assert marker in all_values, f"Missing planned marker: {marker}"


def test_drawio_files_on_disk():
    """Verify that both target draw.io files exist and are non-empty."""
    paths = [
        os.path.join("docs", "assets", "architecture.drawio"),
        "architecture.drawio",
    ]
    for p in paths:
        assert os.path.exists(p), f"File does not exist: {p}"
        assert os.path.getsize(p) > 20000, f"File is too small: {p}"
