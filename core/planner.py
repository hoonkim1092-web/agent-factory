"""Planner: compile Spec + Premortem into an executable Plan.

§17 Step 6 — Add Plan generation from Spec + Premortem.

An ExecutablePlan is the bridge between premortem risk analysis and actual
implementation.  Steps are ordered: investigation (resolve gaps) → implementation
(scope items) → verification (premortem checks).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

_WORD_RE = re.compile(r"[a-zA-Z0-9]+")
_SAFE_STEM_RE = re.compile(r"^[\w\-\.]+$")

from core.spec_compiler import CompiledSpec
from core.premortem import PremortomResult


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class PlanStep:
    id: str
    action: str
    target: str
    tests_required: list[str] = field(default_factory=list)
    artifacts: list[str] = field(default_factory=list)
    depends_on: list[str] = field(default_factory=list)
    commands: list[str] = field(default_factory=list)
    # Read-only context paths pulled from research_findings — AI executor should
    # consult these for existing patterns but not modify them.
    reference_artifacts: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "action": self.action,
            "target": self.target,
            "tests_required": self.tests_required,
            "artifacts": self.artifacts,
            "depends_on": self.depends_on,
            "commands": self.commands,
            "reference_artifacts": self.reference_artifacts,
        }


@dataclass
class ExecutablePlan:
    intent: str
    steps: list[PlanStep] = field(default_factory=list)
    completion_criteria: list[str] = field(default_factory=list)
    approval_points: list[str] = field(default_factory=list)
    verification_requirements: list[str] = field(default_factory=list)
    unresolved_risks: list[str] = field(default_factory=list)

    def is_empty(self) -> bool:
        return not self.steps

    def to_dict(self) -> dict[str, Any]:
        return {
            "intent": self.intent,
            "steps": [s.to_dict() for s in self.steps],
            "completion_criteria": self.completion_criteria,
            "approval_points": self.approval_points,
            "verification_requirements": self.verification_requirements,
            "unresolved_risks": self.unresolved_risks,
        }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _test_file_for(target: str) -> str | None:
    """Return a conventional test file path for a Python source target."""
    p = Path(target)
    if p.suffix == ".py" and p.parent.name in ("core", "scripts"):
        if _SAFE_STEM_RE.match(p.stem):  # block shell metachar in synthesized command
            return f"tests/test_{p.stem}.py"
    return None


def _collect_verification_commands(premortem: PremortomResult) -> list[str]:
    """Return all non-comment verification commands from all risks."""
    cmds: list[str] = []
    for risk in premortem.risks:
        for v in risk.verification:
            if not v.command.strip().startswith("#"):
                cmds.append(v.command)
    return cmds


def _collect_approval_points(
    approval_policy: str,
    premortem: PremortomResult,
) -> list[str]:
    points: list[str] = []
    if approval_policy:
        points.append(approval_policy)
    for risk in premortem.risks:
        if risk.category == "approval":
            for v in risk.verification:
                if not v.command.strip().startswith("#"):
                    points.append(v.command)
    return points


def _unresolved_risks(
    premortem: PremortomResult,
    scope: list[str],
) -> list[str]:
    """Gap risks whose question tokens do not appear in any scope item.

    Tokenizes on word boundaries so 'retry' matches 'core/retry_policy.py'.
    """
    scope_tokens = set(_WORD_RE.findall(" ".join(scope).lower()))
    unresolved: list[str] = []
    for risk in premortem.risks:
        if risk.category == "research_gap":
            # Strip fixed premortem prefix before tokenizing to avoid false-negative
            # when scope paths contain boilerplate words like "research" or "question".
            gap_text = risk.description.removeprefix("Unanswered research question: ")
            risk_tokens = set(_WORD_RE.findall(gap_text.lower()))
            if not risk_tokens & scope_tokens:
                unresolved.append(risk.description)
    return unresolved


# ---------------------------------------------------------------------------
# Step builders
# ---------------------------------------------------------------------------

def _build_investigation_steps(
    premortem: PremortomResult,
    counter: list[int],
) -> list[PlanStep]:
    """One step per research_gap risk — must be resolved before implementation."""
    steps: list[PlanStep] = []
    for risk in premortem.risks:
        if risk.category == "research_gap":
            gap = risk.description.removeprefix("Unanswered research question: ")
            steps.append(PlanStep(
                id=f"S{counter[0]}",
                action=f"Resolve: {gap}",
                target="research",
                tests_required=[],
                artifacts=["research_notes.md"],
                depends_on=[],
            ))
            counter[0] += 1
    return steps


def _references_for_scope_item(
    item: str,
    research_findings: list[dict],
) -> list[str]:
    """Collect research_findings paths related to *item* but not the item itself.

    Surfaces only the conventional companion test path (`tests/test_<stem>.py`)
    to avoid false positives from same-stem siblings in unrelated directories
    (e.g. `core/utils.py` would otherwise drag in `scripts/utils.py`).
    """
    if not research_findings:
        return []
    item_stem = Path(item).stem
    refs: list[str] = []
    seen: set[str] = set()
    for finding in research_findings:
        path = str(finding.get("path") or "").strip()
        if not path or path == item or path in seen:
            continue
        # Only the canonical companion test layout qualifies as a reference.
        if Path(path).stem == f"test_{item_stem}":
            refs.append(path)
            seen.add(path)
    return refs


def _build_implementation_steps(
    scope: list[str],
    investigation_ids: list[str],
    counter: list[int],
    research_findings: list[dict] | None = None,
) -> list[PlanStep]:
    """One step per scope item; each depends on all investigation steps."""
    steps: list[PlanStep] = []
    findings = research_findings or []
    for item in scope:
        test = _test_file_for(item)
        artifacts = [item]
        if re.match(r"core/[^/]+\.py$", item):
            artifacts.append("Master_Blueprint.md")
        references = _references_for_scope_item(item, findings)
        steps.append(PlanStep(
            id=f"S{counter[0]}",
            action=f"Implement {item}",
            target=item,
            tests_required=[test] if test else [],
            artifacts=artifacts,
            depends_on=list(investigation_ids),
            reference_artifacts=references,
        ))
        counter[0] += 1
    return steps


def _build_verification_step(
    commands: list[str],
    impl_ids: list[str],
    counter: list[int],
) -> PlanStep | None:
    """Single consolidated verification step after all implementation steps."""
    if not commands:
        return None
    step = PlanStep(
        id=f"S{counter[0]}",
        action="Run verification checks from premortem",
        target="verification",
        tests_required=[],
        artifacts=["verification_report.md"],
        depends_on=list(impl_ids),
        commands=list(commands),
    )
    counter[0] += 1
    return step


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def build_plan(spec: CompiledSpec, premortem: PremortomResult) -> ExecutablePlan:
    """Produce an ExecutablePlan from a CompiledSpec and PremortomResult.

    Step order: investigation (gap resolution) → implementation (scope items)
    → verification (premortem checks).
    """
    counter = [1]  # mutable counter shared across builders

    investigation = _build_investigation_steps(premortem, counter)
    inv_ids = [s.id for s in investigation]

    implementation = _build_implementation_steps(
        spec.scope, inv_ids, counter, spec.research_findings
    )
    impl_ids = [s.id for s in implementation]

    verify_cmds = _collect_verification_commands(premortem)
    # Fallback: if premortem produced no commands, derive pytest runs from scope file paths.
    if not verify_cmds:
        for item in spec.scope:
            test = _test_file_for(item)
            if test:
                verify_cmds.append(f"python -m pytest {test} -v")
    verify_step = _build_verification_step(verify_cmds, impl_ids, counter)

    steps = investigation + implementation
    if verify_step:
        steps.append(verify_step)

    return ExecutablePlan(
        intent=spec.intent,
        steps=steps,
        completion_criteria=list(spec.success_criteria),
        approval_points=_collect_approval_points(spec.approval_policy, premortem),
        verification_requirements=verify_cmds,
        unresolved_risks=_unresolved_risks(premortem, spec.scope),
    )


def implementation_steps(plan: ExecutablePlan) -> list[PlanStep]:
    """`id`에 'IMPLEMENT'가 포함된 PlanStep만 반환한다. 없으면 빈 리스트."""
    return [s for s in plan.steps if "IMPLEMENT" in s.id]
