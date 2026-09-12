"""Scoring: deterministic metrics first, a constrained judge second.

LLM-as-judge is the only practical way to grade a paragraph of legal reasoning, and it is also the
easiest part of a benchmark to get wrong. Three safeguards are applied here:

1. **The judge is not the model under test.** Models systematically prefer their own outputs;
   separating the roles costs nothing and removes the objection.
2. **The judge answers a fixed checklist, not an open question.** Rubric item ids are baked into the
   response schema, so it cannot invent a criterion, skip one, or drift between cases.
3. **The judge never grades the part that can be measured.** Citations are scored deterministically
   against canonical keys. If the two disagree — a fluent answer that cites a superseded rule — the
   disagreement is visible instead of being averaged away.

Retrieval recall is measured separately from answer quality, so a failure can be attributed:
did the agent never see the governing provision, or did it see it and reason past it?
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from .agent_base import AgentResult, Case
from .config import RunConfig
from .corpus import Corpus
from .llm import Accountant, LLMClient
from .schemas import judge_schema

VERDICT_SCORE = {"correct": 1.0, "partially_correct": 0.5, "incorrect": 0.0}
ITEM_SCORE = {"met": 1.0, "partial": 0.5, "missed": 0.0}

JUDGE_SYSTEM = """\
You are grading an answer to a Brazilian labour-law question against a reference answer and a fixed
rubric. You are strict, literal and consistent.

Rules:
- Grade only against the rubric items you are given. Do not invent criteria.
- An item is 'met' only if the answer actually states or clearly entails it. Mentioning a provision
  without drawing its consequence is 'partial', not 'met'.
- Style, length and fluency are irrelevant. A terse correct answer outranks an eloquent wrong one.
- 'contradicts_gold' is true when the answer's bottom line is the opposite of the reference
  answer's — for example granting a claim the reference denies.
- The overall verdict is about the bottom line, not about how many rubric items were hit.
"""


@dataclass
class CaseScore:
    """Everything measured for one (agent, case) pair."""

    agent: str
    case_id: str
    reasoning_type: str = ""
    difficulty: str = ""

    verdict: str = "incorrect"
    verdict_score: float = 0.0
    contradicts_gold: bool = False
    rubric_score: float = 0.0
    rubric_items: list[dict[str, Any]] = field(default_factory=list)

    citation_precision: float = 0.0
    citation_recall: float = 0.0
    citation_f1: float = 0.0
    distractor_cited: int = 0
    citations_outside_corpus: list[str] = field(default_factory=list)

    retrieval_recall: float = 0.0
    steps: int = 0
    wall_seconds: float = 0.0
    total_tokens: int = 0
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "agent": self.agent,
            "case_id": self.case_id,
            "reasoning_type": self.reasoning_type,
            "difficulty": self.difficulty,
            "verdict": self.verdict,
            "verdict_score": round(self.verdict_score, 3),
            "contradicts_gold": self.contradicts_gold,
            "rubric_score": round(self.rubric_score, 3),
            "rubric_items": self.rubric_items,
            "citation_precision": round(self.citation_precision, 3),
            "citation_recall": round(self.citation_recall, 3),
            "citation_f1": round(self.citation_f1, 3),
            "distractor_cited": self.distractor_cited,
            "citations_outside_corpus": self.citations_outside_corpus,
            "retrieval_recall": round(self.retrieval_recall, 3),
            "steps": self.steps,
            "wall_seconds": round(self.wall_seconds, 2),
            "total_tokens": self.total_tokens,
            "error": self.error,
        }


class Evaluator:
    def __init__(self, client: LLMClient, config: RunConfig, corpus: Corpus) -> None:
        self.client = client
        self.config = config
        self.corpus = corpus
        self.accountant = Accountant()

    def score(self, case: Case, result: AgentResult) -> CaseScore:
        score = CaseScore(
            agent=result.agent,
            case_id=case.id,
            reasoning_type=case.reasoning_type,
            difficulty=case.difficulty,
            steps=result.steps,
            wall_seconds=result.wall_seconds,
            total_tokens=int(result.usage.get("total", {}).get("total_tokens", 0)),
            error=result.error,
        )

        self._score_citations(case, result, score)
        self._score_retrieval(case, result, score)

        if result.answer.strip():
            self._judge(case, result, score)
        return score

    # --------------------------------------------------------- deterministic

    def _score_citations(self, case: Case, result: AgentResult, score: CaseScore) -> None:
        required = {self.corpus.resolve(c) or c for c in case.required_citations}
        supporting = {self.corpus.resolve(c) or c for c in case.supporting_citations}
        distractors = {self.corpus.resolve(c) or c for c in case.distractor_citations}
        acceptable = required | supporting

        resolved: set[str] = set()
        for raw in result.citations:
            key = self.corpus.resolve(raw)
            if key is None:
                # A citation that does not resolve to any corpus key is an invented authority --
                # the failure mode that matters most in this domain, so it is reported verbatim
                # rather than folded into a score.
                score.citations_outside_corpus.append(raw)
            else:
                resolved.add(key)

        if resolved:
            score.citation_precision = len(resolved & acceptable) / len(resolved)
        if required:
            score.citation_recall = len(resolved & required) / len(required)
        if score.citation_precision + score.citation_recall > 0:
            score.citation_f1 = (
                2
                * score.citation_precision
                * score.citation_recall
                / (score.citation_precision + score.citation_recall)
            )
        score.distractor_cited = len(resolved & distractors)

    def _score_retrieval(self, case: Case, result: AgentResult, score: CaseScore) -> None:
        """Did the governing provisions ever reach the model's context?

        Separating this from answer quality is what turns 'the baseline lost' into a diagnosis.
        """
        required = {self.corpus.resolve(c) or c for c in case.required_citations}
        if not required:
            score.retrieval_recall = 1.0
            return
        seen = {self.corpus.resolve(k) or k for k in result.retrieved}
        score.retrieval_recall = len(required & seen) / len(required)

    # ---------------------------------------------------------------- judge

    def _judge(self, case: Case, result: AgentResult, score: CaseScore) -> None:
        rubric = case.rubric
        if not rubric:
            return
        rubric_ids = [str(item["id"]) for item in rubric]

        rubric_block = "\n".join(
            f"- {item['id']} (weight {item.get('weight', 1)}): {item['claim']}" for item in rubric
        )
        prompt = f"""\
