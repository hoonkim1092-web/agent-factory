"""Tests for core.dogfood (§17 Step 7)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from core.dogfood import (
    MAX_VERIFY_ATTEMPTS,
    DogfoodPhase,
    DogfoodState,
    MergePolicy,
    ReviewDecision,
    VerifyResult,
    _PHASE_ORDER,
    _TERMINAL_PHASES,
    _premortem_from_dict,
    _spec_from_dict,
    _state_path,
    advance_phase,
    block_run,
    create_run,
    load_state,
    retry_run,
    run_all,
    run_phase,
    save_state,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _state(
    tmp_path,
    phase: DogfoodPhase = DogfoodPhase.PENDING,
    task: str = "Add dogfood loop",
    run_id: str = "test-run-001",
) -> DogfoodState:
    return DogfoodState(
        run_id=run_id,
        task=task,
        phase=phase,
        source_workspace=str(tmp_path),
        runtime_workspace=str(tmp_path / "runtime"),
    )


def _interview_artifact(
    intent: str = "Add dogfood loop",
    scope: list | None = None,
    success_criteria: list | None = None,
) -> dict:
    return {
        "goal": intent,
        "scope": scope or ["core/dogfood.py"],
        "success_criteria": success_criteria or ["dogfood complete runs end-to-end"],
        "constraints": [],
        "approval_policy": "",
        "risk_hints": [],
        "assumptions": [],
        "research_questions": [],
    }


# ---------------------------------------------------------------------------
# DogfoodPhase — enum values and ordering
# ---------------------------------------------------------------------------

def test_phase_values_are_strings():
    for phase in DogfoodPhase:
        assert isinstance(phase.value, str)


def test_phase_order_starts_at_pending():
    assert _PHASE_ORDER[0] == DogfoodPhase.PENDING


def test_phase_order_ends_at_complete():
    assert _PHASE_ORDER[-1] == DogfoodPhase.COMPLETE


def test_terminal_phases_not_in_order():
    for tp in _TERMINAL_PHASES:
        if tp != DogfoodPhase.COMPLETE:
            assert tp not in _PHASE_ORDER


def test_blocked_is_terminal():
    assert DogfoodPhase.BLOCKED in _TERMINAL_PHASES


def test_complete_is_terminal():
    assert DogfoodPhase.COMPLETE in _TERMINAL_PHASES


def test_pending_is_not_terminal():
    assert DogfoodPhase.PENDING not in _TERMINAL_PHASES


# ---------------------------------------------------------------------------
# DogfoodState — data model
# ---------------------------------------------------------------------------

def test_state_to_dict_keys(tmp_path):
    state = _state(tmp_path)
    d = state.to_dict()
    required = {
        "run_id", "task", "phase",
        "source_workspace", "workspace",  # workspace is a backward-compat alias
        "runtime_workspace",
        "source_branch", "base_ref", "worktree_workspace", "dogfood_branch",
        "isolation_status", "merge_status", "merge_mode",
        "dogfood_commit", "merged_commit",
        "interview_path", "research_brief_path", "spec_path", "plan_path",
        "attempts", "last_failure", "next_action", "approval_policy",
        "completion_criteria",
    }
    assert required == set(d.keys())


def test_state_phase_serialized_as_string(tmp_path):
    state = _state(tmp_path, phase=DogfoodPhase.SPEC)
    assert state.to_dict()["phase"] == "spec"


def test_state_from_dict_roundtrip(tmp_path):
    state = _state(tmp_path, phase=DogfoodPhase.PREMORTEM)
    state.attempts = 2
    state.last_failure = "pytest failed"
    state.completion_criteria = ["all tests pass"]
    restored = DogfoodState.from_dict(state.to_dict())
    assert restored.run_id == state.run_id
    assert restored.phase == DogfoodPhase.PREMORTEM
    assert restored.attempts == 2
    assert restored.last_failure == "pytest failed"
    assert restored.completion_criteria == ["all tests pass"]


def test_state_from_dict_defaults(tmp_path):
    minimal = {
        "run_id": "r1",
        "task": "test",
        "phase": "pending",
        "workspace": str(tmp_path),
        "runtime_workspace": str(tmp_path / "rt"),
    }
    state = DogfoodState.from_dict(minimal)
    assert state.interview_path == ""
    assert state.attempts == 0
    assert state.completion_criteria == []


def test_state_is_terminal_true(tmp_path):
    for tp in _TERMINAL_PHASES:
        state = _state(tmp_path, phase=tp)
        assert state.is_terminal() is True


def test_state_is_terminal_false(tmp_path):
    state = _state(tmp_path, phase=DogfoodPhase.PLAN)
    assert state.is_terminal() is False


# ---------------------------------------------------------------------------
# State persistence — save / load
# ---------------------------------------------------------------------------

def test_save_creates_file(tmp_path):
    state = _state(tmp_path)
    save_state(state)
    path = _state_path(state)
    assert path.exists()


def test_save_load_roundtrip(tmp_path):
    state = _state(tmp_path, phase=DogfoodPhase.SPEC)
    state.spec_path = "/tmp/spec.json"
    save_state(state)
    loaded = load_state(state.runtime_workspace, state.run_id)
    assert loaded.phase == DogfoodPhase.SPEC
    assert loaded.spec_path == "/tmp/spec.json"


def test_save_overwrites_on_phase_change(tmp_path):
    state = _state(tmp_path, phase=DogfoodPhase.PENDING)
    save_state(state)
    state.phase = DogfoodPhase.INTERVIEW
    save_state(state)
    loaded = load_state(state.runtime_workspace, state.run_id)
    assert loaded.phase == DogfoodPhase.INTERVIEW


def test_state_path_structure(tmp_path):
    state = _state(tmp_path, run_id="myrun")
    path = _state_path(state)
    assert path.name == "dogfood_state.json"
    assert path.parent.name == "myrun"
    assert path.parent.parent.name == "dogfood"


# ---------------------------------------------------------------------------
# create_run
# ---------------------------------------------------------------------------

def test_create_run_returns_pending(tmp_path):
    state = create_run("test task", str(tmp_path), runtime_workspace=str(tmp_path / "rt"))
    assert state.phase == DogfoodPhase.PENDING


def test_create_run_persists_state(tmp_path):
    state = create_run("test task", str(tmp_path), runtime_workspace=str(tmp_path / "rt"))
    loaded = load_state(state.runtime_workspace, state.run_id)
    assert loaded.task == "test task"


def test_create_run_custom_run_id(tmp_path):
    state = create_run(
        "task", str(tmp_path),
        run_id="custom-id",
        runtime_workspace=str(tmp_path / "rt"),
    )
    assert state.run_id == "custom-id"


def test_create_run_unique_ids(tmp_path):
    s1 = create_run("t", str(tmp_path), runtime_workspace=str(tmp_path / "rt1"))
    s2 = create_run("t", str(tmp_path), runtime_workspace=str(tmp_path / "rt2"))
    assert s1.run_id != s2.run_id


# ---------------------------------------------------------------------------
# advance_phase
# ---------------------------------------------------------------------------

def test_advance_from_pending(tmp_path):
    state = _state(tmp_path, phase=DogfoodPhase.PENDING)
    new = advance_phase(state)
    assert new == DogfoodPhase.INTERVIEW
    assert state.phase == DogfoodPhase.INTERVIEW


def test_advance_from_plan(tmp_path):
    state = _state(tmp_path, phase=DogfoodPhase.PLAN)
    new = advance_phase(state)
    assert new == DogfoodPhase.ISOLATE


def test_advance_from_review(tmp_path):
    state = _state(tmp_path, phase=DogfoodPhase.REVIEW)
    new = advance_phase(state)
    assert new == DogfoodPhase.FINALIZE


def test_advance_from_complete_raises(tmp_path):
    state = _state(tmp_path, phase=DogfoodPhase.COMPLETE)
    with pytest.raises(RuntimeError, match="terminal"):
        advance_phase(state)


def test_advance_from_blocked_raises(tmp_path):
    state = _state(tmp_path, phase=DogfoodPhase.BLOCKED)
    with pytest.raises(RuntimeError, match="terminal"):
        advance_phase(state)


def test_advance_full_sequence(tmp_path):
    state = _state(tmp_path, phase=DogfoodPhase.PENDING)
    visited = [state.phase]
    while not state.is_terminal():
        advance_phase(state)
        visited.append(state.phase)
    assert visited == _PHASE_ORDER


# ---------------------------------------------------------------------------
# block_run
# ---------------------------------------------------------------------------

def test_block_run_sets_blocked(tmp_path):
    state = _state(tmp_path, phase=DogfoodPhase.VERIFY)
    block_run(state, "review blocked")
    assert state.phase == DogfoodPhase.BLOCKED
    assert state.last_failure == "review blocked"


# ---------------------------------------------------------------------------
# run_phase — dispatch
# ---------------------------------------------------------------------------

def test_run_phase_pending_returns_empty(tmp_path):
    state = _state(tmp_path, phase=DogfoodPhase.PENDING)
    result = run_phase(state)
    assert result == {}


def test_run_phase_terminal_raises(tmp_path):
    state = _state(tmp_path, phase=DogfoodPhase.COMPLETE)
    with pytest.raises(RuntimeError, match="terminal"):
        run_phase(state)


def test_run_phase_blocked_raises(tmp_path):
    state = _state(tmp_path, phase=DogfoodPhase.BLOCKED)
    with pytest.raises(RuntimeError, match="terminal"):
        run_phase(state)


# ---------------------------------------------------------------------------
# run_phase — INTERVIEW
# ---------------------------------------------------------------------------

def test_run_interview_stores_path(tmp_path):
    state = _state(tmp_path, phase=DogfoodPhase.INTERVIEW)
    artifact = _interview_artifact()
    run_phase(state, artifact=artifact)
    assert state.interview_path != ""
    assert Path(state.interview_path).exists()


def test_run_interview_missing_intent_and_goal_raises(tmp_path):
    state = _state(tmp_path, phase=DogfoodPhase.INTERVIEW)
    with pytest.raises(ValueError, match="intent"):
        run_phase(state, artifact={"scope": []})


def test_run_interview_empty_artifact_ok(tmp_path):
    state = _state(tmp_path, phase=DogfoodPhase.INTERVIEW)
    result = run_phase(state, artifact={})
    assert isinstance(result, dict)


def test_run_interview_returns_artifact(tmp_path):
    state = _state(tmp_path, phase=DogfoodPhase.INTERVIEW)
    artifact = _interview_artifact(intent="dogfood")
    result = run_phase(state, artifact=artifact)
    assert result["goal"] == "dogfood"


# ---------------------------------------------------------------------------
# run_phase — RESEARCH_BRIEF
# ---------------------------------------------------------------------------

def test_run_research_brief_stores_path(tmp_path):
    state = _state(tmp_path, phase=DogfoodPhase.RESEARCH_BRIEF)
    artifact = _interview_artifact()
    run_phase(state, artifact=artifact)
    assert state.research_brief_path != ""
    assert Path(state.research_brief_path).exists()


def test_run_research_brief_returns_dict(tmp_path):
    state = _state(tmp_path, phase=DogfoodPhase.RESEARCH_BRIEF)
    result = run_phase(state, artifact=_interview_artifact())
    assert "questions" in result


# ---------------------------------------------------------------------------
# run_phase — RESEARCH (stub)
# ---------------------------------------------------------------------------

def test_run_research_returns_context(tmp_path):
    state = _state(tmp_path, phase=DogfoodPhase.RESEARCH)
    ctx = {"findings": ["fact A"]}
    result = run_phase(state, context=ctx)
    assert result == ctx


# ---------------------------------------------------------------------------
# run_phase — SPEC
# ---------------------------------------------------------------------------

def test_run_spec_stores_path(tmp_path):
    state = _state(tmp_path, phase=DogfoodPhase.SPEC)
    run_phase(state, interview_artifact=_interview_artifact(), research_artifact={})
    assert state.spec_path != ""
    assert Path(state.spec_path).exists()


def test_run_spec_sets_completion_criteria(tmp_path):
    state = _state(tmp_path, phase=DogfoodPhase.SPEC)
    artifact = _interview_artifact(success_criteria=["all tests pass"])
    run_phase(state, interview_artifact=artifact, research_artifact={})
    assert "all tests pass" in state.completion_criteria


def test_run_spec_returns_dict_with_intent(tmp_path):
    state = _state(tmp_path, phase=DogfoodPhase.SPEC)
    result = run_phase(state, interview_artifact=_interview_artifact(), research_artifact={})
    assert "intent" in result


# ---------------------------------------------------------------------------
# run_phase — PREMORTEM
# ---------------------------------------------------------------------------

def _minimal_spec_dict(intent: str = "test") -> dict:
    return {
        "intent": intent,
        "scope": ["core/dogfood.py"],
        "success_criteria": [],
        "constraints": [],
        "approval_policy": "",
        "research_findings": [],
        "supplemental": [],
        "gaps": [],
        "risk_hints": [],
        "assumptions": [],
    }


def test_run_premortem_returns_dict_with_risks(tmp_path):
    state = _state(tmp_path, phase=DogfoodPhase.PREMORTEM)
    result = run_phase(state, spec_dict=_minimal_spec_dict())
    assert "risks" in result


# ---------------------------------------------------------------------------
# run_phase — PLAN
# ---------------------------------------------------------------------------

def _minimal_premortem_dict() -> dict:
    return {"spec_intent": "test", "risks": []}


def test_run_plan_stores_path(tmp_path):
    state = _state(tmp_path, phase=DogfoodPhase.PLAN)
    run_phase(
        state,
        spec_dict=_minimal_spec_dict(),
        premortem_dict=_minimal_premortem_dict(),
    )
    assert state.plan_path != ""
    assert Path(state.plan_path).exists()


def test_run_plan_returns_dict_with_intent(tmp_path):
    state = _state(tmp_path, phase=DogfoodPhase.PLAN)
    result = run_phase(
        state,
        spec_dict=_minimal_spec_dict(intent="build dogfood"),
        premortem_dict=_minimal_premortem_dict(),
    )
    assert result.get("intent") == "build dogfood"


# ---------------------------------------------------------------------------
# run_phase — IMPLEMENT (§17 Step 9)
# ---------------------------------------------------------------------------

def _plan_dict(steps: list[dict] | None = None) -> dict:
    return {
        "intent": "test",
        "steps": steps or [],
        "completion_criteria": [],
        "approval_points": [],
        "verification_requirements": [],
        "unresolved_risks": [],
    }


def _step(sid: str, commands: list[str] | None = None, target: str = "file.py") -> dict:
    return {"id": sid, "action": f"Implement {target}", "target": target, "commands": commands or []}


def test_run_implement_empty_plan_ok(tmp_path):
    state = _state(tmp_path, phase=DogfoodPhase.IMPLEMENT)
    result = run_phase(state, context={"plan_dict": _plan_dict()})
    assert result["ok"] is True
    assert result["executed"] == []
    assert result["failures"] == []
    assert result["skipped_no_commands"] == []


def test_run_implement_steps_without_commands_are_skipped(tmp_path):
    state = _state(tmp_path, phase=DogfoodPhase.IMPLEMENT)
    plan = _plan_dict([_step("S1"), _step("S2")])
    result = run_phase(state, context={"plan_dict": plan})
    assert result["ok"] is True
    assert result["skipped_no_commands"] == ["S1", "S2"]
    assert result["executed"] == []


def test_run_implement_commands_all_pass(tmp_path, monkeypatch):
    import core.dogfood as df
    monkeypatch.setattr(df, "_command_runner", _make_runner({"echo ok": True}))
    state = _state(tmp_path, phase=DogfoodPhase.IMPLEMENT)
    plan = _plan_dict([_step("S1", commands=["echo ok"])])
    result = run_phase(state, context={"plan_dict": plan})
    assert result["ok"] is True
    assert result["failures"] == []
    assert result["executed"] == [{"step": "S1", "command": "echo ok", "ok": True, "output": ""}]


def test_run_implement_command_failure(tmp_path, monkeypatch):
    import core.dogfood as df
    monkeypatch.setattr(df, "_command_runner", _make_runner({"bad": False}))
    state = _state(tmp_path, phase=DogfoodPhase.IMPLEMENT)
    plan = _plan_dict([_step("S1", commands=["bad"])])
    result = run_phase(state, context={"plan_dict": plan})
    assert result["ok"] is False
    assert result["failures"] == ["S1: bad"]


def test_run_implement_loads_plan_from_disk(tmp_path, monkeypatch):
    import core.dogfood as df
    monkeypatch.setattr(df, "_command_runner", _make_runner({"pytest": True}))
    state = _state(tmp_path, phase=DogfoodPhase.IMPLEMENT)
    # write plan to disk at state.plan_path location
    plan = _plan_dict([_step("S1", commands=["pytest"])])
    plan_file = tmp_path / "runtime" / "dogfood" / "test-run-001" / "plan.json"
    plan_file.parent.mkdir(parents=True, exist_ok=True)
    plan_file.write_text(json.dumps(plan), encoding="utf-8")
    state.plan_path = str(plan_file)
    result = run_phase(state, context={})
    assert result["ok"] is True
    assert result["executed"][0]["command"] == "pytest"


def test_run_implement_context_plan_dict_takes_priority(tmp_path, monkeypatch):
    import core.dogfood as df
    monkeypatch.setattr(df, "_command_runner", _make_runner({"ctx_cmd": True, "disk_cmd": False}))
    state = _state(tmp_path, phase=DogfoodPhase.IMPLEMENT)
    # disk plan has failing command
    disk_plan = _plan_dict([_step("S1", commands=["disk_cmd"])])
    plan_file = tmp_path / "plan.json"
    plan_file.write_text(json.dumps(disk_plan), encoding="utf-8")
    state.plan_path = str(plan_file)
    # context plan has passing command — should win
    ctx_plan = _plan_dict([_step("S1", commands=["ctx_cmd"])])
    result = run_phase(state, context={"plan_dict": ctx_plan})
    assert result["ok"] is True
    assert result["executed"][0]["command"] == "ctx_cmd"


def test_run_implement_mixed_steps(tmp_path, monkeypatch):
    import core.dogfood as df
    monkeypatch.setattr(df, "_command_runner", _make_runner({"run.sh": True}))
    state = _state(tmp_path, phase=DogfoodPhase.IMPLEMENT)
    plan = _plan_dict([
        _step("S1"),               # no commands → skipped
        _step("S2", commands=["run.sh"]),  # has command → executed
        _step("S3"),               # no commands → skipped
    ])
    result = run_phase(state, context={"plan_dict": plan})
    assert result["ok"] is True
    assert result["skipped_no_commands"] == ["S1", "S3"]
    assert len(result["executed"]) == 1
    assert result["executed"][0]["step"] == "S2"


# ---------------------------------------------------------------------------
# VerifyResult / ReviewDecision dataclasses
# ---------------------------------------------------------------------------

def test_verify_result_to_dict():
    vr = VerifyResult(passed=True, commands_run=["pytest"], failures=[])
    d = vr.to_dict()
    assert d == {"passed": True, "commands_run": ["pytest"], "failures": []}


def test_review_decision_to_dict():
    rd = ReviewDecision(decision="retry", reason="first attempt")
    d = rd.to_dict()
    assert d == {"decision": "retry", "reason": "first attempt"}


# ---------------------------------------------------------------------------
# run_phase — VERIFY (Step 8)
# ---------------------------------------------------------------------------

def _make_runner(results: dict[str, bool]):
    """Return a fake command runner using a {cmd: ok} map."""
    def _runner(cmd: str, cwd: str):
        return results.get(cmd, True), ""
    return _runner


def test_run_verify_no_commands_passes(tmp_path):
    state = _state(tmp_path, phase=DogfoodPhase.VERIFY)
    result = run_phase(state, context={})
    assert result["passed"] is True
    assert result["commands_run"] == []
    assert result["failures"] == []


def test_run_verify_all_commands_pass(tmp_path, monkeypatch):
    import core.dogfood as df
    monkeypatch.setattr(df, "_command_runner", _make_runner({"pytest": True, "py_compile x.py": True}))
    state = _state(tmp_path, phase=DogfoodPhase.VERIFY)
    result = run_phase(state, context={"commands": ["pytest", "py_compile x.py"]})
    assert result["passed"] is True
    assert result["failures"] == []
    assert result["commands_run"] == ["pytest", "py_compile x.py"]


def test_run_verify_partial_failure(tmp_path, monkeypatch):
    import core.dogfood as df
    monkeypatch.setattr(df, "_command_runner", _make_runner({"pytest": True, "bad_cmd": False}))
    state = _state(tmp_path, phase=DogfoodPhase.VERIFY)
    result = run_phase(state, context={"commands": ["pytest", "bad_cmd"]})
    assert result["passed"] is False
    assert result["failures"] == ["bad_cmd"]


def test_run_verify_commands_from_plan_dict(tmp_path, monkeypatch):
    import core.dogfood as df
    monkeypatch.setattr(df, "_command_runner", _make_runner({"pytest tests/": True}))
    state = _state(tmp_path, phase=DogfoodPhase.VERIFY)
    plan = {"verification_requirements": ["pytest tests/"]}
    result = run_phase(state, context={"plan_dict": plan})
    assert result["passed"] is True
    assert result["commands_run"] == ["pytest tests/"]


def test_run_verify_context_commands_takes_priority(tmp_path, monkeypatch):
    import core.dogfood as df
    monkeypatch.setattr(df, "_command_runner", _make_runner({"ctx_cmd": True, "plan_cmd": False}))
    state = _state(tmp_path, phase=DogfoodPhase.VERIFY)
    plan = {"verification_requirements": ["plan_cmd"]}
    result = run_phase(state, context={"commands": ["ctx_cmd"], "plan_dict": plan})
    assert result["commands_run"] == ["ctx_cmd"]


def test_run_verify_no_commands_no_steps_passes(tmp_path):
    """Empty plan (steps=[]) + no commands → trivially pass (nothing to verify)."""
    state = _state(tmp_path, phase=DogfoodPhase.VERIFY)
    result = run_phase(state, context={"plan_dict": {"steps": [], "verification_requirements": []}})
    assert result["passed"] is True


def test_run_verify_no_commands_with_steps_fails(tmp_path):
    """F-PHASE-COMPLETE guard: non-empty plan + no verification commands → fail."""
    state = _state(tmp_path, phase=DogfoodPhase.VERIFY)
    plan = {
        "steps": [{"id": "S1", "action": "Implement core/utils.py", "target": "core/utils.py",
                   "commands": []}],
        "verification_requirements": [],
    }
    result = run_phase(state, context={"plan_dict": plan})
    assert result["passed"] is False
    assert result["commands_run"] == []
    assert "no verification commands" in result["failures"][0]
    assert "completion_criteria" not in result["failures"][0]


# ---------------------------------------------------------------------------
# run_phase — REVIEW (Step 8)
# ---------------------------------------------------------------------------

def _verify_passed_ctx(passed: bool = True) -> dict:
    return {"verify_result": {"passed": passed, "commands_run": [], "failures": []}}


def test_run_review_passed_returns_pass(tmp_path):
    state = _state(tmp_path, phase=DogfoodPhase.REVIEW)
    result = run_phase(state, context=_verify_passed_ctx(True))
    assert result["decision"] == "pass"


def test_run_review_failed_first_attempt_returns_retry(tmp_path):
    state = _state(tmp_path, phase=DogfoodPhase.REVIEW)
    state.attempts = 0  # first attempt
    result = run_phase(state, context=_verify_passed_ctx(False))
    assert result["decision"] == "retry"
    assert "1/" in result["reason"]


def test_run_review_failed_last_attempt_returns_block(tmp_path):
    state = _state(tmp_path, phase=DogfoodPhase.REVIEW)
    state.attempts = MAX_VERIFY_ATTEMPTS - 1
    result = run_phase(state, context=_verify_passed_ctx(False))
    assert result["decision"] == "block"
    assert str(MAX_VERIFY_ATTEMPTS) in result["reason"]


def test_run_review_missing_verify_result_assumes_passed(tmp_path):
    state = _state(tmp_path, phase=DogfoodPhase.REVIEW)
    result = run_phase(state, context={})
    assert result["decision"] == "pass"


def test_run_review_retry_boundary(tmp_path):
    """attempts == MAX-2 still retries; attempts == MAX-1 blocks."""
    state = _state(tmp_path, phase=DogfoodPhase.REVIEW)
    state.attempts = MAX_VERIFY_ATTEMPTS - 2
    r1 = run_phase(state, context=_verify_passed_ctx(False))
    assert r1["decision"] == "retry"

    state.attempts = MAX_VERIFY_ATTEMPTS - 1
    r2 = run_phase(state, context=_verify_passed_ctx(False))
    assert r2["decision"] == "block"


# ---------------------------------------------------------------------------
# retry_run
# ---------------------------------------------------------------------------

def test_retry_run_resets_to_implement(tmp_path):
    state = _state(tmp_path, phase=DogfoodPhase.REVIEW)
    retry_run(state)
    assert state.phase == DogfoodPhase.IMPLEMENT


def test_retry_run_increments_attempts(tmp_path):
    state = _state(tmp_path, phase=DogfoodPhase.REVIEW)
    assert state.attempts == 0
    retry_run(state)
    assert state.attempts == 1


def test_retry_run_multiple(tmp_path):
    state = _state(tmp_path, phase=DogfoodPhase.REVIEW)
    retry_run(state)
    advance_phase(state)  # IMPLEMENT → VERIFY
    advance_phase(state)  # VERIFY → REVIEW
    retry_run(state)
    assert state.attempts == 2
    assert state.phase == DogfoodPhase.IMPLEMENT


def test_retry_run_does_not_persist(tmp_path):
    """retry_run mutates state in-memory only; save_state must be called explicitly."""
    state = _state(tmp_path)
    save_state(state)
    state.phase = DogfoodPhase.REVIEW
    retry_run(state)
    loaded = load_state(state.runtime_workspace, state.run_id)
    assert loaded.phase == DogfoodPhase.PENDING  # not persisted yet


# ---------------------------------------------------------------------------
# _spec_from_dict / _premortem_from_dict helpers
# ---------------------------------------------------------------------------

def test_spec_from_dict_roundtrip():
    from core.spec_compiler import CompiledSpec
    original = CompiledSpec(
        intent="test",
        scope=["core/x.py"],
        success_criteria=["pass"],
        gaps=["unanswered q"],
    )
    restored = _spec_from_dict(original.to_dict())
    assert restored.intent == "test"
    assert restored.scope == ["core/x.py"]
    assert restored.gaps == ["unanswered q"]


def test_premortem_from_dict_roundtrip():
    from core.premortem import PremortomResult, PremortomRisk, VerificationStep
    original = PremortomResult(
        spec_intent="test",
        risks=[
            PremortomRisk(
                id="R1",
                description="risk desc",
                category="packaging",
                verification=[VerificationStep(command="py_compile x.py", description="check")],
            )
        ],
    )
    restored = _premortem_from_dict(original.to_dict())
    assert len(restored.risks) == 1
    assert restored.risks[0].id == "R1"
    assert restored.risks[0].verification[0].command == "py_compile x.py"


# ---------------------------------------------------------------------------
# run_all — end-to-end orchestration (§17 Step 10)
# ---------------------------------------------------------------------------

def _patch_all_runners(monkeypatch, verify_seq=None):
    """Stub all phase runners. verify_seq controls verify passed values (default [True])."""
    import core.dogfood as df

    _verify_it = iter(verify_seq if verify_seq is not None else [True])

    monkeypatch.setattr(df, "_run_interview_phase",
        lambda s, artifact, **kw: artifact or {"goal": "stub"})
    monkeypatch.setattr(df, "_run_research_brief_phase",
        lambda s, artifact: {"questions": []})
    monkeypatch.setattr(df, "_run_research_phase",
        lambda s, context: context)
    monkeypatch.setattr(df, "_run_spec_phase",
        lambda s, interview_artifact, research_artifact: {
            "intent": interview_artifact.get("goal", ""),
            "scope": [], "success_criteria": [], "constraints": [],
            "approval_policy": "", "research_findings": [],
            "supplemental": [], "gaps": [], "risk_hints": [], "assumptions": [],
        })
    monkeypatch.setattr(df, "_run_premortem_phase",
        lambda s, spec_dict: {"spec_intent": spec_dict.get("intent", ""), "risks": []})
    monkeypatch.setattr(df, "_run_plan_phase",
        lambda s, spec_dict, premortem_dict, **kw: {
            "intent": spec_dict.get("intent", ""),
            "steps": [], "completion_criteria": [],
            "approval_points": [], "verification_requirements": [],
            "unresolved_risks": [],
        })
    monkeypatch.setattr(df, "_run_isolate_phase",
        lambda s: {"isolation_status": "ready"})
    monkeypatch.setattr(df, "_run_implement_phase",
        lambda s, context: {"executed": [], "failures": [], "skipped_no_commands": [], "ok": True})

    def _fake_verify(s, context):
        passed = next(_verify_it, True)
        return {"passed": passed, "commands_run": [], "failures": [] if passed else ["fail"]}

    monkeypatch.setattr(df, "_run_verify_phase", _fake_verify)
    monkeypatch.setattr(df, "_run_finalize_phase",
        lambda s: {"merge_status": "ready"})
    monkeypatch.setattr(df, "_run_merge_phase",
        lambda s, merge_mode="auto_policy": _stub_merge(s))


def _stub_merge(state):
    """Stub merge that immediately completes."""
    import core.dogfood as df
    state.phase = df.DogfoodPhase.COMPLETE
    state.merge_status = "merged"
    return {"merge_status": "merged"}


def test_run_all_returns_complete(tmp_path, monkeypatch):
    _patch_all_runners(monkeypatch)
    state = run_all(
        "test task", str(tmp_path),
        interview_artifact={"goal": "test task"},
        runtime_workspace=str(tmp_path / "rt"),
    )
    assert state.phase == DogfoodPhase.COMPLETE


def test_run_all_persists_complete_state(tmp_path, monkeypatch):
    _patch_all_runners(monkeypatch)
    state = run_all(
        "test task", str(tmp_path),
        interview_artifact={"goal": "test task"},
        runtime_workspace=str(tmp_path / "rt"),
    )
    loaded = load_state(state.runtime_workspace, state.run_id)
    assert loaded.phase == DogfoodPhase.COMPLETE


def test_run_all_retry_then_pass_returns_complete(tmp_path, monkeypatch):
    _patch_all_runners(monkeypatch, verify_seq=[False, True])
    state = run_all(
        "retry task", str(tmp_path),
        interview_artifact={"goal": "retry task"},
        runtime_workspace=str(tmp_path / "rt"),
    )
    assert state.phase == DogfoodPhase.COMPLETE
    assert state.attempts == 1


def test_run_all_max_retries_returns_blocked(tmp_path, monkeypatch):
    _patch_all_runners(monkeypatch, verify_seq=[False] * MAX_VERIFY_ATTEMPTS)
    state = run_all(
        "blocked task", str(tmp_path),
        interview_artifact={"goal": "blocked task"},
        runtime_workspace=str(tmp_path / "rt"),
    )
    assert state.phase == DogfoodPhase.BLOCKED
    assert state.attempts == MAX_VERIFY_ATTEMPTS - 1


def test_run_all_blocked_persists_state(tmp_path, monkeypatch):
    _patch_all_runners(monkeypatch, verify_seq=[False] * MAX_VERIFY_ATTEMPTS)
    state = run_all(
        "blocked", str(tmp_path),
        interview_artifact={"goal": "blocked"},
        runtime_workspace=str(tmp_path / "rt"),
    )
    loaded = load_state(state.runtime_workspace, state.run_id)
    assert loaded.phase == DogfoodPhase.BLOCKED
    assert loaded.last_failure != ""


def test_run_all_default_interview_uses_task_as_goal(tmp_path, monkeypatch):
    import core.dogfood as df
    captured: dict = {}

    def _capture_interview(s, artifact, **kw):
        captured.update(artifact)
        return artifact

    _patch_all_runners(monkeypatch)
    monkeypatch.setattr(df, "_run_interview_phase", _capture_interview)

    run_all("my task", str(tmp_path), runtime_workspace=str(tmp_path / "rt"))
    assert captured.get("goal") == "my task"


def test_run_all_returns_dogfood_state(tmp_path, monkeypatch):
    _patch_all_runners(monkeypatch)
    state = run_all(
        "t", str(tmp_path),
        interview_artifact={"goal": "t"},
        runtime_workspace=str(tmp_path / "rt"),
    )
    assert isinstance(state, DogfoodState)
    assert state.task == "t"


def test_run_all_verify_uses_plan_verification_requirements(tmp_path, monkeypatch):
    """VERIFY must receive plan_dict so verification_requirements are not silently skipped."""
    import core.dogfood as df

    received_contexts: list[dict] = []

    def _capture_verify(s, context):
        received_contexts.append(dict(context))
        return {"passed": True, "commands_run": [], "failures": []}

    _patch_all_runners(monkeypatch)
    monkeypatch.setattr(df, "_run_plan_phase",
        lambda s, spec_dict, premortem_dict, **kw: {
            "intent": "t", "steps": [], "completion_criteria": [],
            "approval_points": [], "verification_requirements": ["pytest -q"],
            "unresolved_risks": [],
        })
    monkeypatch.setattr(df, "_run_verify_phase", _capture_verify)

    run_all("t", str(tmp_path), interview_artifact={"goal": "t"},
            runtime_workspace=str(tmp_path / "rt"))

    assert len(received_contexts) == 1
    plan = received_contexts[0].get("plan_dict", {})
    assert plan.get("verification_requirements") == ["pytest -q"]


def test_run_all_traverses_all_non_terminal_phases(tmp_path, monkeypatch):
    import core.dogfood as df
    visited: list[str] = []

    def _track(phase_name, orig_fn):
        def _wrapper(*args, **kwargs):
            visited.append(phase_name)
            return orig_fn(*args, **kwargs)
        return _wrapper

    _patch_all_runners(monkeypatch)

    for attr, name in [
        ("_run_interview_phase", "interview"),
        ("_run_research_brief_phase", "research_brief"),
        ("_run_research_phase", "research"),
        ("_run_spec_phase", "spec"),
        ("_run_premortem_phase", "premortem"),
        ("_run_plan_phase", "plan"),
        ("_run_isolate_phase", "isolate"),
        ("_run_implement_phase", "implement"),
        ("_run_verify_phase", "verify"),
        ("_run_review_phase", "review"),
        ("_run_finalize_phase", "finalize"),
        ("_run_merge_phase", "merge"),
    ]:
        orig = getattr(df, attr)
        monkeypatch.setattr(df, attr, _track(name, orig))

    run_all(
        "track test", str(tmp_path),
        interview_artifact={"goal": "track test"},
        runtime_workspace=str(tmp_path / "rt"),
    )
    assert visited == [
        "interview", "research_brief", "research", "spec",
        "premortem", "plan", "isolate", "implement", "verify", "review",
        "finalize", "merge",
    ]


def test_run_all_triad_blocked_transitions_to_blocked(tmp_path, monkeypatch):
    """TriadBlockedError from _run_plan_phase → run_all() reaches BLOCKED state."""
    import core.dogfood as df
    from core.triad import TriadBlockedError

    _patch_all_runners(monkeypatch)

    def _raise_triad(s, spec_dict, premortem_dict, **kw):
        raise TriadBlockedError("Critical: core.triad missing from af.spec")

    monkeypatch.setattr(df, "_run_plan_phase", _raise_triad)

    state = run_all(
        "t", str(tmp_path),
        interview_artifact={"goal": "t"},
        runtime_workspace=str(tmp_path / "rt"),
    )
    assert state.phase == DogfoodPhase.BLOCKED
    assert "Critical" in state.last_failure
