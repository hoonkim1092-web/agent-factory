"""Tests for core.planner (§17 Step 6)."""
from __future__ import annotations

import pytest

from core.spec_compiler import CompiledSpec
from core.premortem import PremortomResult, PremortomRisk, VerificationStep
from core.planner import (
    ExecutablePlan,
    PlanStep,
    build_plan,
    implementation_steps,
    _test_file_for,
    _collect_verification_commands,
    _collect_approval_points,
    _unresolved_risks,
    _extract_scope_file_paths,
    _extract_stale_test_paths,
    _extract_duplicate_function_paths,
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
    research_findings=None,
) -> CompiledSpec:
    return CompiledSpec(
        intent=intent,
        scope=scope or [],
        success_criteria=success_criteria or [],
        constraints=constraints or [],
        approval_policy=approval_policy,
        gaps=gaps or [],
        research_findings=research_findings or [],
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
    assert set(d.keys()) == {"id", "action", "target", "tests_required", "artifacts", "depends_on", "commands", "reference_artifacts"}


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


def test_build_plan_core_py_includes_blueprint_in_artifacts():
    """P2: core/*.py scope items must include Master_Blueprint.md in artifacts."""
    spec = _spec(scope=["core/utils.py"])
    plan = build_plan(spec, _premortem())
    impl_step = next(s for s in plan.steps if "core/utils.py" in s.target)
    assert "core/utils.py" in impl_step.artifacts
    assert "Master_Blueprint.md" in impl_step.artifacts


def test_build_plan_non_core_py_excludes_blueprint():
    """P2: files outside core/ do not get Master_Blueprint.md injected."""
    spec = _spec(scope=["run_factory_cli.py", "scripts/build.py"])
    plan = build_plan(spec, _premortem())
    for step in plan.steps:
        if step.target in ("run_factory_cli.py", "scripts/build.py"):
            assert "Master_Blueprint.md" not in step.artifacts


# ---------------------------------------------------------------------------
# reference_artifacts (research_findings injection)
# ---------------------------------------------------------------------------

def test_build_plan_reference_artifacts_includes_companion_test():
    """research_findings 의 companion test 가 reference_artifacts 로 노출된다."""
    findings = [
        {"path": "core/utils.py", "kind": "source"},
        {"path": "tests/test_utils.py", "kind": "test"},
    ]
    spec = _spec(scope=["core/utils.py"], research_findings=findings)
    plan = build_plan(spec, _premortem())
    impl = next(s for s in plan.steps if s.target == "core/utils.py")
    assert "tests/test_utils.py" in impl.reference_artifacts
    # scope item itself must not appear in reference_artifacts (already in artifacts)
    assert "core/utils.py" not in impl.reference_artifacts


def test_build_plan_reference_artifacts_empty_when_no_findings():
    """research_findings 가 비어있으면 reference_artifacts 도 빈 리스트."""
    spec = _spec(scope=["core/utils.py"])
    plan = build_plan(spec, _premortem())
    impl = next(s for s in plan.steps if s.target == "core/utils.py")
    assert impl.reference_artifacts == []


def test_build_plan_reference_artifacts_per_scope_item():
    """다중 core/*.py scope — 각 step 이 자기 companion test 만 받는다."""
    findings = [
        {"path": "core/utils.py", "kind": "source"},
        {"path": "tests/test_utils.py", "kind": "test"},
        {"path": "core/premortem.py", "kind": "source"},
        {"path": "tests/test_premortem.py", "kind": "test"},
    ]
    spec = _spec(scope=["core/utils.py", "core/premortem.py"], research_findings=findings)
    plan = build_plan(spec, _premortem())
    utils_step = next(s for s in plan.steps if s.target == "core/utils.py")
    pre_step = next(s for s in plan.steps if s.target == "core/premortem.py")
    assert utils_step.reference_artifacts == ["tests/test_utils.py"]
    assert pre_step.reference_artifacts == ["tests/test_premortem.py"]


def test_build_plan_reference_artifacts_ignores_unrelated():
    """무관한 finding 경로는 reference_artifacts 에 포함되지 않는다."""
    findings = [
        {"path": "core/utils.py", "kind": "source"},
        {"path": "docs/random.md", "kind": "doc"},
    ]
    spec = _spec(scope=["core/utils.py"], research_findings=findings)
    plan = build_plan(spec, _premortem())
    impl = next(s for s in plan.steps if s.target == "core/utils.py")
    assert "docs/random.md" not in impl.reference_artifacts


def test_build_plan_reference_artifacts_no_stem_collision():
    """동일 stem 다른 경로(`scripts/utils.py` vs `core/utils.py`) 는 reference 에서 제외된다.

    WARN-fix 회귀 가드: companion test 만 매칭하므로 `scripts/utils.py` 같은 sibling
    소스가 잘못 끌려오지 않는다.
    """
    findings = [
        {"path": "core/utils.py", "kind": "source"},
        {"path": "scripts/utils.py", "kind": "source"},   # 동일 stem, 무관한 모듈
        {"path": "tests/test_utils.py", "kind": "test"},
    ]
    spec = _spec(scope=["core/utils.py"], research_findings=findings)
    plan = build_plan(spec, _premortem())
    impl = next(s for s in plan.steps if s.target == "core/utils.py")
    assert impl.reference_artifacts == ["tests/test_utils.py"]


def test_build_plan_reference_artifacts_dedup_path_separator():
    """Windows/POSIX path separator 가 섞여도 한 번만 포함된다 (canonical=POSIX)."""
    findings = [
        {"path": "core/utils.py", "kind": "source"},
        {"path": "tests\\test_utils.py", "kind": "test"},   # Windows-style
        {"path": "tests/test_utils.py", "kind": "test"},    # POSIX-style (dup)
    ]
    spec = _spec(scope=["core/utils.py"], research_findings=findings)
    plan = build_plan(spec, _premortem())
    impl = next(s for s in plan.steps if s.target == "core/utils.py")
    assert impl.reference_artifacts == ["tests/test_utils.py"]


def test_build_plan_reference_artifacts_scope_backslash_excludes_self():
    """scope item 이 backslash 로 들어와도 자기 자신을 reference 에 끌어오지 않는다."""
    findings = [
        {"path": "core\\utils.py", "kind": "source"},
        {"path": "tests/test_utils.py", "kind": "test"},
    ]
    spec = _spec(scope=["core/utils.py"], research_findings=findings)
    plan = build_plan(spec, _premortem())
    impl = next(s for s in plan.steps if s.target == "core/utils.py")
    assert "core/utils.py" not in impl.reference_artifacts
    assert "core\\utils.py" not in impl.reference_artifacts


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


def test_build_plan_fallback_pytest_when_only_comment_risks():
    # Comment-only premortem → fallback derives pytest cmd from scope file path.
    risks = [_risk("R5", "assumption", "assumption", ["# Validate assumption"])]
    spec = _spec(scope=["core/foo.py"])
    plan = build_plan(spec, _premortem(risks))
    verify = next((s for s in plan.steps if s.target == "verification"), None)
    assert verify is not None
    assert any("test_foo" in cmd for cmd in verify.commands)
    assert any("test_foo" in cmd for cmd in plan.verification_requirements)


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
# build_plan — investigation steps (assumption risks)
# ---------------------------------------------------------------------------

def test_build_plan_single_assumption_risk_becomes_investigation_step():
    """assumption risk 1개 → investigation step 1개 생성."""
    risks = [_risk("R10", "rate limiting not validated", "assumption", ["grep rate_limit core/"])]
    plan = build_plan(_spec(), _premortem(risks))
    inv = [s for s in plan.steps if s.target == "rate limiting not validated"]
    assert len(inv) == 1
    assert "Investigate" in inv[0].action
    assert "grep rate_limit core/" in inv[0].commands


def test_build_plan_two_assumption_risks_become_two_investigation_steps():
    """assumption risk 2개 → investigation step 2개 생성, 순서 보존."""
    risks = [
        _risk("R7", "cache size assumption", "assumption", ["check cache size"]),
        _risk("R12", "timeout assumption", "assumption", ["ping endpoint"]),
    ]
    plan = build_plan(_spec(), _premortem(risks))
    inv = [s for s in plan.steps if s.target in ("cache size assumption", "timeout assumption")]
    assert len(inv) == 2
    targets = [s.target for s in inv]
    assert "cache size assumption" in targets
    assert "timeout assumption" in targets


def test_build_plan_no_assumption_risks_no_assumption_investigation_steps():
    """assumption 범주 외 risk만 있으면 assumption investigation step 없음."""
    risks = [_risk("R1", "blueprint sync risk", "blueprint_sync", ["cmd"])]
    plan = build_plan(_spec(), _premortem(risks))
    inv = [s for s in plan.steps if s.action.startswith("Investigate")]
    assert inv == []


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


# ---------------------------------------------------------------------------
# implementation_steps
# ---------------------------------------------------------------------------

class TestImplementationSteps:
    def test_returns_empty_for_empty_plan(self):
        plan = ExecutablePlan(intent="x")
        assert implementation_steps(plan) == []

    def test_returns_empty_when_no_implement_id(self):
        plan = ExecutablePlan(intent="x", steps=[
            PlanStep(id="S1", action="research", target="research"),
            PlanStep(id="S2", action="verify", target="verification"),
        ])
        assert implementation_steps(plan) == []

    def test_filters_only_implement_ids(self):
        impl_a = PlanStep(id="IMPLEMENT_1", action="impl a", target="core/a.py")
        impl_b = PlanStep(id="STEP_IMPLEMENT_B", action="impl b", target="core/b.py")
        other = PlanStep(id="S1", action="other", target="research")
        plan = ExecutablePlan(intent="x", steps=[impl_a, other, impl_b])
        result = implementation_steps(plan)
        assert result == [impl_a, impl_b]

    def test_preserves_step_order(self):
        steps = [
            PlanStep(id="IMPLEMENT_3", action="3", target="c"),
            PlanStep(id="IMPLEMENT_1", action="1", target="a"),
            PlanStep(id="IMPLEMENT_2", action="2", target="b"),
        ]
        plan = ExecutablePlan(intent="x", steps=steps)
        result = implementation_steps(plan)
        assert [s.id for s in result] == ["IMPLEMENT_3", "IMPLEMENT_1", "IMPLEMENT_2"]

    def test_case_sensitive_match(self):
        # 'implement' (lowercase) must NOT match 'IMPLEMENT'.
        plan = ExecutablePlan(intent="x", steps=[
            PlanStep(id="implement_1", action="lower", target="core/a.py"),
        ])
        assert implementation_steps(plan) == []

    def test_returns_list_type(self):
        plan = ExecutablePlan(intent="x")
        assert isinstance(implementation_steps(plan), list)


# ---------------------------------------------------------------------------
# TestScopeFileRiskInvestigation
# ---------------------------------------------------------------------------

class TestScopeFileRiskInvestigation:
    def test_no_scope_file_risk_no_investigation_step(self):
        """scope_file risk 없으면 경로 확인 step이 생성되지 않는다."""
        risks = [_risk("R1", "blueprint sync", "blueprint_sync", ["cmd"])]
        plan = build_plan(_spec(), _premortem(risks))
        path_check = [s for s in plan.steps if s.action.startswith("경로 확인")]
        assert path_check == []

    def test_scope_file_risk_single_missing_generates_one_step(self):
        """scope_file risk 1개(파일 1개) → 경로 확인 step 1개 생성."""
        risks = [_risk(
            "R11",
            "Scope file(s) not found on disk: core/missing.py. Possible typo in path.",
            "scope_file",
        )]
        plan = build_plan(_spec(), _premortem(risks))
        path_check = [s for s in plan.steps if s.action.startswith("경로 확인")]
        assert len(path_check) == 1
        assert path_check[0].action == "경로 확인: core/missing.py"
        assert path_check[0].target == "core/missing.py"

    def test_scope_file_risk_step_has_existence_check_command(self):
        """경로 확인 step의 command는 os.path.exists 호출이다."""
        risks = [_risk(
            "R11",
            "Scope file(s) not found on disk: core/missing.py. Possible typo in path.",
            "scope_file",
        )]
        plan = build_plan(_spec(), _premortem(risks))
        step = next(s for s in plan.steps if s.action.startswith("경로 확인"))
        assert len(step.commands) == 1
        assert "os.path.exists" in step.commands[0]
        assert "core/missing.py" in step.commands[0]

    def test_scope_file_risk_multiple_missing_generates_one_step_each(self):
        """scope_file risk 1개에 파일 2개 → 경로 확인 step 2개 생성, 순서 보존."""
        risks = [_risk(
            "R11",
            "Scope file(s) not found on disk: core/a.py, core/b.py. Possible typo in path.",
            "scope_file",
        )]
        plan = build_plan(_spec(), _premortem(risks))
        path_check = [s for s in plan.steps if s.action.startswith("경로 확인")]
        assert len(path_check) == 2
        assert path_check[0].target == "core/a.py"
        assert path_check[1].target == "core/b.py"

    def test_extract_scope_file_paths_single(self):
        """_extract_scope_file_paths: 단일 경로 파싱."""
        risk = _risk(
            "R11",
            "Scope file(s) not found on disk: core/foo.py. Possible typo in path.",
            "scope_file",
        )
        assert _extract_scope_file_paths(risk) == ["core/foo.py"]

    def test_extract_scope_file_paths_multiple(self):
        """_extract_scope_file_paths: 다중 경로 파싱."""
        risk = _risk(
            "R11",
            "Scope file(s) not found on disk: core/a.py, scripts/b.py. Possible typo in path.",
            "scope_file",
        )
        assert _extract_scope_file_paths(risk) == ["core/a.py", "scripts/b.py"]

    def test_extract_scope_file_paths_unrecognized_format_returns_empty(self):
        """형식이 다르면 빈 리스트 반환 — 파싱 실패 silent."""
        risk = _risk("R11", "Some other description.", "scope_file")
        assert _extract_scope_file_paths(risk) == []

    def test_scope_file_steps_come_before_implementation(self):
        """경로 확인 step은 implementation step보다 먼저 배치된다."""
        risks = [_risk(
            "R11",
            "Scope file(s) not found on disk: core/missing.py. Possible typo in path.",
            "scope_file",
        )]
        spec = _spec(scope=["core/utils.py"])
        plan = build_plan(spec, _premortem(risks))
        idx_path = next(i for i, s in enumerate(plan.steps) if s.action.startswith("경로 확인"))
        idx_impl = next(i for i, s in enumerate(plan.steps) if s.target == "core/utils.py")
        assert idx_path < idx_impl


# ---------------------------------------------------------------------------
# TestStaleTestRiskInvestigation
# ---------------------------------------------------------------------------

class TestStaleTestRiskInvestigation:
    def test_no_stale_test_risk_no_investigation_step(self):
        """stale_test risk 없으면 테스트 작성 step이 생성되지 않는다."""
        risks = [_risk("R1", "blueprint sync", "blueprint_sync", ["cmd"])]
        plan = build_plan(_spec(), _premortem(risks))
        write_steps = [s for s in plan.steps if s.action.startswith("테스트 작성")]
        assert write_steps == []

    def test_stale_test_risk_single_file_generates_one_step(self):
        """stale_test risk 1개(파일 1개) → 테스트 작성 step 1개 생성."""
        risks = [_risk(
            "R12",
            "No test file found for scope file(s): core/utils.py.",
            "stale_test",
        )]
        plan = build_plan(_spec(), _premortem(risks))
        write_steps = [s for s in plan.steps if s.action.startswith("테스트 작성")]
        assert len(write_steps) == 1
        assert write_steps[0].action == "테스트 작성: tests/test_utils.py"
        assert write_steps[0].target == "tests/test_utils.py"

    def test_stale_test_risk_target_is_test_file_path(self):
        """step target은 소스 파일이 아니라 tests/test_<stem>.py 경로이다."""
        risks = [_risk(
            "R12",
            "No test file found for scope file(s): core/planner.py.",
            "stale_test",
        )]
        plan = build_plan(_spec(), _premortem(risks))
        step = next(s for s in plan.steps if s.action.startswith("테스트 작성"))
        assert step.target == "tests/test_planner.py"

    def test_stale_test_risk_step_has_test_in_tests_required(self):
        """테스트 작성 step의 tests_required에 생성할 테스트 파일 경로가 포함된다."""
        risks = [_risk(
            "R12",
            "No test file found for scope file(s): core/utils.py.",
            "stale_test",
        )]
        plan = build_plan(_spec(), _premortem(risks))
        step = next(s for s in plan.steps if s.action.startswith("테스트 작성"))
        assert "tests/test_utils.py" in step.tests_required

    def test_stale_test_risk_multiple_files_generates_one_step_each(self):
        """stale_test risk 1개에 파일 2개 → 테스트 작성 step 2개 생성, 순서 보존."""
        risks = [_risk(
            "R12",
            "No test file found for scope file(s): core/utils.py, core/planner.py.",
            "stale_test",
        )]
        plan = build_plan(_spec(), _premortem(risks))
        write_steps = [s for s in plan.steps if s.action.startswith("테스트 작성")]
        assert len(write_steps) == 2
        assert write_steps[0].target == "tests/test_utils.py"
        assert write_steps[1].target == "tests/test_planner.py"

    def test_stale_test_steps_come_before_implementation(self):
        """테스트 작성 step은 implementation step보다 먼저 배치된다."""
        risks = [_risk(
            "R12",
            "No test file found for scope file(s): core/utils.py.",
            "stale_test",
        )]
        spec = _spec(scope=["core/utils.py"])
        plan = build_plan(spec, _premortem(risks))
        idx_write = next(i for i, s in enumerate(plan.steps) if s.action.startswith("테스트 작성"))
        idx_impl = next(i for i, s in enumerate(plan.steps) if s.target == "core/utils.py")
        assert idx_write < idx_impl

    def test_extract_stale_test_paths_single(self):
        """_extract_stale_test_paths: 단일 파일 → 단일 테스트 경로 반환."""
        risk = _risk(
            "R12",
            "No test file found for scope file(s): core/utils.py.",
            "stale_test",
        )
        assert _extract_stale_test_paths(risk) == ["tests/test_utils.py"]

    def test_extract_stale_test_paths_multiple(self):
        """_extract_stale_test_paths: 다중 파일 → 다중 테스트 경로 반환."""
        risk = _risk(
            "R12",
            "No test file found for scope file(s): core/utils.py, core/planner.py.",
            "stale_test",
        )
        assert _extract_stale_test_paths(risk) == [
            "tests/test_utils.py",
            "tests/test_planner.py",
        ]

    def test_extract_stale_test_paths_unrecognized_format_returns_empty(self):
        """형식이 다르면 빈 리스트 반환."""
        risk = _risk("R12", "Some other description.", "stale_test")
        assert _extract_stale_test_paths(risk) == []


class TestDuplicateFunctionRiskInvestigation:
    """R13(duplicate_function) risk → investigation steps."""

    def _dup_risk(self, desc: str) -> PremortomRisk:
        return _risk("R13", desc, "duplicate_function")

    def test_single_duplicate_generates_one_step(self):
        """`foo` in core/utils.py → 1개 investigation step."""
        risk = self._dup_risk(
            "Function(s) named in intent already exist in scope: `foo` in core/utils.py."
        )
        spec = _spec(scope=["core/utils.py"])
        plan = build_plan(spec, _premortem([risk]))
        inv = [s for s in plan.steps if s.action.startswith("기존 정의 확인")]
        assert len(inv) == 1
        assert "`foo`" in inv[0].action
        assert "core/utils.py" in inv[0].action

    def test_step_has_grep_command(self):
        """investigation step에 grep 명령어가 포함된다."""
        risk = self._dup_risk(
            "Function(s) named in intent already exist in scope: `bar` in core/utils.py."
        )
        spec = _spec(scope=["core/utils.py"])
        plan = build_plan(spec, _premortem([risk]))
        inv = [s for s in plan.steps if s.action.startswith("기존 정의 확인")]
        assert inv[0].commands
        assert "grep" in inv[0].commands[0]
        assert "bar" in inv[0].commands[0]

    def test_multiple_duplicates_generate_multiple_steps(self):
        """두 함수 → 2개 investigation step."""
        risk = self._dup_risk(
            "Function(s) named in intent already exist in scope: "
            "`foo` in core/utils.py, `bar` in core/utils.py."
        )
        spec = _spec(scope=["core/utils.py"])
        plan = build_plan(spec, _premortem([risk]))
        inv = [s for s in plan.steps if s.action.startswith("기존 정의 확인")]
        assert len(inv) == 2

    def test_duplicate_steps_come_before_implementation(self):
        """investigation step은 implementation step보다 먼저 배치된다."""
        risk = self._dup_risk(
            "Function(s) named in intent already exist in scope: `foo` in core/utils.py."
        )
        spec = _spec(scope=["core/utils.py"])
        plan = build_plan(spec, _premortem([risk]))
        idx_inv = next(i for i, s in enumerate(plan.steps) if s.action.startswith("기존 정의 확인"))
        idx_impl = next(i for i, s in enumerate(plan.steps) if s.action.startswith("Implement"))
        assert idx_inv < idx_impl

    def test_extract_duplicate_function_paths_single(self):
        """_extract_duplicate_function_paths: 단일 항목 파싱."""
        risk = self._dup_risk(
            "Function(s) named in intent already exist in scope: `foo` in core/utils.py."
        )
        assert _extract_duplicate_function_paths(risk) == [("foo", "core/utils.py")]

    def test_extract_duplicate_function_paths_multiple(self):
        """_extract_duplicate_function_paths: 다중 항목 파싱."""
        risk = self._dup_risk(
            "Function(s) named in intent already exist in scope: "
            "`foo` in core/utils.py, `bar` in core/planner.py."
        )
        assert _extract_duplicate_function_paths(risk) == [
            ("foo", "core/utils.py"),
            ("bar", "core/planner.py"),
        ]

    def test_extract_duplicate_function_paths_unrecognized_format_returns_empty(self):
        """형식이 다르면 빈 리스트 반환."""
        risk = self._dup_risk("Some other description.")
        assert _extract_duplicate_function_paths(risk) == []


class TestConflictingImportRiskInvestigation:
    """R14(conflicting_import) risk → investigation steps."""

    def _import_risk(self, desc: str) -> PremortomRisk:
        return _risk("R14", desc, "conflicting_import")

    def test_single_conflict_generates_one_step(self):
        """`foo` in core/utils.py → 1개 investigation step."""
        risk = self._import_risk(
            "Function name(s) in intent conflict with existing imports in scope: `foo` in core/utils.py."
        )
        spec = _spec(scope=["core/utils.py"])
        plan = build_plan(spec, _premortem([risk]))
        inv = [s for s in plan.steps if s.action.startswith("import 충돌 확인")]
        assert len(inv) == 1
        assert "`foo`" in inv[0].action
        assert "core/utils.py" in inv[0].action

    def test_step_has_grep_import_command(self):
        """investigation step에 'grep ... import foo' 명령어가 포함된다."""
        risk = self._import_risk(
            "Function name(s) in intent conflict with existing imports in scope: `bar` in core/utils.py."
        )
        spec = _spec(scope=["core/utils.py"])
        plan = build_plan(spec, _premortem([risk]))
        inv = [s for s in plan.steps if s.action.startswith("import 충돌 확인")]
        assert inv[0].commands
        assert "grep" in inv[0].commands[0]
        assert "import" in inv[0].commands[0]
        assert "bar" in inv[0].commands[0]

    def test_multiple_conflicts_generate_multiple_steps(self):
        """두 충돌 → 2개 investigation step."""
        risk = self._import_risk(
            "Function name(s) in intent conflict with existing imports in scope: "
            "`foo` in core/utils.py, `bar` in core/utils.py."
        )
        spec = _spec(scope=["core/utils.py"])
        plan = build_plan(spec, _premortem([risk]))
        inv = [s for s in plan.steps if s.action.startswith("import 충돌 확인")]
        assert len(inv) == 2

    def test_conflict_steps_come_before_implementation(self):
        """investigation step은 implementation step보다 먼저 배치된다."""
        risk = self._import_risk(
            "Function name(s) in intent conflict with existing imports in scope: `foo` in core/utils.py."
        )
        spec = _spec(scope=["core/utils.py"])
        plan = build_plan(spec, _premortem([risk]))
        idx_inv = next(i for i, s in enumerate(plan.steps) if s.action.startswith("import 충돌 확인"))
        idx_impl = next(i for i, s in enumerate(plan.steps) if s.action.startswith("Implement"))
        assert idx_inv < idx_impl

    def test_extract_conflicting_import_pairs_single(self):
        """_extract_conflicting_import_pairs: 단일 항목 파싱."""
        risk = self._import_risk(
            "Function name(s) in intent conflict with existing imports in scope: `foo` in core/utils.py."
        )
        from core.planner import _extract_conflicting_import_pairs
        assert _extract_conflicting_import_pairs(risk) == [("foo", "core/utils.py")]

    def test_extract_conflicting_import_pairs_multiple(self):
        """_extract_conflicting_import_pairs: 다중 항목 파싱."""
        risk = self._import_risk(
            "Function name(s) in intent conflict with existing imports in scope: "
            "`foo` in core/utils.py, `bar` in core/planner.py."
        )
        from core.planner import _extract_conflicting_import_pairs
        assert _extract_conflicting_import_pairs(risk) == [
            ("foo", "core/utils.py"),
            ("bar", "core/planner.py"),
        ]

    def test_extract_conflicting_import_pairs_unrecognized_format_returns_empty(self):
        """형식이 다르면 빈 리스트 반환."""
        risk = self._import_risk("Some other description.")
        from core.planner import _extract_conflicting_import_pairs
        assert _extract_conflicting_import_pairs(risk) == []

    def test_no_conflicting_import_risk_no_investigation_step(self):
        """conflicting_import risk 없으면 import 충돌 확인 step이 생성되지 않는다."""
        risks = [_risk("R1", "blueprint sync", "blueprint_sync", ["cmd"])]
        plan = build_plan(_spec(), _premortem(risks))
        inv = [s for s in plan.steps if s.action.startswith("import 충돌 확인")]
        assert inv == []


class TestLongFunctionRiskInvestigation:
    """R15(long_function) risk → investigation steps."""

    def _long_risk(self, desc: str) -> PremortomRisk:
        return _risk("R15", desc, "long_function")

    def _risk_desc(self, fn: str = "big_fn", path: str = "core/utils.py", n: int = 80) -> str:
        return (
            f"Scope contains function(s) exceeding 50 lines: "
            f"`{fn}` in {path} ({n} lines)."
        )

    def test_single_long_function_generates_one_step(self):
        """긴 함수 1개 → 1개 investigation step."""
        risk = self._long_risk(self._risk_desc())
        plan = build_plan(_spec(scope=["core/utils.py"]), _premortem([risk]))
        inv = [s for s in plan.steps if s.action.startswith("긴 함수 검토")]
        assert len(inv) == 1
        assert "big_fn" in inv[0].action
        assert "core/utils.py" in inv[0].action

    def test_step_has_grep_def_command(self):
        """investigation step에 'grep -n def <func>' 명령어가 포함된다."""
        risk = self._long_risk(self._risk_desc(fn="my_fn"))
        plan = build_plan(_spec(scope=["core/utils.py"]), _premortem([risk]))
        inv = [s for s in plan.steps if s.action.startswith("긴 함수 검토")]
        assert inv[0].commands
        assert "grep" in inv[0].commands[0]
        assert "def my_fn" in inv[0].commands[0]

    def test_multiple_long_functions_generate_multiple_steps(self):
        """두 긴 함수 → 2개 investigation step."""
        desc = (
            "Scope contains function(s) exceeding 50 lines: "
            "`fn_a` in core/utils.py (60 lines), `fn_b` in core/planner.py (75 lines)."
        )
        risk = self._long_risk(desc)
        plan = build_plan(_spec(scope=["core/utils.py"]), _premortem([risk]))
        inv = [s for s in plan.steps if s.action.startswith("긴 함수 검토")]
        assert len(inv) == 2

    def test_long_function_steps_come_before_implementation(self):
        """investigation step은 implementation step보다 먼저 배치된다."""
        risk = self._long_risk(self._risk_desc())
        plan = build_plan(_spec(scope=["core/utils.py"]), _premortem([risk]))
        idx_inv = next(i for i, s in enumerate(plan.steps) if s.action.startswith("긴 함수 검토"))
        idx_impl = next(i for i, s in enumerate(plan.steps) if s.action.startswith("Implement"))
        assert idx_inv < idx_impl

    def test_extract_long_function_pairs_single(self):
        """_extract_long_function_pairs: 단일 항목 파싱."""
        risk = self._long_risk(self._risk_desc("my_fn", "core/utils.py", 99))
        from core.planner import _extract_long_function_pairs
        assert _extract_long_function_pairs(risk) == [("my_fn", "core/utils.py", 99)]

    def test_extract_long_function_pairs_multiple(self):
        """_extract_long_function_pairs: 복수 항목 파싱."""
        desc = (
            "Scope contains function(s) exceeding 50 lines: "
            "`fn_a` in core/utils.py (60 lines), `fn_b` in core/planner.py (75 lines)."
        )
        risk = self._long_risk(desc)
        from core.planner import _extract_long_function_pairs
        assert _extract_long_function_pairs(risk) == [
            ("fn_a", "core/utils.py", 60),
            ("fn_b", "core/planner.py", 75),
        ]

    def test_extract_long_function_pairs_unrecognized_format_returns_empty(self):
        """형식이 다르면 빈 리스트 반환."""
        risk = self._long_risk("Some other description.")
        from core.planner import _extract_long_function_pairs
        assert _extract_long_function_pairs(risk) == []

    def test_no_long_function_risk_no_investigation_step(self):
        """long_function risk 없으면 긴 함수 검토 step이 생성되지 않는다."""
        risks = [_risk("R1", "blueprint sync", "blueprint_sync", ["cmd"])]
        plan = build_plan(_spec(), _premortem(risks))
        inv = [s for s in plan.steps if s.action.startswith("긴 함수 검토")]
        assert inv == []
