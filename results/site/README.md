# numbers_of_record.json

Written by `src/site_export.py`, never by hand.

## Schema

```json
{
  "generated_at": "ISO 8601 UTC timestamp",
  "git_sha": "short commit SHA at generation time",
  "numbers": {
    "<tile_key>": {
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

## Tile keys

| Key | Label | Produced in |
| --- | --- | --- |
| `pilot.unsupported_rate` | Unsupported ground truth, 50-row spot-check | Phase 1 |
| `pilot.rouge_auroc` | ROUGE-L AUROC on dev | Phase 1 |
| `exp1.filter_a.f1` | Filter A F1, Exp 1 test | Phase 8 |
| `exp1.filter_b.f1` | Filter B F1, Exp 1 test | Phase 8 |
| `exp1.rouge.f1` | ROUGE-L baseline F1, Exp 1 test | Phase 8 |
| `exp1.filter_a.fnr` | Filter A FNR | Phase 8 |
| `exp1.filter_b.fnr` | Filter B FNR | Phase 8 |
| `exp1.mcnemar_ab.p` | McNemar exact p-value, A vs B | Phase 8 |
| `timing.filter_b.median_ms` | Median latency, Filter B | Phase 5 |
| `timing.filter_a.median_ms` | Median latency, Filter A | Phase 5 |
| `cost.filter_a.per_1k_usd` | Shadow cost per 1,000, Filter A | Phase 5 |
| `exp2.kappa` | Cohen's kappa, annotator agreement | Phase 6 |
| `exp2.filter_a.f1` | Filter A F1 on RAG output | Phase 8 |
| `exp2.filter_b.f1` | Filter B F1 on RAG output | Phase 8 |
| `cross.ranking_agrees` | Benchmark ranking holds on RAG output | Phase 9 |
