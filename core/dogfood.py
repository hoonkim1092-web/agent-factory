"""Dogfood state machine: orchestrate the deep-interview pipeline.

§17 Step 7 — Add Dogfood state machine.
§17 Step 8 — Verify/Review/Retry loop.

Manages persistent run state and coordinates the pipeline phases:
  interview → research_brief → research → spec → premortem → plan →
  implement → verify → review → complete | blocked

State is persisted to .af_runtime/dogfood/<run_id>/dogfood_state.json
after each phase transition so runs can resume.
"""
from __future__ import annotations

import json
import os
import subprocess
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Tuple


# ---------------------------------------------------------------------------
# Phase enum
# ---------------------------------------------------------------------------

class DogfoodPhase(str, Enum):
    PENDING = "pending"
    INTERVIEW = "interview"
    RESEARCH_BRIEF = "research_brief"
    RESEARCH = "research"
    SPEC = "spec"
    PREMORTEM = "premortem"
    PLAN = "plan"
    IMPLEMENT = "implement"
    VERIFY = "verify"
    REVIEW = "review"
    COMPLETE = "complete"
    BLOCKED = "blocked"


# Ordered progression; terminal phases are not in this list.
_PHASE_ORDER = [
    DogfoodPhase.PENDING,
    DogfoodPhase.INTERVIEW,
    DogfoodPhase.RESEARCH_BRIEF,
    DogfoodPhase.RESEARCH,
    DogfoodPhase.SPEC,
    DogfoodPhase.PREMORTEM,
    DogfoodPhase.PLAN,
    DogfoodPhase.IMPLEMENT,
    DogfoodPhase.VERIFY,
    DogfoodPhase.REVIEW,
    DogfoodPhase.COMPLETE,
]

_TERMINAL_PHASES = {DogfoodPhase.COMPLETE, DogfoodPhase.BLOCKED}


# ---------------------------------------------------------------------------
# State dataclass
# ---------------------------------------------------------------------------

@dataclass
class DogfoodState:
    run_id: str
    task: str
    phase: DogfoodPhase
    workspace: str
    runtime_workspace: str
    interview_path: str = ""
    research_brief_path: str = ""
    spec_path: str = ""
    plan_path: str = ""
    attempts: int = 0
    last_failure: str = ""
    next_action: str = ""
    approval_policy: str = ""
    completion_criteria: list[str] = field(default_factory=list)

    def is_terminal(self) -> bool:
        return self.phase in _TERMINAL_PHASES

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "task": self.task,
            "phase": self.phase.value,
            "workspace": self.workspace,
            "runtime_workspace": self.runtime_workspace,
            "interview_path": self.interview_path,
            "research_brief_path": self.research_brief_path,
            "spec_path": self.spec_path,
            "plan_path": self.plan_path,
            "attempts": self.attempts,
            "last_failure": self.last_failure,
            "next_action": self.next_action,
            "approval_policy": self.approval_policy,
            "completion_criteria": self.completion_criteria,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DogfoodState":
        return cls(
            run_id=data["run_id"],
            task=data["task"],
            phase=DogfoodPhase(data["phase"]),
            workspace=data["workspace"],
            runtime_workspace=data["runtime_workspace"],
            interview_path=data.get("interview_path", ""),
            research_brief_path=data.get("research_brief_path", ""),
            spec_path=data.get("spec_path", ""),
            plan_path=data.get("plan_path", ""),
            attempts=data.get("attempts", 0),
            last_failure=data.get("last_failure", ""),
            next_action=data.get("next_action", ""),
            approval_policy=data.get("approval_policy", ""),
            completion_criteria=data.get("completion_criteria", []),
        )


# ---------------------------------------------------------------------------
# Verify/Review constants and result types (§17 Step 8)
# ---------------------------------------------------------------------------

MAX_VERIFY_ATTEMPTS = 3


@dataclass
class VerifyResult:
    passed: bool
    commands_run: list[str]
    failures: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "commands_run": self.commands_run,
            "failures": self.failures,
        }


