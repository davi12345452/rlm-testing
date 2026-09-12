"""The Recursive Language Model agent.

**The idea.** A Recursive Language Model does not receive its context — it *inhabits* it. The corpus
is an environment the model queries programmatically, one observation at a time, and when a
sub-problem is big enough to deserve its own attention the model spawns a **child instance of
itself** to solve it against a narrower slice, returning only a distilled conclusion.

**Why that matters here.** Retrieval is a single decision made before any reasoning has happened,
and it is bounded by similarity: it can only surface passages that look like the question. In
Brazilian labour law the dispositive rule is routinely a commencement date or a constitutional
ruling that shares no vocabulary with the facts and sits one cross-reference away from the provision
that *does* match. Navigation can take that hop; ranking cannot.

**Two phases, deliberately separate.** Investigation decides *when* to stop; a final composition
call decides *what to say*, under a schema where the answer is mandatory. Merging them into one
schema is a real trap: the model reliably returns ``finish`` with correct citations and no prose,
and an agent that did the work perfectly scores zero. See ``_compose``.

**Where the recursion earns its keep.** ``spawn`` is not a second opinion, it is context isolation.
A sub-agent investigating "which regime applied before November 2017" works in a clean window and
returns two sentences instead of six sections of statute. The parent's context stays small and
decision-relevant, which is what keeps a twelve-step investigation from degrading into the
long-context failure mode it was meant to avoid.

**The honest caveat.** On a corpus this size the whole thing fits in a modern context window. The
long-context arm in ``agent_longcontext.py`` exists precisely so that claim is falsifiable: if
recursion only helped because of a context limit, that arm would win. It is a control, not a
formality.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

from .agent_base import LEGAL_GUIDANCE, AgentResult, Case
from .config import RunConfig
from .corpus import Corpus
from .llm import Accountant, LLMClient
from .schemas import ANSWER_SCHEMA, RLM_STEP_SCHEMA
from .tools import TOOL_REFERENCE, CorpusEnvironment, ToolCall

COMPOSE_SYSTEM = (
    LEGAL_GUIDANCE
    + """
You have already finished investigating the corpus. Below is the transcript of everything you read.

Write the final answer now, using only what the transcript actually shows. Do not speculate beyond
it. State the bottom line explicitly -- including when the correct bottom line is that nothing is
owed -- and, where the facts span a legislative change, give the answer for each period separately.
"""
)

ROOT_SYSTEM = (
    LEGAL_GUIDANCE
    + """
You do not receive the corpus. You explore it, one action per turn, using these tools:

"""
    + TOOL_REFERENCE
    + """
plus two control actions:

spawn(sub_question, focus_keys=[])  -> run a fresh copy of yourself on a self-contained
                                       sub-question, starting from the given section keys. It
                                       explores on its own and returns a short conclusion with
                                       citations. Use it when a sub-problem would otherwise force
                                       you to read several long sections you do not need in full.
finish(citations)                  -> stop investigating. You will then be asked to write the
                                       final answer from your transcript, so finish only once you
                                       can support every part of it from sections you have read.

How to work:
- Start with outline() to see every section key and its validity status. It is cheap and it is the
  map. Do not grep blindly before you have seen the map.
- When a section looks relevant, read() it, then follow() it. A cross-reference is the corpus
  telling you that another provision modifies or completes this one; ignoring it is how you get a
  confidently wrong answer.
- Delegate with spawn when a sub-question is separable, for example one period of a contract that
  straddles a legal reform.
- Do not finish while an unread cross-reference could change the outcome.

Return exactly one action per turn, as JSON matching the schema. Fill only the fields that action
needs.
"""
)

CHILD_SYSTEM = (
    LEGAL_GUIDANCE
    + """
You are a sub-agent. You were given one narrow sub-question by a parent agent. You have the same
corpus tools:

"""
    + TOOL_REFERENCE
    + """
and finish(citations) to stop, after which you will be asked to write your conclusion.

Answer only the sub-question you were given, in at most six sentences. You cannot spawn further
sub-agents at this depth. Your parent will not see anything you read — only what you return — so
your answer must be self-contained and must carry the citation keys that support it.

