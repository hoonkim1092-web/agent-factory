"""Planner: compile Spec + Premortem into an executable Plan.

§17 Step 6 — Add Plan generation from Spec + Premortem.

An ExecutablePlan is the bridge between premortem risk analysis and actual
implementation.  Steps are ordered: investigation (resolve gaps) → implementation
(scope items) → verification (premortem checks).
"""
from __future__ import annotations

import os
import re
import shlex
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

_WORD_RE = re.compile(r"[a-zA-Z0-9]+")
_SAFE_STEM_RE = re.compile(r"^[\w\-\.]+$")

from core.spec_compiler import CompiledSpec
from core.premortem import PremortomResult, PremortomRisk


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

def _is_assumption_risk(risk: PremortomResult) -> bool:
    """True when risk qualifies as an assumption: category='assumption' OR risk_id in [5, 20)."""
    if risk.category == "assumption":
        return True
    try:
        return 5 <= int(risk.id.lstrip("R")) < 20
    except (ValueError, AttributeError):
        return False


_SCOPE_FILE_PREFIX = "Scope file(s) not found on disk: "
_SCOPE_FILE_SUFFIX = ". Possible typo in path."

_STALE_TEST_PREFIX = "No test file found for scope file(s): "
_STALE_TEST_SUFFIX = "."

_DUPLICATE_FUNC_PREFIX = "Function(s) named in intent already exist in scope: "
_DUPLICATE_FUNC_SUFFIX = "."


def _extract_duplicate_function_paths(risk: PremortomRisk) -> list[tuple[str, str]]:
    """Parse (function_name, file_path) pairs from a duplicate_function risk description."""
    desc = risk.description
    if desc.startswith(_DUPLICATE_FUNC_PREFIX) and desc.endswith(_DUPLICATE_FUNC_SUFFIX):
        inner = desc[len(_DUPLICATE_FUNC_PREFIX):len(desc) - len(_DUPLICATE_FUNC_SUFFIX)]
        result = []
        for part in inner.split(", "):
            part = part.strip()
            # format: "`name` in path"
            if " in " in part:
                name_part, path_part = part.split(" in ", 1)
                func_name = name_part.strip("`")
                result.append((func_name, path_part.strip()))
        return result
    return []


def _extract_scope_file_paths(risk: PremortomRisk) -> list[str]:
    """Parse individual missing file paths from a scope_file risk description."""
    desc = risk.description
    if desc.startswith(_SCOPE_FILE_PREFIX) and desc.endswith(_SCOPE_FILE_SUFFIX):
        inner = desc[len(_SCOPE_FILE_PREFIX):len(desc) - len(_SCOPE_FILE_SUFFIX)]
        return [p.strip() for p in inner.split(",") if p.strip()]
    return []


def _extract_stale_test_paths(risk: PremortomRisk) -> list[str]:
    """Parse scope file paths from a stale_test risk and return the missing test paths.

    E.g. "No test file found for scope file(s): core/utils.py." → ["tests/test_utils.py"]
    """
    desc = risk.description
    if desc.startswith(_STALE_TEST_PREFIX) and desc.endswith(_STALE_TEST_SUFFIX):
        inner = desc[len(_STALE_TEST_PREFIX):len(desc) - len(_STALE_TEST_SUFFIX)]
        paths = [p.strip() for p in inner.split(",") if p.strip()]
        return [
            f"tests/test_{os.path.splitext(os.path.basename(p))[0]}.py"
            for p in paths
        ]
    return []


def _build_investigation_steps(
    premortem: PremortomResult,
    counter: list[int],
) -> list[PlanStep]:
    """One step per research_gap, assumption, or scope_file risk — must be resolved before implementation."""
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
        elif risk.category == "scope_file":
            for missing_file in _extract_scope_file_paths(risk):
                steps.append(PlanStep(
                    id=f"S{counter[0]}",
                    action=f"경로 확인: {missing_file}",
                    target=missing_file,
                    tests_required=[],
                    artifacts=[],
                    depends_on=[],
                    commands=[
                        f"python -c \"import os; print(os.path.exists({shlex.quote(missing_file)}))\"",
                    ],
                ))
                counter[0] += 1
        elif risk.category == "stale_test":
            for test_path in _extract_stale_test_paths(risk):
                steps.append(PlanStep(
                    id=f"S{counter[0]}",
                    action=f"테스트 작성: {test_path}",
                    target=test_path,
                    tests_required=[test_path],
                    artifacts=[test_path],
                    depends_on=[],
                ))
                counter[0] += 1
        elif risk.category == "duplicate_function":
            for func_name, file_path in _extract_duplicate_function_paths(risk):
                steps.append(PlanStep(
                    id=f"S{counter[0]}",
                    action=f"기존 정의 확인: `{func_name}` in {file_path}",
                    target=file_path,
                    tests_required=[],
                    artifacts=[],
                    depends_on=[],
                    commands=[
                        shlex.join(["grep", "-n", f"def {func_name}", file_path]),
                    ],
                ))
                counter[0] += 1
        elif _is_assumption_risk(risk):
            cmds = [
                v.command for v in risk.verification
                if not v.command.strip().startswith("#")
            ]
            steps.append(PlanStep(
                id=f"S{counter[0]}",
                action=f"Investigate: {risk.description}",
                target=risk.description,
                tests_required=[],
                artifacts=[],
                depends_on=[],
                commands=cmds,
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
    item_norm = item.replace("\\", "/")
    refs: list[str] = []
    seen: set[str] = set()
    for finding in research_findings:
        raw = str(finding.get("path") or "").strip()
        if not raw:
            continue
        # Normalize separators so Windows-style and POSIX-style entries dedup
        # to the same canonical key (and emit POSIX form, matching repo convention).
        path = raw.replace("\\", "/")
        if path == item_norm or path in seen:
            continue
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