FACTS:
{case.facts}

QUESTION:
{case.question}

REFERENCE ANSWER (gold):
{case.gold.get("answer", "")}

RUBRIC:
{rubric_block}

CANDIDATE ANSWER TO GRADE:
{result.answer}

CITATIONS GIVEN BY THE CANDIDATE:
{", ".join(result.citations) or "none"}
"""

        response = self.client.generate(
            model=self.config.models.judge,
            prompt=prompt,
            system=JUDGE_SYSTEM,
            schema=judge_schema(rubric_ids),
            temperature=0.0,
            max_output_tokens=self.config.max_output_tokens,
        )
        self.accountant.record("judge", response.usage)

        parsed = response.parsed if isinstance(response.parsed, dict) else {}
        items = parsed.get("items") or []
        by_id = {str(i.get("id")): str(i.get("verdict", "missed")) for i in items if isinstance(i, dict)}

        total_weight = sum(float(item.get("weight", 1)) for item in rubric) or 1.0
        earned = sum(
            float(item.get("weight", 1)) * ITEM_SCORE.get(by_id.get(str(item["id"]), "missed"), 0.0)
            for item in rubric
        )
        score.rubric_score = earned / total_weight
        score.rubric_items = [
            {
                "id": str(item["id"]),
                "weight": item.get("weight", 1),
                "claim": item["claim"],
                "verdict": by_id.get(str(item["id"]), "missed"),
            }
            for item in rubric
        ]
        score.verdict = str(parsed.get("verdict", "incorrect"))
        score.verdict_score = VERDICT_SCORE.get(score.verdict, 0.0)
        score.contradicts_gold = bool(parsed.get("contradicts_gold", False))


def aggregate(scores: list[CaseScore]) -> dict[str, dict[str, Any]]:
    """Per-agent means, plus the breakdowns that actually explain a result."""
    by_agent: dict[str, list[CaseScore]] = {}
    for score in scores:
        by_agent.setdefault(score.agent, []).append(score)

    summary: dict[str, dict[str, Any]] = {}
    for agent, agent_scores in by_agent.items():
        n = len(agent_scores)
        by_type: dict[str, list[float]] = {}
        for score in agent_scores:
            by_type.setdefault(score.reasoning_type or "unspecified", []).append(score.rubric_score)

        summary[agent] = {
            "cases": n,
            "verdict_accuracy": _mean(s.verdict_score for s in agent_scores),
            "rubric_score": _mean(s.rubric_score for s in agent_scores),
            "fully_correct": sum(1 for s in agent_scores if s.verdict == "correct"),
            "contradicts_gold": sum(1 for s in agent_scores if s.contradicts_gold),
            "citation_precision": _mean(s.citation_precision for s in agent_scores),
            "citation_recall": _mean(s.citation_recall for s in agent_scores),
            "citation_f1": _mean(s.citation_f1 for s in agent_scores),
            "retrieval_recall": _mean(s.retrieval_recall for s in agent_scores),
            "distractor_citations": sum(s.distractor_cited for s in agent_scores),
            "citations_outside_corpus": sum(len(s.citations_outside_corpus) for s in agent_scores),
            # The failure mode that a headline accuracy number cannot show: the right bottom line
            # reached without ever seeing all the provisions that produce it. In a legal setting an
            # ungrounded correct answer is not a success, it is an unfalsifiable one.
            "correct_but_ungrounded": sum(
                1 for s in agent_scores if s.verdict == "correct" and s.retrieval_recall < 1.0
            ),
            "mean_steps": _mean(float(s.steps) for s in agent_scores),
            "mean_wall_seconds": _mean(s.wall_seconds for s in agent_scores),
            "total_tokens": sum(s.total_tokens for s in agent_scores),
            "mean_tokens_per_case": _mean(float(s.total_tokens) for s in agent_scores),
            "errors": sum(1 for s in agent_scores if s.error),
            "rubric_by_reasoning_type": {k: _mean(v) for k, v in sorted(by_type.items())},
        }
    return summary


def _mean(values) -> float:
    items = list(values)
    return round(sum(items) / len(items), 4) if items else 0.0


def load_scores(path) -> list[dict[str, Any]]:
    return json.loads(open(path, encoding="utf-8").read())["scores"]
