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

import ast
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
from typing import Any, Callable, Final, Literal, Tuple

# ---------------------------------------------------------------------------
# Artifact filename constants (SSOT — never use raw strings for these paths)
# ---------------------------------------------------------------------------

ARTIFACT_STATE: Final = "dogfood_state.json"
ARTIFACT_INTERVIEW: Final = "interview.json"
ARTIFACT_RESEARCH_BRIEF: Final = "research_brief.json"
ARTIFACT_RESEARCH: Final = "research.json"
ARTIFACT_SPEC: Final = "spec.json"
ARTIFACT_PLAN: Final = "plan.json"
ARTIFACT_MERGE_REPORT: Final = "merge_report.json"
ARTIFACT_PHASE_TRACE: Final = "phase_trace.jsonl"

ArtifactName = Literal[
    "dogfood_state.json",
    "interview.json",
    "research_brief.json",
    "research.json",
    "spec.json",
    "plan.json",
    "merge_report.json",
    "phase_trace.jsonl",
]

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
    isolation_status: str = "pending"   # pending | ready | failed | cleaned | worktree_removed | cleanup_failed
    # Disambiguates a "cleanup_failed" label: "wt_never_created" means cleanup
    # was intentionally skipped (worktree never existed → branch ownership
    # unconfirmed, branch preserved), not an actual removal failure. "" = real failure.
    cleanup_skip_reason: str = ""
    merge_status: str = "none"          # none | ready | merged | conflict | policy_rejected | failed
    merge_mode: str = "auto_policy"     # auto_policy | manual | never
    dogfood_commit: str = ""
    merged_commit: str = ""

    # artifact paths
    interview_path: str = ""
    research_brief_path: str = ""
    research_path: str = ""
    spec_path: str = ""
    plan_path: str = ""

    # runtime tracking
    attempts: int = 0
    last_failure: str = ""
    next_action: str = ""
    approval_policy: str = ""
    completion_criteria: list[str] = field(default_factory=list)

    # F-RUN-BUDGET-STATE: snapshot of core.run_budget singleton for restart survival
    budget_consumed: int = 0
    budget_max_tokens: int = 0
    budget_stopped: bool = False
    budget_project_id: str = ""

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
            "cleanup_skip_reason": self.cleanup_skip_reason,
            "merge_status": self.merge_status,
            "merge_mode": self.merge_mode,
            "dogfood_commit": self.dogfood_commit,
            "merged_commit": self.merged_commit,
            "interview_path": self.interview_path,
            "research_brief_path": self.research_brief_path,
            "research_path": self.research_path,
            "spec_path": self.spec_path,
            "plan_path": self.plan_path,
            "attempts": self.attempts,
            "last_failure": self.last_failure,
            "next_action": self.next_action,
            "approval_policy": self.approval_policy,
            "completion_criteria": self.completion_criteria,
            "budget_consumed": self.budget_consumed,
            "budget_max_tokens": self.budget_max_tokens,
            "budget_stopped": self.budget_stopped,
            "budget_project_id": self.budget_project_id,
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
            cleanup_skip_reason=data.get("cleanup_skip_reason", ""),
            merge_status=data.get("merge_status", "none"),
            merge_mode=data.get("merge_mode", "auto_policy"),
            dogfood_commit=data.get("dogfood_commit", ""),
            merged_commit=data.get("merged_commit", ""),
            interview_path=data.get("interview_path", ""),
            research_brief_path=data.get("research_brief_path", ""),
            research_path=data.get("research_path", ""),
            spec_path=data.get("spec_path", ""),
            plan_path=data.get("plan_path", ""),
            attempts=data.get("attempts", 0),
            last_failure=data.get("last_failure", ""),
            next_action=data.get("next_action", ""),
            approval_policy=data.get("approval_policy", ""),
            completion_criteria=data.get("completion_criteria", []),
            budget_consumed=int(data.get("budget_consumed", 0) or 0),
            budget_max_tokens=int(data.get("budget_max_tokens", 0) or 0),
            budget_stopped=bool(data.get("budget_stopped", False)),
            budget_project_id=data.get("budget_project_id", "") or "",
        )


# ---------------------------------------------------------------------------
# MergePolicy dataclass
# ---------------------------------------------------------------------------

# Valid merge modes — enforced at run entry (create_run) and policy construction
# (MergePolicy.__post_init__) so an unexpected value fails closed instead of
# falling through to auto_policy.
VALID_MERGE_MODES: Final[frozenset[str]] = frozenset({"auto_policy", "manual", "never"})


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
    denied_paths: list[str] = field(default_factory=list)
    # Allow VERIFY to proceed even when IMPLEMENT has failures.
    # Incompatible with auto_policy: partial results cannot auto-merge safely.
    allow_partial_impl: bool = False
    # When True, remove the worktree on BLOCKED (save disk space).
    # Default False — preserve for debugging.  Failed isolations are always cleaned.
    cleanup_worktree_on_block: bool = False

    def __post_init__(self) -> None:
        if self.mode not in VALID_MERGE_MODES:
            raise ValueError(
                f"invalid merge mode: {self.mode!r}."
                f" Expected one of {sorted(VALID_MERGE_MODES)}."
            )
        if self.allow_partial_impl and self.mode == "auto_policy":
            raise ValueError(
                "allow_partial_impl=True is incompatible with mode='auto_policy'."
                " Use mode='manual' or 'never' to proceed with partial results."
            )


