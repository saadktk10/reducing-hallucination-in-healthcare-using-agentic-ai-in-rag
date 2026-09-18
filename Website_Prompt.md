# Website_Prompt.md

Paste everything below the line into Antigravity as one task. It builds a project website in the same style as https://ahmadkhanraj01.github.io/adaptishield/ for this study. Run it after Phase 0 (repo scaffold exists). Read `Agent.md`, `Rules.md` (especially section 9), `Architecture.md` section 11, and `Phase.md` first.

---

## Task: build the project website

Build a documentation website for this repository with **MkDocs + Material for MkDocs**, deployed to **GitHub Pages** by GitHub Actions on every push to `main`. The site is a living research record: it shows current results, architecture, phase progress, and the paper draft. It must stay correct without anyone editing it by hand, because every number and every status on it is generated from files in the repository.

### 1. Reference and scope

Match the structure and behaviour of https://ahmadkhanraj01.github.io/adaptishield/ (Home, Architecture, Manuscript, Write-up, Progress). Do not copy its text or claims. The subject here is:

> **Local NLI Cross-Encoder vs API-Based LLM-as-a-Judge for Hallucination Verification in Healthcare Agentic RAG**
> Muhammad Saad, Rabia Qaiser. Supervisor: Dr. Laeeq Ahmed. UET Peshawar, Jalozai Campus.

### 2. Non-negotiable principles

1. **No number is typed by hand on the site.** Every metric comes from a committed JSON file under `results/site/`, read by a build hook. If the file or key is missing, the tile shows `pending` with the phase that will produce it. Never a placeholder number.
2. **Single source of truth.** `Architecture.md`, `Phase.md`, `Design.md`, `Rules.md` stay at the repo root. The site includes them with `pymdownx.snippets`; it never keeps a second copy.
3. **Build stamp on every page footer:** short commit SHA and UTC build time, from `GITHUB_SHA` in CI or `git rev-parse --short HEAD` locally.
4. **`mkdocs build --strict` must pass.** Broken links, missing includes, or a malformed Snapshot table fail the build.
5. **No private data on the site.** Never publish `.env`, `data/`, annotation CSVs, cache files, raw model outputs, or labeled Experiment 2 data (license check pending, Rules R7.3).
6. **Research prototype notice** in the footer of every page: "Research prototype. Not for clinical use."
7. Writing style on generated text: concise, no em dashes, no filler.

### 3. Files to create

```text
mkdocs.yml
requirements-docs.txt           # mkdocs, mkdocs-material, pymdown-extensions (pinned)
.github/workflows/pages.yml
hooks/
├── __init__.py
├── build_stamp.py              # footer: commit SHA + UTC build time
├── tiles.py                    # replaces {{ tile:<key> }} with a rendered tile
├── progress.py                 # parses Phase.md Snapshot table into a phase board
└── external_numbers.py         # renders paper/external_numbers.json (verified rows only)
docs/
├── index.md                    # Home
├── architecture.md             # includes ../Architecture.md
├── design.md                   # includes ../Design.md
├── rules.md                    # includes ../Rules.md
├── progress.md                 # phase board + includes ../Phase.md
├── manuscript/
│   ├── index.md
│   └── 00-abstract.md ... 06-conclusion.md   # includes ../../paper/manuscript/*.md
├── writeup/
│   ├── index.md                # "How to use", copied from writeup/README.md via include
│   └── 00-abstract.md ... 06-conclusion.md   # includes ../../writeup/*.md
├── assets/
│   ├── figures/                # copied from results/figures/ by a hook at build time
│   └── extra.css               # tile grid + phase board styling
└── claim.md                    # the one-sentence claim, written by the researchers
results/site/
├── numbers_of_record.json      # written by src/site_export.py, never by hand
└── README.md                   # schema of the file
paper/
├── external_numbers.json       # published figures, human_verified flag per row
└── manuscript/                 # 00-abstract.md ... 06-conclusion.md
writeup/
├── README.md
└── 00-abstract.md ... 06-conclusion.md
src/site_export.py              # collects metrics from results/<exp>/<run_id>/ into numbers_of_record.json
```

### 4. `mkdocs.yml`

- `site_name`: short project name (ask the researchers; default `MedVerify-C`).
- `site_description`: the research question in one line.
- `repo_url` and `site_url`: from the GitHub repo (ask for the username if unknown).
- Theme: `material`, features `navigation.tabs`, `navigation.sections`, `navigation.top`, `toc.follow`, `search.highlight`, `content.code.copy`. Light and dark palette toggle.
- Markdown extensions: `admonition`, `pymdownx.details`, `pymdownx.superfences` with a `mermaid` custom fence, `pymdownx.snippets` with `base_path: ["."]` and `check_paths: true`, `pymdownx.tabbed`, `tables`, `attr_list`, `md_in_html`, `toc` with `permalink: true`.
- `hooks:` all four files in `hooks/`.
- Nav:

