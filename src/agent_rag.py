"""The retrieval-augmented baseline.

A benchmark is only worth publishing if its baseline is the one a competent engineer would actually
ship. This one is:

* **Overlapping chunks** sized so that a provision and its status metadata stay together, with the
  citation key prefixed onto every chunk so a retrieved fragment is always attributable.
* **A real embedding model with task-typed vectors** — documents embedded as ``RETRIEVAL_DOCUMENT``,
  questions as ``RETRIEVAL_QUERY`` — which is a measurable improvement over embedding both sides the
  same way and is routinely skipped.
* **Maximal Marginal Relevance**, so the top-k is not five paraphrases of the single most similar
  passage. Without MMR, near-duplicate crowding alone would account for part of the gap, and the
  result would say more about the chunker than about retrieval.
* **The same legal instructions and the same output schema** as every other arm.

What it cannot do — by construction, not by neglect — is take a second look. Retrieval happens once,
before any reasoning, and it ranks by similarity to the question. A commencement date or a
constitutional ruling that decides the case while sharing no vocabulary with the facts is invisible
to it. That limitation *is* the hypothesis under test.
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass

from .agent_base import LEGAL_GUIDANCE, AgentResult, Case
from .config import RunConfig
from .corpus import Corpus
from .llm import Accountant, LLMClient
from .schemas import ANSWER_SCHEMA

SYSTEM = (
    LEGAL_GUIDANCE
    + """
You are given a set of passages retrieved from the corpus. Answer from those passages alone.

If the retrieved passages are not sufficient to settle the question — for instance because they
point to a provision you were not given — say so explicitly in your answer rather than guessing.
"""
)


@dataclass
class Chunk:
    section_key: str
    doc_id: str
    text: str


class RAGAgent:
    """Embed, retrieve, answer. One shot."""

    name = "rag"

    def __init__(self, client: LLMClient, config: RunConfig, corpus: Corpus) -> None:
        self.client = client
        self.config = config
        self.corpus = corpus
        self._chunks: list[Chunk] | None = None
        self._vectors: list[list[float]] | None = None

    # ------------------------------------------------------------- indexing

    def _build_index(self) -> tuple[list[Chunk], list[list[float]]]:
        if self._chunks is not None and self._vectors is not None:
            return self._chunks, self._vectors

        chunks: list[Chunk] = []
        for section in self.corpus.sections:
            for piece in _split(
                section.text,
                self.config.rag.chunk_chars,
                self.config.rag.chunk_overlap,
            ):
                # Prefixing the key keeps every fragment attributable: a retrieved chunk that cannot
                # be cited is worse than useless in a legal setting.
                chunks.append(
                    Chunk(
                        section_key=section.key,
                        doc_id=section.doc_id,
                        text=f"[{section.key}] ({section.doc_id})\n{piece}",
                    )
                )

        vectors = self.client.embed(
            model=self.config.models.embedding,
            texts=[c.text for c in chunks],
            task_type="RETRIEVAL_DOCUMENT",
        )
        self._chunks, self._vectors = chunks, vectors
        return chunks, vectors

    def retrieve(self, query: str) -> list[Chunk]:
        chunks, vectors = self._build_index()
        query_vector = self.client.embed(
            model=self.config.models.embedding,
            texts=[query],
            task_type="RETRIEVAL_QUERY",
        )[0]

        scores = [_cosine(query_vector, v) for v in vectors]
        k = min(self.config.rag.top_k, len(chunks))

        if not self.config.rag.use_mmr:
            order = sorted(range(len(chunks)), key=lambda i: scores[i], reverse=True)[:k]
            return [chunks[i] for i in order]

        return [chunks[i] for i in _mmr(vectors, scores, k, self.config.rag.mmr_lambda)]

    # --------------------------------------------------------------- answer

    def answer(self, case: Case) -> AgentResult:
        started = time.perf_counter()
        accountant = Accountant()

        try:
            query = f"{case.question}\n\n{case.facts}"
            retrieved = self.retrieve(query)
            context = "\n\n".join(f"--- passage {i} ---\n{c.text}" for i, c in enumerate(retrieved, 1))
            prompt = f"PASSAGENS RECUPERADAS:\n{context}\n\n{case.prompt_block()}"

            response = self.client.generate(
                model=self.config.models.agent,
                prompt=prompt,
                system=SYSTEM,
                schema=ANSWER_SCHEMA,
                temperature=self.config.temperature,
                max_output_tokens=self.config.max_output_tokens,
            )
            accountant.record("rag:answer", response.usage)
            parsed = response.parsed if isinstance(response.parsed, dict) else {}
            error = None
            trace = [
                {
                    "depth": 0,
                    "agent": "rag",
                    "tool": "retrieve",
                    "args": {"top_k": self.config.rag.top_k, "mmr": self.config.rag.use_mmr},
                    "ok": True,
                    "observation": "\n".join(
                        f"{i}. [{c.section_key}] ({c.doc_id})" for i, c in enumerate(retrieved, 1)
                    ),
                }
            ]
            retrieved_keys = sorted({c.section_key for c in retrieved})
        except Exception as exc:  # noqa: BLE001
            parsed, error, trace, retrieved_keys = {}, f"{type(exc).__name__}: {exc}", [], []

        return AgentResult(
            agent=self.name,
            case_id=case.id,
            answer=str(parsed.get("answer", "")).strip(),
            citations=[str(c).strip().strip("[]").strip() for c in parsed.get("citations", []) or []],
            reasoning=str(parsed.get("reasoning", "")).strip(),
            steps=1,
            wall_seconds=time.perf_counter() - started,
            usage=accountant.to_dict(),
            trace=trace,
            retrieved=retrieved_keys,
            error=error,
        )


# ----------------------------------------------------------------- numerics


def _split(text: str, size: int, overlap: int) -> list[str]:
    if len(text) <= size:
        return [text]
    step = max(1, size - overlap)
    pieces = [text[i : i + size] for i in range(0, len(text), step)]
    return [p for p in pieces if p.strip()]


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / (na * nb)


def _mmr(vectors: list[list[float]], scores: list[float], k: int, lambda_: float) -> list[int]:
    """Maximal Marginal Relevance: trade query relevance against redundancy with what is already
    selected. Without it, overlapping chunks of one long provision crowd out everything else."""
    selected: list[int] = []
    candidates = sorted(range(len(vectors)), key=lambda i: scores[i], reverse=True)[: max(k * 6, k)]

    while candidates and len(selected) < k:
        best_index, best_value = candidates[0], -float("inf")
        for index in candidates:
            redundancy = max((_cosine(vectors[index], vectors[s]) for s in selected), default=0.0)
            value = lambda_ * scores[index] - (1.0 - lambda_) * redundancy
            if value > best_value:
                best_index, best_value = index, value
        selected.append(best_index)
        candidates.remove(best_index)

    return selected
