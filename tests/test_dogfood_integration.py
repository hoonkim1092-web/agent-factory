"""Smoke test: dogfood run_all() end-to-end (§17 Step 14).

Chains real core modules (research_brief, spec_compiler, premortem, planner)
through the DogfoodState machine using a pre-built interview artifact so no
interactive TTY is needed.  _command_runner is mocked to return success so
IMPLEMENT/VERIFY/REVIEW complete without executing real shell commands.
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

import core.dogfood as dogfood_mod
from core.dogfood import DogfoodPhase, run_all


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _minimal_interview(
    goal: str = "Add a utility helper",
    scope: list | None = None,
    success_criteria: list | None = None,
    commands: list | None = None,
) -> dict:
    """Minimal interview artifact accepted by the full pipeline.

    assumptions must be list[dict] to match core.interview.run_interview() output
    (see core/interview.py _build_assumptions — keys: statement, confidence, source).
    """
    return {
        "goal": goal,
        "scope": scope or ["core/utils.py"],
        "success_criteria": success_criteria or ["all tests pass"],
        "constraints": ["no breaking changes"],
        "approval_policy": "auto",
        "risk_hints": ["existing callers may break"],
        "assumptions": [
            {"statement": "Python 3.9+", "confidence": "high", "source": "context"},
        ],
        "research_questions": ["What callers use utils.py?"],
    }


def _noop_runner(cmd: str, cwd: str):
    """Command runner that always succeeds without running anything."""
    return True, f"ok: {cmd}"


def _failing_runner(cmd: str, cwd: str):
    return False, f"fail: {cmd}"


def _noop_isolate(state):
    """Stub isolation: mark ready without creating a real worktree."""
    state.isolation_status = "ready"
    state.source_branch = "main"
    state.base_ref = "abc1234"
    state.worktree_workspace = state.source_workspace  # no actual worktree
    return {"isolation_status": "ready"}


def _noop_finalize(state):
    """Stub finalize: record a fake dogfood_commit."""
    state.dogfood_commit = "deadbeef"
    state.merge_status = "ready"
    return {"merge_status": "ready"}


def _noop_merge(state, merge_mode="auto_policy"):
    """Stub merge: immediately complete."""
    state.merge_status = "merged"
    state.merged_commit = "feedcafe"
    state.phase = dogfood_mod.DogfoodPhase.COMPLETE
    return {"merge_status": "merged"}


def _noop_ai_executor(task: str, cwd: str, run_id: str):
    """AI executor stub for smoke tests; never call the real provider CLI."""
    return {"ok": True, "text": f"ai ok: {run_id}"}


# ---------------------------------------------------------------------------
# End-to-end smoke: PENDING → COMPLETE
# ---------------------------------------------------------------------------

def _smoke_patches(dogfood_mod):
    """Return context managers that stub external side effects for smoke tests."""
    return (
        patch.object(dogfood_mod, "_run_isolate_phase", side_effect=_noop_isolate),
        patch.object(dogfood_mod, "_run_finalize_phase", side_effect=_noop_finalize),
        patch.multiple(
            dogfood_mod,
            _run_merge_phase=_noop_merge,
            _ai_executor=_noop_ai_executor,
        ),
    )


def test_run_all_reaches_complete(tmp_path):
    """Full pipeline completes when all commands succeed."""
    artifact = _minimal_interview()
    p1, p2, p3 = _smoke_patches(dogfood_mod)
    with patch.object(dogfood_mod, "_command_runner", side_effect=_noop_runner), p1, p2, p3:
        state = run_all(
            task="Add a utility helper",
            workspace=str(tmp_path),
            interview_artifact=artifact,
            runtime_workspace=str(tmp_path / ".af_runtime"),
            run_id="smoke-001",
        )
    assert state.phase == DogfoodPhase.COMPLETE


def test_run_all_persists_state_json(tmp_path):
    """Final state is written to disk at the expected path."""
    artifact = _minimal_interview()
    p1, p2, p3 = _smoke_patches(dogfood_mod)
    with patch.object(dogfood_mod, "_command_runner", side_effect=_noop_runner), p1, p2, p3:
        state = run_all(
            task="Add a utility helper",
            workspace=str(tmp_path),
            interview_artifact=artifact,
            runtime_workspace=str(tmp_path / ".af_runtime"),
            run_id="smoke-002",
        )
    state_path = Path(state.runtime_workspace) / "dogfood" / state.run_id / "dogfood_state.json"
    assert state_path.exists()
    data = json.loads(state_path.read_text(encoding="utf-8"))
    assert data["phase"] == "complete"


def test_run_all_artifacts_written(tmp_path):
    """interview.json, research_brief.json, spec.json, plan.json all created."""
    artifact = _minimal_interview()
    p1, p2, p3 = _smoke_patches(dogfood_mod)
    with patch.object(dogfood_mod, "_command_runner", side_effect=_noop_runner), p1, p2, p3:
        state = run_all(
            task="Add a utility helper",
            workspace=str(tmp_path),
            interview_artifact=artifact,
            runtime_workspace=str(tmp_path / ".af_runtime"),
            run_id="smoke-003",
        )
    assert Path(state.interview_path).exists(), "interview.json missing"
    assert Path(state.research_brief_path).exists(), "research_brief.json missing"
    assert Path(state.spec_path).exists(), "spec.json missing"
    assert Path(state.plan_path).exists(), "plan.json missing"


def test_run_all_spec_contains_intent(tmp_path):
    """Compiled spec preserves the goal from the interview artifact."""
    artifact = _minimal_interview(goal="My specific task goal")
    p1, p2, p3 = _smoke_patches(dogfood_mod)
    with patch.object(dogfood_mod, "_command_runner", side_effect=_noop_runner), p1, p2, p3:
        state = run_all(
            task="My specific task goal",
            workspace=str(tmp_path),
            interview_artifact=artifact,
            runtime_workspace=str(tmp_path / ".af_runtime"),
            run_id="smoke-004",
        )
    spec = json.loads(Path(state.spec_path).read_text(encoding="utf-8"))
    assert spec["intent"] == "My specific task goal"


def test_run_all_plan_contains_steps(tmp_path):
    """Planner produces at least one step."""
    artifact = _minimal_interview()
    p1, p2, p3 = _smoke_patches(dogfood_mod)
    with patch.object(dogfood_mod, "_command_runner", side_effect=_noop_runner), p1, p2, p3:
        state = run_all(
            task="Add a utility helper",
            workspace=str(tmp_path),
            interview_artifact=artifact,
            runtime_workspace=str(tmp_path / ".af_runtime"),
            run_id="smoke-005",
        )
    plan = json.loads(Path(state.plan_path).read_text(encoding="utf-8"))
    assert isinstance(plan.get("steps"), list)
    assert len(plan["steps"]) >= 1


# ---------------------------------------------------------------------------
# Verify/Review retry loop: failing commands → BLOCKED after max attempts
# ---------------------------------------------------------------------------

def test_run_all_blocks_after_max_verify_failures(tmp_path):
    """When verification commands always fail, pipeline reaches BLOCKED."""
    artifact = _minimal_interview()

    call_count = {"n": 0}

    def _selective_runner(cmd: str, cwd: str):
        call_count["n"] += 1
        if "verify" in cmd.lower() or "pytest" in cmd.lower():
            return False, "test failed"
        return True, "ok"

    from core import planner as planner_mod
    original_build = planner_mod.build_plan

    def _patched_build_plan(spec, premortem):
        plan = original_build(spec, premortem)
        plan.verification_requirements = ["pytest --verify-step"]
        return plan

    p1, p2, p3 = _smoke_patches(dogfood_mod)
    with patch.object(dogfood_mod, "_command_runner", side_effect=_selective_runner), \
         patch.object(planner_mod, "build_plan", side_effect=_patched_build_plan), \
         p1, p2, p3:
        state = run_all(
            task="Add a utility helper",
            workspace=str(tmp_path),
            interview_artifact=artifact,
            runtime_workspace=str(tmp_path / ".af_runtime"),
            run_id="smoke-block-001",
        )

    assert state.phase == DogfoodPhase.BLOCKED
    assert state.last_failure != ""


def test_run_all_attempts_incremented_on_retry(tmp_path):
    """state.attempts increases each time the retry loop fires."""
    artifact = _minimal_interview()

    from core import planner as planner_mod
    original_build = planner_mod.build_plan

    def _patched_build_plan(spec, premortem):
        plan = original_build(spec, premortem)
        plan.verification_requirements = ["fail-command"]
        return plan

    # IMPLEMENT must succeed so that the VERIFY retry loop can fire.
    # PR 3: ok=False in IMPLEMENT → immediate BLOCK; isolate VERIFY failure via
    # _failing_runner only (stub IMPLEMENT to return ok=True).
    def _noop_implement(state, context):
        return {"executed": [{"step": "S1", "command": "ok", "ok": True, "output": ""}],
                "failures": [], "skipped_no_commands": [], "actual_changed": [], "ok": True}

    p1, p2, p3 = _smoke_patches(dogfood_mod)
    with patch.object(dogfood_mod, "_command_runner", side_effect=_failing_runner), \
         patch.object(dogfood_mod, "_run_implement_phase", side_effect=_noop_implement), \
         patch.object(planner_mod, "build_plan", side_effect=_patched_build_plan), \
         p1, p2, p3:
        state = run_all(
            task="Add a utility helper",
            workspace=str(tmp_path),
            interview_artifact=artifact,
            runtime_workspace=str(tmp_path / ".af_runtime"),
            run_id="smoke-retry-001",
        )

    assert state.phase == DogfoodPhase.BLOCKED
    from core.dogfood import MAX_VERIFY_ATTEMPTS
    assert state.attempts >= MAX_VERIFY_ATTEMPTS - 1


# ---------------------------------------------------------------------------
# Non-interactive _interview_fn path (injectable)
# ---------------------------------------------------------------------------

def test_run_all_injectable_interview_fn(tmp_path):
    """When _interview_fn is provided, it is called instead of run_interview()."""
    called = {"n": 0}
    artifact = _minimal_interview(goal="injectable goal")

    def _fake_interview_fn(task: str, workspace: str) -> dict:
        called["n"] += 1
        return {"ok": True, "project_brief": artifact}

    p1, p2, p3 = _smoke_patches(dogfood_mod)
    with patch.object(dogfood_mod, "_command_runner", side_effect=_noop_runner), p1, p2, p3:
        state = run_all(
            task="injectable goal",
            workspace=str(tmp_path),
            runtime_workspace=str(tmp_path / ".af_runtime"),
            run_id="smoke-inject-001",
            _interview_fn=_fake_interview_fn,
        )

    assert state.phase == DogfoodPhase.COMPLETE
    assert called["n"] == 1


# ---------------------------------------------------------------------------
# §17 Step 20: architect_agent wired into _run_plan_phase
# ---------------------------------------------------------------------------

def _minimal_state(tmp_path) -> "dogfood_mod.DogfoodState":
    """Minimal DogfoodState sufficient for _run_plan_phase."""
    return dogfood_mod.DogfoodState(
        run_id="arch-test-001",
        task="test task",
        phase=dogfood_mod.DogfoodPhase.PLAN,
        source_workspace=str(tmp_path),
        runtime_workspace=str(tmp_path / ".af_runtime"),
    )


def _minimal_spec() -> dict:
    return {
        "intent": "test task",
        "scope": ["core/utils.py"],
        "success_criteria": ["tests pass"],
        "constraints": [],
        "approval_policy": "auto",
        "research_findings": [],
        "supplemental": [],
        "gaps": [],
        "risk_hints": [],
        "assumptions": [],
    }


def test_plan_phase_wires_real_architect_fn(tmp_path):
    """_run_plan_phase auto-wires core.architect_agent.architect_fn when no stub given."""
    import core.architect_agent as arch_mod

    called = {}
    original = arch_mod.architect_fn

    def _spy(plan_dict, critic_report, context, **kw):
        called["invoked"] = True
        return original(plan_dict, critic_report, context, **kw)

    state = _minimal_state(tmp_path)
    with patch.object(arch_mod, "architect_fn", side_effect=_spy):
        dogfood_mod._run_plan_phase(state, _minimal_spec(), {})

    assert called.get("invoked"), "architect_fn was not called by _run_plan_phase"


def test_plan_phase_accept_finding_surfaces_in_plan(tmp_path):
    """A Critic finding with no blueprint/ADR match is ACCEPTed and lands in unresolved_risks.

    Uses empty blueprint and ADR dir so no REJECT is possible — any finding must
    be ACCEPTed and surface in final_plan["unresolved_risks"].
    """
    import core.architect_agent as arch_mod
    from core.triad import TriadCriticFinding, TriadCriticReport

    accept_finding = TriadCriticFinding(
        severity="High",
        title="Missing input guard",
        evidence_type="file_line",
        evidence="core/utils.py:12 — no None check",
        affected_plan_step="implementation",
        why_it_breaks="None input causes AttributeError",
        required_fix="Add `if value is None: raise ValueError`",
    )

    def _critic_with_accept(plan_dict, context):
        return TriadCriticReport(verdict="WARN", findings=[accept_finding])

    # Empty blueprint + empty ADR dir → architect has no grounds to REJECT
    empty_bp = tmp_path / "empty_blueprint.md"
    empty_bp.write_text("")
    empty_adr_dir = tmp_path / "empty_adrs"
    empty_adr_dir.mkdir()

    def _architect_no_refs(plan_dict, critic_report, context):
        return arch_mod.architect_fn(
            plan_dict, critic_report, context,
            _blueprint_path=empty_bp,
            _adr_dir=empty_adr_dir,
        )

    state = _minimal_state(tmp_path)
    plan = dogfood_mod._run_plan_phase(
        state, _minimal_spec(), {},
        _triad_critic_fn=_critic_with_accept,
        _triad_architect_fn=_architect_no_refs,
    )

    risks = plan.get("unresolved_risks", [])
    assert any("Missing input guard" in r for r in risks), (
        f"ACCEPT finding not in unresolved_risks: {risks}"
    )


def test_plan_phase_e2e_runs_complete(tmp_path):
    """_run_plan_phase with no injected fns completes and writes plan.json."""
    state = _minimal_state(tmp_path)
    plan = dogfood_mod._run_plan_phase(state, _minimal_spec(), {})

    assert isinstance(plan, dict), "plan dict not returned"
    assert "steps" in plan, "plan missing 'steps' key"
    assert state.plan_path, "state.plan_path not set"
    assert Path(state.plan_path).exists(), "plan.json not written to disk"
