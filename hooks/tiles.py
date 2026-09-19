"""Tile rendering hook: replaces {{ tile:<key> }} and {{ tile_pair:<a>|<b> }} markers.

Reads numbers from results/site/numbers_of_record.json. Missing keys render
a grey "pending (Phase N)" tile. Malformed JSON raises an error so
--strict fails (Website_Prompt.md §6).
"""

import json
import re
from pathlib import Path

# Static registry: tile key -> phase that produces it.
_TILE_PHASES = {
    "pilot.unsupported_rate": "Phase 1",
    "pilot.rouge_auroc": "Phase 1",
    "exp1.filter_a.f1": "Phase 8",
    "exp1.filter_b.f1": "Phase 8",
    "exp1.rouge.f1": "Phase 8",
    "exp1.filter_a.fnr": "Phase 8",
    "exp1.filter_b.fnr": "Phase 8",
    "exp1.mcnemar_ab.p": "Phase 8",
    "timing.filter_b.median_ms": "Phase 5",
    "timing.filter_a.median_ms": "Phase 5",
    "cost.filter_a.per_1k_usd": "Phase 5",
    "exp2.kappa": "Phase 6",
    "exp2.filter_a.f1": "Phase 8",
    "exp2.filter_b.f1": "Phase 8",
    "cross.ranking_agrees": "Phase 9",
}

_NUMBERS = None
_NUMBERS_PATH = Path("results/site/numbers_of_record.json")


def _load_numbers():
    """Load numbers_of_record.json once per build."""
    global _NUMBERS
    if _NUMBERS is not None:
        return _NUMBERS

    if not _NUMBERS_PATH.exists():
        _NUMBERS = {}
        return _NUMBERS

    try:
        with open(_NUMBERS_PATH) as f:
            data = json.load(f)
        _NUMBERS = data.get("numbers", {})
    except json.JSONDecodeError as e:
        raise ValueError(f"Malformed {_NUMBERS_PATH}: {e}") from e

    return _NUMBERS


def _render_tile(key: str) -> str:
    """Render a single tile as HTML."""
    numbers = _load_numbers()
    entry = numbers.get(key)

    if entry is None:
        phase = _TILE_PHASES.get(key, "unknown phase")
        return (
            f'<div class="tile tile-pending">'
            f'<span class="tile-value">pending</span>'
            f'<span class="tile-label">{key}</span>'
            f'<span class="tile-phase">{phase}</span>'
            f"</div>"
        )

    if isinstance(entry, (int, float, str)):
        entry = {"value": entry, "display": str(entry)}
    elif not isinstance(entry, dict):
        entry = {"value": str(entry), "display": str(entry)}

    value = entry.get("display", str(entry.get("value", "?")))
    ci = entry.get("ci")
    n = entry.get("n")
    source = entry.get("source", "")
    note = entry.get("note", "")

    ci_str = f' <span class="tile-ci">[{ci[0]:.2f}, {ci[1]:.2f}]</span>' if ci else ""
    n_str = f' <span class="tile-n">n={n}</span>' if n else ""
    source_str = f'<code class="tile-source">{source}</code>' if source else ""
    note_str = f'<span class="tile-note">{note}</span>' if note else ""

    return (
        f'<div class="tile">'
        f'<span class="tile-value">{value}</span>{ci_str}{n_str}'
        f'<span class="tile-label">{key}</span>'
        f"{note_str}"
        f"{source_str}"
        f"</div>"
    )


def _render_tile_pair(key_a: str, key_b: str) -> str:
    """Render two tiles side by side for comparison."""
    return f'<div class="tile-pair">{_render_tile(key_a)}{_render_tile(key_b)}</div>'


def on_page_markdown(markdown, page, config, files, **kwargs):
    """Replace tile markers in markdown."""
    # Reset cache per build
    global _NUMBERS
    _NUMBERS = None

    # {{ tile_pair:<key_a>|<key_b> }}
    def replace_pair(match):
        key_a, key_b = match.group(1), match.group(2)
        return _render_tile_pair(key_a, key_b)

    markdown = re.sub(
        r"\{\{\s*tile_pair:\s*([^|]+?)\s*\|\s*(.+?)\s*\}\}",
        replace_pair,
        markdown,
    )

    # {{ tile:<key> }}
    def replace_single(match):
        return _render_tile(match.group(1).strip())

    markdown = re.sub(
        r"\{\{\s*tile:\s*(.+?)\s*\}\}",
        replace_single,
        markdown,
    )

    return markdown
