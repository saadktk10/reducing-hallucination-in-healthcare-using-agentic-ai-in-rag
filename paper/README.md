# Paper Artifacts (`paper/`)

This directory houses the academic manuscript draft, comparative literature benchmarks, and publication-ready assets.

## Contents

| Path | Description |
| :--- | :--- |
| `manuscript/` | Markdown draft of each section (`00-abstract.md` through `06-conclusion.md`). Rendered live on the project website under the Manuscript tab. |
| `external_numbers.json` | Comparison metrics extracted from published literature (Self-MedRAG, Luna, MiniCheck). |

## Verification Workflow for External Numbers

Candidate comparison rows from the literature review are stored in `external_numbers.json` with `"human_verified": false`. Only a researcher may switch the flag to `true` after checking the primary paper source. Unverified rows are excluded from public site tables (Website_Prompt.md §5.1).

---
*Research prototype. Not for clinical use.*
