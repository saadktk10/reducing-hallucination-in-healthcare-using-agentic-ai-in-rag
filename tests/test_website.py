"""Tests for project website hooks and site export (Website_Prompt.md §10)."""

from pathlib import Path

import pytest

from hooks.progress import _STATUS_ICONS, _get_current_status, _parse_snapshot_table
from hooks.tiles import _TILE_PHASES, _render_tile, _render_tile_pair
from src.site_export import TILE_REGISTRY, export_site_numbers


def test_parse_snapshot_table() -> None:
    """Verify that Phase.md Snapshot table parses correctly and rows have valid status icons."""
    rows = _parse_snapshot_table("Phase.md")
    assert len(rows) > 0
    for r in rows:
        assert "phase" in r
        assert "scope" in r
        assert "state" in r
        assert r["icon"] in _STATUS_ICONS
        assert len(r["state_text"]) > 0


def test_parse_snapshot_table_missing_icon(tmp_path: Path) -> None:
    """Test that a Snapshot row missing a valid icon raises ValueError (fails --strict)."""
    bad_phase_md = tmp_path / "Phase.md"
    bad_phase_md.write_text(
        """# Phase
## Snapshot
| Phase | Scope | State |
| --- | --- | --- |
| 0 | Environment | Planned without icon |
""",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="has no status icon"):
        _parse_snapshot_table(str(bad_phase_md))


def test_parse_snapshot_table_missing_section(tmp_path: Path) -> None:
    """Test that missing ## Snapshot raises ValueError."""
    bad_phase_md = tmp_path / "Phase.md"
    bad_phase_md.write_text("# Phase\nNo snapshot table here\n", encoding="utf-8")
    with pytest.raises(ValueError, match="No '## Snapshot' section found"):
        _parse_snapshot_table(str(bad_phase_md))


def test_get_current_status() -> None:
    """Check extraction of current status from Phase.md."""
    status = _get_current_status("Phase.md")
    assert status != "Unknown"
    assert "Phase" in status


def test_tile_rendering_missing_keys() -> None:
    """Test that missing keys render as pending without raising an exception."""
    tile_html = _render_tile("nonexistent.metric")
    assert "tile-pending" in tile_html
    assert "pending" in tile_html


def test_tile_rendering_registered_pending_keys() -> None:
    """Test that registered tile keys render their expected Phase label when pending."""
    for key, phase in _TILE_PHASES.items():
        tile_html = _render_tile(key)
        assert "tile-pending" in tile_html
        assert phase in tile_html


def test_tile_pair_rendering() -> None:
    """Test rendering of tile pairs."""
    pair_html = _render_tile_pair("timing.filter_b.median_ms", "timing.filter_a.median_ms")
    assert "tile-pair" in pair_html
    assert "Phase 5" in pair_html


def test_site_export_empty_and_tile_registry(tmp_path: Path) -> None:
    """Test export_site_numbers when no experiment runs exist yet."""
    results_dir = tmp_path / "results"
    results_dir.mkdir()
    out_file = results_dir / "site" / "numbers_of_record.json"

    record = export_site_numbers(results_dir=results_dir, output_path=out_file)
    assert out_file.exists()
    assert record["numbers"] == {}

    # Verify that all tile registry keys are accounted for in documentation or pending
    for key in TILE_REGISTRY:
        assert key in _TILE_PHASES
