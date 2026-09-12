"""A thin, cached, accounted wrapper around the Gemini API.

Three things this module exists to guarantee:

1. **Reproducibility.** Every call is keyed by a hash of everything that could change its output and
   written to ``cache/``. A committed cache makes a published run replayable with no API key
   (``--offline``), which is the difference between a benchmark and a screenshot of a benchmark.
2. **Honest accounting.** Token usage is attributed to the agent that spent it, including the
   *thinking* tokens that reasoning models bill for and that naive benchmarks silently drop. Cost
   comparisons between a one-shot RAG call and a 12-step recursive agent are meaningless otherwise.
3. **Structured output.** Every agent returns the same JSON schema, so scoring never has to parse
   prose.
"""

from __future__ import annotations

import hashlib
import json
import os
import random
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from google import genai
from google.genai import types

from .config import CACHE_DIR, load_pricing


class CacheMiss(RuntimeError):
    """Raised in offline mode when a call was not found in the committed cache."""


@dataclass
class Usage:
    """Token accounting for one or many calls."""

    calls: int = 0
    prompt_tokens: int = 0
    output_tokens: int = 0
    thought_tokens: int = 0
    cached_calls: int = 0

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.output_tokens + self.thought_tokens

    def add(self, other: "Usage") -> None:
        self.calls += other.calls
        self.prompt_tokens += other.prompt_tokens
        self.output_tokens += other.output_tokens
        self.thought_tokens += other.thought_tokens
        self.cached_calls += other.cached_calls

    def to_dict(self) -> dict[str, Any]:
        return {
            "calls": self.calls,
            "cached_calls": self.cached_calls,
            "prompt_tokens": self.prompt_tokens,
            "output_tokens": self.output_tokens,
            "thought_tokens": self.thought_tokens,
            "total_tokens": self.total_tokens,
        }


@dataclass
class LLMResponse:
    text: str
    parsed: Any | None
    usage: Usage
    from_cache: bool
    finish_reason: str | None = None


@dataclass
class Accountant:
    """Per-role token ledger, so 'the RLM is 4x more expensive' is a measured claim."""

    by_role: dict[str, Usage] = field(default_factory=dict)

    def record(self, role: str, usage: Usage) -> None:
        self.by_role.setdefault(role, Usage()).add(usage)

    def total(self) -> Usage:
        out = Usage()
        for usage in self.by_role.values():
            out.add(usage)
        return out

    def to_dict(self) -> dict[str, Any]:
        return {
            "total": self.total().to_dict(),
            "by_role": {k: v.to_dict() for k, v in sorted(self.by_role.items())},
        }


def estimate_cost_usd(model: str, usage: Usage) -> float | None:
    """Return an estimated USD cost, or None when the model has no configured price.

    Thinking tokens are billed as output tokens by Gemini, so they are added to the output side.
    """
    pricing = load_pricing().get(model)
    if not pricing:
        return None
    inp = pricing.get("input_per_mtok")
    out = pricing.get("output_per_mtok")
    if inp is None or out is None:
        return None
    billable_output = usage.output_tokens + usage.thought_tokens
    return (usage.prompt_tokens / 1e6) * inp + (billable_output / 1e6) * out


_TRANSIENT = ("429", "500", "502", "503", "504", "deadline", "timeout", "unavailable", "overloaded")


