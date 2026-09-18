"""External numbers hook: renders paper/external_numbers.json as a table.

Only rows with "human_verified": true appear. The agent may add candidate
rows with human_verified: false; researchers flip the flag after reading
the primary source (Website_Prompt.md §5.1).
"""

import json
from pathlib import Path

_EXTERNAL_PATH = Path("paper/external_numbers.json")


def _render_table() -> str:
    """Render the external numbers table from JSON."""
    if not _EXTERNAL_PATH.exists():
        return "*No external comparison data available yet.*"

    try:
        with open(_EXTERNAL_PATH) as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f"Malformed {_EXTERNAL_PATH}: {e}") from e

    rows = [r for r in data.get("rows", []) if r.get("human_verified", False)]

    if not rows:
        return "*No verified external comparison data yet. Candidate rows exist but need researcher verification.*"

    table = "| System | Setting | Metric | Value | Source |\n"
    table += "| --- | --- | --- | --- | --- |\n"

    for r in rows:
        system = r.get("system", "")
        setting = r.get("setting", "")
        metric = r.get("metric", "")
        value = r.get("value", "")
        source = r.get("source_url", "")
        source_link = f"[link]({source})" if source else ""
        table += f"| {system} | {setting} | {metric} | {value} | {source_link} |\n"

    table += "\n*None of these is a like-for-like comparison.*\n"
    return table


def on_page_markdown(markdown, page, config, files, **kwargs):
    """Replace external numbers placeholder."""
    if "{{ external_numbers }}" in markdown:
        markdown = markdown.replace("{{ external_numbers }}", _render_table())
    return markdown
