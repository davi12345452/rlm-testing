"""Central configuration for the benchmark.

Every knob that affects a measurement lives here, so that a run can be described by a single
serialisable object and reproduced from it. Anything read from the environment has a default that
works out of the box.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent

KNOWLEDGE_DIR = ROOT / "knowledge"
CASES_DIR = ROOT / "cases"
RESULTS_DIR = ROOT / "results"
CACHE_DIR = ROOT / "cache"
CONFIG_DIR = ROOT / "config"


def _env(name: str, default: str) -> str:
    value = os.environ.get(name)
    return value if value else default


@dataclass(frozen=True)
class ModelConfig:
    """Which model plays which role.

    The judge is deliberately a *different* model family position from the agents. Using the same
    model to answer and to grade introduces self-preference bias, a well-documented failure of
    LLM-as-judge evaluations, and it is cheap to avoid.
    """

    agent: str = field(default_factory=lambda: _env("RLM_AGENT_MODEL", "gemini-3.8-flash"))
    judge: str = field(default_factory=lambda: _env("RLM_JUDGE_MODEL", "gemini-3.1-pro-preview"))
    embedding: str = field(default_factory=lambda: _env("RLM_EMBEDDING_MODEL", "gemini-embedding-2"))


@dataclass(frozen=True)
class RLMConfig:
    """Budgets for the recursive agent.

    These are the levers that decide whether recursion is an advantage or just an expensive way to
    reach the same answer. They are reported alongside every result.
    """

    max_depth: int = 2
    """Maximum recursion depth. Depth 0 is the root call; a depth-2 agent may spawn children that
    themselves may spawn children, and those grandchildren must answer from what they read."""

    max_steps_root: int = 12
    """Tool-call budget for the root agent before it is forced to answer."""

    max_steps_child: int = 6
    """Tool-call budget for a spawned sub-agent."""

    max_children: int = 4
    """How many sub-queries a single agent may spawn in total."""

    max_chars_per_observation: int = 6000
    """Observations are truncated to this length. A tool that can dump the whole corpus into the
    context would quietly turn the RLM into the long-context baseline."""


@dataclass(frozen=True)
class RAGConfig:
    """Baseline retrieval settings.

    The baseline is meant to be *competent*, not a strawman: overlapping chunks, a proper embedding
    model with task-typed queries, and MMR so the top-k is not five paraphrases of one passage. A
    benchmark that beats a deliberately bad baseline measures nothing.
    """

    chunk_chars: int = 1400
    chunk_overlap: int = 280
    top_k: int = 6
    use_mmr: bool = True
    mmr_lambda: float = 0.6
    """1.0 = pure relevance, 0.0 = pure diversity."""


@dataclass(frozen=True)
class RunConfig:
    models: ModelConfig = field(default_factory=ModelConfig)
    rlm: RLMConfig = field(default_factory=RLMConfig)
    rag: RAGConfig = field(default_factory=RAGConfig)

    temperature: float = 0.0
    max_output_tokens: int = 8192
    offline: bool = False
    """When true, a cache miss is an error instead of an API call. This is what makes a committed
    run replayable by someone who has no API key."""

    seed: int = 7

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def load_pricing() -> dict[str, dict[str, float]]:
    """USD per 1M tokens, if the user has configured it.

    Token counts are always exact and are the primary cost metric in this benchmark. Monetary cost
    is reported only for models present in config/pricing.json, because published prices change and
    a hardcoded stale number is worse than no number.
    """
    path = CONFIG_DIR / "pricing.json"
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    return {k: v for k, v in data.get("models", {}).items() if isinstance(v, dict)}
