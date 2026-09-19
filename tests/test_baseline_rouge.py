"""Tests for Baseline ROUGE-L verifier — Phase 3a.

Checks:
- Protocol conformance
- Toy strings: identical, partial, completely disjoint
- Field selection: precision, recall, fmeasure
- Returns validated VerifierResult
"""

from __future__ import annotations

from src.filters.base import Verifier
from src.filters.baseline_rouge import RougeLVerifier


def test_protocol_conformance() -> None:
    verifier = RougeLVerifier()
    assert isinstance(verifier, Verifier)
    assert verifier.name == "rouge"


def test_toy_strings_precision() -> None:
    verifier = RougeLVerifier(field="precision")
    verifier.load()

    # Identical context and answer -> precision = 1.0
    context = "Paracetamol reduces fever and relieves pain."
    answer_exact = "Paracetamol reduces fever and relieves pain."
    res_exact = verifier.score(context, answer_exact, pair_id="p1")
    assert res_exact.score == 1.0
    assert res_exact.details["rougeL_precision"] == 1.0

    # Answer contained in context -> precision = 1.0
    answer_sub = "Paracetamol relieves pain."
    res_sub = verifier.score(context, answer_sub, pair_id="p2")
    assert res_sub.score == 1.0

    # Completely disjoint words -> precision = 0.0
    answer_disjoint = "Zebras graze quietly under blue skies."
    res_disjoint = verifier.score(context, answer_disjoint, pair_id="p3")
    assert res_disjoint.score == 0.0


def test_field_selection() -> None:
    context = "The quick brown fox jumps over the lazy dog."
    answer = "The quick brown fox."

    v_prec = RougeLVerifier(field="precision")
    v_rec = RougeLVerifier(field="recall")
    v_f1 = RougeLVerifier(field="fmeasure")

    res_p = v_prec.score(context, answer)
    res_r = v_rec.score(context, answer)
    res_f = v_f1.score(context, answer)

    # All words of answer are in context -> precision = 1.0
    assert res_p.score == 1.0
    # Context has 9 words, answer has 4 -> recall < 1.0
    assert res_r.score < 1.0
    # F-measure between precision and recall
    assert res_f.score < res_p.score
    assert res_f.score > res_r.score
