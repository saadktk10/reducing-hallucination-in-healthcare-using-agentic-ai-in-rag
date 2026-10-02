"""Tests for writeup digests to verify all source references exist (Phase 10 Acceptance Criteria)."""

import re
from pathlib import Path


def test_writeup_sources_exist() -> None:
    """Verify that every bullet in writeup/*.md referencing a file path points to an existing file."""
    writeup_dir = Path("writeup")
    assert writeup_dir.exists() and writeup_dir.is_dir()

    md_files = list(writeup_dir.glob("*.md"))
    assert len(md_files) >= 7  # 00-abstract to 06-conclusion + README

    pattern = re.compile(r"`([^`]+)`")
    checked_refs = 0

    for md_file in md_files:
        if md_file.name == "README.md":
            continue
        text = md_file.read_text(encoding="utf-8")
        for line in text.splitlines():
            line_str = line.strip()
            if not line_str.startswith("-"):
                continue
            # Find backtick paths
            matches = pattern.findall(line_str)
            for m in matches:
                # If it looks like a path (results/..., data/..., configs/..., paper/..., etc.)
                if any(m.startswith(prefix) for prefix in ("results/", "results\\", "data/", "data\\", "configs/", "paper/", "Architecture.md", "Rules.md")):
                    p = Path(m)
                    assert p.exists(), f"Source path '{m}' in {md_file.name} does not exist!"
                    checked_refs += 1

    assert checked_refs > 15, f"Expected > 15 verified source references in writeup, found {checked_refs}"