# Paths always blocked from dogfood merges unless overridden via MergePolicy.
DEFAULT_DENIED_PATHS: Final[tuple[str, ...]] = (
    ".af_runtime/",
    "runtime/",
    "skills/registry.yaml",
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
        # On Windows, cmd.exe treats < > as redirect metacharacters, breaking
        # commands like `grep -n '<module>'`. PowerShell handles single-quoted
        # strings and < correctly, matching Unix shell conventions.
        if os.name == "nt":
            # catch{exit 1} converts CommandNotFoundException (grep not on PATH)
            # to rc=1 so VERIFY does not silently pass on bare Windows. The
            # if($LASTEXITCODE) block propagates native-exe exit codes; when
            # $LASTEXITCODE is null (pure-PS success) we fall through and exit 0.
            ps_cmd = (
                f"try {{ & {{ {cmd} }} }} catch {{ exit 1 }}; "
                f"if ($LASTEXITCODE) {{ exit $LASTEXITCODE }}"
            )
            args = ["powershell.exe", "-NonInteractive", "-Command", ps_cmd]
            result = subprocess.run(
                args, cwd=cwd,
                capture_output=True, text=True, encoding="utf-8", errors="replace",
                timeout=60, env=_utf8_subprocess_env(),
            )
        else:
            result = subprocess.run(
                cmd, shell=True, cwd=cwd,
                capture_output=True, text=True, encoding="utf-8", errors="replace",
                timeout=60, env=_utf8_subprocess_env(),
            )
        return result.returncode == 0, (result.stdout + result.stderr).strip()
    except Exception as exc:
        return False, str(exc)


# Injectable for tests: monkeypatch core.dogfood._command_runner
_command_runner: Callable[[str, str], Tuple[bool, str]] = _default_command_runner


def _build_ai_task(step: dict[str, Any], plan_intent: str) -> str:
    """Build a task description for the AI executor from a plan step."""
    parts = [f"Plan intent: {plan_intent}", "", f"Step {step.get('id', '?')}: {step.get('action', '')}"]
    if step.get("target"):
        parts.append(f"Target: {step['target']}")
    artifacts = step.get("artifacts") or []
    if artifacts:
        parts.append(f"Files to create/modify: {', '.join(artifacts)}")
    references = step.get("reference_artifacts") or []
    if references:
        parts.append(f"Reference files (read-only context for existing patterns): {', '.join(references)}")
    tests = step.get("tests_required") or []
    if tests:
        parts.append(f"Tests required: {', '.join(tests)}")
    parts.append("\nImplement this step. Write production-quality code. Do not modify files outside the listed artifacts.")
    return "\n".join(parts)


def _record_run_budget(text: str) -> None:
    """Best-effort dogfood budget accounting for direct CLI executor calls."""
    if not str(text or "").strip():
        return
    try:
        from core.run_budget import get_run_budget
        get_run_budget().record(str(text))
    except Exception:
        pass


def _run_budget_exhausted() -> bool:
    try:
        from core.run_budget import get_run_budget
        return bool(get_run_budget().is_exhausted())
    except Exception:
        return False


def _default_ai_executor(task: str, *, cwd: str, run_id: str) -> dict[str, Any]:
    """Call claude_cli to execute an AI-coded plan step in the worktree."""
    from core.providers.cli import CliChatRequest, execute_cli_chat  # noqa: PLC0415
    request = CliChatRequest(
        provider_id="claude_cli",
        model="",
        system_prompt=(
            "You are implementing a software task inside a git worktree. "
            "Make only the changes described. Do not modify files outside the listed artifacts."
        ),
        task_input=task,
        workspace=cwd,
        run_id=run_id,
        auto_approve=True,
    )
    return execute_cli_chat(request)


# Injectable for tests: monkeypatch core.dogfood._ai_executor
_ai_executor: Callable[..., dict[str, Any]] = _default_ai_executor


def _utf8_subprocess_env() -> dict[str, str]:
    """Environment for subprocesses that must not depend on OS locale."""
    env = os.environ.copy()
    env.setdefault("PYTHONUTF8", "1")
    env.setdefault("PYTHONIOENCODING", "utf-8")
    env.setdefault("LANG", "C.UTF-8")
    env.setdefault("LC_ALL", "C.UTF-8")
    return env


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
    return Path(state.runtime_workspace) / "dogfood" / state.run_id / ARTIFACT_STATE


def _snapshot_run_budget(state: DogfoodState) -> None:
    """Sync core.run_budget singleton into state fields (F-RUN-BUDGET-STATE)."""
    try:
        from core.run_budget import get_run_budget
        budget = get_run_budget()
        state.budget_consumed = int(budget.consumed)
        state.budget_max_tokens = int(budget.max_tokens)
        state.budget_stopped = bool(budget.stopped)
        state.budget_project_id = str(budget.project_id or "")
    except Exception:
        pass  # singleton snapshot is best-effort — must not crash persistence


def _restore_run_budget(state: DogfoodState) -> None:
    """Re-hydrate core.run_budget singleton from state fields (F-RUN-BUDGET-STATE)."""
    if state.budget_max_tokens <= 0 and state.budget_consumed <= 0:
        return  # no budget tracking was active
    try:
        from core.run_budget import set_run_budget, get_run_budget
        set_run_budget(
            state.budget_max_tokens,
            run_id=state.run_id,
            project_id=state.budget_project_id,
        )
        budget = get_run_budget()
        budget.consumed = state.budget_consumed
        budget.stopped = state.budget_stopped
        if state.budget_max_tokens > 0 and state.budget_consumed >= state.budget_max_tokens * 0.8:
            budget.warned_80 = True
    except Exception:
        pass  # restoration is best-effort


def save_state(state: DogfoodState) -> None:
    """Persist state to disk (atomic write via temp-file + replace)."""
    _snapshot_run_budget(state)
    path = _state_path(state)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(state.to_dict(), indent=2), encoding="utf-8")
    tmp.replace(path)


def load_state(runtime_workspace: str, run_id: str) -> DogfoodState:
    """Load state from disk."""
    _validate_run_id(run_id)
    path = Path(runtime_workspace) / "dogfood" / run_id / ARTIFACT_STATE
    data = load_policy_json(path, required=True)
    state = DogfoodState.from_dict(data)
    _restore_run_budget(state)
    return state


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
    if merge_mode not in VALID_MERGE_MODES:
        raise ValueError(
            f"invalid merge_mode: {merge_mode!r}."
            f" Expected one of {sorted(VALID_MERGE_MODES)}."
        )
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

