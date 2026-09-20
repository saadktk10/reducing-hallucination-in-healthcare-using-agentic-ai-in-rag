"""Tests for Phase 10 figures generation module (src/figures.py)."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from src.common.config import load_config
from src.figures import VERIFIER_COLORS, generate_all_figures, save_figure


def test_verifier_colors_okabe_ito() -> None:
    assert "filter_b" in VERIFIER_COLORS
    assert "filter_a" in VERIFIER_COLORS
    assert "rouge" in VERIFIER_COLORS
    assert VERIFIER_COLORS["filter_b"] == "#0072B2"
    assert VERIFIER_COLORS["filter_a"] == "#E69F00"
    assert VERIFIER_COLORS["rouge"] == "#009E73"


def test_save_figure(tmp_path: Path) -> None:
    fig, ax = plt.subplots()
    ax.plot([0, 1], [0, 1])
    png, pdf = save_figure(fig, "test_fig", tmp_path)
    assert png.exists()
    assert pdf.exists()
    assert png.stat().st_size > 0
    assert pdf.stat().st_size > 0


def test_generate_all_figures_integration(tmp_path: Path) -> None:
    cfg = load_config("configs/config.yaml")
    out_dir = tmp_path / "figures"
    files = generate_all_figures(cfg, out_dir=out_dir)
    assert len(files) == 12  # 6 png + 6 pdf
    assert (out_dir / "README.md").exists()
    for f in files:
        assert f.stat().st_size > 0
