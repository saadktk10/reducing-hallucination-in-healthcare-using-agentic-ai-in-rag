"""Progress board hook: parses Phase.md Snapshot table into a visual board.

Only runs on progress.md. Raises if the Snapshot table is missing or a
row lacks a status icon, so --strict fails (Website_Prompt.md §6).
"""

import re
from pathlib import Path

_STATUS_ICONS = {"✅", "🟡", "🔲", "🔴", "🔵", "⛔"}
_STATUS_LABELS = {
    "✅": "done",
    "🟡": "partial",
    "🔲": "planned",
    "🔴": "open defect",
    "🔵": "blocked",
    "⛔": "withdrawn",
}


def _parse_snapshot_table(phase_md_path: str = "Phase.md") -> list[dict]:
    """Parse the Snapshot table from Phase.md.

    Returns a list of dicts: {phase, scope, state, icon, state_text}.

    Raises:
        ValueError: If the table is missing or a row has no status icon.
    """
    path = Path(phase_md_path)
    if not path.exists():
        raise ValueError(f"Phase.md not found at {path}")

    text = path.read_text(encoding="utf-8")

    # Find the ## Snapshot section
    snapshot_match = re.search(r"## Snapshot\b.*?\n(.*?)(?=\n## |\Z)", text, re.DOTALL)
    if not snapshot_match:
        raise ValueError("No '## Snapshot' section found in Phase.md")

    section = snapshot_match.group(1)

    # Parse table rows (skip header and separator)
    rows = []
    table_started = False
    for line in section.strip().split("\n"):
        line = line.strip()
        if not line.startswith("|"):
            if table_started:
                break
            continue

        cells = [c.strip() for c in line.split("|")[1:-1]]
        if len(cells) < 3:
            continue

        # Skip header row
        if cells[0] in ("Phase", "---") or all(c.startswith("-") for c in cells):
            table_started = True
            continue

        table_started = True
        phase = cells[0].strip()
        scope = cells[1].strip()
        state = cells[2].strip()

        # Detect icon
        icon = None
        for ic in _STATUS_ICONS:
            if state.startswith(ic):
                icon = ic
                break

        if icon is None:
            raise ValueError(
                f"Phase.md Snapshot row for phase '{phase}' has no status icon. "
                f"State cell must start with one of: {', '.join(sorted(_STATUS_ICONS))}"
            )

        state_text = state[len(icon) :].strip()
        rows.append(
            {
                "phase": phase,
                "scope": scope,
                "state": state,
                "icon": icon,
                "state_text": state_text,
            }
        )

    if not rows:
        raise ValueError("Snapshot table in Phase.md has no data rows")

    return rows


def _get_current_status(phase_md_path: str = "Phase.md") -> str:
    """Extract the Current status line from Phase.md."""
    path = Path(phase_md_path)
    if not path.exists():
        return "Unknown"

    for line in path.read_text(encoding="utf-8").split("\n"):
        if line.strip().startswith("**Current status:**"):
            return line.strip().replace("**Current status:**", "").strip()
    return "Unknown"


def _get_latest_session(phase_md_path: str = "Phase.md") -> str:
    """Extract the latest session log entry from Phase.md."""
    path = Path(phase_md_path)
    if not path.exists():
        return ""

    text = path.read_text(encoding="utf-8")
    session_match = re.search(r"## Session [Ll]og\b.*?\n(.*?)(?=\n## |\Z)", text, re.DOTALL)
    if not session_match:
        return ""

    entries = session_match.group(1).strip()
    if not entries:
        return "*No session log entries yet.*"

    # Return the last entry block
    blocks = re.split(r"\n(?=###\s)", entries)
    return blocks[-1].strip() if blocks else entries[:500]


def on_page_markdown(markdown, page, config, files, **kwargs):
    """Replace progress board markers on progress.md only."""
    if page.file.src_path != "progress.md":
        return markdown

    rows = _parse_snapshot_table()
    status = _get_current_status()
    latest = _get_latest_session()

    # Count statuses
    counts = {}
    for r in rows:
        label = _STATUS_LABELS.get(r["icon"], "unknown")
        counts[label] = counts.get(label, 0) + 1

    counter_parts = []
    for label in ["done", "partial", "planned", "open defect", "blocked", "withdrawn"]:
        icon = [k for k, v in _STATUS_LABELS.items() if v == label][0]
        if label in counts:
            counter_parts.append(f"**{counts[label]}** {icon} {label}")
    counter_line = " | ".join(counter_parts)

    # Build cards
    cards_html = '<div class="phase-board">\n'
    for r in rows:
        truncated = r["state_text"][:120]
        full_state = r["state_text"].replace('"', "&quot;")
        anchor = f"phase-{r['phase'].lower().replace(' ', '-')}"
        cards_html += (
            f'<a href="#{anchor}" class="phase-card-link">\n'
            f'  <div class="phase-card phase-{_STATUS_LABELS.get(r["icon"], "unknown")}" '
            f'title="{full_state}">\n'
            f'    <span class="phase-icon">{r["icon"]}</span>\n'
            f"    <strong>Phase {r['phase']}</strong>\n"
            f'    <span class="phase-scope">{r["scope"]}</span>\n'
            f'    <span class="phase-state">{truncated}</span>\n'
            f"  </div>\n"
            f"</a>\n"
        )
    cards_html += "</div>\n"

    # Build the board content
    board = (
        f"*Generated from `Phase.md`'s Snapshot table at build time.*\n\n"
        f"**Legend:** ✅ done · 🟡 partial · 🔲 planned · 🔴 open defect · 🔵 blocked · ⛔ withdrawn\n\n"
        f"### Counters\n\n{counter_line}\n\n"
        f"### Current status\n\n{status}\n\n"
        f"### Phase board\n\n{cards_html}\n\n"
    )

    if latest:
        board += f"### Latest session\n\n{latest}\n\n"

    markdown = markdown.replace("{{ progress_board }}", board)
    return markdown
