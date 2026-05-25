"""Dogfood state machine: orchestrate the deep-interview pipeline.

§17 Step 7  — Add Dogfood state machine.
§17 Step 8  — Verify/Review/Retry loop.
§17 Step 9  — IMPLEMENT phase: execute plan step commands.
§17 Step 16 — Worktree isolation + auto-merge lifecycle.

Phases:
  interview → research_brief → research → spec → premortem → plan →
  isolate → implement → verify → review → finalize → merge →
  complete | blocked

Source workspace is isolated into a dogfood/<run_id> git worktree before
IMPLEMENT so self-modifying runs never touch the source working copy.
Runtime artifacts live in %USERPROFILE%/.af-dogfood/<run_id>/runtime
(CWD-independent, set via AF_DOGFOOD_ROOT env var to override).
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Literal, Tuple

# run_id must be alphanumeric + hyphens — no path separators or dots
_RUN_ID_RE = re.compile(r'^[\w\-]+$')


def _validate_run_id(run_id: str) -> None:
    """Raise ValueError if run_id contains path traversal characters."""
    if not _RUN_ID_RE.fullmatch(run_id):
        raise ValueError(
            f"Invalid run_id {run_id!r}: only alphanumerics, underscores, and hyphens are allowed."
        )


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
    ISOLATE = "isolate"
    IMPLEMENT = "implement"
    VERIFY = "verify"
    REVIEW = "review"
    FINALIZE = "finalize"
    MERGE = "merge"
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
    DogfoodPhase.ISOLATE,
    DogfoodPhase.IMPLEMENT,
    DogfoodPhase.VERIFY,
    DogfoodPhase.REVIEW,
    DogfoodPhase.FINALIZE,
    DogfoodPhase.MERGE,
    DogfoodPhase.COMPLETE,
]

_TERMINAL_PHASES = {DogfoodPhase.COMPLETE, DogfoodPhase.BLOCKED}


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class GitWorktreeError(RuntimeError):
    """Raised when git worktree operations fail."""


class TriadContractError(RuntimeError):
    """Raised when Architect output violates a contract constraint."""


# ---------------------------------------------------------------------------
# State dataclass
# ---------------------------------------------------------------------------

@dataclass
class DogfoodState:
    run_id: str
    task: str
    phase: DogfoodPhase
    source_workspace: str
    runtime_workspace: str

    # isolation fields (Step 16)
    source_branch: str = ""
    base_ref: str = ""
    worktree_workspace: str = ""
    dogfood_branch: str = ""
    isolation_status: str = "pending"   # pending | ready | failed | cleaned
    merge_status: str = "none"          # none | ready | merged | conflict | policy_rejected | failed
    merge_mode: str = "auto_policy"     # auto_policy | manual | never
    dogfood_commit: str = ""
    merged_commit: str = ""

    # artifact paths
    interview_path: str = ""
    research_brief_path: str = ""
    spec_path: str = ""
    plan_path: str = ""

    # runtime tracking
    attempts: int = 0
    last_failure: str = ""
    next_action: str = ""
    approval_policy: str = ""
    completion_criteria: list[str] = field(default_factory=list)

    @property
    def workspace(self) -> str:
        """Backward-compat alias for source_workspace."""
        return self.source_workspace

    def _cwd(self) -> str:
        """Return the cwd for command execution (worktree if ready, else source)."""
        if self.worktree_workspace and self.isolation_status == "ready":
            return self.worktree_workspace
        return self.source_workspace

    def is_terminal(self) -> bool:
        return self.phase in _TERMINAL_PHASES

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "task": self.task,
            "phase": self.phase.value,
            "source_workspace": self.source_workspace,
            "workspace": self.source_workspace,   # backward-compat alias in JSON
            "runtime_workspace": self.runtime_workspace,
            "source_branch": self.source_branch,
            "base_ref": self.base_ref,
            "worktree_workspace": self.worktree_workspace,
            "dogfood_branch": self.dogfood_branch,
            "isolation_status": self.isolation_status,
            "merge_status": self.merge_status,
            "merge_mode": self.merge_mode,
            "dogfood_commit": self.dogfood_commit,
            "merged_commit": self.merged_commit,
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
        # source_workspace falls back to legacy "workspace" key
        src_ws = data.get("source_workspace") or data.get("workspace", "")
        return cls(
            run_id=data["run_id"],
            task=data["task"],
            phase=DogfoodPhase(data["phase"]),
            source_workspace=src_ws,
            runtime_workspace=data["runtime_workspace"],
            source_branch=data.get("source_branch", ""),
            base_ref=data.get("base_ref", ""),
            worktree_workspace=data.get("worktree_workspace", ""),
            dogfood_branch=data.get("dogfood_branch", ""),
            isolation_status=data.get("isolation_status", "pending"),
            merge_status=data.get("merge_status", "none"),
            merge_mode=data.get("merge_mode", "auto_policy"),
            dogfood_commit=data.get("dogfood_commit", ""),
            merged_commit=data.get("merged_commit", ""),
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
# MergePolicy dataclass
# ---------------------------------------------------------------------------

@dataclass
class MergePolicy:
    mode: Literal["auto_policy", "manual", "never"] = "auto_policy"
    require_clean_source: bool = True
    allow_source_advanced: bool = False
    require_verify_pass: bool = True
    require_review_pass: bool = True
    require_plan_triad_pass: bool = True
    require_dogfood_commit: bool = True
    allowed_paths: list[str] = field(default_factory=list)
    denied_paths: list[str] = field(default_factory=lambda: [
        ".af_runtime/",
        "runtime/",
        "skills/registry.yaml",
    ])


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
# Runtime root helpers
# ---------------------------------------------------------------------------

def _dogfood_root() -> Path:
    """Return the global dogfood runtime root (CWD-independent)."""
    custom = os.environ.get("AF_DOGFOOD_ROOT", "")
    if custom:
        return Path(custom)
    return Path.home() / ".af-dogfood"


def _default_runtime_workspace(run_id: str) -> str:
    """Return the runtime workspace path for run_id.

    Uses %USERPROFILE%/.af-dogfood/<run_id>/runtime by default.
    Override with AF_DOGFOOD_ROOT env var.
    """
    return str(_dogfood_root() / run_id / "runtime")


def _default_worktree_workspace(run_id: str) -> str:
    return str(_dogfood_root() / run_id / "worktree")


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
    _validate_run_id(run_id)
    path = Path(runtime_workspace) / "dogfood" / run_id / "dogfood_state.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    return DogfoodState.from_dict(data)


# ---------------------------------------------------------------------------
# Run creation
# ---------------------------------------------------------------------------

def create_run(
    task: str,
    workspace: str,
    *,
    run_id: str | None = None,
    runtime_workspace: str | None = None,
    merge_mode: str = "auto_policy",
) -> DogfoodState:
    """Create a new DogfoodState and persist it."""
    rid = run_id or f"{int(time.time())}-{uuid.uuid4().hex[:8]}"
    _validate_run_id(rid)
    rws = runtime_workspace or _default_runtime_workspace(rid)
    state = DogfoodState(
        run_id=rid,
        task=task,
        phase=DogfoodPhase.PENDING,
        source_workspace=workspace,
        runtime_workspace=rws,
        merge_mode=merge_mode,
        dogfood_branch=f"dogfood/{rid}",
        worktree_workspace=_default_worktree_workspace(rid),
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

    Retries stay within the existing worktree (no re-isolation).
    Caller must call save_state() after this to persist the new state.
    """
    state.phase = DogfoodPhase.IMPLEMENT
    state.attempts += 1


