"""Tests for core.dogfood (§17 Step 7)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from core.dogfood import (
    DogfoodPhase,
    DogfoodState,
    _PHASE_ORDER,
    _TERMINAL_PHASES,
    _premortem_from_dict,
    _spec_from_dict,
    _state_path,
    advance_phase,
    block_run,
    create_run,
    load_state,
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
        workspace=str(tmp_path),
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
        "run_id", "task", "phase", "workspace", "runtime_workspace",
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
    assert new == DogfoodPhase.IMPLEMENT


def test_advance_from_review(tmp_path):
    state = _state(tmp_path, phase=DogfoodPhase.REVIEW)
    new = advance_phase(state)
    assert new == DogfoodPhase.COMPLETE


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
# run_phase — IMPLEMENT / VERIFY / REVIEW (stubs)
# ---------------------------------------------------------------------------

def test_run_implement_stub(tmp_path):
    state = _state(tmp_path, phase=DogfoodPhase.IMPLEMENT)
    ctx = {"step": "impl"}
    result = run_phase(state, context=ctx)
    assert result == ctx


def test_run_verify_stub(tmp_path):
    state = _state(tmp_path, phase=DogfoodPhase.VERIFY)
    ctx = {"step": "verify"}
    result = run_phase(state, context=ctx)
    assert result == ctx


def test_run_review_stub(tmp_path):
    state = _state(tmp_path, phase=DogfoodPhase.REVIEW)
    ctx = {"step": "review"}
    result = run_phase(state, context=ctx)
    assert result == ctx


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
