"""Tests for the corpus layer.

These run offline and touch no API. They guard the two things that would silently corrupt a result:
a broken cross-reference edge (which removes the path the recursive agent is supposed to follow) and
a sloppy citation resolver (which would inflate the one metric that has to be beyond doubt).
"""

from __future__ import annotations

import pytest

from src.corpus import Corpus


@pytest.fixture(scope="module")
def corpus() -> Corpus:
    return Corpus.load()


def test_corpus_loads_documents_and_sections(corpus: Corpus) -> None:
    stats = corpus.stats()
    assert stats["documents"] >= 3
    assert stats["sections"] >= 40
    assert stats["cross_ref_edges"] > 0


def test_every_cross_reference_resolves(corpus: Corpus) -> None:
    """A dangling edge is the difference between measuring an architecture and measuring a typo."""
    for section in corpus.sections:
        for ref in section.cross_refs:
            assert ref in corpus.by_key, f"[{section.key}] points at missing [{ref}]"


def test_section_keys_are_unique(corpus: Corpus) -> None:
    keys = [s.key for s in corpus.sections]
    assert len(keys) == len(set(keys))


@pytest.mark.parametrize(
    ("written", "expected"),
    [
        ("CLT art. 483", "CLT art. 483"),
        ("art. 483 da CLT", "CLT art. 483"),
        ("artigo 62 da CLT", "CLT art. 62"),
        ("Súmula 13 do TST", "Súmula 13 TST"),
        ("ADI 5766", "STF ADI 5766"),
        ("ADPF 323", "STF ADPF 323"),
        ("art. 468, §2º, CLT", "CLT art. 468"),
        ("parágrafo 2º do art. 74 da CLT", "CLT art. 74 §2º"),
    ],
)
def test_resolve_accepts_natural_citation_forms(corpus: Corpus, written: str, expected: str) -> None:
    assert corpus.resolve(written) == expected


@pytest.mark.parametrize("written", ["CLT art. 999", "Súmula 9999 TST", "", "CLT"])
def test_resolve_refuses_to_guess(corpus: Corpus, written: str) -> None:
    """An over-eager resolver would turn invented law into a passing citation score."""
    assert corpus.resolve(written) is None


def test_paragraph_marker_does_not_collide_with_article_number(corpus: Corpus) -> None:
    """'§ 2º' must never be matched against 'art. 2º'."""
    assert corpus.resolve("CLT art. 58 §1º") == "CLT art. 58 §1º"
    assert corpus.resolve("CLT art. 58 §2º") == "CLT art. 58 §2º"
