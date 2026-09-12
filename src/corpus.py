"""The corpus: a small, hyperlinked legal knowledge base.

The corpus is a graph, not a bag of text. Each section carries a canonical citation key, a validity
``status`` and a list of ``cross_refs`` pointing at provisions that modify, supersede or complete it.

That structure is the experimental variable. A similarity-based retriever can only see the *nodes*
whose wording resembles the query. An agent that can navigate can follow the *edges* — which is
exactly where the dispositive rule tends to live in this domain.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from .config import KNOWLEDGE_DIR

SECTION_RE = re.compile(r"^##\s+\[(?P<key>[^\]]+)\]\s*(?P<title>.*)$")
META_RE = re.compile(r"^\*\*(?P<name>Status|Cross-refs):\*\*\s*(?P<value>.*)$")
REF_RE = re.compile(r"\[([^\]]+)\]")


@dataclass
class Section:
    """One retrievable, citable unit of law."""

    key: str
    """Canonical citation key, e.g. 'CLT art. 483'. This is what agents must cite and what the
    evaluator scores against, which keeps citation metrics exact instead of fuzzy string matching."""

    title: str
    doc_id: str
    doc_title: str
    line_start: int
    line_end: int
    status: str = ""
    cross_refs: list[str] = field(default_factory=list)
    body: str = ""

    @property
    def text(self) -> str:
        parts = [f"[{self.key}] {self.title}"]
        if self.status:
            parts.append(f"Status: {self.status}")
        if self.cross_refs:
            parts.append("Cross-refs: " + ", ".join(f"[{r}]" for r in self.cross_refs))
        parts.append(self.body.strip())
        return "\n".join(parts).strip()

    def render(self) -> str:
        return f"--- {self.doc_id} (lines {self.line_start}-{self.line_end}) ---\n{self.text}"


@dataclass
class Document:
    doc_id: str
    title: str
    path: Path
    lines: list[str]
    sections: list[Section]


class Corpus:
    """Loads and indexes the knowledge base."""

    def __init__(self, documents: list[Document]) -> None:
        self.documents = documents
        self.sections: list[Section] = [s for d in documents for s in d.sections]
        self.by_key: dict[str, Section] = {s.key: s for s in self.sections}
        self._by_key_lower: dict[str, Section] = {s.key.lower(): s for s in self.sections}

    @classmethod
    def load(cls, knowledge_dir: Path = KNOWLEDGE_DIR) -> "Corpus":
        documents = [_parse_document(p) for p in sorted(knowledge_dir.glob("*.md"))]
        corpus = cls([d for d in documents if d.sections])
        corpus.validate()
        return corpus

    def get(self, key: str) -> Section | None:
        return self.by_key.get(key) or self._by_key_lower.get(key.strip().lower())

    def resolve(self, key: str) -> str | None:
        """Map a loosely written citation onto a canonical key, or None.

        Agents are told to cite exact keys, but they are language models: "art. 483 da CLT" must not
        be scored as a hallucination just because the word order differs. Matching is deliberately
        conservative — an order-insensitive token-set comparison, never a similarity guess — and an
        ambiguous match resolves to nothing. An over-eager resolver would inflate the citation
        metric, which is the one number in this benchmark that has to be beyond doubt.
        """
        section = self.get(key)
        if section:
            return section.key

        tokens = _citation_tokens(key)
        if not tokens:
            return None

        exact = [c.key for c in self.sections if _citation_tokens(c.key) == tokens]
        if len(exact) == 1:
            return exact[0]

        # The citation carries extra words ("art. 468, § 2º, da CLT" -> "CLT art. 468").
        narrower = [c.key for c in self.sections if _citation_tokens(c.key) < tokens]
        if len(narrower) == 1:
            return narrower[0]

        # The citation is shorter than the canonical key ("ADI 5766" -> "STF ADI 5766").
        broader = [c.key for c in self.sections if tokens < _citation_tokens(c.key)]
        return broader[0] if len(broader) == 1 else None

    def validate(self) -> None:
        """Fail loudly on a dangling cross-reference.

        A broken edge silently removes the very path the recursive agent is supposed to follow, so
        this check is the difference between measuring an architecture and measuring a typo.
        """
        dangling = [
            (section.key, ref)
            for section in self.sections
            for ref in section.cross_refs
            if ref not in self.by_key
        ]
        if dangling:
            details = ", ".join(f"[{src}] -> [{ref}]" for src, ref in dangling)
            raise ValueError(f"Corpus has dangling cross-references: {details}")

    def full_text(self) -> str:
        blocks = []
        for document in self.documents:
            blocks.append(f"===== DOCUMENT: {document.doc_id} — {document.title} =====")
            blocks.extend(section.render() for section in document.sections)
        return "\n\n".join(blocks)

    def stats(self) -> dict[str, int]:
        return {
            "documents": len(self.documents),
            "sections": len(self.sections),
            "cross_ref_edges": sum(len(s.cross_refs) for s in self.sections),
            "characters": sum(len(s.text) for s in self.sections),
        }


def _parse_document(path: Path) -> Document:
    raw = path.read_text(encoding="utf-8")
    lines = raw.splitlines()
    doc_id = path.stem
    doc_title = next((line.lstrip("# ").strip() for line in lines if line.startswith("# ")), doc_id)

    sections: list[Section] = []
    current: Section | None = None
    body: list[str] = []

    def close(end_line: int) -> None:
        if current is not None:
            current.body = "\n".join(body).strip()
            current.line_end = end_line
            sections.append(current)

    for number, line in enumerate(lines, start=1):
        match = SECTION_RE.match(line)
        if match:
            close(number - 1)
            current = Section(
                key=match.group("key").strip(),
                title=match.group("title").strip(),
                doc_id=doc_id,
                doc_title=doc_title,
                line_start=number,
                line_end=number,
            )
            body = []
            continue

        if current is None:
            continue

        meta = META_RE.match(line.strip())
        if meta:
            name, value = meta.group("name"), meta.group("value").strip()
            if name == "Status":
                current.status = value
            else:
                current.cross_refs = [r.strip() for r in REF_RE.findall(value)]
            continue

        body.append(line)

    close(len(lines))
    return Document(doc_id=doc_id, title=doc_title, path=path, lines=lines, sections=sections)


_ORDINALS = ("º", "°", "ª")
_FILLER = frozenset({"da", "de", "do", "das", "dos", "e"})


def _citation_tokens(value: str) -> frozenset[str]:
    """Reduce a citation to an order-insensitive bag of meaningful tokens."""
    text = value.strip().lower()
    for ordinal in _ORDINALS:
        text = text.replace(ordinal, "")
    text = text.replace("artigo", "art").replace("súmula", "sumula")
    text = text.replace("parágrafo", "§")
    text = re.sub(r"[^a-z0-9§]+", " ", text)
    # Keep a paragraph marker glued to its number so that "§ 2" cannot collide with "art. 2".
    text = re.sub(r"§\s*", "§", text)
    return frozenset(t for t in text.split() if t and t not in _FILLER)