```yaml
nav:
  - Home: index.md
  - Architecture: architecture.md
  - Manuscript: manuscript/
  - Write-up: writeup/
  - Progress: progress.md
  - Reference:
      - Design: design.md
      - Rules: rules.md
```

### 5. Page specifications

#### 5.1 Home (`docs/index.md`)

Top to bottom:

1. **Title and one-line subtitle.** The research question in plain words.
2. **Claim admonition** (`!!! abstract "The one claim"`), included from `docs/claim.md`. Before the researchers write it, this box shows the four research questions from Methodology C section 12 instead, titled "Research questions".
3. **Status admonition**, generated from the `Current status:` line at the top of `Phase.md` (for example "Phase 3 in progress: dev tuning").
4. **Numbers of record**: a grid of tiles. Each tile shows value, a one-line label, `[95% CI]` and `n` where they exist, and the source path in `code`. Tiles, in this order:

| Tile key | Label | Produced in |
| --- | --- | --- |
| `pilot.unsupported_rate` | Unsupported ground truth, 50-row spot-check | Phase 1 |
| `pilot.rouge_auroc` | ROUGE-L AUROC on dev (lexical shortcut check) | Phase 1 |
| `exp1.filter_a.f1` | Filter A (Gemini judge) F1, Exp 1 test | Phase 8 |
| `exp1.filter_b.f1` | Filter B (DeBERTa NLI) F1, Exp 1 test | Phase 8 |
| `exp1.rouge.f1` | ROUGE-L baseline F1, Exp 1 test | Phase 8 |
| `exp1.filter_a.fnr` / `exp1.filter_b.fnr` | Hallucinations passed through (FNR) | Phase 8 |
| `exp1.mcnemar_ab.p` | McNemar exact p, A vs B | Phase 8 |
| `timing.filter_b.median_ms` vs `timing.filter_a.median_ms` | Median latency per verification, B vs A | Phase 5 |
| `cost.filter_a.per_1k_usd` | Shadow cost per 1,000 verifications, Filter A | Phase 5 |
| `exp2.kappa` | Annotator agreement, Cohen's kappa | Phase 6 |
| `exp2.filter_a.f1` / `exp2.filter_b.f1` | F1 on real RAG output (direction check) | Phase 8 |
| `cross.ranking_agrees` | Benchmark ranking holds on RAG output | Phase 9 |

Below the grid, in italics: "Every tile is read from `results/site/numbers_of_record.json` at build time. Commit `<sha>`, built `<UTC time>`. Nothing on this page is typed by hand."

5. **Against published results**: table rendered by `hooks/external_numbers.py` from `paper/external_numbers.json`. Only rows with `"human_verified": true` appear. Columns: published system, setting, metric, value, source link. Candidate rows come from the literature review (Self-MedRAG PubMedQA accuracy with and without NLI verification, Luna cost and latency reduction versus GPT-3.5, MiniCheck model size). The agent may add candidate rows with `human_verified: false`; only a researcher flips the flag after reading the primary source. Italic note under the table: none of these is a like-for-like comparison.
6. **Where to go**: a two-column table linking Manuscript, Architecture, Write-up, Progress with one line each.

#### 5.2 Architecture (`docs/architecture.md`)

Short intro sentence, then `--8<-- "Architecture.md"`. All Mermaid diagrams must render. Add a note at the top: "Rendered from `Architecture.md` at build time."

#### 5.3 Manuscript (`docs/manuscript/`)

The paper as a living draft, one page per section, each including `paper/manuscript/0N-*.md`. The index page lists sections with a status badge (`draft`, `in review`, `final`) read from front matter `status:` in each file. Tables and figures in the manuscript are generated files (`results/figures/*.png`, `results/<exp>/<run_id>/tables/*.md`) included by path, not pasted. Prose is written or approved by the researchers.

#### 5.4 Write-up (`docs/writeup/`)

Study digests the paper is written from, one file per paper section, created in Phase 10. Every bullet follows:

```
- <statement> : <value> [95% CI] (n=<n>, `results/...`) [meaning: <same thing in the simplest words>]
```

Plus two rules pages: `writeup/rules/general-research-paper-rules.md` and `writeup/rules/conference-or-journal-rules.md` (target venue chosen by supervisor). The `How to use` page explains: read the digest, explain each bullet without looking, write in your own words, keep numbers exact, write the abstract last.

