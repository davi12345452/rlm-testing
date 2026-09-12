"""Benchmark runner.

    python -m src.benchmark run                          # every agent, every case
    python -m src.benchmark run --agents rlm,rag         # a subset
    python -m src.benchmark run --cases case_03,case_05  # substring match on case ids
    python -m src.benchmark run --offline                # replay the committed cache, no API key
    python -m src.benchmark inspect --case case_03 --agent rlm   # read one agent's trace

Results are written as a single JSON document containing the full configuration, every trace and
every score, plus a rendered Markdown report. The JSON is the artefact; the report is a view of it.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

from .agent_base import AgentResult, Case
from .agent_closedbook import ClosedBookAgent
from .agent_longcontext import LongContextAgent
from .agent_rag import RAGAgent
from .agent_rlm import RLMAgent
from .config import CACHE_DIR, RESULTS_DIR, RunConfig
from .corpus import Corpus
from .evaluator import Evaluator, aggregate
from .llm import CacheMiss, LLMClient, estimate_cost_usd
from .report import render_report

AGENTS = {
    "rlm": RLMAgent,
    "rag": RAGAgent,
    "longcontext": LongContextAgent,
    "closedbook": ClosedBookAgent,
}


def _load_env() -> None:
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path, override=False)


def run(args: argparse.Namespace) -> int:
    _load_env()

    config = RunConfig(offline=args.offline)
    corpus = Corpus.load()
    cases = Case.load_all()

    if args.cases:
        wanted = [c.strip() for c in args.cases.split(",") if c.strip()]
        cases = [c for c in cases if any(w in c.id for w in wanted)]
    if args.limit:
        cases = cases[: args.limit]
    if not cases:
        print("No cases matched.", file=sys.stderr)
        return 1

    names = [a.strip() for a in args.agents.split(",") if a.strip()]
    unknown = [n for n in names if n not in AGENTS]
    if unknown:
        print(f"Unknown agent(s): {', '.join(unknown)}. Choose from {', '.join(AGENTS)}.", file=sys.stderr)
        return 1

    client = LLMClient(offline=args.offline)
    agents = {name: AGENTS[name](client, config, corpus) for name in names}
    evaluator = Evaluator(client, config, corpus)

    print(f"corpus: {corpus.stats()}")
    print(f"cases : {len(cases)}  agents: {', '.join(names)}  offline: {args.offline}")
    print()

    started = time.perf_counter()
    jobs = [(name, case) for name in names for case in cases]

    def work(job: tuple[str, Case]) -> tuple[str, Case, AgentResult]:
        name, case = job
        result = agents[name].answer(case)
        return name, case, result

    results: list[tuple[str, Case, AgentResult]] = []
    try:
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            for name, case, result in pool.map(work, jobs):
                flag = "!" if result.error else " "
                print(
                    f"{flag} {name:<12} {case.id:<34} "
                    f"steps={result.steps:<3} "
                    f"tokens={result.usage.get('total', {}).get('total_tokens', 0):<7} "
                    f"{result.wall_seconds:5.1f}s"
                )
                if result.error:
                    print(f"    error: {result.error}")
                results.append((name, case, result))
    except CacheMiss as exc:
        print(f"\nOffline replay failed: {exc}", file=sys.stderr)
        return 2

    print("\nscoring...")
    scores = []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        scores = list(pool.map(lambda item: evaluator.score(item[1], item[2]), results))

    summary = aggregate(scores)
    by_case = {c.id: c for c in cases}

    payload = {
        "meta": {
            "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "wall_seconds": round(time.perf_counter() - started, 1),
            "offline_replay": args.offline,
            "config": config.to_dict(),
            "corpus": corpus.stats(),
            "case_count": len(cases),
            "agents": names,
        },
        "summary": summary,
        "judge_usage": evaluator.accountant.to_dict(),
        "judge_cost_usd": estimate_cost_usd(config.models.judge, evaluator.accountant.total()),
        "scores": [s.to_dict() for s in scores],
        "runs": [r.to_dict() for _, _, r in results],
        "cases": {
            c.id: {"title": c.title, "reasoning_type": c.reasoning_type, "difficulty": c.difficulty}
            for c in by_case.values()
        },
    }

    out_dir = Path(args.out) if args.out else RESULTS_DIR / "latest"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "results.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    report = render_report(payload)
    (out_dir / "report.md").write_text(report, encoding="utf-8")

    print("\n" + report.split("## Per-case", 1)[0].strip())
    print(f"\nwrote {out_dir / 'results.json'} and {out_dir / 'report.md'}")
    return 0


def prune(args: argparse.Namespace) -> int:
    """Drop cache entries the published run does not depend on.

    Iterating on an agent leaves behind responses to prompts that no longer exist. Committing them
    would ship several megabytes of dead weight and blur what the published numbers actually rest
    on. This replays the canonical run offline -- no API calls -- and deletes everything it did not
    touch, so the committed cache is exactly the evidence for the committed report.
    """
    _load_env()
    config = RunConfig(offline=True)
    corpus = Corpus.load()
    cases = Case.load_all()
    client = LLMClient(offline=True)
    agents = {name: AGENTS[name](client, config, corpus) for name in AGENTS}
    evaluator = Evaluator(client, config, corpus)

    try:
        for name, agent in agents.items():
            for case in cases:
                evaluator.score(case, agent.answer(case))
    except CacheMiss as exc:
        print(f"Refusing to prune: the canonical run is not fully cached.\n{exc}", file=sys.stderr)
        return 2

    used = client.used_keys
    removed = kept = 0
    freed = 0
    for path in sorted(CACHE_DIR.rglob("*.json")):
        if path.stem in used:
            kept += 1
            continue
        freed += path.stat().st_size
        if not args.dry_run:
            path.unlink()
        removed += 1

    if not args.dry_run:
        for directory in sorted(CACHE_DIR.glob("*")):
            if directory.is_dir() and not any(directory.iterdir()):
                directory.rmdir()

    verb = "would remove" if args.dry_run else "removed"
    print(f"kept {kept} entries, {verb} {removed} ({freed / 1e6:.1f} MB)")
    return 0


def inspect(args: argparse.Namespace) -> int:
    path = Path(args.results) if args.results else RESULTS_DIR / "latest" / "results.json"
    if not path.exists():
        print(f"No results at {path}. Run the benchmark first.", file=sys.stderr)
        return 1
    payload = json.loads(path.read_text(encoding="utf-8"))

    runs = [
        r
        for r in payload["runs"]
        if (not args.case or args.case in r["case_id"]) and (not args.agent or r["agent"] == args.agent)
    ]
    if not runs:
        print("No run matched.", file=sys.stderr)
        return 1

    for run_data in runs:
        print("=" * 78)
        print(f"{run_data['agent']} — {run_data['case_id']}  ({run_data['steps']} steps)")
        print("=" * 78)
        for i, call in enumerate(run_data["trace"], 1):
            args_text = ", ".join(f"{k}={v!r}" for k, v in call["args"].items())
            print(f"\n[{i}] depth={call['depth']} {call['tool']}({args_text})")
            observation = call["observation"]
            if len(observation) > args.max_chars:
                observation = observation[: args.max_chars] + " […]"
            print("    " + observation.replace("\n", "\n    "))
        print(f"\nANSWER:\n{run_data['answer']}")
        print(f"\nCITATIONS: {', '.join(run_data['citations']) or 'none'}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="benchmark", description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)

    run_parser = sub.add_parser("run", help="run the benchmark")
    run_parser.add_argument("--agents", default="rlm,rag,longcontext,closedbook")
    run_parser.add_argument("--cases", default="", help="comma-separated substrings of case ids")
    run_parser.add_argument("--limit", type=int, default=0)
    run_parser.add_argument("--workers", type=int, default=4)
    run_parser.add_argument("--offline", action="store_true", help="replay the cache; no API calls")
    run_parser.add_argument("--out", default="", help="output directory")
    run_parser.set_defaults(func=run)

    prune_parser = sub.add_parser("prune", help="drop cache entries the published run does not need")
    prune_parser.add_argument("--dry-run", action="store_true")
    prune_parser.set_defaults(func=prune)

    inspect_parser = sub.add_parser("inspect", help="print an agent's trace for one case")
    inspect_parser.add_argument("--case", default="")
    inspect_parser.add_argument("--agent", default="")
    inspect_parser.add_argument("--results", default="")
    inspect_parser.add_argument("--max-chars", type=int, default=900)
    inspect_parser.set_defaults(func=inspect)

    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
