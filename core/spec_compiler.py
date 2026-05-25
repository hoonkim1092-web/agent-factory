"""Spec Compiler: compile Interview + Research into an executable Spec.

§17 Step 4 — Compile Research + Interview into an executable Spec.

A CompiledSpec is the bridge between the interview intake artifact and the
Premortem / Planner phases.  It combines structured decisions from the
interview with evidence organised by the Research Brief.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from core.research_brief import ResearchBrief, split_evidence, _tokenize

_PATH_RE = re.compile(r"[/\\]")
_PATH_TOKEN_RE = re.compile(r'[\w.\-/\\]+\.(?:py|json|js|ts|md|yaml|yml|txt|sh|toml|cfg|ini)')


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class CompiledSpec:
    intent: str
    scope: list[str] = field(default_factory=list)
    success_criteria: list[str] = field(default_factory=list)
    constraints: list[str] = field(default_factory=list)
    approval_policy: str = ""
    research_findings: list[dict] = field(default_factory=list)   # on-brief
    supplemental: list[dict] = field(default_factory=list)        # off-brief
    gaps: list[str] = field(default_factory=list)                 # unanswered questions
    risk_hints: list[str] = field(default_factory=list)
    assumptions: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "intent": self.intent,
            "scope": self.scope,
            "success_criteria": self.success_criteria,
            "constraints": self.constraints,
            "approval_policy": self.approval_policy,
            "research_findings": self.research_findings,
            "supplemental": self.supplemental,
            "gaps": self.gaps,
            "risk_hints": self.risk_hints,
            "assumptions": self.assumptions,
        }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _str_list(val: Any) -> list[str]:
    """Coerce a list/str/None value to list[str], stripping blank entries."""
    if not val:
        return []
    if isinstance(val, list):
        return [str(x).strip() for x in val if str(x).strip()]
    s = str(val).strip()
    return [s] if s else []


def _flatten_evidence(bundle: dict[str, Any]) -> list[dict[str, Any]]:
    """Collect all evidence items from a research evidence bundle dict."""
    items: list[dict] = []
    for key in ("local_refs", "web_refs", "llm_prior", "references"):
        chunk = bundle.get(key)
        if isinstance(chunk, list):
            items.extend(chunk)
    return items


def _detect_gaps(questions: list[str], on_brief: list[dict[str, Any]]) -> list[str]:
    """Return questions whose tokens appear in no on-brief evidence item.

    Gap detection is intentionally conservative (token overlap), the same
    heuristic used by research_brief._is_on_brief, so the two are consistent.
    """
    gaps = []
    for q in questions:
        q_tokens = _tokenize(q)
        answered = any(
            q_tokens
            & _tokenize(
                " ".join(
                    str(e.get(k, ""))
                    for k in ("content", "summary", "title", "text", "source")
                )
            )
            for e in on_brief
        )
        if not answered:
            gaps.append(q)
    return gaps


def _scope_from_intent(intent: str) -> list[str]:
    """Extract file-path tokens from the task intent string as a last-resort scope fallback.

    Used when neither explicit scope nor clarification_log entries are present
    (e.g. --non-interactive runs that provide the task as a single string).
    Only tokens with a known file extension and a path separator are accepted.
    """
    matches = _PATH_TOKEN_RE.findall(intent)
    return [m for m in dict.fromkeys(matches) if _PATH_RE.search(m) and not m.startswith("//")]


def _scope_from_clarification_log(src: dict[str, Any]) -> list[str]:
    """Extract file-path scope items from clarification_log entries with category 'scope'.

    merge_clarification() writes scope-category answers to 'deliverables' but the
    clarification_log always records the raw answer with its category. Using the log
    avoids conflating functional deliverable descriptions (researcher.py:1310 contract)
    with file-path scope items.

    Only entries whose answer contains a path character (./\\) are accepted so that
    descriptive boundary answers ("관리자 화면 포함") never reach planner as targets.
    """
    _EXCLUDE = ("불필요", "없", "제외")
    items = []
    for entry in (src.get("clarification_log") or []):
        if entry.get("category") == "scope":
            answer = str(entry.get("answer", "")).strip()
            if (answer
                    and not any(kw in answer for kw in _EXCLUDE)
                    and _PATH_RE.search(answer)):
                items.append(answer)
    return items


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compile_spec(
    interview_artifact: dict[str, Any],
    evidence_bundle: dict[str, Any] | None,
    research_brief: ResearchBrief | None = None,
) -> CompiledSpec:
    """Compile an interview artifact + research evidence into a CompiledSpec.

    *interview_artifact*  — the dict returned by ``run_interview()``.
    *evidence_bundle*     — optional research evidence dict (keys: local_refs,
                            web_refs, llm_prior, references).
    *research_brief*      — optional ResearchBrief for on-brief/supplemental
                            split; pass ``None`` or an empty brief to treat all
                            evidence as on-brief.
    """
    src = interview_artifact.get("project_brief") or interview_artifact

    intent = str(src.get("goal") or src.get("task_input") or "").strip()
    # merge_clarification maps scope-category answers to "deliverables"; fall back to
    # clarification_log to avoid picking up functional descriptions from other pipelines.
    scope = (
        _str_list(src.get("scope"))
        or _scope_from_clarification_log(src)
        or _scope_from_intent(intent)
    )
    success_criteria = _str_list(src.get("success_criteria"))
    constraints = _str_list(src.get("constraints"))
    approval_policy = str(src.get("approval_policy") or "").strip()
    risk_hints = _str_list(src.get("risk_hints"))
    assumptions = list(src.get("assumptions") or [])

    raw_evidence = _flatten_evidence(evidence_bundle) if evidence_bundle else []

    if research_brief and not research_brief.is_empty():
        on_brief, supplemental = split_evidence(raw_evidence, research_brief)
        gaps = _detect_gaps(research_brief.questions, on_brief)
    else:
        on_brief = raw_evidence
        supplemental = []
        gaps = []

    return CompiledSpec(
        intent=intent,
        scope=scope,
        success_criteria=success_criteria,
        constraints=constraints,
        approval_policy=approval_policy,
        research_findings=on_brief,
        supplemental=supplemental,
        gaps=gaps,
        risk_hints=risk_hints,
        assumptions=assumptions,
    )