@dataclass
class ReviewDecision:
    decision: str  # "pass" | "retry" | "block"
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {"decision": self.decision, "reason": self.reason}


def _default_command_runner(cmd: str, cwd: str) -> Tuple[bool, str]:
    try:
        result = subprocess.run(
            cmd, shell=True, cwd=cwd,
            capture_output=True, text=True, timeout=60,
        )
        return result.returncode == 0, (result.stdout + result.stderr).strip()
    except Exception as exc:
        return False, str(exc)


# Injectable for tests: monkeypatch core.dogfood._command_runner
_command_runner: Callable[[str, str], Tuple[bool, str]] = _default_command_runner


# ---------------------------------------------------------------------------
# State persistence
# ---------------------------------------------------------------------------

def _state_path(state: DogfoodState) -> Path:
    return Path(state.runtime_workspace) / "dogfood" / state.run_id / "dogfood_state.json"


def save_state(state: DogfoodState) -> None:
    """Persist state to disk (atomic write via temp-file + replace)."""
    path = _state_path(state)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(state.to_dict(), indent=2), encoding="utf-8")
    tmp.replace(path)


def load_state(runtime_workspace: str, run_id: str) -> DogfoodState:
    """Load state from disk."""
    path = Path(runtime_workspace) / "dogfood" / run_id / "dogfood_state.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    return DogfoodState.from_dict(data)


# ---------------------------------------------------------------------------
# Run creation
# ---------------------------------------------------------------------------

def _default_runtime_workspace(workspace: str) -> str:
    af_runtime = os.environ.get("AF_RUNTIME_DIR", "")
    if af_runtime:
        return af_runtime
    return str(Path(workspace) / ".af_runtime")


def create_run(
    task: str,
    workspace: str,
    *,
    run_id: str | None = None,
    runtime_workspace: str | None = None,
) -> DogfoodState:
    """Create a new DogfoodState and persist it."""
    rid = run_id or f"{int(time.time())}-{uuid.uuid4().hex[:8]}"
    rws = runtime_workspace or _default_runtime_workspace(workspace)
    state = DogfoodState(
        run_id=rid,
        task=task,
        phase=DogfoodPhase.PENDING,
        workspace=workspace,
        runtime_workspace=rws,
    )
    save_state(state)
    return state


# ---------------------------------------------------------------------------
# Phase transitions
# ---------------------------------------------------------------------------

def advance_phase(state: DogfoodState) -> DogfoodPhase:
    """Advance state to next phase and return the new phase.

    Does NOT persist state; caller must call save_state() after advancing.
    Raises RuntimeError if already at a terminal phase.
    """
    if state.phase in _TERMINAL_PHASES:
        raise RuntimeError(
            f"Cannot advance from terminal phase '{state.phase.value}'"
        )
    try:
        idx = _PHASE_ORDER.index(state.phase)
    except ValueError:
        raise RuntimeError(f"Unknown phase '{state.phase}'")
    state.phase = _PHASE_ORDER[idx + 1]
    return state.phase


def block_run(state: DogfoodState, reason: str) -> None:
    """Transition to BLOCKED terminal phase."""
    state.phase = DogfoodPhase.BLOCKED
    state.last_failure = reason


def retry_run(state: DogfoodState) -> None:
    """Reset to IMPLEMENT for a retry and increment the attempts counter.

    Caller must call save_state() after this to persist the new state.
    """
    state.phase = DogfoodPhase.IMPLEMENT
    state.attempts += 1


# ---------------------------------------------------------------------------
# Phase runners — wire Steps 3~6; stubs for later steps
# ---------------------------------------------------------------------------

def _run_interview_phase(state: DogfoodState, artifact: dict[str, Any]) -> dict[str, Any]:
    """Record interview artifact path and return artifact unchanged."""
    if artifact and "intent" not in artifact and "goal" not in artifact:
        raise ValueError("Interview artifact must contain 'intent' or 'goal'")
    path = _artifact_path(state, "interview.json")
    _write_json(path, artifact or {})
    state.interview_path = str(path)
    return artifact