def _git(
    args: list[str],
    cwd: str,
    check: bool = True,
    extra_env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess:
    """Run a git command and return the result."""
    env = _utf8_subprocess_env()
    if extra_env:
        env = {**env, **extra_env}
    return subprocess.run(
        ["git"] + args, cwd=cwd,
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        env=env,
        check=check,
    )


def _is_crlf_only_diff(filepath: str, cwd: str) -> bool:
    """Return True iff the only diff for filepath is CR/LF line-ending noise."""
    r = _git(["diff", "--ignore-cr-at-eol", "--", filepath], cwd=cwd, check=False)
    return r.returncode == 0 and not r.stdout.strip()


def _dirty_files(
    workspace: str,
    *,
    include_untracked: bool,
    ignore_crlf: bool,
) -> list[str]:
    """Return list of dirty files in workspace.

    Single policy entry-point used by prepare/finalize/merge so all three
    callers apply identical dirty-detection semantics.

    include_untracked: include untracked files (git status '??' entries)
    ignore_crlf: filter out files where the only diff is CR/LF noise.
        Untracked files (no index version) are exempt from CRLF filtering —
        git diff returns empty for them, which would otherwise wrongly drop them.

    Raises:
        GitWorktreeError: if `git status` exits non-zero. All 5 current callers
            guard with try/except, so this does not crash the pipeline.
    """
    ut_flag = [] if include_untracked else ["--untracked-files=no"]
    result = _git(["status", "--porcelain"] + ut_flag, cwd=workspace, check=False)
    if result.returncode != 0:
        raise GitWorktreeError(f"git status failed (rc={result.returncode}): {workspace}")
    entries: list[tuple[str, bool]] = []  # (name, is_untracked)
    for line in result.stdout.splitlines():
        if not line.strip():
            continue
        is_untracked = line[:2].strip() == "??"
        name = line[3:]
        if " -> " in name:
            name = name.split(" -> ", 1)[1]
        entries.append((name, is_untracked))
    if ignore_crlf:
        return [
            name for name, is_untracked in entries
            if is_untracked or not _is_crlf_only_diff(name, workspace)
        ]
    return [name for name, _ in entries]


def _safe_to_cleanup_partial_isolation(state: DogfoodState) -> bool:
    """True if a partial worktree can be safely removed."""
    wt = Path(state.worktree_workspace)
    return wt.exists() and state.isolation_status != "ready"


def _cleanup_partial_isolation(state: DogfoodState) -> None:
    """Remove a partial (failed) worktree and delete the dogfood branch.

    Used only for failed isolations — branch has no meaningful commits yet.
    For successful isolations (isolation_status=="ready"), use
    _remove_worktree_only() to preserve the branch.

    The branch is only deleted when the worktree was present before cleanup.
    If the worktree never existed (e.g. ISOLATE failed before git worktree add,
    or the branch already existed and git worktree add rejected it), we cannot
    confirm this run created the branch — skip branch deletion to avoid
    removing a pre-existing branch unrelated to this run.
    """
    wt = Path(state.worktree_workspace)
    wt_was_present = wt.exists()
    if wt_was_present:
        try:
            _git(["worktree", "remove", "--force", str(wt)], cwd=state.source_workspace, check=False)
        except Exception:
            pass
    # Only delete the branch if this run's worktree was present — that confirms
    # git worktree add -b succeeded and this run owns the branch.
    if wt_was_present and state.dogfood_branch:
        try:
            _git(["branch", "-D", state.dogfood_branch], cwd=state.source_workspace, check=False)
        except Exception:
            pass


def _branch_exists(branch_name: str, cwd: str) -> "bool | None":
    """Return True if branch exists, False if absent, None if git is unavailable.

    Callers must treat None as "cannot verify" and default to cleanup_failed.
    """
    if not branch_name:
        return False
    try:
        r = _git(["branch", "--list", branch_name], cwd=cwd, check=False)
        return bool(r.stdout.strip())
    except Exception:
        return None  # git unavailable or invalid cwd — caller decides


def _remove_worktree_only(state: DogfoodState) -> bool:
    """Remove the worktree but keep the dogfood branch intact.

    Used when isolation_status=="ready" so that dogfood_commit (if created
    during FINALIZE) remains reachable via the branch.

    Refuses to remove a dirty worktree (uncommitted artifacts would be lost).
    Returns True iff the worktree was actually removed; False if it still exists
    (either because it was dirty or because git worktree remove failed).
    """
    wt = Path(state.worktree_workspace)
    if not wt.exists():
        return True
    # Fail-safe: do not force-remove uncommitted work from the worktree.
    try:
        dirty = _dirty_files(str(wt), include_untracked=True, ignore_crlf=True)
    except Exception:
        return False  # cannot verify dirtiness — preserve worktree
    if dirty:
        return False  # preserve — uncommitted work present
    try:
        _git(["worktree", "remove", "--force", str(wt)], cwd=state.source_workspace, check=False)
    except Exception:
        pass
    return not wt.exists()


def _handle_blocked_worktree(state: DogfoodState, *, cleanup_on_block: bool) -> None:
    """Apply worktree cleanup policy when a run transitions to BLOCKED.

    isolation_status == "pending"        → no worktree exists; no-op.
    isolation_status == "failed"         → partial worktree + branch; always clean up.
                                           Sets "cleaned" when both are gone, else "cleanup_failed".
                                           If branch-existence cannot be verified, sets "cleanup_failed".
    isolation_status == "ready"          → worktree removed (branch preserved so that
                                           any dogfood_commit stays reachable); only
                                           when cleanup_on_block=True.
                                           Sets "worktree_removed" (not "cleaned" — branch still exists).
    "cleaned"         = worktree + branch both gone.
    "worktree_removed"= worktree gone, branch preserved (ready path only).
    "cleanup_failed"  = cleanup attempted but something still exists, or could not be verified.
    """
    status = state.isolation_status
    if status in ("pending", "cleaned", "worktree_removed", "cleanup_failed"):
        return
    try:
        if status == "failed":
            # Capture before cleanup: if the worktree never existed,
            # _cleanup_partial_isolation intentionally skips branch deletion
            # (cannot confirm this run owns the branch). A surviving branch in
            # that case is an intentional skip, not a removal failure.
            wt_was_present = Path(state.worktree_workspace).exists()
            _cleanup_partial_isolation(state)
            wt_gone = not Path(state.worktree_workspace).exists()
            branch_result = _branch_exists(state.dogfood_branch, state.source_workspace)
            if branch_result is None:
                # git unavailable — cannot confirm branch is gone; mark cleanup_failed
                state.isolation_status = "cleanup_failed"
                return
            branch_gone = not branch_result
            if wt_gone and branch_gone:
                state.isolation_status = "cleaned"
            elif not wt_was_present and not branch_gone:
                # Worktree never created → branch deletion skipped by design.
                # Not a failure — record reason so debugging doesn't false-alarm.
                state.isolation_status = "cleanup_failed"
                state.cleanup_skip_reason = "wt_never_created"
            else:
                state.isolation_status = "cleanup_failed"
            return
        # status == "ready"
        if cleanup_on_block:
            removed = _remove_worktree_only(state)
            # Branch is intentionally preserved — use "worktree_removed", not "cleaned"
            state.isolation_status = "worktree_removed" if removed else "cleanup_failed"
    except Exception:
        state.isolation_status = "cleanup_failed"


def prepare_isolated_worktree(state: DogfoodState) -> None:
    """Create an isolated git worktree for the dogfood run.

    Populates state fields: source_branch, base_ref, worktree_workspace,
    isolation_status.  Raises GitWorktreeError on failure after one retry.
    """
    src = state.source_workspace

    # Refuse dirty source workspace (tracked changes only; untracked not copied to worktree).
    # CRLF-only diffs (Windows↔Mac EOL noise) are ignored — same policy as FINALIZE/MERGE.
    real_dirty = _dirty_files(src, include_untracked=False, ignore_crlf=True)
    if real_dirty:
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

FINAL_DOC_PATHS = (
    "Master_Blueprint.md",
    "docs/code_review/code-review.md",
)


def _run_final_docs_sync(state: DogfoodState) -> list[str]:
    """Best-effort final documentation sync for dogfood result commits.

    Dogfood semantics treat REVIEW → FINALIZE as the point where a feature is
    finalized. Running the docs sync here makes Blueprint/code-review updates
    part of the dogfood result instead of relying only on commit hooks.
    """
    workspace = state.worktree_workspace
    if not workspace:
        return []
    context = f"dogfood finalize: {state.task[:120]}"
    updated: list[str] = []
    try:
        from scripts import blueprint_updater
        if blueprint_updater.update_blueprint(workspace, context, no_llm=True):
            updated.append("Master_Blueprint.md")
    except Exception:
        pass
    try:
        from scripts import code_review_updater
        if code_review_updater.update_code_review_doc(workspace, context, no_llm=True):
            updated.append("docs/code_review/code-review.md")
    except Exception:
        pass
    return updated


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

    pre_finalize_head = _git(["rev-parse", "HEAD"], cwd=wt).stdout.strip()
    final_docs_synced = _run_final_docs_sync(state)

    # Collect all dirty files (tracked modified + untracked) via unified policy helper.
    # CRLF filtering only applies to tracked files — untracked files are newly created
    # and have no index version to diff against, so _is_crlf_only_diff would return True
    # for them (empty diff == no tracked baseline), which would silently drop them.
    all_dirty = _dirty_files(wt, include_untracked=True, ignore_crlf=False)
    tracked_dirty_set = set(_dirty_files(wt, include_untracked=False, ignore_crlf=False))
    real_dirty = [
        f for f in all_dirty
        if f not in tracked_dirty_set  # untracked (newly created): always real
        or not _is_crlf_only_diff(f, wt)  # tracked: apply CRLF filter
    ]

    # Build allowlist from plan artifacts + tests_required
    plan_allowlist: set[str] = set()
    if state.plan_path:
        _plan_path = Path(state.plan_path)
        if _plan_path.exists():
            _plan_data = json.loads(_plan_path.read_text(encoding="utf-8"))
            for _step in _plan_data.get("steps", []):
                for _f in (_step.get("artifacts") or []):
                    plan_allowlist.add(_f.replace("\\", "/"))
                for _f in (_step.get("tests_required") or []):
                    plan_allowlist.add(_f.replace("\\", "/"))
    if plan_allowlist and (
        final_docs_synced or any(f.replace("\\", "/").startswith("core/") for f in real_dirty)
    ):
        plan_allowlist.update(FINAL_DOC_PATHS)

    if real_dirty and plan_allowlist:
        stage_files = [f for f in real_dirty if f.replace("\\", "/") in plan_allowlist]
        scope_violations = [f for f in real_dirty if f not in stage_files]
    elif real_dirty:
        stage_files = list(real_dirty)
        scope_violations = []
    else:
        stage_files = []
        scope_violations = []

    if stage_files:
        _git(["add", "--"] + stage_files, cwd=wt)
        task_summary = state.task[:72].replace('"', "'")
        _git(
            ["commit", "-m", f"dogfood: {task_summary}"],
            cwd=wt,
            extra_env={"AF_SKIP_REVIEW_GATE": "1"},
        )

    # Record dogfood commit and whether a new commit was actually created
    head = _git(["rev-parse", "HEAD"], cwd=wt).stdout.strip()
    dogfood_commit_created = head != pre_finalize_head
    state.dogfood_commit = head

    # committed_changed: files in base_ref..HEAD (survives AI-commit advances)
    if dogfood_commit_created and state.base_ref:
        _committed = _git(
            ["diff", "--name-only", f"{state.base_ref}..HEAD"], cwd=wt, check=False
        )
        committed_changed = [f for f in _committed.stdout.splitlines() if f]
    else:
        committed_changed = []

    # Generate merge report
    report: dict[str, Any] = {
        "source_workspace": state.source_workspace,
        "worktree_workspace": wt,
        "runtime_workspace": state.runtime_workspace,
        "source_branch": state.source_branch,
        "dogfood_branch": state.dogfood_branch,
        "base_ref": state.base_ref,
        "dogfood_commit": head,
        "dogfood_commit_created": dogfood_commit_created,
        "changed_files": committed_changed,
        "all_dirty_files": all_dirty,
        "final_docs_synced": final_docs_synced,
        "scope_violations": scope_violations,
        "denied_path_hits": [],
        "policy_checks": {},
        "merge_status": "ready" if committed_changed else "no_changes",
    }

    report_path = _artifact_path(state, ARTIFACT_MERGE_REPORT)
    atomic_write_json(report_path, report)

    state.merge_status = "ready" if committed_changed else "no_changes"
    return report


# ---------------------------------------------------------------------------
# Merge helpers (Step 16)
# ---------------------------------------------------------------------------

def _check_merge_policy(
    state: DogfoodState,
    policy: MergePolicy,
    changed_files: list[str],
    scope_violations: list[str] | None = None,
) -> tuple[bool, str]:
    """Return (ok, reason). ok=False means policy rejected."""
    # Scope violation check (CRLF-only files are already filtered by finalize)
    if scope_violations:
        return False, f"scope_violations: {', '.join(scope_violations[:3])}"

    # Dirty source check (CRLF-only noise filtered — same policy as ISOLATE/FINALIZE)
    if policy.require_clean_source:
        if _dirty_files(state.source_workspace, include_untracked=False, ignore_crlf=True):
            return False, "source_workspace is dirty"

    # Source drift check
    if not policy.allow_source_advanced:
        cur_ref = _git(["rev-parse", "HEAD"], cwd=state.source_workspace).stdout.strip()
        if cur_ref != state.base_ref:
            return False, f"source branch advanced: {state.base_ref[:8]}→{cur_ref[:8]}"

    # Dogfood commit required — verify a *new* commit was created, not just any SHA
    if policy.require_dogfood_commit and (
        not state.dogfood_commit or state.dogfood_commit == state.base_ref
    ):
        return False, "dogfood_commit not recorded"

    # Denied path check — boundary-aware to avoid false positives:
    # "runtime/" must not match "myruntime/foo" via substring.
    for f in changed_files:
        for denied in policy.denied_paths:
            if f == denied or f.startswith(denied.rstrip("/") + "/"):
                return False, f"denied path: {f}"

    # Allowed path check — boundary-aware: exact match for files, directory
    # boundary for dir entries. Plain startswith() is fail-open: it would let
    # "core/utils.py.bak" pass an allowlist of "core/utils.py".
    if policy.allowed_paths:
        for f in changed_files:
            if not any(
                f == p or f.startswith(p.rstrip("/") + "/")
                for p in policy.allowed_paths
            ):
                return False, f"file not in allowed_paths: {f}"

    return True, ""


def build_merge_policy(state: DogfoodState, mode: str | None = None) -> MergePolicy:
    """Construct the MergePolicy for a dogfood merge from the plan-derived allowlist.

    Both the manual path (merge_dogfood_branch with policy=None) and the auto
    path (_run_merge_phase) MUST route through this so scope enforcement is
    identical. Constructing a bare MergePolicy elsewhere leaves allowed_paths
    empty, which disables the allowed-path gate in _check_merge_policy() and
    lets IMPLEMENT commits bypass scope boundaries on auto-merge.
    """
    allowed: list[str] = []
    has_core_allowed = False
    if state.plan_path:
        _pd = load_policy_json(Path(state.plan_path), required=False)
        for _s in _pd.get("steps", []):
            for _f in (_s.get("artifacts") or []):
                rel = _f.replace("\\", "/")
                allowed.append(rel)
                has_core_allowed = has_core_allowed or rel.startswith("core/")
            for _f in (_s.get("tests_required") or []):
                rel = _f.replace("\\", "/")
                allowed.append(rel)
                has_core_allowed = has_core_allowed or rel.startswith("core/")
    if has_core_allowed:
        allowed.extend(FINAL_DOC_PATHS)
    return MergePolicy(  # type: ignore[arg-type]
        # None means "use state default"; an explicit invalid string (e.g. "")
        # must reach __post_init__ and raise, not silently coerce to the default.
        mode=state.merge_mode if mode is None else mode,
        allowed_paths=list(dict.fromkeys(allowed)),
        denied_paths=list(DEFAULT_DENIED_PATHS),
    )


def merge_dogfood_branch(
    state: DogfoodState,
    policy: MergePolicy | None = None,
) -> None:
    """Merge the dogfood branch into source_branch per policy.

    Updates state.merge_status, state.merged_commit, state.phase.
    """
    if policy is None:
        policy = build_merge_policy(state)

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

    # Load changed files and scope_violations from merge_report.
    # Corrupt JSON is fatal (always raises JSONDecodeError).
    # Missing report with a recorded dogfood_commit is ambiguous — cannot verify
    # changed files → reject rather than allowing scope-unchecked merge.
    report_path = _artifact_path(state, ARTIFACT_MERGE_REPORT)
    report = load_policy_json(report_path, required=False)
    if not report and state.dogfood_commit:
        state.merge_status = "policy_rejected"
        state.last_failure = "merge_report missing: cannot verify changed files"
        state.phase = DogfoodPhase.BLOCKED
        return
    changed_files: list[str] = report.get("changed_files", [])
    scope_violations: list[str] = report.get("scope_violations", [])

    # Policy checks
    ok, reason = _check_merge_policy(state, policy, changed_files, scope_violations)
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
    path = _artifact_path(state, ARTIFACT_INTERVIEW)
    atomic_write_json(path, artifact or {})
    state.interview_path = str(path)
    return artifact


def _run_research_brief_phase(
    state: DogfoodState, artifact: dict[str, Any]
) -> dict[str, Any]:
    """Build ResearchBrief from interview artifact."""
    from core.research_brief import build_from_interview
    brief = build_from_interview(artifact)
    path = _artifact_path(state, ARTIFACT_RESEARCH_BRIEF)
    atomic_write_json(path, brief.to_dict())
    state.research_brief_path = str(path)
    return brief.to_dict()


_RESEARCH_FILE_CAP = 8_000   # chars per source file
_RESEARCH_TEST_CAP = 4_000   # chars per test file


def _research_load_interview(state: DogfoodState) -> dict[str, Any]:
    if state.interview_path:
        try:
            return json.loads(Path(state.interview_path).read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def _research_scope_files(interview: dict[str, Any], workspace: str) -> list[str]:
    """Return .py files from scope that actually exist in workspace.

    Resolution order mirrors spec_compiler.compile_spec:
      1. explicit ``scope`` field
      2. ``clarification_log`` entries with category='scope' (interactive runs)
      3. file-path tokens extracted from intent string (non-interactive runs)

    All returned paths are confirmed inside *workspace* (no traversal).
    """
    from core.spec_compiler import _scope_from_clarification_log, _scope_from_intent, _str_list  # lazy import — matches pattern used elsewhere in this file
    src = interview.get("project_brief") or interview
    raw_scope: list[str] = [s for s in _str_list(src.get("scope")) if s.endswith(".py")]
    if not raw_scope:
        raw_scope = [p for p in _scope_from_clarification_log(src) if p.endswith(".py")]
    if not raw_scope:
        intent = str(src.get("goal") or src.get("task_input") or "").strip()
        raw_scope = [p for p in _scope_from_intent(intent) if p.endswith(".py")]
    ws_resolved = Path(workspace).resolve()
    return [
        p for p in raw_scope
        if Path(workspace, p).resolve().is_relative_to(ws_resolved) and Path(workspace, p).exists()
    ]


def _research_collect_refs(
    scope: list[str], workspace: str
) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    seen: set[str] = set()
    scope_set = set(scope)
    for filepath in scope:
        if filepath in seen:
            continue
        seen.add(filepath)
        full = Path(workspace, filepath)
        content = full.read_text(encoding="utf-8", errors="replace")[: _RESEARCH_FILE_CAP]
        refs.append({"path": filepath, "content": content, "kind": "source"})
        # Companion test file — skip if already in scope (will be read as source above)
        test_rel = str(Path("tests", f"test_{full.name}"))
        if test_rel not in scope_set:
            test_path = Path(workspace, test_rel)
            if test_path.exists():
                tc = test_path.read_text(encoding="utf-8", errors="replace")[: _RESEARCH_TEST_CAP]
                refs.append({"path": test_rel, "content": tc, "kind": "test"})
                seen.add(test_rel)
    return refs


def _run_research_phase(state: DogfoodState, context: dict[str, Any]) -> dict[str, Any]:
    """Collect code context for scope files (source + companion tests).

    Returns an evidence bundle {local_refs: [...]} consumed by spec_compiler.
    Falls back to empty bundle when interview_path is absent or scope is empty.
    """
    interview = _research_load_interview(state)
    scope = _research_scope_files(interview, state.source_workspace)
    local_refs = _research_collect_refs(scope, state.source_workspace) if scope else []
    artifact: dict[str, Any] = {"local_refs": local_refs}
    path = _artifact_path(state, ARTIFACT_RESEARCH)
    atomic_write_json(path, artifact)
    state.research_path = str(path)
    return artifact


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
    path = _artifact_path(state, ARTIFACT_SPEC)
    atomic_write_json(path, spec.to_dict())
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

    path = _artifact_path(state, ARTIFACT_PLAN)
    atomic_write_json(path, result.final_plan)
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


_FINGERPRINT_SIZE_THRESHOLD = 65_536  # 64 KB — use hash below, size+mtime above


def _fingerprint_untracked(cwd: str) -> dict[str, Any]:
    """Return {relpath: fingerprint} for every untracked file in *cwd*.

    Fingerprint is a SHA-1 hex string for files ≤ _FINGERPRINT_SIZE_THRESHOLD bytes,
    or a (size, mtime_ns) tuple for larger files (avoids reading large binaries).
    Missing/unreadable files are silently skipped.
    """
    import hashlib
    try:
        names = _git(
            ["ls-files", "--others", "--exclude-standard"], cwd=cwd, check=False
        ).stdout.splitlines()
    except (OSError, FileNotFoundError):
        return {}
    result: dict[str, Any] = {}
    for name in names:
        p = Path(cwd) / name
        try:
            st = p.stat()
            if st.st_size <= _FINGERPRINT_SIZE_THRESHOLD:
                result[name] = hashlib.sha1(p.read_bytes(), usedforsecurity=False).hexdigest()
            else:
                result[name] = (st.st_size, st.st_mtime_ns)
        except (OSError, FileNotFoundError):
            # File listed by git but unreadable — record as present with unknown fingerprint.
            result[name] = None
    return result


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
        plan_dict = load_policy_json(Path(state.plan_path), required=False)

    cwd = state._cwd()
    if context.get("preflight_static"):
        preflight_failures = _pre_implement_static_smoke(plan_dict, cwd)
        if preflight_failures:
            return {
                "executed": [],
                "failures": preflight_failures,
                "skipped_no_commands": [],
                "actual_changed": [],
                "ok": False,
            }

    # P5: capture baseline SHA before any changes (SHA-based to survive AI commits advancing HEAD)
    try:
        _pre_sha = _git(["rev-parse", "HEAD"], cwd=cwd, check=False).stdout.strip()
    except (OSError, FileNotFoundError):
        _pre_sha = ""
    # Capture untracked files before execution — names + fingerprints to detect
    # pre-existing untracked files that are MODIFIED (not just newly created).
    _pre_untracked: dict[str, Any] = _fingerprint_untracked(cwd)

    executed: list[dict[str, Any]] = []
    failures: list[str] = []
    skipped: list[str] = []

    plan_intent: str = plan_dict.get("intent", "")
    for step in plan_dict.get("steps", []):
        commands: list[str] = step.get("commands") or []
        step_id: str = step.get("id", "?")
        if not commands:
            if _run_budget_exhausted():
                failures.append(f"{step_id}: budget exhausted before AI execution")
                continue
            # P6: delegate to AI executor instead of skipping
            ai_task = _build_ai_task(step, plan_intent)
            ai_result = _ai_executor(ai_task, cwd=cwd, run_id=state.run_id)
            ok = ai_result.get("ok", False)
            output = ai_result.get("text", "") or ai_result.get("error", "")
            _record_run_budget(output)
            executed.append({"step": step_id, "command": f"[AI] {step.get('action', '')}", "ok": ok, "output": output})
            if not ok:
                failures.append(f"{step_id}: AI execution failed")
            continue
        for cmd in commands:
            ok, output = _command_runner(cmd, cwd)
            executed.append({"step": step_id, "command": cmd, "ok": ok, "output": output})
            if not ok:
                failures.append(f"{step_id}: {cmd}")

    # P5: compute actual file changes since baseline SHA (includes AI-committed files)
    if _pre_sha:
        _post = _git(["diff", "--name-only", f"{_pre_sha}..HEAD"], cwd=cwd, check=False)
        _unstaged = _git(["diff", "--name-only", "HEAD"], cwd=cwd, check=False)
        _post_untracked: dict[str, Any] = _fingerprint_untracked(cwd)
        # New untracked: appeared after execution.
        _new_untracked = set(_post_untracked) - set(_pre_untracked)
        # Modified pre-existing untracked: present in both but fingerprint changed.
        _modified_untracked = {
            f for f in set(_pre_untracked) & set(_post_untracked)
            if _pre_untracked[f] != _post_untracked[f]
        }
        actual_changed = sorted({
            f for f in (_post.stdout + "\n" + _unstaged.stdout).splitlines() if f
        } | _new_untracked | _modified_untracked)
    else:
        actual_changed = []

    return {
        "executed": executed,
        "failures": failures,
        "skipped_no_commands": skipped,
        "actual_changed": actual_changed,
        "ok": len(failures) == 0,
    }


def _run_verify_phase(state: DogfoodState, context: dict[str, Any]) -> dict[str, Any]:
    """Run verification commands and return a VerifyResult dict.

    Execution cwd: worktree_workspace when isolation is ready, else source_workspace.
    Commands are taken from context["commands"] first; if absent, falls back to
    context["plan_dict"]["verification_requirements"].  Empty command list with a
    non-trivial plan fails (F-PHASE-COMPLETE guard).
    """
    plan_dict: dict[str, Any] = context.get("plan_dict") or {}
    commands: list[str] = list(context.get("commands") or [])
    if not commands:
        commands = list(plan_dict.get("verification_requirements", []))

    # F-PHASE-COMPLETE guard: a plan with no verification commands has no
    # completion proof. Fail so the pipeline does not trivially reach COMPLETE.
    if not commands and plan_dict.get("steps"):
        return VerifyResult(
            passed=False,
            commands_run=[],
            failures=["no verification commands defined; add verification_requirements to plan or premortem risks"],
        ).to_dict()

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

    # auto_policy — route through build_merge_policy() so the plan-derived
    # allowed_paths (and DEFAULT_DENIED_PATHS) match the manual 'dogfood merge'
    # path exactly. A bare MergePolicy here would leave allowed_paths empty and
    # disable the scope gate.
    merge_dogfood_branch(state, build_merge_policy(state, merge_mode))
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
    strict_contract: bool = False,
    allow_partial_impl: bool = False,
    cleanup_worktree_on_block: bool = False,
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
    strict_contract: production-mode artifact contract checks. Direct phase
        tests remain permissive via run_phase() or strict_contract=False.
    cleanup_worktree_on_block: when True, remove the worktree if the run ends
        BLOCKED.  Failed isolations are always cleaned regardless of this flag.
    _interview_fn: injectable for tests; overrides the default run_interview wrapper.
    Returns the final DogfoodState (phase COMPLETE or BLOCKED).
    """
    # Validate policy combination before creating state (fail-fast).
    if allow_partial_impl and merge_mode == "auto_policy":
        raise ValueError(
            "allow_partial_impl=True is incompatible with merge_mode='auto_policy'."
            " Use merge_mode='manual' or 'never'."
        )

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
        phase_started = time.time()
        trace_input: Any = {}
        trace_output: Any = {}
        phase_llm_called = False

        if phase == DogfoodPhase.PENDING:
            advance_phase(state)
            save_state(state)
            continue

        if phase == DogfoodPhase.INTERVIEW:
            trace_input = interview
            interview = run_phase(state, artifact=interview, _interview_fn=effective_interview_fn)
            trace_output = interview
        elif phase == DogfoodPhase.RESEARCH_BRIEF:
            trace_input = interview
            research_brief = run_phase(state, artifact=interview)
            trace_output = research_brief
        elif phase == DogfoodPhase.RESEARCH:
            trace_input = research_brief
            research = run_phase(state, context=research_brief)
            trace_output = research
        elif phase == DogfoodPhase.SPEC:
            trace_input = {"interview": interview, "research": research}
            spec = run_phase(
                state,
                interview_artifact=interview,
                research_artifact=research,
            )
            trace_output = spec
        elif phase == DogfoodPhase.PREMORTEM:
            trace_input = spec
            premortem = run_phase(state, spec_dict=spec)
            trace_output = premortem
        elif phase == DogfoodPhase.PLAN:
            from core.triad import TriadBlockedError
            trace_input = {"spec": spec, "premortem": premortem}
            try:
                plan_dict = run_phase(state, spec_dict=spec, premortem_dict=premortem)
            except TriadBlockedError as exc:
                block_run(state, str(exc))
                _append_phase_trace(
                    state, phase, trace_input, {}, phase_started,
                    exception_type=type(exc).__name__, blocked_reason=state.last_failure,
                )
                save_state(state)
                continue
            trace_output = plan_dict
        elif phase == DogfoodPhase.ISOLATE:
            try:
                trace_output = run_phase(state)
            except GitWorktreeError as exc:
                block_run(state, str(exc))
                _append_phase_trace(
                    state, phase, trace_input, {}, phase_started,
                    exception_type=type(exc).__name__, blocked_reason=state.last_failure,
                )
                save_state(state)
                continue
        elif phase == DogfoodPhase.IMPLEMENT:
            trace_input = plan_dict
            impl_result = run_phase(state, context={"preflight_static": True})
            trace_output = impl_result
            phase_llm_called = any(
                str(item.get("command", "")).startswith("[AI]")
                for item in impl_result.get("executed", [])
                if isinstance(item, dict)
            )
            if strict_contract and not impl_result.get("executed"):
                block_run(state, "strict_contract: implementation produced no executed steps")
                _append_phase_trace(
                    state, phase, trace_input, trace_output, phase_started,
                    llm_called=phase_llm_called, blocked_reason=state.last_failure,
                )
                save_state(state)
                continue
            if not impl_result.get("ok"):
                # ok=False always BLOCK unless caller explicitly opted in.
                # Empty execution and partial failure are both fail-closed.
                if not allow_partial_impl:
                    _failures = impl_result.get("failures") or []
                    _reason = (
                        "implementation phase produced no executed steps"
                        if not impl_result.get("executed")
                        else f"implementation failed: {_failures}"
                    )
                    block_run(state, _reason)
                    _append_phase_trace(
                        state, phase, trace_input, trace_output, phase_started,
                        llm_called=phase_llm_called, blocked_reason=state.last_failure,
                    )
                    save_state(state)
                    continue
        elif phase == DogfoodPhase.VERIFY:
            trace_input = plan_dict
            verify_result = run_phase(state, context={"plan_dict": plan_dict})
            trace_output = verify_result
        elif phase == DogfoodPhase.REVIEW:
            trace_input = verify_result
            review = run_phase(state, context={"verify_result": verify_result})
            trace_output = review
            decision = review.get("decision", "pass")
            if decision == "retry":
                retry_run(state)
            elif decision == "block":
                block_run(state, review.get("reason", ""))
            else:
                advance_phase(state)  # → FINALIZE
            _append_phase_trace(state, phase, trace_input, trace_output, phase_started, blocked_reason=state.last_failure)
            save_state(state)
            continue
        elif phase == DogfoodPhase.FINALIZE:
            try:
                trace_output = run_phase(state)
            except Exception as exc:
                block_run(state, f"finalize failed: {exc}")
                _append_phase_trace(
                    state, phase, trace_input, {}, phase_started,
                    exception_type=type(exc).__name__, blocked_reason=state.last_failure,
                )
                save_state(state)
                continue
        elif phase == DogfoodPhase.MERGE:
            try:
                trace_output = run_phase(state, merge_mode=merge_mode)
            except Exception as exc:
                block_run(state, f"merge failed: {exc}")
                _append_phase_trace(
                    state, phase, trace_input, {}, phase_started,
                    exception_type=type(exc).__name__, blocked_reason=state.last_failure,
                )
                save_state(state)
                continue
            # _run_merge_phase sets state.phase directly for COMPLETE/BLOCKED
            _append_phase_trace(state, phase, trace_input, trace_output, phase_started, blocked_reason=state.last_failure)
            save_state(state)
            continue

        strict_failure = _strict_contract_failure(phase, trace_output) if strict_contract else ""
        if strict_failure:
            block_run(state, strict_failure)
            _append_phase_trace(
                state, phase, trace_input, trace_output, phase_started,
                llm_called=phase_llm_called, blocked_reason=state.last_failure,
            )
            save_state(state)
            continue
        if _run_budget_exhausted():
            block_run(state, "budget_exhausted")
            _append_phase_trace(
                state, phase, trace_input, trace_output, phase_started,
                llm_called=phase_llm_called, blocked_reason=state.last_failure,
            )
            save_state(state)
            continue

        _append_phase_trace(
            state, phase, trace_input, trace_output, phase_started,
            llm_called=phase_llm_called,
        )
        advance_phase(state)
        save_state(state)

    if state.phase == DogfoodPhase.BLOCKED:
        _handle_blocked_worktree(state, cleanup_on_block=cleanup_worktree_on_block)
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

def _artifact_path(state: DogfoodState, filename: ArtifactName) -> Path:
    return Path(state.runtime_workspace) / "dogfood" / state.run_id / filename


def atomic_write_json(path: Path, data: dict[str, Any]) -> None:
    """Write JSON atomically: serialize → tmp → fsync → os.replace."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    serialized = json.dumps(data, indent=2)
    tmp.write_text(serialized, encoding="utf-8")
    try:
        with tmp.open("rb") as fh:
            os.fsync(fh.fileno())
    except OSError:
        pass  # fsync not supported on all platforms/filesystems
    tmp.replace(path)


def load_policy_json(path: Path, *, required: bool = True) -> dict[str, Any]:
    """Load and parse a JSON artifact.

    required=True  → raise on missing file or corrupt JSON (fail-closed).
    required=False → return {} on missing file; raise on corrupt JSON.
    """
    if not path.exists():
        if required:
            raise FileNotFoundError(f"Required artifact missing: {path}")
        return {}
    raw = path.read_text(encoding="utf-8")
    return json.loads(raw)  # JSONDecodeError propagates — corrupt artifact is always fatal


def _estimate_tokens(data: Any) -> int:
    try:
        raw = json.dumps(data, ensure_ascii=False, default=str)
    except Exception:
        raw = str(data)
    return max(0, len(raw) // 4)


def _keys(data: Any) -> list[str]:
    return sorted(data.keys()) if isinstance(data, dict) else []


def _critical_counts(data: Any) -> dict[str, int]:
    if not isinstance(data, dict):
        return {}
    counts: dict[str, int] = {}
    for key in (
        "scope",
        "steps",
        "verification_requirements",
        "risks",
        "executed",
        "failures",
        "commands_run",
    ):
        val = data.get(key)
        if isinstance(val, (list, tuple, set, dict)):
            counts[f"{key}_len"] = len(val)
    return counts


def _append_phase_trace(
    state: DogfoodState,
    phase: DogfoodPhase,
    input_data: Any,
    output_data: Any,
    started_at: float,
    *,
    fallback_used: bool = False,
    llm_called: bool = False,
    exception_type: str | None = None,
    blocked_reason: str = "",
) -> None:
    record = {
        "phase": phase.value,
        "input_keys": _keys(input_data),
        "output_keys": _keys(output_data),
        "critical_counts": _critical_counts(output_data),
        "fallback_used": bool(fallback_used),
        "llm_called": bool(llm_called),
        "exception_type": exception_type,
        "blocked_reason": blocked_reason,
        "elapsed_ms": int((time.time() - started_at) * 1000),
        "estimated_tokens": _estimate_tokens(input_data) + _estimate_tokens(output_data),
    }
    try:
        path = _artifact_path(state, ARTIFACT_PHASE_TRACE)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception:
        pass


def read_phase_trace(state: DogfoodState) -> list[dict[str, Any]]:
    """Return all phase trace records from phase_trace.jsonl.

    Returns [] if the trace file doesn't exist.
    Corrupt lines (e.g. truncated last write after a crash) are silently dropped.
    """
    path = _artifact_path(state, ARTIFACT_PHASE_TRACE)
    if not path.exists():
        return []
    records: list[dict[str, Any]] = []
    # errors="replace": a crash mid-write can truncate a multi-byte UTF-8 char,
    # which would raise UnicodeDecodeError before splitlines() — the replacement
    # char makes that line fail json.loads instead, preserving the silent-drop
    # contract. OSError (lock/permission) → return what we have ([]).
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        # Non-throwing contract preserved for status/diagnostic callers, but a
        # lock/permission failure is not "no trace" — surface it so it isn't
        # invisible (no consumer gates on this today; this guards future use).
        print(f"[dogfood] phase_trace read failed: {exc}", file=sys.stderr)
        return []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        try:
            records.append(json.loads(stripped))
        except json.JSONDecodeError:
            pass  # truncated last-write — skip silently
    return records


def _strict_contract_failure(phase: DogfoodPhase, artifact: dict[str, Any]) -> str:
    if phase == DogfoodPhase.INTERVIEW and not (
        artifact.get("goal") or artifact.get("intent") or artifact.get("project_brief")
    ):
        return "strict_contract: interview artifact missing goal/intent"
    if phase == DogfoodPhase.SPEC:
        if not artifact.get("intent"):
            return "strict_contract: spec missing intent"
        if not artifact.get("scope"):
            return "strict_contract: spec missing scope"
    if phase == DogfoodPhase.PREMORTEM and not artifact.get("spec_intent"):
        return "strict_contract: premortem missing spec_intent"
    if phase == DogfoodPhase.PLAN:
        if not artifact.get("steps"):
            return "strict_contract: plan has no steps"
        if not artifact.get("verification_requirements"):
            return "strict_contract: plan has no verification_requirements"
    if phase == DogfoodPhase.VERIFY and not artifact.get("commands_run"):
        return "strict_contract: verify ran no commands"
    return ""


def _plan_python_paths(plan_dict: dict[str, Any]) -> list[str]:
    paths: list[str] = []
    for step in plan_dict.get("steps", []):
        candidates = [
            step.get("target"),
            *(step.get("artifacts") or []),
            *(step.get("tests_required") or []),
        ]
        for value in candidates:
            if (
                isinstance(value, str)
                and value.replace("\\", "/").endswith(".py")
                and value not in paths
            ):
                paths.append(value)
    return paths


def _pre_implement_static_smoke(plan_dict: dict[str, Any], cwd: str) -> list[str]:
    failures: list[str] = []
    for rel in _plan_python_paths(plan_dict):
        path = Path(cwd) / rel
        if not path.exists():
            continue
        try:
            ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except SyntaxError as exc:
            failures.append(f"static smoke syntax error: {rel}:{exc.lineno}")
        except OSError as exc:
            failures.append(f"static smoke read failed: {rel}:{exc}")
    return failures


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
