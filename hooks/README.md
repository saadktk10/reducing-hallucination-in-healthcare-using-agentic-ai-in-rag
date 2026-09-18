# Build Hooks (`hooks/`)

This directory contains Python hooks executed by MkDocs during the documentation build lifecycle (configured in `mkdocs.yml`).

## Hook Modules

| Hook | Lifecycle Events | Responsibility |
| :--- | :--- | :--- |
| `build_stamp.py` | `on_config`, `on_pre_build`, `on_page_markdown`, `on_post_page` | Extracts git commit SHA and UTC build timestamp; synchronizes figures from `results/figures/` to `docs/assets/figures/`; injects build stamp and research disclaimer footer into HTML. |
| `tiles.py` | `on_page_markdown` | Replaces `{{ tile:<key> }}` and `{{ tile_pair:<a>|<b> }}` with HTML metric tiles reading from `results/site/numbers_of_record.json`. Unproduced metrics render as `pending (Phase N)`. |
| `progress.py` | `on_page_markdown` | Parses the `## Snapshot` table in root `Phase.md` into responsive phase cards, status counters, and current status display for `docs/progress.md`. Enforces status icon presence. |
| `external_numbers.py` | `on_page_markdown` | Replaces `{{ external_numbers }}` with a comparative markdown table from `paper/external_numbers.json` (filtered strictly to rows where `human_verified == true`). |

## Guidelines

- Hooks must remain lightweight and standard-library dependent (plus PyYAML). They do not load heavy ML or scientific packages (PyTorch, Transformers).
- Any malformed JSON or missing required fields must raise an exception to fail `mkdocs build --strict` loudly.

---
*Research prototype. Not for clinical use.*