class LLMClient:
    """Cached Gemini client. Thread-safe for the modest concurrency this benchmark uses."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        cache_dir: Path = CACHE_DIR,
        offline: bool = False,
        max_retries: int = 5,
    ) -> None:
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.offline = offline
        self.max_retries = max_retries
        self._lock = threading.Lock()
        self._client: genai.Client | None = None
        self.used_keys: set[str] = set()
        """Cache keys touched in this process, so a replay can prove which entries the published
        run actually depends on and the rest can be pruned before committing."""

        if not offline:
            key = api_key or os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
            if not key:
                raise RuntimeError(
                    "No API key. Set GEMINI_API_KEY in your environment or .env, "
                    "or run with --offline to replay the committed cache."
                )
            self._client = genai.Client(api_key=key)

    # ---------------------------------------------------------------- caching

    def _cache_path(self, key: str) -> Path:
        return self.cache_dir / key[:2] / f"{key}.json"

    @staticmethod
    def _key(payload: dict[str, Any]) -> str:
        blob = json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str)
        return hashlib.sha256(blob.encode("utf-8")).hexdigest()

    def _read_cache(self, key: str) -> dict[str, Any] | None:
        path = self._cache_path(key)
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return None

    def _write_cache(self, key: str, record: dict[str, Any]) -> None:
        path = self._cache_path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(record, ensure_ascii=False, indent=1), encoding="utf-8")
        tmp.replace(path)

    # ------------------------------------------------------------- generation

    def generate(
        self,
        *,
        model: str,
        prompt: str,
        system: str | None = None,
        schema: dict[str, Any] | None = None,
        temperature: float = 0.0,
        max_output_tokens: int = 8192,
    ) -> LLMResponse:
        payload = {
            "kind": "generate",
            "model": model,
            "prompt": prompt,
            "system": system,
            "schema": schema,
            "temperature": temperature,
            "max_output_tokens": max_output_tokens,
        }
        key = self._key(payload)
        with self._lock:
            self.used_keys.add(key)

        cached = self._read_cache(key)
        if cached is not None:
            usage = Usage(**{k: v for k, v in cached["usage"].items() if k in Usage.__annotations__})
            usage.cached_calls = usage.calls
            return LLMResponse(
                text=cached["text"],
                parsed=cached.get("parsed"),
                usage=usage,
                from_cache=True,
                finish_reason=cached.get("finish_reason"),
            )

        if self.offline:
            raise CacheMiss(
                f"Cache miss for {model} in offline mode (key {key[:12]}). "
                "The committed cache only covers the published run configuration."
            )

        config_kwargs: dict[str, Any] = {
            "temperature": temperature,
            "max_output_tokens": max_output_tokens,
        }
        if system:
            config_kwargs["system_instruction"] = system
        if schema is not None:
            config_kwargs["response_mime_type"] = "application/json"
            config_kwargs["response_schema"] = schema

        response = self._call_with_retry(model, prompt, config_kwargs)

        text = response.text or ""
        finish_reason = None
        if response.candidates:
            finish_reason = str(getattr(response.candidates[0], "finish_reason", "") or "")

        parsed: Any | None = None
        if schema is not None and text.strip():
            parsed = _loads_lenient(text)

        meta = response.usage_metadata
        usage = Usage(
            calls=1,
            prompt_tokens=int(getattr(meta, "prompt_token_count", 0) or 0),
            output_tokens=int(getattr(meta, "candidates_token_count", 0) or 0),
            thought_tokens=int(getattr(meta, "thoughts_token_count", 0) or 0),
        )

        self._write_cache(
            key,
            {
                "request": payload,
                "text": text,
                "parsed": parsed,
                "usage": usage.to_dict(),
                "finish_reason": finish_reason,
            },
        )
        return LLMResponse(text=text, parsed=parsed, usage=usage, from_cache=False, finish_reason=finish_reason)

    def _call_with_retry(self, model: str, prompt: str, config_kwargs: dict[str, Any]):
        assert self._client is not None
        last: Exception | None = None
        for attempt in range(self.max_retries):
            try:
                return self._client.models.generate_content(
                    model=model,
                    contents=prompt,
                    config=types.GenerateContentConfig(**config_kwargs),
                )
            except Exception as exc:  # noqa: BLE001 - the SDK raises a wide surface
                last = exc
                message = str(exc).lower()
                if not any(token in message for token in _TRANSIENT):
                    raise
                sleep_for = min(2**attempt, 30) + random.random()
                time.sleep(sleep_for)
        raise RuntimeError(f"Gemini call failed after {self.max_retries} attempts: {last}")

    # ------------------------------------------------------------- embeddings

    def embed(self, *, model: str, texts: list[str], task_type: str) -> list[list[float]]:
        """Embed a list of texts, caching each one independently.

        Per-text caching (rather than per-batch) means adding one document to the corpus does not
        invalidate the embeddings of all the others.
        """
        out: list[list[float]] = []
        pending: list[tuple[int, str, str]] = []

        for index, text in enumerate(texts):
            key = self._key({"kind": "embed", "model": model, "task_type": task_type, "text": text})
            with self._lock:
                self.used_keys.add(key)
            cached = self._read_cache(key)
            if cached is not None:
                out.append(cached["embedding"])
            else:
                out.append([])
                pending.append((index, text, key))

        if pending and self.offline:
            raise CacheMiss(f"{len(pending)} embeddings missing from the cache in offline mode.")

        assert self._client is not None or not pending
        for index, text, key in pending:
            response = self._client.models.embed_content(  # type: ignore[union-attr]
                model=model,
                contents=text,
                config=types.EmbedContentConfig(task_type=task_type),
            )
            vector = list(response.embeddings[0].values)
            self._write_cache(key, {"model": model, "task_type": task_type, "embedding": vector})
            out[index] = vector

        return out


def _loads_lenient(text: str) -> Any | None:
    """Parse JSON, tolerating the occasional fenced block a model emits despite a schema."""
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = stripped.split("\n", 1)[-1]
        if stripped.rstrip().endswith("```"):
            stripped = stripped.rstrip()[:-3]
    start = stripped.find("{")
    end = stripped.rfind("}")
    if start != -1 and end > start:
        try:
            return json.loads(stripped[start : end + 1])
        except json.JSONDecodeError:
            return None
    return None
