"""Research Brief: convert interview artifact into bounded research constraints.

§17 Step 3 — Constrain Research to the Research Brief.

A ResearchBrief is built from the interview artifact's research_questions and
risk_hints fields.  Evidence items are tagged on_brief/supplemental so that
callers can surface off-topic findings separately without discarding them.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ResearchBrief:
    questions: list[str] = field(default_factory=list)
    risk_hints: list[str] = field(default_factory=list)

    def is_empty(self) -> bool:
        return not self.questions and not self.risk_hints

    def to_dict(self) -> dict[str, Any]:
        return {
            "questions": list(self.questions),
            "risk_hints": list(self.risk_hints),
        }


def build_from_interview(artifact: dict[str, Any]) -> ResearchBrief:
    """Build a ResearchBrief from a run_interview() result artifact.

    Accepts both the full interview result (with nested 'project_brief') and a
    bare project_brief dict — whichever layer the caller has in hand.
    """
    src = artifact.get("project_brief") or artifact
    questions = [
        str(q).strip()
        for q in (src.get("research_questions") or [])
        if str(q).strip()
    ]
    risk_hints = [
        str(r).strip()
        for r in (src.get("risk_hints") or [])
        if str(r).strip()
    ]
    return ResearchBrief(questions=questions, risk_hints=risk_hints)


# ---------------------------------------------------------------------------
# Token-based relevance helpers
# ---------------------------------------------------------------------------

def _tokenize(text: str) -> set[str]:
    """Lower-case word tokens longer than 2 characters."""
    return {t.lower() for t in re.split(r"\W+", text) if len(t) > 2}


def _is_on_brief(text: str, brief: ResearchBrief) -> bool:
    """Return True when *text* shares tokens with any brief question or risk.

    An empty brief is treated as unconstrained — every item is on-brief.
    """
    if brief.is_empty():
        return True
    tokens = _tokenize(text)
    for phrase in (*brief.questions, *brief.risk_hints):
        if tokens & _tokenize(phrase):
            return True
    return False


# ---------------------------------------------------------------------------
# Evidence tagging
# ---------------------------------------------------------------------------

def _evidence_text(item: dict[str, Any]) -> str:
    return " ".join(
        str(item.get(k, ""))
        for k in ("content", "summary", "title", "source", "text")
    )


def tag_evidence(
    evidence_list: list[dict[str, Any]],
    brief: ResearchBrief,
) -> list[dict[str, Any]]:
    """Return a new list with 'on_brief' bool added to each item.

    Items are never mutated; a shallow copy is returned with the extra key.
    """
    tagged = []
    for item in evidence_list:
        copy = dict(item)
        copy["on_brief"] = _is_on_brief(_evidence_text(item), brief)
        tagged.append(copy)
    return tagged


def split_evidence(
    evidence_list: list[dict[str, Any]],
    brief: ResearchBrief,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Split evidence into *(on_brief, supplemental)* lists.

    Items in *supplemental* retain the 'on_brief': False tag so callers can
    surface them as optional follow-ups rather than silently drop them.
    """
    tagged = tag_evidence(evidence_list, brief)
    on_brief = [e for e in tagged if e.get("on_brief")]
    supplemental = [e for e in tagged if not e.get("on_brief")]
    return on_brief, supplemental
