"""The corpus environment: the tools an agent uses to *navigate* rather than receive text.

This is the substantive difference between the two architectures under test. RAG decides what the
model will see before the model has thought about anything. Here the model decides, one observation
at a time, and can act on what it just learned — including following a cross-reference to a
provision whose wording has nothing in common with the question.

Two design constraints keep the comparison honest:

* **Every observation is truncated.** A tool that could dump the corpus would turn the recursive
  agent into the long-context baseline and the experiment would measure nothing.
* **Every call is traced.** The trace is the artefact that explains *why* an answer was right, and
  it is what lets a reader audit a result instead of trusting a score.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from .corpus import Corpus, Section

MAX_GREP_HITS = 12
SNIPPET_CHARS = 240


@dataclass
class ToolCall:
    """One step of an agent's interaction with the corpus."""

    depth: int
    agent: str
    name: str
    args: dict[str, Any]
    observation: str
    ok: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "depth": self.depth,
            "agent": self.agent,
            "tool": self.name,
            "args": self.args,
            "ok": self.ok,
            "observation": self.observation,
        }


@dataclass
class CorpusEnvironment:
    """A read-only, budgeted view over the corpus, shared by every agent in one case."""

    corpus: Corpus
    max_chars: int = 6000
    trace: list[ToolCall] = field(default_factory=list)
    sections_seen: set[str] = field(default_factory=set)

    # ------------------------------------------------------------------ tools

    def list_documents(self) -> str:
        rows = [
            f"- {d.doc_id}: {d.title} ({len(d.sections)} sections)" for d in self.corpus.documents
        ]
        return "Documents in the corpus:\n" + "\n".join(rows)

    def outline(self, doc_id: str = "") -> str:
        """Section keys, titles and validity status — the cheapest way to see the whole map.

        Exposing ``status`` in the outline is intentional: it gives *both* architectures a fair shot
        at noticing that a provision has been superseded. The recursive agent's advantage must come
        from traversal, not from privileged information.
        """
        documents = self.corpus.documents
        if doc_id:
            documents = [d for d in documents if d.doc_id == doc_id or doc_id in d.doc_id]
            if not documents:
                available = ", ".join(d.doc_id for d in self.corpus.documents)
                return f"No document matches {doc_id!r}. Available: {available}"

        blocks = []
        for document in documents:
            lines = [f"# {document.doc_id}"]
            for section in document.sections:
                status = f" — status: {section.status}" if section.status else ""
                lines.append(f"  [{section.key}] {section.title}{status}")
            blocks.append("\n".join(lines))
        return "\n".join(blocks)

    def grep(self, pattern: str, doc_id: str = "") -> str:
        """Case-insensitive regex search over section text, returning keys plus snippets."""
        try:
            regex = re.compile(pattern, re.IGNORECASE)
        except re.error as exc:
            return f"Invalid regular expression {pattern!r}: {exc}"

        hits: list[str] = []
        for section in self.corpus.sections:
            if doc_id and doc_id not in section.doc_id:
                continue
            match = regex.search(section.text)
            if not match:
                continue
            start = max(0, match.start() - SNIPPET_CHARS // 2)
            snippet = section.text[start : start + SNIPPET_CHARS].replace("\n", " ")
            hits.append(f"[{section.key}] ({section.doc_id}) …{snippet}…")
            if len(hits) >= MAX_GREP_HITS:
                hits.append(f"(stopped at {MAX_GREP_HITS} hits; narrow the pattern for more)")
                break

        if not hits:
            return f"No section matches {pattern!r}. Try a broader pattern or a synonym."
        return f"{len(hits)} match(es) for {pattern!r}:\n" + "\n".join(hits)

    def read(self, key: str) -> str:
        """Read one section in full, by citation key."""
        resolved = self.corpus.resolve(key)
        if resolved is None:
            return (
                f"No section with key {key!r}. Use outline() to see the exact keys, "
                "which are the strings you must cite."
            )
        section = self.corpus.by_key[resolved]
        self.sections_seen.add(resolved)
        return section.render()

    def follow(self, key: str) -> str:
        """List the provisions cross-referenced by a section, with their validity status.

        This is the edge-traversal primitive. In this domain the rule that decides the case is very
        often one hop away from the rule that *matches* the question, and one hop is exactly what a
        single-shot retriever cannot take.
        """
        resolved = self.corpus.resolve(key)
        if resolved is None:
            return f"No section with key {key!r}."
        section = self.corpus.by_key[resolved]
        if not section.cross_refs:
            return f"[{section.key}] has no cross-references."

        rows = []
        for ref in section.cross_refs:
            target: Section | None = self.corpus.by_key.get(ref)
            if target is None:
                rows.append(f"  [{ref}] (missing from corpus)")
                continue
            status = target.status or "unspecified"
            rows.append(f"  [{target.key}] {target.title} — status: {status}")
        return f"[{section.key}] cross-references:\n" + "\n".join(rows)

    # ------------------------------------------------------------- dispatcher

    TOOLS = ("list_documents", "outline", "grep", "read", "follow")

    def call(self, name: str, args: dict[str, Any], *, depth: int, agent: str) -> str:
        handlers = {
            "list_documents": lambda: self.list_documents(),
            "outline": lambda: self.outline(str(args.get("doc_id", "") or "")),
            "grep": lambda: self.grep(str(args.get("pattern", "") or ""), str(args.get("doc_id", "") or "")),
            "read": lambda: self.read(str(args.get("key", "") or "")),
            "follow": lambda: self.follow(str(args.get("key", "") or "")),
        }
        handler = handlers.get(name)
        if handler is None:
            observation = f"Unknown tool {name!r}. Available: {', '.join(self.TOOLS)}."
            ok = False
        else:
            try:
                observation = handler()
                ok = True
            except Exception as exc:  # noqa: BLE001 - a tool error must not kill the run
                observation = f"Tool {name} raised {type(exc).__name__}: {exc}"
                ok = False

        observation = _truncate(observation, self.max_chars)
        self.trace.append(ToolCall(depth=depth, agent=agent, name=name, args=args, observation=observation, ok=ok))
        return observation

    def trace_dicts(self) -> list[dict[str, Any]]:
        return [c.to_dict() for c in self.trace]


def _truncate(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[:limit] + f"\n[... truncated, {len(text) - limit} more characters ...]"


TOOL_REFERENCE = """\
list_documents()            -> the documents in the corpus
outline(doc_id="")          -> every section key, title and validity status (cheap, start here)
grep(pattern, doc_id="")    -> case-insensitive regex over section text, returns keys + snippets
read(key)                   -> the full text of one section, by its citation key
follow(key)                 -> the sections cross-referenced by a section, with their status
"""