# ---------------------------------------------------------------------------
# Isolation helpers (Step 16)
# ---------------------------------------------------------------------------

def _git(args: list[str], cwd: str, check: bool = True) -> subprocess.CompletedProcess:
    """Run a git command and return the result."""
    return subprocess.run(
        ["git"] + args, cwd=cwd,
        capture_output=True, text=True,
        check=check,
    )


def _safe_to_cleanup_partial_isolation(state: DogfoodState) -> bool:
    """True if a partial worktree can be safely removed."""
    wt = Path(state.worktree_workspace)
    return wt.exists() and state.isolation_status != "ready"


def _cleanup_partial_isolation(state: DogfoodState) -> None:
    """Remove a partial worktree and delete the dogfood branch if needed."""
    wt = Path(state.worktree_workspace)
    if wt.exists():
        try:
            _git(["worktree", "remove", "--force", str(wt)], cwd=state.source_workspace, check=False)
        except Exception:
            pass
    try:
        _git(["branch", "-D", state.dogfood_branch], cwd=state.source_workspace, check=False)
    except Exception:
        pass


def prepare_isolated_worktree(state: DogfoodState) -> None:
    """Create an isolated git worktree for the dogfood run.

    Populates state fields: source_branch, base_ref, worktree_workspace,
    isolation_status.  Raises GitWorktreeError on failure after one retry.
    """
    src = state.source_workspace

    # Refuse dirty source workspace
    dirty = _git(["status", "--porcelain"], cwd=src)
    if dirty.stdout.strip():
        state.isolation_status = "failed"
        raise GitWorktreeError(
            "Source workspace is dirty. Commit or stash changes before starting dogfood."
        )

    # Capture source branch and base ref
    branch_result = _git(["branch", "--show-current"], cwd=src)
    state.source_branch = branch_result.stdout.strip() or "HEAD"

    ref_result = _git(["rev-parse", "HEAD"], cwd=src)
    state.base_ref = ref_result.stdout.strip()

    wt = state.worktree_workspace or _default_worktree_workspace(state.run_id)
    state.worktree_workspace = wt
    branch = state.dogfood_branch or f"dogfood/{state.run_id}"
    state.dogfood_branch = branch

    for attempt in range(2):
        try:
            _git(
                ["worktree", "add", "-b", branch, wt, state.base_ref],
                cwd=src,
            )
            state.isolation_status = "ready"
            return
        except subprocess.CalledProcessError:
            if attempt == 0 and _safe_to_cleanup_partial_isolation(state):
                _cleanup_partial_isolation(state)
                continue
            state.isolation_status = "failed"
            raise GitWorktreeError(
                f"Failed to create worktree at {wt!r} on branch {branch!r}"
            )


