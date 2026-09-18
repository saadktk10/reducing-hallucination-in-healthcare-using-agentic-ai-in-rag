"""Tests for Filter A (API judge) — Phase 3.

Checks:
- Parser handles fences, extra text, bad JSON
- One retry only on parse failure
- Cache key stable
- Timing mode skips cache reads (mocked client)
"""
