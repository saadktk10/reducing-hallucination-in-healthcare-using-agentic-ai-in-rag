"""Build stamp hook: injects commit SHA, UTC build time, and clinical-use notice.

Also copies results/figures/* into docs/assets/figures/ at pre-build so
figures are never stale (Website_Prompt.md §6).
"""

import os
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

_BUILD_SHA = ""
_BUILD_TIME = ""


def _get_sha() -> str:
    sha = os.environ.get("GITHUB_SHA", "")
    if sha:
        return sha[:7]
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, check=True, timeout=5,
        )
        return result.stdout.strip()
    except Exception:
        return "unknown"


def on_config(config, **kwargs):
    """Capture build metadata at config time."""
    global _BUILD_SHA, _BUILD_TIME
    _BUILD_SHA = _get_sha()
    _BUILD_TIME = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    return config


def on_pre_build(config, **kwargs):
    """Copy results/figures/ into docs/assets/figures/ so images are fresh."""
    src = Path("results/figures")
    dst = Path("docs/assets/figures")
    dst.mkdir(parents=True, exist_ok=True)

    if src.exists():
        for f in src.iterdir():
            if f.is_file() and f.suffix in (".png", ".pdf", ".svg"):
                shutil.copy2(f, dst / f.name)


def on_page_markdown(markdown, page, config, files, **kwargs):
    """Replace build stamp placeholders."""
    markdown = markdown.replace("{{ build_sha }}", _BUILD_SHA)
    markdown = markdown.replace("{{ build_time }}", _BUILD_TIME)
    return markdown


def on_post_page(output, page, config, **kwargs):
    """Inject the footer notice into every page's HTML."""
    notice = (
        f'<div class="build-stamp">'
        f'Commit <code>{_BUILD_SHA}</code> | Built {_BUILD_TIME} | '
        f'<strong>Research prototype. Not for clinical use.</strong>'
        f'</div>'
    )
    if "</body>" in output:
        output = output.replace("</body>", f"{notice}</body>")
    return output
