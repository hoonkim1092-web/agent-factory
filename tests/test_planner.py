"""Tests for core.planner (§17 Step 6)."""
from __future__ import annotations

import pytest

from core.spec_compiler import CompiledSpec
from core.premortem import PremortomResult, PremortomRisk, VerificationStep
from core.planner import (
    ExecutablePlan,
    PlanStep,
    build_plan,
    _test_file_for,
    _collect_verification_commands,
    _collect_approval_points,
    _unresolved_risks,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _spec(
    intent="Add dogfood loop",
    scope=None,
    success_criteria=None,
    constraints=None,
    approval_policy="",
    gaps=None,
) -> CompiledSpec:
    return CompiledSpec(
        intent=intent,
        scope=scope or [],
        success_criteria=success_criteria or [],
        constraints=constraints or [],
        approval_policy=approval_policy,
        gaps=gaps or [],
    )


def _premortem(risks=None) -> PremortomResult:
    return PremortomResult(risks=risks or [], spec_intent="test")


def _risk(rid, description, category, commands=None) -> PremortomRisk:
    steps = []
    for cmd in (commands or []):
        steps.append(VerificationStep(command=cmd, description="check"))
    return PremortomRisk(id=rid, description=description, category=category, verification=steps)


# ---------------------------------------------------------------------------
# PlanStep / ExecutablePlan data model
# ---------------------------------------------------------------------------

def test_plan_step_to_dict_keys():
    step = PlanStep(
        id="S1", action="Implement core/foo.py", target="core/foo.py",
        tests_required=["tests/test_foo.py"], artifacts=["core/foo.py"], depends_on=[],
    )
    d = step.to_dict()
    assert set(d.keys()) == {"id", "action", "target", "tests_required", "artifacts", "depends_on", "commands"}


def test_executable_plan_to_dict_keys():
    plan = ExecutablePlan(intent="x")
    d = plan.to_dict()
    assert set(d.keys()) == {
        "intent", "steps", "completion_criteria", "approval_points",
        "verification_requirements", "unresolved_risks",
    }


def test_executable_plan_is_empty_true():
    assert ExecutablePlan(intent="x").is_empty() is True


def test_executable_plan_is_empty_false():
    plan = ExecutablePlan(intent="x", steps=[PlanStep("S1", "do", "target")])
    assert plan.is_empty() is False


# ---------------------------------------------------------------------------
# _test_file_for
# ---------------------------------------------------------------------------

def test_test_file_for_core_module():
    assert _test_file_for("core/dogfood.py") == "tests/test_dogfood.py"


def test_test_file_for_scripts_module():
    assert _test_file_for("scripts/review_gate.py") == "tests/test_review_gate.py"


def test_test_file_for_non_python():
    assert _test_file_for("docs/README.md") is None


def test_test_file_for_root_py():
    # root-level .py has no known parent dir → None
    assert _test_file_for("run_factory_cli.py") is None


# ---------------------------------------------------------------------------
# _collect_verification_commands
# ---------------------------------------------------------------------------

def test_collect_verification_commands_excludes_comments():
    risks = [
        _risk("R1", "d", "blueprint_sync", ["python -m py_compile core/foo.py", "# manual check"]),
    ]
    cmds = _collect_verification_commands(_premortem(risks))
    assert "python -m py_compile core/foo.py" in cmds
    assert "# manual check" not in cmds


def test_collect_verification_commands_empty():
    cmds = _collect_verification_commands(_premortem())
    assert cmds == []


def test_collect_verification_commands_multiple_risks():
    risks = [
        _risk("R1", "d1", "blueprint_sync", ["cmd1"]),
        _risk("R2", "d2", "packaging", ["cmd2", "cmd3"]),
    ]
    cmds = _collect_verification_commands(_premortem(risks))
    assert cmds == ["cmd1", "cmd2", "cmd3"]


# ---------------------------------------------------------------------------
# _collect_approval_points
# ---------------------------------------------------------------------------

def test_collect_approval_points_from_policy():
    points = _collect_approval_points("require_human_for_destructive", _premortem())
    assert "require_human_for_destructive" in points


def test_collect_approval_points_from_approval_risk():
    risks = [_risk("R4", "destructive op", "approval", ["grep 'approval' core/"])]
    points = _collect_approval_points("", _premortem(risks))
    assert "grep 'approval' core/" in points


def test_collect_approval_points_empty():
    assert _collect_approval_points("", _premortem()) == []


# ---------------------------------------------------------------------------
# _unresolved_risks
# ---------------------------------------------------------------------------

def test_unresolved_risks_gap_not_in_scope():
    risks = [_risk("R20", "Unanswered research question: retry budget", "research_gap")]
    unresolved = _unresolved_risks(_premortem(risks), scope=["core/dogfood.py"])
    assert len(unresolved) == 1


def test_unresolved_risks_gap_resolved_by_scope():
    # "retry" appears in scope item
    risks = [_risk("R20", "Unanswered research question: retry limit", "research_gap")]
    unresolved = _unresolved_risks(_premortem(risks), scope=["core/retry_policy.py"])
    assert unresolved == []


def test_unresolved_risks_non_gap_ignored():
    risks = [_risk("R1", "blueprint_sync risk", "blueprint_sync", ["cmd"])]
    assert _unresolved_risks(_premortem(risks), scope=[]) == []


def test_unresolved_risks_boilerplate_prefix_does_not_cause_false_negative():
    """'research' in scope path must not match the boilerplate prefix token."""
    risks = [_risk("R20", "Unanswered research question: retry budget", "research_gap")]
    # scope contains "research" but not "retry" or "budget"
    unresolved = _unresolved_risks(_premortem(risks), scope=["docs/research.md"])
    assert len(unresolved) == 1


# ---------------------------------------------------------------------------
# build_plan — basic
# ---------------------------------------------------------------------------

def test_build_plan_empty_spec_empty_premortem():
    plan = build_plan(_spec(), _premortem())
    assert plan.intent == "Add dogfood loop"
    assert plan.is_empty()
    assert plan.steps == []
    assert plan.verification_requirements == []


def test_build_plan_scope_generates_implementation_steps():
    spec = _spec(scope=["core/dogfood.py", "run_factory_cli.py"])
    plan = build_plan(spec, _premortem())
    actions = [s.action for s in plan.steps]
    assert any("core/dogfood.py" in a for a in actions)
    assert any("run_factory_cli.py" in a for a in actions)


def test_build_plan_impl_steps_have_test_suggestions():
    spec = _spec(scope=["core/dogfood.py"])
    plan = build_plan(spec, _premortem())
    impl_step = next(s for s in plan.steps if "core/dogfood.py" in s.target)
    assert "tests/test_dogfood.py" in impl_step.tests_required


def test_build_plan_no_test_for_root_py():
    spec = _spec(scope=["run_factory_cli.py"])
    plan = build_plan(spec, _premortem())
    impl_step = next(s for s in plan.steps if "run_factory_cli.py" in s.target)
    assert impl_step.tests_required == []


# ---------------------------------------------------------------------------
# build_plan — investigation steps (gaps)
# ---------------------------------------------------------------------------

def test_build_plan_gap_risks_become_investigation_steps():
    risks = [_risk("R20", "Unanswered research question: retry budget", "research_gap")]
    plan = build_plan(_spec(), _premortem(risks))
    inv = [s for s in plan.steps if s.target == "research"]
    assert len(inv) == 1
    assert "retry budget" in inv[0].action


def test_build_plan_investigation_steps_come_first():
    risks = [_risk("R20", "Unanswered research question: q1", "research_gap")]
    spec = _spec(scope=["core/foo.py"])
    plan = build_plan(spec, _premortem(risks))
    assert plan.steps[0].target == "research"
    assert plan.steps[1].target == "core/foo.py"


def test_build_plan_implementation_depends_on_investigation():
    risks = [_risk("R20", "Unanswered research question: q1", "research_gap")]
    spec = _spec(scope=["core/foo.py"])
    plan = build_plan(spec, _premortem(risks))
    inv_id = plan.steps[0].id
    impl_step = next(s for s in plan.steps if s.target == "core/foo.py")
    assert inv_id in impl_step.depends_on


# ---------------------------------------------------------------------------
# build_plan — verification step
# ---------------------------------------------------------------------------

def test_build_plan_premortem_risk_generates_verification_step():
    risks = [_risk("R1", "blueprint_sync", "blueprint_sync", ["python -m py_compile core/foo.py"])]
    spec = _spec(scope=["core/foo.py"])
    plan = build_plan(spec, _premortem(risks))
    verify = next((s for s in plan.steps if s.target == "verification"), None)
    assert verify is not None


def test_build_plan_verification_step_depends_on_impl():
    risks = [_risk("R1", "blueprint_sync", "blueprint_sync", ["cmd"])]
    spec = _spec(scope=["core/foo.py"])
    plan = build_plan(spec, _premortem(risks))
    impl_step = next(s for s in plan.steps if s.target == "core/foo.py")
    verify = next(s for s in plan.steps if s.target == "verification")
    assert impl_step.id in verify.depends_on


def test_build_plan_no_verification_step_when_only_comment_risks():
    risks = [_risk("R5", "assumption", "assumption", ["# Validate assumption"])]
    spec = _spec(scope=["core/foo.py"])
    plan = build_plan(spec, _premortem(risks))
    verify = next((s for s in plan.steps if s.target == "verification"), None)
    assert verify is None


def test_build_plan_verification_requirements_populated():
    risks = [_risk("R1", "d", "blueprint_sync", ["cmd1", "cmd2"])]
    plan = build_plan(_spec(), _premortem(risks))
    assert "cmd1" in plan.verification_requirements
    assert "cmd2" in plan.verification_requirements


def test_build_plan_verification_step_commands_stored_on_step():
    """Verification step must carry commands so Step 7 runner can execute them."""
    risks = [_risk("R1", "d", "blueprint_sync", ["cmd_a", "cmd_b"])]
    spec = _spec(scope=["core/foo.py"])
    plan = build_plan(spec, _premortem(risks))
    verify = next(s for s in plan.steps if s.target == "verification")
    assert "cmd_a" in verify.commands
    assert "cmd_b" in verify.commands


def test_build_plan_investigation_step_no_commands():
    """Investigation steps have no commands — only action and target."""
    risks = [_risk("R20", "Unanswered research question: q", "research_gap")]
    plan = build_plan(_spec(), _premortem(risks))
    inv = next(s for s in plan.steps if s.target == "research")
    assert inv.commands == []


# ---------------------------------------------------------------------------
# build_plan — step IDs are unique and sequential
# ---------------------------------------------------------------------------

def test_build_plan_step_ids_unique():
    risks = [
        _risk("R20", "Unanswered research question: q", "research_gap"),
        _risk("R1", "blueprint", "blueprint_sync", ["cmd"]),
    ]
    spec = _spec(scope=["core/a.py", "core/b.py"])
    plan = build_plan(spec, _premortem(risks))
    ids = [s.id for s in plan.steps]
    assert len(ids) == len(set(ids)), f"Duplicate step IDs: {ids}"


def test_build_plan_step_ids_start_at_s1():
    spec = _spec(scope=["core/foo.py"])
    plan = build_plan(spec, _premortem())
    assert plan.steps[0].id == "S1"


# ---------------------------------------------------------------------------
# build_plan — completion criteria and approval
# ---------------------------------------------------------------------------

def test_build_plan_completion_criteria_from_spec():
    spec = _spec(success_criteria=["af dogfood complete works", "no scope leak"])
    plan = build_plan(spec, _premortem())
    assert "af dogfood complete works" in plan.completion_criteria
    assert "no scope leak" in plan.completion_criteria


def test_build_plan_approval_from_policy():
    spec = _spec(approval_policy="require_human_for_destructive")
    plan = build_plan(spec, _premortem())
    assert "require_human_for_destructive" in plan.approval_points


def test_build_plan_to_dict_round_trip():
    risks = [_risk("R1", "d", "blueprint_sync", ["cmd"])]
    spec = _spec(scope=["core/foo.py"], success_criteria=["done"])
    plan = build_plan(spec, _premortem(risks))
    d = plan.to_dict()
    assert isinstance(d["steps"], list)
    assert d["completion_criteria"] == ["done"]
