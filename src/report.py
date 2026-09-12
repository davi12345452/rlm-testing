"""Render a results payload as Markdown.

The report leads with the comparison table, then immediately breaks the result down by reasoning
type and separates retrieval failures from reasoning failures. A single headline accuracy number
hides exactly the information that makes a benchmark useful.
"""

from __future__ import annotations

from typing import Any

AGENT_LABEL = {
    "rlm": "RLM (recursive)",
    "rag": "RAG (top-k)",
    "longcontext": "Long context",
    "closedbook": "Closed book (control)",
}


def render_report(payload: dict[str, Any]) -> str:
    meta = payload["meta"]
    summary = payload["summary"]
    order = [a for a in ("rlm", "rag", "longcontext", "closedbook") if a in summary]
    order += [a for a in summary if a not in order]

    lines: list[str] = []
    lines.append("# Benchmark report")
    lines.append("")
    lines.append(
        f"Generated {meta['generated_at']} · {meta['case_count']} cases · "
        f"{meta['corpus']['sections']} corpus sections · "
        f"agent `{meta['config']['models']['agent']}` · judge `{meta['config']['models']['judge']}`"
        + (" · **offline replay**" if meta.get("offline_replay") else "")
    )
    lines.append("")

    lines.append("## Headline")
    lines.append("")
    lines.append(
        "| Agent | Rubric | Verdict acc. | Fully correct | Contradicts gold | "
        "Citation F1 | Retrieval recall | Tokens/case | Steps |"
    )
    lines.append("|---|---|---|---|---|---|---|---|---|")
    for agent in order:
        s = summary[agent]
        lines.append(
            f"| {AGENT_LABEL.get(agent, agent)} "
            f"| {s['rubric_score']:.2f} "
            f"| {s['verdict_accuracy']:.2f} "
            f"| {s['fully_correct']}/{s['cases']} "
            f"| {s['contradicts_gold']} "
            f"| {s['citation_f1']:.2f} "
            f"| {s['retrieval_recall']:.2f} "
            f"| {s['mean_tokens_per_case']:,.0f} "
            f"| {s['mean_steps']:.1f} |"
        )
    lines.append("")
    lines.append(
        "*Rubric* is the weighted fraction of gold reasoning steps the answer actually made. "
        "*Verdict acc.* scores the bottom line (correct 1.0, partially correct 0.5). "
        "*Contradicts gold* counts answers that reached the opposite conclusion — the failure that "
        "matters most in this domain and the one an average hides."
    )
    lines.append("")

    lines.append("## By reasoning type")
    lines.append("")
    types = sorted({t for a in order for t in summary[a]["rubric_by_reasoning_type"]})
    lines.append("| Reasoning type | " + " | ".join(AGENT_LABEL.get(a, a) for a in order) + " |")
    lines.append("|---" * (len(order) + 1) + "|")
    for reasoning_type in types:
        cells = [
            f"{summary[a]['rubric_by_reasoning_type'].get(reasoning_type, float('nan')):.2f}"
            for a in order
        ]
        lines.append(f"| `{reasoning_type}` | " + " | ".join(cells) + " |")
    lines.append("")

    lines.append("## Citation behaviour")
    lines.append("")
    lines.append(
        "| Agent | Precision | Recall | Distractors cited | Citations outside corpus | "
        "Correct but ungrounded |"
    )
    lines.append("|---|---|---|---|---|---|")
    for agent in order:
        s = summary[agent]
        lines.append(
            f"| {AGENT_LABEL.get(agent, agent)} | {s['citation_precision']:.2f} | "
            f"{s['citation_recall']:.2f} | {s['distractor_citations']} | "
            f"{s['citations_outside_corpus']} | {s['correct_but_ungrounded']}/{s['cases']} |"
        )
    lines.append("")
    lines.append(
        "*Distractors cited* are the specific wrong provisions each case was built to bait, such as "
        "art. 482 (employee misconduct) in a constructive-dismissal claim. *Citations outside "
        "corpus* means two different things by arm: for a corpus-bound arm it is an ungrounded "
        "claim, while for the closed-book control it is usually real law that lies outside this "
        "curated excerpt — inspect them before calling either one a hallucination. *Correct but "
        "ungrounded* counts cases where the arm reached the right bottom line without ever having "
        "all the governing provisions in front of it: the right answer for reasons it could not "
        "have had, which is the failure an accuracy column cannot show."
    )
    lines.append("")

    lines.append("## Per-case rubric scores")
    lines.append("")
    case_ids = sorted({s["case_id"] for s in payload["scores"]})
    by_pair = {(s["agent"], s["case_id"]): s for s in payload["scores"]}
    lines.append("| Case | Type | " + " | ".join(AGENT_LABEL.get(a, a) for a in order) + " |")
    lines.append("|---" * (len(order) + 2) + "|")
    for case_id in case_ids:
        meta_case = payload["cases"].get(case_id, {})
        cells = []
        for agent in order:
            score = by_pair.get((agent, case_id))
            if score is None:
                cells.append("—")
                continue
            mark = " ⚠" if score["contradicts_gold"] else ""
            cells.append(f"{score['rubric_score']:.2f}{mark}")
        lines.append(
            f"| `{case_id}` | `{meta_case.get('reasoning_type', '')}` | " + " | ".join(cells) + " |"
        )
    lines.append("")
    lines.append("⚠ marks an answer whose bottom line contradicts the reference answer.")
    lines.append("")

    cost_lines = []
    for agent in order:
        s = summary[agent]
        cost_lines.append(
            f"- **{AGENT_LABEL.get(agent, agent)}**: {s['total_tokens']:,} tokens total, "
            f"{s['mean_tokens_per_case']:,.0f} per case, {s['mean_wall_seconds']:.1f}s per case"
        )
    lines.append("## Cost")
    lines.append("")
    lines.extend(cost_lines)
    judge = payload.get("judge_usage", {}).get("total", {})
    if judge:
        lines.append(f"- **Judge**: {judge.get('total_tokens', 0):,} tokens over all gradings")
    lines.append("")
    lines.append(
        "Token counts include reasoning ('thinking') tokens, which reasoning models bill as output "
        "and which benchmarks routinely omit. A recursive agent that takes twelve turns pays for "
        "its transcript on every turn; that is the price of the accuracy it buys, and it is stated "
        "here rather than hidden."
    )
    lines.append("")
    return "\n".join(lines)
