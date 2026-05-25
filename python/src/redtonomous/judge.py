"""Goal-evaluation judge used by ``redtonomous goal``.

The judge re-uses any provider adapter — it just asks the model whether the
agent achieved the stated criteria and parses a strict-JSON response.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass

from .models.base import ModelAdapter

JUDGE_SYSTEM = """\
You are a strict acceptance judge. You receive a goal and a transcript of
an autonomous coding agent's actions. Decide whether the goal was fully
achieved. Be conservative — if anything material is missing or the agent
gave up, mark it not achieved.

Respond with exactly one line of JSON and nothing else, in this shape:
{"achieved": true|false, "missing": "<one sentence>", "confidence": 0.0..1.0}
"""


@dataclass
class Verdict:
    achieved: bool
    missing: str
    confidence: float
    raw: str


_JSON_OBJECT = re.compile(r"\{[^{}]*\}", re.DOTALL)


def _parse(text: str) -> Verdict:
    # Be lenient: pull the first JSON object out of the response even if the
    # model surrounded it with markdown.
    match = _JSON_OBJECT.search(text)
    payload = match.group(0) if match else text.strip()
    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        return Verdict(
            achieved=False,
            missing=f"could not parse judge response: {text[:200]!r}",
            confidence=0.0,
            raw=text,
        )
    return Verdict(
        achieved=bool(data.get("achieved", False)),
        missing=str(data.get("missing", "") or "")[:500],
        confidence=float(data.get("confidence", 0.0) or 0.0),
        raw=text,
    )


def evaluate(criteria: str, transcript: str, adapter: ModelAdapter) -> Verdict:
    """Ask the adapter whether ``criteria`` was achieved given ``transcript``.

    ``transcript`` is the agent's final text plus a condensed tool trace
    (caller's responsibility to summarise — we don't replay tool_use blocks
    here so the judge can re-use any provider).
    """
    user = (
        "GOAL:\n"
        f"{criteria}\n\n"
        "AGENT TRANSCRIPT:\n"
        f"{transcript}\n\n"
        "Verdict?"
    )
    resp = adapter.chat(
        messages=[{"role": "user", "content": user}],
        tools=[],
        system=JUDGE_SYSTEM,
    )
    return _parse(resp.text or "")