# ---------------------------------------------------------------------------
# Finalize helpers (Step 16)
# ---------------------------------------------------------------------------

def finalize_dogfood_result(state: DogfoodState) -> dict[str, Any]:
    """Commit dogfood result in the worktree and record dogfood_commit.

    Returns a merge_report dict written to runtime_workspace.
    """
    wt = state.worktree_workspace
    if not wt or not Path(wt).exists():
        raise RuntimeError("worktree_workspace not available for FINALIZE")

    # Check we are on the dogfood branch
    cur_branch = _git(["branch", "--show-current"], cwd=wt).stdout.strip()
    if cur_branch != state.dogfood_branch:
        raise RuntimeError(
            f"Worktree is on {cur_branch!r}, expected {state.dogfood_branch!r}"
        )

    # Check for changes to commit
    diff = _git(["diff", "--name-only", "HEAD"], cwd=wt)
    untracked = _git(["ls-files", "--others", "--exclude-standard"], cwd=wt)
    changed_files = [
        f for f in (diff.stdout.strip() + "\n" + untracked.stdout.strip()).splitlines() if f
    ]

    if changed_files:
        _git(["add", "-A"], cwd=wt)
        task_summary = state.task[:72].replace('"', "'")
        _git(["commit", "-m", f"dogfood: {task_summary}"], cwd=wt)

    # Record dogfood commit
    head = _git(["rev-parse", "HEAD"], cwd=wt).stdout.strip()
    state.dogfood_commit = head

    # Generate merge report
    report: dict[str, Any] = {
        "source_workspace": state.source_workspace,
        "worktree_workspace": wt,
        "runtime_workspace": state.runtime_workspace,
        "source_branch": state.source_branch,
        "dogfood_branch": state.dogfood_branch,
        "base_ref": state.base_ref,
        "dogfood_commit": head,
        "changed_files": changed_files,
        "denied_path_hits": [],
        "policy_checks": {},
        "merge_status": "ready" if changed_files else "no_changes",
    }

    report_path = _artifact_path(state, "merge_report.json")
    _write_json(report_path, report)

    state.merge_status = "ready" if changed_files else "no_changes"
    return report