def _run_research_brief_phase(
    state: DogfoodState, artifact: dict[str, Any]
) -> dict[str, Any]:
    """Build ResearchBrief from interview artifact."""
    from core.research_brief import build_from_interview
    brief = build_from_interview(artifact)
    path = _artifact_path(state, "research_brief.json")
    _write_json(path, brief.to_dict())
    state.research_brief_path = str(path)
    return brief.to_dict()


def _run_research_phase(state: DogfoodState, context: dict[str, Any]) -> dict[str, Any]:
    """Research execution — stub for Step 8.

    Returns context unchanged; actual research invocation added in Step 8.
    """
    return context


def _run_spec_phase(
    state: DogfoodState,
    interview_artifact: dict[str, Any],
    research_artifact: dict[str, Any],
) -> dict[str, Any]:
    """Compile spec from interview + research evidence bundle."""
    from core.research_brief import build_from_interview
    from core.spec_compiler import compile_spec
    brief = build_from_interview(interview_artifact)
    spec = compile_spec(interview_artifact, research_artifact, brief)
    path = _artifact_path(state, "spec.json")
    _write_json(path, spec.to_dict())
    state.spec_path = str(path)
    if spec.approval_policy:
        state.approval_policy = spec.approval_policy
    state.completion_criteria = list(spec.success_criteria)
    return spec.to_dict()


def _run_premortem_phase(
    state: DogfoodState, spec_dict: dict[str, Any]
) -> dict[str, Any]:
    """Run premortem on compiled spec."""
    from core.spec_compiler import CompiledSpec
    from core.premortem import run_premortem
    spec = _spec_from_dict(spec_dict)
    result = run_premortem(spec)
    return result.to_dict()


def _run_plan_phase(
    state: DogfoodState,
    spec_dict: dict[str, Any],
    premortem_dict: dict[str, Any],
) -> dict[str, Any]:
    """Generate executable plan from spec + premortem."""
    from core.premortem import PremortomResult, PremortomRisk, VerificationStep
    from core.planner import build_plan
    spec = _spec_from_dict(spec_dict)
    premortem = _premortem_from_dict(premortem_dict)
    plan = build_plan(spec, premortem)
    path = _artifact_path(state, "plan.json")
    _write_json(path, plan.to_dict())
    state.plan_path = str(path)
    return plan.to_dict()


def _run_implement_phase(state: DogfoodState, context: dict[str, Any]) -> dict[str, Any]:
    """Implementation execution — stub for Step 8."""
    return context


def _run_verify_phase(state: DogfoodState, context: dict[str, Any]) -> dict[str, Any]:
    """Run verification commands and return a VerifyResult dict.

    Commands are taken from context["commands"] first; if absent, falls back to
    context["plan_dict"]["verification_requirements"].  Empty command list → pass.
    """
    commands: list[str] = list(context.get("commands") or [])
    if not commands:
        plan_dict = context.get("plan_dict", {})
        commands = list(plan_dict.get("verification_requirements", []))

    failures: list[str] = []
    for cmd in commands:
        ok, _ = _command_runner(cmd, state.workspace)
        if not ok:
            failures.append(cmd)

    return VerifyResult(
        passed=len(failures) == 0,
        commands_run=list(commands),
        failures=failures,
    ).to_dict()


