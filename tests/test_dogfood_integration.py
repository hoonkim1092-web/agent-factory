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


# ---------------------------------------------------------------------------
# End-to-end smoke: PENDING → COMPLETE
# ---------------------------------------------------------------------------

def test_run_all_reaches_complete(tmp_path):
    """Full pipeline completes when all commands succeed."""
    artifact = _minimal_interview()
    with patch.object(dogfood_mod, "_command_runner", side_effect=_noop_runner):
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
    with patch.object(dogfood_mod, "_command_runner", side_effect=_noop_runner):
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
    with patch.object(dogfood_mod, "_command_runner", side_effect=_noop_runner):
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
    with patch.object(dogfood_mod, "_command_runner", side_effect=_noop_runner):
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
    with patch.object(dogfood_mod, "_command_runner", side_effect=_noop_runner):
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
    # Plan must have verification_requirements for the verify phase to run commands.
    artifact = _minimal_interview()

    call_count = {"n": 0}

    def _selective_runner(cmd: str, cwd: str):
        # IMPLEMENT succeeds; VERIFY always fails so retry loop triggers.
        call_count["n"] += 1
        if "verify" in cmd.lower() or "pytest" in cmd.lower():
            return False, "test failed"
        return True, "ok"

    # Patch planner to inject a verification_requirement so VERIFY has a command.
    from core import planner as planner_mod
    original_build = planner_mod.build_plan

    def _patched_build_plan(spec, premortem):
        plan = original_build(spec, premortem)
        plan.verification_requirements = ["pytest --verify-step"]
        return plan

    with patch.object(dogfood_mod, "_command_runner", side_effect=_selective_runner), \
         patch.object(planner_mod, "build_plan", side_effect=_patched_build_plan):
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

    with patch.object(dogfood_mod, "_command_runner", side_effect=_failing_runner), \
         patch.object(planner_mod, "build_plan", side_effect=_patched_build_plan):
        state = run_all(
            task="Add a utility helper",
            workspace=str(tmp_path),
            interview_artifact=artifact,
            runtime_workspace=str(tmp_path / ".af_runtime"),
            run_id="smoke-retry-001",
        )

    assert state.phase == DogfoodPhase.BLOCKED
    # MAX_VERIFY_ATTEMPTS = 3; attempts counter reflects retry cycles fired.
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

    with patch.object(dogfood_mod, "_command_runner", side_effect=_noop_runner):
        state = run_all(
            task="injectable goal",
            workspace=str(tmp_path),
            runtime_workspace=str(tmp_path / ".af_runtime"),
            run_id="smoke-inject-001",
            _interview_fn=_fake_interview_fn,
        )

    assert state.phase == DogfoodPhase.COMPLETE
    assert called["n"] == 1