# ---------------------------------------------------------------------------
# Merge helpers (Step 16)
# ---------------------------------------------------------------------------

def _check_merge_policy(
    state: DogfoodState,
    policy: MergePolicy,
    changed_files: list[str],
) -> tuple[bool, str]:
    """Return (ok, reason). ok=False means policy rejected."""
    # Dirty source check
    if policy.require_clean_source:
        dirty = _git(["status", "--porcelain"], cwd=state.source_workspace, check=False)
        if dirty.stdout.strip():
            return False, "source_workspace is dirty"

    # Source drift check
    if not policy.allow_source_advanced:
        cur_ref = _git(["rev-parse", "HEAD"], cwd=state.source_workspace).stdout.strip()
        if cur_ref != state.base_ref:
            return False, f"source branch advanced: {state.base_ref[:8]}→{cur_ref[:8]}"

    # Dogfood commit required
    if policy.require_dogfood_commit and not state.dogfood_commit:
        return False, "dogfood_commit not recorded"

    # Denied path check
    for f in changed_files:
        for denied in policy.denied_paths:
            if f.startswith(denied) or denied in f:
                return False, f"denied path: {f}"

    # Allowed path check
    if policy.allowed_paths:
        for f in changed_files:
            if not any(f.startswith(p) for p in policy.allowed_paths):
                return False, f"file not in allowed_paths: {f}"

    return True, ""


def merge_dogfood_branch(
    state: DogfoodState,
    policy: MergePolicy | None = None,
) -> None:
    """Merge the dogfood branch into source_branch per policy.

    Updates state.merge_status, state.merged_commit, state.phase.
    """
    if policy is None:
        policy = MergePolicy(mode=state.merge_mode)  # type: ignore[arg-type]

    src = state.source_workspace

    # Crash recovery: dogfood commit already ancestor of source HEAD?
    if state.dogfood_commit:
        result = _git(
            ["merge-base", "--is-ancestor", state.dogfood_commit, "HEAD"],
            cwd=src, check=False,
        )
        if result.returncode == 0:
            head = _git(["rev-parse", "HEAD"], cwd=src).stdout.strip()
            state.merge_status = "merged"
            state.merged_commit = head
            state.phase = DogfoodPhase.COMPLETE
            return

    # Load changed files from merge_report if available
    report_path = _artifact_path(state, "merge_report.json")
    changed_files: list[str] = []
    if report_path.exists():
        try:
            report = json.loads(report_path.read_text(encoding="utf-8"))
            changed_files = report.get("changed_files", [])
        except Exception:
            pass

    # Policy checks
    ok, reason = _check_merge_policy(state, policy, changed_files)
    if not ok:
        state.merge_status = "policy_rejected"
        state.last_failure = reason
        state.phase = DogfoodPhase.BLOCKED
        return

    # Conflict check
    try:
        _git(["merge", "--no-commit", "--no-ff", state.dogfood_branch], cwd=src)
    except subprocess.CalledProcessError:
        # Conflict detected — cleanup and block
        _git(["reset", "--merge"], cwd=src, check=False)
        state.merge_status = "conflict"
        state.last_failure = "merge_conflict"
        state.phase = DogfoodPhase.BLOCKED
        return
    # No conflict — undo the tentative merge
    _git(["reset", "--merge"], cwd=src, check=False)

    # Actual merge
    try:
        _git(["merge", "--no-ff", state.dogfood_branch], cwd=src)
        head = _git(["rev-parse", "HEAD"], cwd=src).stdout.strip()
        state.merge_status = "merged"
        state.merged_commit = head
        state.phase = DogfoodPhase.COMPLETE
    except subprocess.CalledProcessError as exc:
        state.merge_status = "failed"
        state.last_failure = str(exc)
        state.phase = DogfoodPhase.BLOCKED


# ---------------------------------------------------------------------------
# Phase runners — wire Steps 3~6 + isolate/finalize/merge
# ---------------------------------------------------------------------------