#### 5.5 Progress (`docs/progress.md`)

1. Italic line: "Generated from `Phase.md`'s Snapshot table at build time." Then the status legend: ✅ done · 🟡 partial · 🔲 planned · 🔴 open defect · 🔵 blocked · ⛔ withdrawn.
2. **Counters**: number of phases per status, e.g. **4** ✅ done, **1** 🟡 partial, **7** 🔲 planned.
3. **Phase board**: one card per Snapshot row (phase ID, status icon, scope, first 120 characters of the state text), each linking to that phase's heading anchor in the rendered `Phase.md`.
4. **Latest session**: the newest entry from `Phase.md`'s Session log.
5. Horizontal rule, then "Below is `Phase.md` from the repository, rendered as-is." and `--8<-- "Phase.md"`.

`hooks/progress.py` parses the table under the `## Snapshot` heading. Required columns: `Phase | Scope | State`. The state cell must start with a legend icon. If the table is missing or a row has no icon, raise an error so `--strict` fails.

### 6. Build hooks

- `tiles.py` (`on_page_markdown`): find `{{ tile:<key> }}` and `{{ tile_pair:<key_a>|<key_b> }}`, look up keys in `results/site/numbers_of_record.json`, render HTML tiles. Missing key renders a grey tile reading `pending (Phase N)`, using `produced_in` from a static key registry inside the hook. Never raise on missing numbers; raise on malformed JSON.
- `progress.py` (`on_page_markdown` for `progress.md` only): as specified in 5.5.
- `external_numbers.py`: as specified in 5.1.
- `build_stamp.py` (`on_config` + `on_post_page`): inject SHA, build time, and the clinical-use notice into the footer. Also copy `results/figures/*` into `docs/assets/figures/` at `on_pre_build` so figures are never stale.

### 7. `numbers_of_record.json` schema (written by `src/site_export.py`)

```json
{
  "generated_at": "2026-01-01T00:00:00Z",
  "git_sha": "abc1234",
  "numbers": {
    "exp1.filter_b.f1": {
      "value": 0.0,
      "display": "0.00",
      "ci": [0.0, 0.0],
      "n": 400,
      "source": "results/exp1/<run_id>/tables/main.csv",
      "run_id": "<run_id>",
      "note": "dev threshold, frozen"
    }
  }
}
```

`src/site_export.py` reads only committed summary tables from the latest valid run folder of each experiment (the one recorded in `results/LATEST.json`). It never recomputes metrics. Add a test that every key in the tile registry is either present or legitimately pending.

### 8. GitHub Actions (`.github/workflows/pages.yml`)

- Trigger: push to `main`, and `workflow_dispatch`.
- Steps: checkout with `fetch-depth: 0`, setup Python 3.12, `pip install -r requirements-docs.txt`, `mkdocs build --strict`, upload with `actions/upload-pages-artifact`, deploy with `actions/deploy-pages`.
- Permissions: `pages: write`, `id-token: write`, `contents: read`.
- The docs build installs **only** `requirements-docs.txt`, not torch or the research stack. Hooks use the standard library plus PyYAML.
- Tell the researchers to set Settings > Pages > Source to "GitHub Actions".

### 9. Style

- Material default fonts. Accent colours: Filter A, Filter B, and ROUGE-L use the same Okabe-Ito colours as the paper figures (Design.md section 10), so a tile and its figure match.
- Tiles: responsive CSS grid, 2 columns on mobile, 4 on desktop, large number, small label, monospace source path.
- Phase cards: status icon, phase ID in bold, scope, truncated state. Hover shows full state.

### 10. Acceptance criteria

- [ ] `mkdocs serve` works locally; `mkdocs build --strict` passes with zero warnings.
- [ ] With an empty `results/site/`, every tile renders `pending` and the build still passes.
- [ ] Editing a State cell in `Phase.md` and pushing changes the Progress board after the Action runs, with no other edit.
- [ ] Deleting the icon from a Snapshot row fails the build.
- [ ] Footer shows the commit SHA, UTC build time, and the not-for-clinical-use notice on every page.
- [ ] No file from `data/` or any `.env` appears in the built `site/` folder (add a CI step that greps for it).
- [ ] All Mermaid diagrams from `Architecture.md` render.
- [ ] Tests for `hooks/progress.py` parsing, tile rendering with missing keys, and `site_export.py`.

### 11. After building

Report in the Agent.md task format, plus: the live site URL, a screenshot description of Home and Progress, and the list of tiles currently `pending`. Then follow the session close procedure in `Rules.md` section 9.
