"""Tests for the deterministic half of scoring.

The judge is a model and cannot be unit-tested. Everything around it can be, and must be: citation
precision and recall are the numbers a sceptical reader will check first.
"""

from __future__ import annotations

import pytest

from src.agent_base import AgentResult, Case
from src.config import RunConfig
from src.corpus import Corpus
from src.evaluator import Evaluator, aggregate


@pytest.fixture(scope="module")
def evaluator() -> Evaluator:
    # An offline client is never called: only the deterministic scorers are exercised here.
    from src.llm import LLMClient

    return Evaluator(LLMClient(offline=True), RunConfig(offline=True), Corpus.load())


def _case(**gold) -> Case:
    return Case(id="t", title="t", facts="f", question="q", gold=gold)


def _result(citations, retrieved=()) -> AgentResult:
    return AgentResult(agent="a", case_id="t", answer="", citations=list(citations), retrieved=list(retrieved))


def test_perfect_citations_score_one(evaluator: Evaluator) -> None:
    case = _case(required_citations=["CLT art. 483", "Súmula 13 TST"])
    score = evaluator.score(case, _result(["CLT art. 483", "Súmula 13 TST"]))
    assert score.citation_precision == 1.0
    assert score.citation_recall == 1.0
    assert score.citation_f1 == 1.0


def test_supporting_citations_do_not_hurt_precision(evaluator: Evaluator) -> None:
    """Citing a genuinely relevant companion provision is good lawyering, not noise."""
    case = _case(required_citations=["CLT art. 483"], supporting_citations=["CLT art. 477 §6º e §8º"])
    score = evaluator.score(case, _result(["CLT art. 483", "CLT art. 477 §6º e §8º"]))
    assert score.citation_precision == 1.0
    assert score.citation_recall == 1.0


def test_irrelevant_citation_lowers_precision(evaluator: Evaluator) -> None:
    case = _case(required_citations=["CLT art. 483"])
    score = evaluator.score(case, _result(["CLT art. 483", "CLT art. 62"]))
    assert score.citation_precision == pytest.approx(0.5)


def test_distractor_is_counted(evaluator: Evaluator) -> None:
    case = _case(required_citations=["CLT art. 483"], distractor_citations=["CLT art. 482"])
    score = evaluator.score(case, _result(["CLT art. 483", "CLT art. 482"]))
    assert score.distractor_cited == 1


def test_invented_authority_is_reported_not_scored(evaluator: Evaluator) -> None:
    case = _case(required_citations=["CLT art. 483"])
    score = evaluator.score(case, _result(["CLT art. 483", "CLT art. 9999"]))
    assert score.citations_outside_corpus == ["CLT art. 9999"]
    # It must not silently count as a correct citation.
    assert score.citation_precision == 1.0
    assert score.citation_recall == 1.0


def test_retrieval_recall_is_independent_of_the_answer(evaluator: Evaluator) -> None:
    """Seeing the governing provision and citing it are different things, measured separately."""
    case = _case(required_citations=["CLT art. 483", "Súmula 13 TST"])
    score = evaluator.score(case, _result(["CLT art. 483"], retrieved=["CLT art. 483"]))
    assert score.retrieval_recall == pytest.approx(0.5)
    assert score.citation_recall == pytest.approx(0.5)


def test_aggregate_flags_correct_but_ungrounded() -> None:
    from src.evaluator import CaseScore

    scores = [
        CaseScore(agent="x", case_id="1", verdict="correct", retrieval_recall=0.5),
        CaseScore(agent="x", case_id="2", verdict="correct", retrieval_recall=1.0),
    ]
    assert aggregate(scores)["x"]["correct_but_ungrounded"] == 1
