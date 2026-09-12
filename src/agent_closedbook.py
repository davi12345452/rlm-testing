"""The closed-book control: no corpus at all.

This arm exists to answer a question that decides whether the rest of the benchmark means anything:
**is the score measuring reasoning over the corpus, or the model's own memory of Brazilian labour
law?**

Frontier models have read the CLT, the TST súmulas and the major constitutional rulings. If a model
with no retrieval, no navigation and no context still answers these cases correctly, then every
other arm is partly measuring recall from pre-training, and any gap between architectures is
measured on top of a prior that already knows the answer.

Almost no published RAG comparison runs this control. It is eleven API calls, and without it a
benchmark on well-known public law cannot support a claim about architectures at all.

The gap between this arm and the others is the **corpus-attributable** portion of performance. It is
the denominator every other number in the report should be read against.
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
You have no corpus and no retrieval. Answer from your own knowledge of Brazilian labour law.

Cite the provisions you rely on in the usual form (for example: CLT art. 483, Súmula 13 TST, STF ADI
5766). If you are unsure whether a rule is still in force, say so.
"""
)


class ClosedBookAgent:
    name = "closedbook"

    def __init__(self, client: LLMClient, config: RunConfig, corpus: Corpus) -> None:
        self.client = client
        self.config = config
        self.corpus = corpus

    def answer(self, case: Case) -> AgentResult:
        started = time.perf_counter()
        accountant = Accountant()

        try:
            response = self.client.generate(
                model=self.config.models.agent,
                prompt=case.prompt_block(),
                system=SYSTEM,
                schema=ANSWER_SCHEMA,
                temperature=self.config.temperature,
                max_output_tokens=self.config.max_output_tokens,
            )
            accountant.record("closedbook:answer", response.usage)
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
            # Nothing was retrieved, by construction. Retrieval recall is 0.0 for this arm and that
            # is the point: whatever it scores, it scored without seeing the corpus.
            retrieved=[],
            error=error,
        )
