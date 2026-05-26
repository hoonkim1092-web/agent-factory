"""Premortem: repo-aware failure prediction converted into verification requirements.

§17 Step 5 — Add repo-context Premortem after Spec.

Takes a CompiledSpec and produces a PremortomResult: a list of risks each
mapped to concrete verification steps.  Detectors fire on scope/risk_hints/
assumptions/gaps rather than on generic heuristics.
"""
from __future__ import annotations

import re
import shlex
from dataclasses import dataclass, field
from typing import Any

from core.spec_compiler import CompiledSpec


@dataclass
class VerificationStep:
    command: str
    description: str

    def to_dict(self) -> dict[str, Any]:
        return {"command": self.command, "description": self.description}


@dataclass
class PremortomRisk:
    id: str
    description: str
    category: str
    verification: list[VerificationStep] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "description": self.description,
            "category": self.category,
            "verification": [v.to_dict() for v in self.verification],
        }


@dataclass
class PremortomResult:
    risks: list[PremortomRisk] = field(default_factory=list)
    spec_intent: str = ""

    def has_risks(self) -> bool:
        return bool(self.risks)

    def to_dict(self) -> dict[str, Any]:
        return {
            "spec_intent": self.spec_intent,
            "risks": [r.to_dict() for r in self.risks],
        }


# ---------------------------------------------------------------------------
# Pattern helpers
# ---------------------------------------------------------------------------

_CORE_PY_RE = re.compile(r"\bcore/\S+\.py\b")
_CLI_ENTRY_RE = re.compile(r"\brun_factory_cli\.py\b|\baf\.spec\b")
_DOGFOOD_RE = re.compile(r"\bdogfood\b|\bworktree\b", re.I)
_DESTRUCTIVE_RE = re.compile(r"destructive|delete|drop|reset|force", re.I)


def _any_match(pattern: re.Pattern, items: list[str]) -> bool:
    return any(pattern.search(item) for item in items)


# ---------------------------------------------------------------------------
# Risk detectors
# ---------------------------------------------------------------------------

def _detect_blueprint_sync_risk(scope: list[str], risk_hints: list[str]) -> PremortomRisk | None:
    """core/*.py changes must be reflected in Master_Blueprint.md."""
    if not _any_match(_CORE_PY_RE, scope + risk_hints):
        return None
    files = [s for s in scope if _CORE_PY_RE.search(s)]
    if files:
        compile_step = VerificationStep(
            command=f"python -m py_compile {' '.join(shlex.quote(f) for f in files)}",
            description="No syntax errors in changed core modules.",
        )
    else:
        compile_step = VerificationStep(
            command="# py_compile: no core/*.py in scope — verify changed modules manually",
            description="No concrete scope target; confirm core module compiles without errors.",
        )
    return PremortomRisk(
        id="R1",
        description="core/*.py change may require Master_Blueprint.md synchronization.",
        category="blueprint_sync",
        verification=[
            compile_step,
            VerificationStep(
                command="grep -n '<module>' Master_Blueprint.md",
                description="Blueprint §3 section updated for changed module.",
            ),
            VerificationStep(
                command="# Blueprint commit check deferred to FINALIZE (P2 artifact tracking handles this)",
                description="Master_Blueprint.md is listed in plan artifacts and will be committed in FINALIZE.",
            ),
        ],
    )


def _detect_packaging_risk(scope: list[str], risk_hints: list[str]) -> PremortomRisk | None:
    """New core module or CLI entry may be missing from af.spec hiddenimports."""
    all_items = scope + risk_hints
    if not (_any_match(_CORE_PY_RE, all_items) or _any_match(_CLI_ENTRY_RE, all_items)):
        return None
    return PremortomRisk(
        id="R2",
        description="New core module or CLI entry may be missing from af.spec hiddenimports.",
        category="packaging",
        verification=[
            VerificationStep(
                command="grep 'hiddenimports' af.spec",
                description="af.spec hiddenimports includes new module.",
            ),
            VerificationStep(
                command="python run_factory_cli.py --help",
                description="CLI entry point loads without import errors.",
            ),
        ],
    )


def _detect_workspace_risk(scope: list[str], risk_hints: list[str]) -> PremortomRisk | None:
    """Dogfood or worktree execution may pollute the current workspace."""
    if not _any_match(_DOGFOOD_RE, scope + risk_hints):
        return None
    return PremortomRisk(
        id="R3",
        description="Dogfood or worktree execution may pollute the current workspace.",
        category="workspace",
        verification=[
            VerificationStep(
                command="git status --short",
                description="No unexpected dirty files outside allowed runtime/worktree paths.",
            ),
            VerificationStep(
                command="python scripts/test_gap_analyzer.py --workspace .",
                description="Runtime state isolation checks pass.",
            ),
        ],
    )


