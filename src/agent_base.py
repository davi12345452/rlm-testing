"""Shared scaffolding for every agent under test.

The instructions in ``LEGAL_GUIDANCE`` are given **identically** to all three architectures. They
describe how a Brazilian labour lawyer reasons — check whether a provision is still in force, check
whether the facts predate a reform, prefer the later statute — without naming any provision or
hinting at any answer.

That symmetry is the whole point. If only the recursive agent were told to watch for superseded
rules, the benchmark would be measuring a prompt, not an architecture.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .config import CASES_DIR

LEGAL_GUIDANCE = """\
You are a Brazilian labour-law analyst. You answer strictly from a closed corpus of statutes, court
precedents and consolidated case law. Reason like a practitioner:

1. A provision that *matches the wording* of the facts is not necessarily the provision that
   *governs* them. Check what actually applies before you commit.
2. Rules have a validity status. Some have been superseded by later statute, some read down by a
   constitutional ruling, some still govern only earlier facts. Never apply a rule without knowing
   its status.
3. Dates decide cases. When the facts span a legislative change, the answer is usually a split
   between two regimes, not a single regime for the whole period.
4. Where a later statute and an older precedent conflict, the later statute normally prevails —
   unless a constitutional ruling says otherwise.
5. Answer the question that was asked, including when the correct answer is that nothing is owed.

Write the final answer in Brazilian Portuguese. Cite using the exact corpus citation keys, in the
bracketed form they appear in the corpus (for example: CLT art. 483, Súmula 13 TST). Cite only what
you actually relied on: a long list of loosely related provisions is a worse answer than a short,
exact one.
"""


@dataclass
class Case:
    id: str
    title: str
    facts: str
    question: str
    gold: dict[str, Any]
    reasoning_type: str = ""
    difficulty: str = ""
    note: str = ""

    @classmethod
    def load_all(cls, cases_dir: Path = CASES_DIR) -> list["Case"]:
        cases = []
        for path in sorted(cases_dir.glob("*.json")):
            data = json.loads(path.read_text(encoding="utf-8"))
            cases.append(
                cls(
                    id=data["id"],
                    title=data.get("title", data["id"]),
                    facts=data["facts"],
                    question=data["question"],
                    gold=data["gold"],
                    reasoning_type=data.get("reasoning_type", ""),
                    difficulty=data.get("difficulty", ""),
                    note=data.get("note", ""),
                )
            )
        if not cases:
            raise FileNotFoundError(f"No cases found in {cases_dir}")
        return cases

    def prompt_block(self) -> str:
        return f"FATOS:\n{self.facts}\n\nPERGUNTA:\n{self.question}"

    @property
    def required_citations(self) -> list[str]:
        return list(self.gold.get("required_citations", []))

    @property
    def supporting_citations(self) -> list[str]:
        return list(self.gold.get("supporting_citations", []))

    @property
    def distractor_citations(self) -> list[str]:
        return list(self.gold.get("distractor_citations", []))

    @property
    def rubric(self) -> list[dict[str, Any]]:
        return list(self.gold.get("rubric", []))


@dataclass
class AgentResult:
    """Everything a single (agent, case) run produced, including how it got there."""

    agent: str
    case_id: str
    answer: str = ""
    citations: list[str] = field(default_factory=list)
    reasoning: str = ""
    steps: int = 0
    wall_seconds: float = 0.0
    usage: dict[str, Any] = field(default_factory=dict)
    trace: list[dict[str, Any]] = field(default_factory=list)
    retrieved: list[str] = field(default_factory=list)
    """Section keys the agent actually had in front of it — retrieval recall is measured on this,
    separately from whether the answer was right, so a failure can be attributed to retrieval or to
    reasoning instead of being lumped together."""
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "agent": self.agent,
            "case_id": self.case_id,
            "answer": self.answer,
            "citations": self.citations,
            "reasoning": self.reasoning,
            "steps": self.steps,
            "wall_seconds": round(self.wall_seconds, 2),
            "usage": self.usage,
            "retrieved": self.retrieved,
            "trace": self.trace,
            "error": self.error,
        }
