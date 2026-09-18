# Notebooks (`notebooks/`)

This directory is reserved for scratch analysis, data exploration, and visual prototyping using JupyterLab.

## Non-Negotiable Rules

- **Exploration Only (Rule R4.5)**: Jupyter notebooks are strictly for prototyping and manual exploratory analysis.
- **Never the Source of Record**: No reported numbers, benchmark tables, or final figures may originate from a notebook run. All reported results must be generated via reproducible CLI scripts in `src/` or `scripts/` with recorded manifests.
- **Do Not Commit Large Outputs**: Strip cell execution outputs before committing `.ipynb` files to git, or keep exploration files local.

---
*Research prototype. Not for clinical use.*
