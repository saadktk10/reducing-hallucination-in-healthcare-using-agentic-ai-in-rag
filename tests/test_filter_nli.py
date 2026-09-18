"""Tests for Filter B (NLI cross-encoder) — Phase 3.

Checks:
- Label index read from model.config.id2label (Rule R5.5)
- min-of-max aggregation on a fake score matrix
- Chunking stays under 512 tokens
"""