def _build_interview_fn(
    non_interactive: bool,
) -> Callable[[str, str], dict[str, Any]]:
    """Return a run_interview wrapper with TTY-aware non_interactive flag."""
    from core.interview import run_interview as _run_iv
    effective = non_interactive or not sys.stdin.isatty()

    def _fn(task: str, workspace: str) -> dict[str, Any]:
        return _run_iv(task, workspace=workspace, non_interactive=effective)

    return _fn


def _run_interview_phase(
    state: DogfoodState,
    artifact: dict[str, Any],
    *,
    _interview_fn: Callable[[str, str], dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Record interview artifact path and return artifact."""
    if _interview_fn is not None:
        result = _interview_fn(state.task, state.workspace)
        if not result.get("ok"):
            raise RuntimeError(f"Interview failed: {result.get('reason', 'unknown')}")
        if "project_brief" not in result:
            import warnings
            warnings.warn(
                "_interview_fn result missing 'project_brief'; using minimal fallback",
                RuntimeWarning,
                stacklevel=2,
            )
        artifact = result.get("project_brief", {"goal": state.task})
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
    """Research execution — stub for future integration.

    Returns context unchanged; actual research invocation added later.
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
    *,
    _triad_critic_fn: Any | None = None,
    _triad_architect_fn: Any | None = None,
) -> dict[str, Any]:
    """Generate executable plan via 正反合 Triad review.

    1. 正 Planner: deterministic plan from spec+premortem (build_plan)
    2. 反 Critic: attack the plan — finds evidence-backed flaws
    3. 合 Architect: resolves findings → final plan

    Raises TriadBlockedError when unresolved Critical findings remain.
    Injectable _triad_critic_fn / _triad_architect_fn for tests.
    """
    from core.planner import build_plan
    from core.triad import TriadBlockedError, run_triad  # noqa: F401

    spec = _spec_from_dict(spec_dict)
    premortem = _premortem_from_dict(premortem_dict)
    plan = build_plan(spec, premortem)

    context = {
        "workspace": state.workspace,
        "spec": spec_dict,
        "premortem": premortem_dict,
    }
    triad_kwargs: dict[str, Any] = {}
    if _triad_critic_fn is not None:
        triad_kwargs["_critic_fn"] = _triad_critic_fn
    if _triad_architect_fn is not None:
        triad_kwargs["_architect_fn"] = _triad_architect_fn
    else:
        from core.architect_agent import architect_fn as _real_architect_fn
        triad_kwargs["_architect_fn"] = _real_architect_fn

    result = run_triad(plan.to_dict(), context, **triad_kwargs)

    path = _artifact_path(state, "plan.json")
    _write_json(path, result.final_plan)
    state.plan_path = str(path)
    return result.final_plan


def _run_isolate_phase(state: DogfoodState) -> dict[str, Any]:
    """Create the git worktree for isolated execution.

    Populates state.source_branch, state.base_ref, state.worktree_workspace,
    state.isolation_status.  Raises GitWorktreeError on failure.
    """
    prepare_isolated_worktree(state)
    return {
        "source_branch": state.source_branch,
        "base_ref": state.base_ref,
        "worktree_workspace": state.worktree_workspace,
        "isolation_status": state.isolation_status,
    }


def _run_implement_phase(state: DogfoodState, context: dict[str, Any]) -> dict[str, Any]:
    """Execute plan step commands and return impl_result dict.

    Loads the plan from state.plan_path when context["plan_dict"] is absent.
    Steps without commands are skipped (AI-coded steps need external invocation);
    their IDs are collected in "skipped_no_commands".

    Execution cwd: worktree_workspace when isolation is ready, else source_workspace.

    context keys:
      plan_dict — ExecutablePlan dict (overrides disk load)
    """
    plan_dict: dict[str, Any] = context.get("plan_dict") or {}
    if not plan_dict and state.plan_path:
        plan_path = Path(state.plan_path)
        if plan_path.exists():
            plan_dict = json.loads(plan_path.read_text(encoding="utf-8"))

    cwd = state._cwd()
    executed: list[dict[str, Any]] = []
    failures: list[str] = []
    skipped: list[str] = []

    for step in plan_dict.get("steps", []):
        commands: list[str] = step.get("commands") or []
        step_id: str = step.get("id", "?")
        if not commands:
            skipped.append(step_id)
            continue
        for cmd in commands:
            ok, output = _command_runner(cmd, cwd)
            executed.append({"step": step_id, "command": cmd, "ok": ok, "output": output})
            if not ok:
                failures.append(f"{step_id}: {cmd}")

    return {
        "executed": executed,
        "failures": failures,
        "skipped_no_commands": skipped,
        "ok": len(failures) == 0,
    }


def _run_verify_phase(state: DogfoodState, context: dict[str, Any]) -> dict[str, Any]:
    """Run verification commands and return a VerifyResult dict.

    Execution cwd: worktree_workspace when isolation is ready, else source_workspace.
    Commands are taken from context["commands"] first; if absent, falls back to
    context["plan_dict"]["verification_requirements"].  Empty command list → pass.
    """
    commands: list[str] = list(context.get("commands") or [])
    if not commands:
        plan_dict = context.get("plan_dict", {})
        commands = list(plan_dict.get("verification_requirements", []))

    cwd = state._cwd()
    failures: list[str] = []
    for cmd in commands:
        ok, _ = _command_runner(cmd, cwd)
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


def _run_finalize_phase(state: DogfoodState) -> dict[str, Any]:
    """Commit dogfood result in the worktree and prepare for merge."""
    return finalize_dogfood_result(state)


def _run_merge_phase(state: DogfoodState, merge_mode: str) -> dict[str, Any]:
    """Execute the merge lifecycle according to merge_mode.

    auto_policy: run policy checks + merge.
    manual: set merge_status=ready and stop (caller merges via 'dogfood merge').
    never: mark complete without merging.
    """
    if merge_mode == "never":
        state.merge_status = "never"
        state.phase = DogfoodPhase.COMPLETE
        return {"merge_status": "never"}

    if merge_mode == "manual":
        # Pipeline finishes (COMPLETE) but merge_status="ready" signals the git
        # merge has not happened — caller triggers it via 'dogfood merge <run_id>'.
        state.merge_status = "ready"
        state.phase = DogfoodPhase.COMPLETE
        return {"merge_status": "ready"}

    # auto_policy
    merge_dogfood_branch(state, MergePolicy(mode="auto_policy"))
    return {"merge_status": state.merge_status, "merged_commit": state.merged_commit}


# ---------------------------------------------------------------------------
# Public orchestration API
# ---------------------------------------------------------------------------

def run_all(
    task: str,
    workspace: str,
    *,
    interview_artifact: dict[str, Any] | None = None,
    non_interactive: bool = False,
    run_id: str | None = None,
    runtime_workspace: str | None = None,
    merge_mode: str = "auto_policy",
    _interview_fn: Callable[[str, str], dict[str, Any]] | None = None,
) -> "DogfoodState":
    """Run the complete dogfood pipeline: PENDING → ... → COMPLETE or BLOCKED.

    Phases execute sequentially. The IMPLEMENT → VERIFY → REVIEW loop repeats
    on retry until verification passes or max attempts are exhausted (BLOCKED).
    After REVIEW pass: FINALIZE commits the result, MERGE merges per merge_mode.

    interview_artifact: pre-built interview data; when None the INTERVIEW phase
        calls run_interview() interactively (TTY-detected) or non-interactively.
    non_interactive: force non-interactive interview (skip TTY detection).
    merge_mode: auto_policy | manual | never
    _interview_fn: injectable for tests; overrides the default run_interview wrapper.
    Returns the final DogfoodState (phase COMPLETE or BLOCKED).
    """
    state = create_run(
        task, workspace,
        run_id=run_id,
        runtime_workspace=runtime_workspace,
        merge_mode=merge_mode,
    )

    # Build interview callable only when no pre-built artifact is provided.
    effective_interview_fn: Callable[[str, str], dict[str, Any]] | None
    if interview_artifact is None:
        effective_interview_fn = _interview_fn or _build_interview_fn(non_interactive)
    else:
        effective_interview_fn = None

    interview: dict[str, Any] = interview_artifact if interview_artifact is not None else {"goal": task}
    research_brief: dict[str, Any] = {}
    research: dict[str, Any] = {}
    spec: dict[str, Any] = {}
    premortem: dict[str, Any] = {}
    plan_dict: dict[str, Any] = {}
    verify_result: dict[str, Any] = {}

    while not state.is_terminal():
        phase = state.phase

        if phase == DogfoodPhase.PENDING:
            advance_phase(state)
            save_state(state)
            continue

        if phase == DogfoodPhase.INTERVIEW:
            interview = run_phase(state, artifact=interview, _interview_fn=effective_interview_fn)
        elif phase == DogfoodPhase.RESEARCH_BRIEF:
            research_brief = run_phase(state, artifact=interview)
        elif phase == DogfoodPhase.RESEARCH:
            research = run_phase(state, context=research_brief)
        elif phase == DogfoodPhase.SPEC:
            spec = run_phase(
                state,
                interview_artifact=interview,
                research_artifact=research,
            )
        elif phase == DogfoodPhase.PREMORTEM:
            premortem = run_phase(state, spec_dict=spec)
        elif phase == DogfoodPhase.PLAN:
            from core.triad import TriadBlockedError
            try:
                plan_dict = run_phase(state, spec_dict=spec, premortem_dict=premortem)
            except TriadBlockedError as exc:
                block_run(state, str(exc))
                save_state(state)
                continue
        elif phase == DogfoodPhase.ISOLATE:
            try:
                run_phase(state)
            except GitWorktreeError as exc:
                block_run(state, str(exc))
                save_state(state)
                continue
        elif phase == DogfoodPhase.IMPLEMENT:
            run_phase(state, context={})
        elif phase == DogfoodPhase.VERIFY:
            verify_result = run_phase(state, context={"plan_dict": plan_dict})
        elif phase == DogfoodPhase.REVIEW:
            review = run_phase(state, context={"verify_result": verify_result})
            decision = review.get("decision", "pass")
            if decision == "retry":
                retry_run(state)
            elif decision == "block":
                block_run(state, review.get("reason", ""))
            else:
                advance_phase(state)  # → FINALIZE
            save_state(state)
            continue
        elif phase == DogfoodPhase.FINALIZE:
            try:
                run_phase(state)
            except Exception as exc:
                block_run(state, f"finalize failed: {exc}")
                save_state(state)
                continue
        elif phase == DogfoodPhase.MERGE:
            run_phase(state, merge_mode=merge_mode)
            # _run_merge_phase sets state.phase directly for COMPLETE/BLOCKED
            save_state(state)
            continue

        advance_phase(state)
        save_state(state)

    return state


def run_phase(state: DogfoodState, **kwargs: Any) -> dict[str, Any]:
    """Execute the current phase and return the resulting artifact dict.

    kwargs are passed through to the phase runner; each runner documents
    which keys it uses.  Unknown kwargs are silently ignored.
    """
    phase = state.phase
    if phase == DogfoodPhase.PENDING:
        return {}
    if phase == DogfoodPhase.INTERVIEW:
        return _run_interview_phase(
            state, kwargs.get("artifact", {}),
            _interview_fn=kwargs.get("_interview_fn"),
        )
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
            _triad_critic_fn=kwargs.get("_triad_critic_fn"),
            _triad_architect_fn=kwargs.get("_triad_architect_fn"),
        )
    if phase == DogfoodPhase.ISOLATE:
        return _run_isolate_phase(state)
    if phase == DogfoodPhase.IMPLEMENT:
        return _run_implement_phase(state, kwargs.get("context", {}))
    if phase == DogfoodPhase.VERIFY:
        return _run_verify_phase(state, kwargs.get("context", {}))
    if phase == DogfoodPhase.REVIEW:
        return _run_review_phase(state, kwargs.get("context", {}))
    if phase == DogfoodPhase.FINALIZE:
        return _run_finalize_phase(state)
    if phase == DogfoodPhase.MERGE:
        return _run_merge_phase(state, kwargs.get("merge_mode", state.merge_mode))
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
