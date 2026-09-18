# MedVerify-C

**Local NLI Cross-Encoder vs API-Based LLM-as-a-Judge for Hallucination Verification in Healthcare Agentic RAG**

Muhammad Saad, Rabia Qaiser. Supervisor: Dr. Laeeq Ahmed. UET Peshawar, Jalozai Campus.

---

!!! abstract "Research questions"

    --8<-- "docs/claim.md"

!!! info "Current status"

    Phase 0 in progress. See [Progress](progress.md) for details.

## Numbers of record

<div class="tile-grid" markdown>

{{ tile:pilot.unsupported_rate }}
{{ tile:pilot.rouge_auroc }}
{{ tile:exp1.filter_a.f1 }}
{{ tile:exp1.filter_b.f1 }}
{{ tile:exp1.rouge.f1 }}
{{ tile_pair:exp1.filter_a.fnr|exp1.filter_b.fnr }}
{{ tile:exp1.mcnemar_ab.p }}
{{ tile_pair:timing.filter_b.median_ms|timing.filter_a.median_ms }}
{{ tile:cost.filter_a.per_1k_usd }}
{{ tile:exp2.kappa }}
{{ tile_pair:exp2.filter_a.f1|exp2.filter_b.f1 }}
{{ tile:cross.ranking_agrees }}

</div>

*Every tile is read from `results/site/numbers_of_record.json` at build time. Commit `{{ build_sha }}`, built `{{ build_time }}`. Nothing on this page is typed by hand.*

## Against published results

{{ external_numbers }}

## Where to go

| Section | Description |
| --- | --- |
| [Manuscript](manuscript/index.md) | Living paper draft, one page per section |
| [Architecture](architecture.md) | System design, data flow, and component diagrams |
| [Write-up](writeup/index.md) | Study digests for writing the paper |
| [Progress](progress.md) | Phase board and detailed implementation status |
