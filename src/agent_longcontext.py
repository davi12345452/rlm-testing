"""The long-context control arm.

This arm puts the **entire corpus** in a single prompt and asks for the answer in one call. It is
not a strawman and it is not an afterthought — it is the control that makes the central claim
falsifiable.

The recursive agent's advantage could have two very different causes:

1. **Access.** Retrieval simply never showed the model the passage that decides the case.
2. **Reasoning discipline.** The model saw everything and still failed to notice that a provision
   had been superseded.

Give a model the whole corpus and the access explanation disappears. Whatever gap remains between
this arm and the recursive agent is attributable to *how* the corpus was worked through, not to
*whether* the text was available — and whatever gap disappears was never about recursion.

On a corpus that outgrows the context window this arm stops being runnable, which is the regime the
recursive architecture is actually designed for. Reporting it here, where it is still feasible, is
what keeps the comparison honest at this scale.
"""

from __future__ import annotations

import time

from .agent_base import LEGAL_GUIDANCE, AgentResult, Case
from .config import RunConfig
from .corpus import Corpus
from .llm import Accountant, LLMClient
from .schemas import ANSWER_SCHEMA

SYSTEM = (
    LEGAL_GUIDANCE
    + """
You are given the complete corpus. Everything you need is present; nothing outside it is relevant.
Work through it carefully before answering.
"""
)


class LongContextAgent:
    name = "longcontext"

    def __init__(self, client: LLMClient, config: RunConfig, corpus: Corpus) -> None:
        self.client = client
        self.config = config
        self.corpus = corpus

    def answer(self, case: Case) -> AgentResult:
        started = time.perf_counter()
        accountant = Accountant()

        try:
            prompt = f"CORPUS COMPLETO:\n{self.corpus.full_text()}\n\n{case.prompt_block()}"
            response = self.client.generate(
                model=self.config.models.agent,
                prompt=prompt,
                system=SYSTEM,
                schema=ANSWER_SCHEMA,
                temperature=self.config.temperature,
                max_output_tokens=self.config.max_output_tokens,
            )
            accountant.record("longcontext:answer", response.usage)
            parsed = response.parsed if isinstance(response.parsed, dict) else {}
            error = None
        except Exception as exc:  # noqa: BLE001
            parsed, error = {}, f"{type(exc).__name__}: {exc}"

        return AgentResult(
            agent=self.name,
            case_id=case.id,
            answer=str(parsed.get("answer", "")).strip(),
            citations=[str(c).strip().strip("[]").strip() for c in parsed.get("citations", []) or []],
            reasoning=str(parsed.get("reasoning", "")).strip(),
            steps=1,
            wall_seconds=time.perf_counter() - started,
            usage=accountant.to_dict(),
            trace=[],
            # By construction every section was in front of the model, so retrieval recall is 1.0
            # for this arm. Recording it explicitly keeps the metric comparable across arms.
            retrieved=sorted(s.key for s in self.corpus.sections),
            error=error,
        )
