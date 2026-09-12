"""Structured-output schemas shared by every agent and by the judge.

Forcing all three architectures through one identical answer schema is what makes the comparison a
comparison. Scoring never parses prose, so a difference in score is a difference in legal reasoning
rather than a difference in how chatty a prompt made the model.
"""

from __future__ import annotations

from typing import Any

ANSWER_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "answer": {
            "type": "string",
            "description": "A self-contained legal answer in Brazilian Portuguese.",
        },
        "citations": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Exact corpus citation keys relied upon, e.g. 'CLT art. 483'.",
        },
        "reasoning": {
            "type": "string",
            "description": "Short justification of why these provisions govern and others do not.",
        },
    },
    "required": ["answer", "citations", "reasoning"],
}

RLM_STEP_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "thought": {
            "type": "string",
            "description": "One or two sentences: what you now know and what you still need.",
        },
        "action": {
            "type": "string",
            "enum": ["list_documents", "outline", "grep", "read", "follow", "spawn", "finish"],
        },
        "doc_id": {"type": "string", "description": "Argument for outline/grep."},
        "pattern": {"type": "string", "description": "Argument for grep."},
        "key": {"type": "string", "description": "Argument for read/follow."},
        "sub_question": {"type": "string", "description": "Argument for spawn."},
        "focus_keys": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Argument for spawn: section keys the sub-agent should start from.",
        },
        "answer": {
            "type": "string",
            "description": (
                "REQUIRED when action is finish: the complete legal answer in Brazilian "
                "Portuguese. Never finish with this field empty."
            ),
        },
        "citations": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Argument for finish: exact corpus citation keys.",
        },
    },
    "required": ["thought", "action"],
}


def judge_schema(rubric_ids: list[str]) -> dict[str, Any]:
    """Build a judging schema bound to this case's rubric.

    The rubric item ids are baked into an enum so the judge cannot invent a criterion or silently
    skip one. A free-form judge drifts; a judge constrained to answer a fixed checklist can be
    audited item by item.
    """
    return {
        "type": "object",
        "properties": {
            "items": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string", "enum": rubric_ids},
                        "verdict": {"type": "string", "enum": ["met", "partial", "missed"]},
                        "justification": {"type": "string"},
                    },
                    "required": ["id", "verdict", "justification"],
                },
            },
            "verdict": {
                "type": "string",
                "enum": ["correct", "partially_correct", "incorrect"],
                "description": "Overall verdict on the bottom line of the answer.",
            },
            "contradicts_gold": {
                "type": "boolean",
                "description": "True if the answer reaches a conclusion opposite to the gold answer.",
            },
        },
        "required": ["items", "verdict", "contradicts_gold"],
    }