Return exactly one action per turn, as JSON matching the schema.
"""
)


@dataclass
class _StepOutcome:
    answer: str
    citations: list[str]
    steps: int
    reasoning: str = ""
    truncated: bool = False


class RLMAgent:
    """Depth-limited recursive agent over the corpus environment."""

    name = "rlm"

    def __init__(self, client: LLMClient, config: RunConfig, corpus: Corpus) -> None:
        self.client = client
        self.config = config
        self.corpus = corpus

    def answer(self, case: Case) -> AgentResult:
        started = time.perf_counter()
        env = CorpusEnvironment(self.corpus, max_chars=self.config.rlm.max_chars_per_observation)
        accountant = Accountant()

        try:
            outcome = self._run(
                task=case.prompt_block(),
                system=ROOT_SYSTEM,
                depth=0,
                agent_id="root",
                env=env,
                accountant=accountant,
                max_steps=self.config.rlm.max_steps_root,
                spawns_left=self.config.rlm.max_children,
            )
            error = None
        except Exception as exc:  # noqa: BLE001 - one bad case must not abort the suite
            outcome = _StepOutcome(answer="", citations=[], steps=0)
            error = f"{type(exc).__name__}: {exc}"

        return AgentResult(
            agent=self.name,
            case_id=case.id,
            answer=outcome.answer,
            citations=outcome.citations,
            reasoning=outcome.reasoning,
            steps=outcome.steps,
            wall_seconds=time.perf_counter() - started,
            usage=accountant.to_dict(),
            trace=env.trace_dicts(),
            retrieved=sorted(env.sections_seen),
            error=error,
        )

    # ------------------------------------------------------------------ loop

    def _run(
        self,
        *,
        task: str,
        system: str,
        depth: int,
        agent_id: str,
        env: CorpusEnvironment,
        accountant: Accountant,
        max_steps: int,
        spawns_left: int,
    ) -> _StepOutcome:
        transcript: list[str] = []
        steps = 0

        for step in range(max_steps):
            remaining = max_steps - step
            prompt = _build_prompt(task, transcript, remaining)
            response = self.client.generate(
                model=self.config.models.agent,
                prompt=prompt,
                system=system,
                schema=RLM_STEP_SCHEMA,
                temperature=self.config.temperature,
                max_output_tokens=self.config.max_output_tokens,
            )
            accountant.record(f"{self.name}:depth{depth}", response.usage)
            steps += 1

            decision = response.parsed if isinstance(response.parsed, dict) else None
            if decision is None:
                transcript.append(
                    "SYSTEM: your last reply was not valid JSON for the action schema. "
                    "Return exactly one action."
                )
                continue

            action = str(decision.get("action", "")).strip()
            thought = str(decision.get("thought", "")).strip()

            if action == "finish":
                return self._compose(
                    task=task,
                    transcript=transcript,
                    depth=depth,
                    accountant=accountant,
                    steps=steps,
                    fallback_citations=_clean_citations(decision.get("citations")),
                )

            if action == "spawn":
                observation, spawns_left, child_steps = self._spawn(
                    decision=decision,
                    depth=depth,
                    env=env,
                    accountant=accountant,
                    spawns_left=spawns_left,
                )
                steps += child_steps
                transcript.append(_turn(thought, "spawn", observation))
                continue

            args = {
                k: decision[k]
                for k in ("doc_id", "pattern", "key")
                if decision.get(k) not in (None, "")
            }
            observation = env.call(action, args, depth=depth, agent=agent_id)
            transcript.append(_turn(thought, f"{action}({_fmt_args(args)})", observation))

        # Budget exhausted. Compose an answer from what was gathered rather than returning
        # nothing: an agent that ran out of steps still has a position, and scoring it is more
        # informative than recording a blank.
        return self._compose(
            task=task,
            transcript=transcript,
            depth=depth,
            accountant=accountant,
            steps=steps,
            fallback_citations=[],
            out_of_steps=True,
        )

    def _compose(
        self,
        *,
        task: str,
        transcript: list[str],
        depth: int,
        accountant: Accountant,
        steps: int,
        fallback_citations: list[str],
        out_of_steps: bool = False,
    ) -> _StepOutcome:
        """Turn a completed investigation into a written answer.

        Deciding to stop and writing the answer are different operations, and giving them one
        schema was a mistake worth naming: with the prose field merely optional alongside a
        required 'action', the model would reliably return ``finish`` with correct citations and no
        answer at all -- an agent that had done the work perfectly, scored as a total failure.

        Splitting the phases removes the failure mode by construction. The composer's only job is
        prose, under a schema where the answer is mandatory, and it sees the transcript rather than
        the corpus, so it can only write what was actually read.
        """
        tail = (
            "You are out of investigation steps. Answer from what you have, and say plainly what "
            "remains uncertain."
            if out_of_steps
            else "Your investigation is complete. Write the final answer."
        )
        if depth > 0:
            # A sub-agent's answer is an observation in its parent's context, not a document. Six
            # sentences of conclusion is the point of delegating; six sections of statute is not.
            tail += (
                " You are a sub-agent: answer only your sub-question, in at most six sentences. "
                "Your parent sees nothing but this."
            )
        prompt = _build_prompt(task, transcript, 0, closing=tail)

        response = self.client.generate(
            model=self.config.models.agent,
            prompt=prompt,
            system=COMPOSE_SYSTEM,
            schema=ANSWER_SCHEMA,
            temperature=self.config.temperature,
            max_output_tokens=self.config.max_output_tokens,
        )
        accountant.record(f"{self.name}:compose", response.usage)

        parsed = response.parsed if isinstance(response.parsed, dict) else {}
        return _StepOutcome(
            answer=str(parsed.get("answer", "")).strip(),
            citations=_clean_citations(parsed.get("citations")) or fallback_citations,
            steps=steps + 1,
            reasoning=str(parsed.get("reasoning", "")).strip(),
            truncated=out_of_steps,
        )

    def _spawn(
        self,
        *,
        decision: dict[str, Any],
        depth: int,
        env: CorpusEnvironment,
        accountant: Accountant,
        spawns_left: int,
    ) -> tuple[str, int, int]:
        sub_question = str(decision.get("sub_question", "")).strip()
        focus_keys = [str(k) for k in (decision.get("focus_keys") or []) if str(k).strip()]

        if not sub_question:
            return ("spawn requires a sub_question.", spawns_left, 0)
        if spawns_left <= 0:
            return ("Sub-agent budget exhausted. Continue on your own and finish.", 0, 0)
        if depth + 1 > self.config.rlm.max_depth:
            return (f"Maximum recursion depth ({self.config.rlm.max_depth}) reached.", spawns_left, 0)

        focus = ""
        if focus_keys:
            focus = "\nStart from these sections: " + ", ".join(f"[{k}]" for k in focus_keys)

        child = self._run(
            task=f"SUB-QUESTION:\n{sub_question}{focus}",
            system=CHILD_SYSTEM,
            depth=depth + 1,
            agent_id=f"child@{depth + 1}",
            env=env,
            accountant=accountant,
            max_steps=self.config.rlm.max_steps_child,
            spawns_left=0,
        )

        citations = ", ".join(child.citations) if child.citations else "none"
        observation = (
            f"Sub-agent answered {sub_question!r}:\n{child.answer}\n"
            f"Sub-agent citations: {citations}"
        )
        env.trace.append(
            ToolCall(
                depth=depth,
                agent=f"spawn@{depth}",
                name="spawn",
                args={"sub_question": sub_question, "focus_keys": focus_keys},
                observation=observation,
            )
        )
        return (observation, spawns_left - 1, child.steps)


def _build_prompt(
    task: str, transcript: list[str], remaining: int, *, closing: str | None = None
) -> str:
    parts = [task]
    if transcript:
        parts.append("WHAT YOU HAVE DONE SO FAR:\n" + "\n\n".join(transcript))
    parts.append(closing or f"Actions remaining before you are forced to answer: {remaining}.")
    return "\n\n".join(parts)


def _turn(thought: str, action: str, observation: str) -> str:
    head = f"THOUGHT: {thought}\n" if thought else ""
    return f"{head}ACTION: {action}\nOBSERVATION:\n{observation}"


def _fmt_args(args: dict[str, Any]) -> str:
    return ", ".join(f"{k}={v!r}" for k, v in args.items())


def _clean_citations(raw: Any) -> list[str]:
    if not isinstance(raw, list):
        return []
    seen: list[str] = []
    for item in raw:
        text = str(item).strip().strip("[]").strip()
        if text and text not in seen:
            seen.append(text)
    return seen