def _detect_destructive_risk(approval_policy: str, constraints: list[str]) -> PremortomRisk | None:
    """Destructive operations require explicit approval enforcement."""
    combined = approval_policy + " " + " ".join(constraints)
    if not _DESTRUCTIVE_RE.search(combined):
        return None
    return PremortomRisk(
        id="R4",
        description="Destructive operations present; approval policy must be enforced.",
        category="approval",
        verification=[
            VerificationStep(
                command="grep -rn 'require_human\\|approval_policy' core/",
                description="Approval gate is wired into the execution path.",
            ),
        ],
    )


def _detect_existing_pattern_risk(
    research_findings: list[dict],
    scope: list[str],
) -> PremortomRisk | None:
    """Existing code patterns found in research that overlap with scope files.

    R10 fires when at least one research finding path is also in the implementation
    scope — the new code must extend those files consistently.
    """
    finding_paths = {f.get("path", "") for f in research_findings if f.get("path")}
    overlap = sorted(finding_paths & set(scope))
    if not overlap:
        return None
    paths_str = " ".join(shlex.quote(p) for p in overlap)
    return PremortomRisk(
        id="R10",
        description=f"Existing code patterns found in scope: {', '.join(overlap)}. New implementation must extend consistently.",
        category="pattern_consistency",
        verification=[
            VerificationStep(
                command=f"python -m py_compile {paths_str}",
                description="Scope files still compile after modification.",
            ),
            VerificationStep(
                command=f"# Review patterns in {paths_str} before implementing",
                description="New code follows naming and style conventions in existing scope files.",
            ),
        ],
    )


def _detect_assumption_risks(assumptions: list[dict], start: int = 5) -> list[PremortomRisk]:
    """Low-confidence assumptions become explicit risks (R5, R6, …).

    *start* is the first ID number to use — callers can pass a higher value to
    guarantee uniqueness when other fixed risks occupy lower IDs.
    """
    risks: list[PremortomRisk] = []
    counter = start
    for a in assumptions:
        if str(a.get("confidence", "")).lower() in ("low", "unknown", ""):
            stmt = str(a.get("statement") or a.get("id") or "unknown assumption")
            risks.append(PremortomRisk(
                id=f"R{counter}",
                description=f"Low-confidence assumption: {stmt}",
                category="assumption",
                verification=[
                    VerificationStep(
                        command="# Validate assumption before proceeding",
                        description=f"Confirm or refute: {stmt}",
                    ),
                ],
            ))
            counter += 1
    return risks


def _detect_gap_risks(gaps: list[str], start: int = 20) -> list[PremortomRisk]:
    """Unanswered research questions become explicit risks (R20, R21, …).

    *start* is the first ID number to use — callers can pass a higher value
    to guarantee uniqueness when assumption risks have consumed R5…R(start-1).
    """
    risks: list[PremortomRisk] = []
    counter = start
    for gap in gaps:
        risks.append(PremortomRisk(
            id=f"R{counter}",
            description=f"Unanswered research question: {gap}",
            category="research_gap",
            verification=[
                VerificationStep(
                    command="# Resolve gap before implementation",
                    description=f"Find or generate evidence for: {gap}",
                ),
            ],
        ))
        counter += 1
    return risks


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def run_premortem(spec: CompiledSpec) -> PremortomResult:
    """Produce a PremortomResult from a CompiledSpec.

    Detectors fire when their trigger condition matches scope, risk_hints,
    constraints, approval_policy, assumptions, or gaps.
    """
    risks: list[PremortomRisk] = []

    r = _detect_blueprint_sync_risk(spec.scope, spec.risk_hints)
    if r:
        risks.append(r)

    r = _detect_packaging_risk(spec.scope, spec.risk_hints)
    if r:
        risks.append(r)

    r = _detect_workspace_risk(spec.scope, spec.risk_hints)
    if r:
        risks.append(r)

    r = _detect_destructive_risk(spec.approval_policy, spec.constraints)
    if r:
        risks.append(r)

    r = _detect_existing_pattern_risk(spec.research_findings, spec.scope)
    if r:
        risks.append(r)

    # R10 is reserved for pattern_consistency; assumptions start at R11 to avoid collision.
    assumption_risks = _detect_assumption_risks(spec.assumptions, start=11)
    risks.extend(assumption_risks)
    gap_start = max(20, 11 + len(assumption_risks))
    risks.extend(_detect_gap_risks(spec.gaps, start=gap_start))

    return PremortomResult(risks=risks, spec_intent=spec.intent)