def _run_review_phase(state: DogfoodState, context: dict[str, Any]) -> dict[str, Any]:
    """Inspect verify result and decide: pass / retry / block.

    Decision logic:
      - verify passed           → "pass"
      - failed, attempts < MAX  → "retry"  (caller should call retry_run())
      - failed, attempts >= MAX → "block"  (caller should call block_run())
    """
    verify_result = context.get("verify_result", {})
    passed = verify_result.get("passed", True)

    if passed:
        return ReviewDecision(
            decision="pass",
            reason="all verification checks passed",
        ).to_dict()

    if state.attempts < MAX_VERIFY_ATTEMPTS - 1:
        return ReviewDecision(
            decision="retry",
            reason=(
                f"attempt {state.attempts + 1}/{MAX_VERIFY_ATTEMPTS};"
                " retrying implementation"
            ),
        ).to_dict()

    return ReviewDecision(
        decision="block",
        reason=f"max attempts ({MAX_VERIFY_ATTEMPTS}) reached without passing verification",
    ).to_dict()


# ---------------------------------------------------------------------------
# Public orchestration API
# ---------------------------------------------------------------------------

def run_phase(state: DogfoodState, **kwargs: Any) -> dict[str, Any]:
    """Execute the current phase and return the resulting artifact dict.

    kwargs are passed through to the phase runner; each runner documents
    which keys it uses.  Unknown kwargs are silently ignored.
    """
    phase = state.phase
    if phase == DogfoodPhase.PENDING:
        # Nothing to execute in PENDING — caller should advance first.
        return {}
    if phase == DogfoodPhase.INTERVIEW:
        return _run_interview_phase(state, kwargs.get("artifact", {}))
    if phase == DogfoodPhase.RESEARCH_BRIEF:
        return _run_research_brief_phase(state, kwargs.get("artifact", {}))
    if phase == DogfoodPhase.RESEARCH:
        return _run_research_phase(state, kwargs.get("context", {}))
    if phase == DogfoodPhase.SPEC:
        return _run_spec_phase(
            state,
            kwargs.get("interview_artifact", {}),
            kwargs.get("research_artifact", {}),
        )
    if phase == DogfoodPhase.PREMORTEM:
        return _run_premortem_phase(state, kwargs.get("spec_dict", {}))
    if phase == DogfoodPhase.PLAN:
        return _run_plan_phase(
            state,
            kwargs.get("spec_dict", {}),
            kwargs.get("premortem_dict", {}),
        )
    if phase == DogfoodPhase.IMPLEMENT:
        return _run_implement_phase(state, kwargs.get("context", {}))
    if phase == DogfoodPhase.VERIFY:
        return _run_verify_phase(state, kwargs.get("context", {}))
    if phase == DogfoodPhase.REVIEW:
        return _run_review_phase(state, kwargs.get("context", {}))
    if phase in _TERMINAL_PHASES:
        raise RuntimeError(f"Cannot run terminal phase '{phase.value}'")
    raise RuntimeError(f"No runner for phase '{phase}'")  # pragma: no cover


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _artifact_path(state: DogfoodState, filename: str) -> Path:
    return Path(state.runtime_workspace) / "dogfood" / state.run_id / filename


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _spec_from_dict(d: dict[str, Any]):  # type: ignore[return]
    from core.spec_compiler import CompiledSpec
    return CompiledSpec(
        intent=d.get("intent", ""),
        scope=d.get("scope", []),
        success_criteria=d.get("success_criteria", []),
        constraints=d.get("constraints", []),
        approval_policy=d.get("approval_policy", ""),
        research_findings=d.get("research_findings", []),
        supplemental=d.get("supplemental", []),
        gaps=d.get("gaps", []),
        risk_hints=d.get("risk_hints", []),
        assumptions=d.get("assumptions", []),
    )


def _premortem_from_dict(d: dict[str, Any]):  # type: ignore[return]
    from core.premortem import PremortomResult, PremortomRisk, VerificationStep
    risks = []
    for r in d.get("risks", []):
        verification = [
            VerificationStep(command=v.get("command", ""), description=v.get("description", ""))
            for v in r.get("verification", [])
        ]
        risks.append(PremortomRisk(
            id=r.get("id", ""),
            description=r.get("description", ""),
            category=r.get("category", ""),
            verification=verification,
        ))
    return PremortomResult(risks=risks, spec_intent=d.get("spec_intent", ""))
