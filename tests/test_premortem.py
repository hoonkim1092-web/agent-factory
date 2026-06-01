"""Tests for core.premortem (§17 Step 5)."""
from __future__ import annotations

import pytest

from core.spec_compiler import CompiledSpec
from core.premortem import (
    PremortomResult,
    PremortomRisk,
    VerificationStep,
    run_premortem,
    _detect_blueprint_sync_risk,
    _detect_packaging_risk,
    _detect_workspace_risk,
    _detect_destructive_risk,
    _detect_assumption_risks,
    _detect_existing_pattern_risk,
    _detect_gap_risks,
    _detect_scope_file_risk,
    _detect_stale_test_risk,
    _detect_duplicate_function_risk,
    _detect_conflicting_import_risk,
    _detect_long_function_risk,
    _LONG_FUNCTION_THRESHOLD,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _spec(
    intent="Add premortem module",
    scope=None,
    risk_hints=None,
    constraints=None,
    approval_policy="",
    assumptions=None,
    gaps=None,
    research_findings=None,
) -> CompiledSpec:
    return CompiledSpec(
        intent=intent,
        scope=scope or [],
        risk_hints=risk_hints or [],
        constraints=constraints or [],
        approval_policy=approval_policy,
        assumptions=assumptions or [],
        gaps=gaps or [],
        research_findings=research_findings or [],
    )


# ---------------------------------------------------------------------------
# VerificationStep / PremortomRisk / PremortomResult data model
# ---------------------------------------------------------------------------

def test_verification_step_to_dict():
    step = VerificationStep(command="pytest tests/", description="All tests pass")
    d = step.to_dict()
    assert d == {"command": "pytest tests/", "description": "All tests pass"}


def test_premortem_risk_to_dict_has_all_keys():
    risk = PremortomRisk(
        id="R1",
        description="Some risk",
        category="blueprint_sync",
        verification=[VerificationStep(command="x", description="y")],
    )
    d = risk.to_dict()
    assert set(d.keys()) == {"id", "description", "category", "verification"}
    assert d["verification"][0]["command"] == "x"


def test_premortem_result_has_risks_true():
    r = PremortomResult(risks=[PremortomRisk("R1", "desc", "cat")], spec_intent="x")
    assert r.has_risks() is True


def test_premortem_result_has_risks_false():
    assert PremortomResult().has_risks() is False


def test_premortem_result_to_dict_shape():
    r = PremortomResult(spec_intent="intent", risks=[])
    d = r.to_dict()
    assert d == {"spec_intent": "intent", "risks": []}


# ---------------------------------------------------------------------------
# _detect_blueprint_sync_risk
# ---------------------------------------------------------------------------

def test_blueprint_risk_fires_for_core_py_scope():
    risk = _detect_blueprint_sync_risk(["core/premortem.py"], [])
    assert risk is not None
    assert risk.id == "R1"
    assert risk.category == "blueprint_sync"
    assert len(risk.verification) == 3


def test_blueprint_risk_fires_for_core_py_in_risk_hints():
    risk = _detect_blueprint_sync_risk([], ["Blueprint sync for core/*.py changes"])
    assert risk is not None


def test_blueprint_risk_no_fire_for_non_core():
    risk = _detect_blueprint_sync_risk(["scripts/foo.py", "docs/bar.md"], [])
    assert risk is None


def test_blueprint_risk_command_includes_file():
    risk = _detect_blueprint_sync_risk(["core/dogfood.py"], [])
    assert "core/dogfood.py" in risk.verification[0].command


def test_blueprint_risk_command_is_comment_when_no_scope_files():
    """Trigger from risk_hints only → first verification step must be a comment (not executable)."""
    risk = _detect_blueprint_sync_risk([], ["core/utils.py needs blueprint update"])
    assert risk is not None
    assert risk.verification[0].command.startswith("#")


def test_blueprint_risk_command_has_no_placeholder_when_scope_files_present():
    """Trigger from scope → py_compile command must not contain placeholder text."""
    risk = _detect_blueprint_sync_risk(["core/utils.py"], [])
    assert risk is not None
    assert "<changed>" not in risk.verification[0].command
    assert "py_compile" in risk.verification[0].command


# ---------------------------------------------------------------------------
# _detect_packaging_risk
# ---------------------------------------------------------------------------

def test_packaging_risk_fires_for_core_py():
    risk = _detect_packaging_risk(["core/dogfood.py"], [])
    assert risk is not None
    assert risk.id == "R2"
    assert risk.category == "packaging"


def test_packaging_risk_fires_for_cli_entry():
    risk = _detect_packaging_risk(["run_factory_cli.py"], [])
    assert risk is not None


def test_packaging_risk_fires_for_af_spec():
    risk = _detect_packaging_risk(["af.spec"], [])
    assert risk is not None


def test_packaging_risk_no_fire_for_tests_only():
    risk = _detect_packaging_risk(["tests/test_foo.py"], [])
    assert risk is None


# ---------------------------------------------------------------------------
# _detect_workspace_risk
# ---------------------------------------------------------------------------

def test_workspace_risk_fires_for_dogfood_scope():
    risk = _detect_workspace_risk(["core/dogfood.py"], [])
    assert risk is not None
    assert risk.id == "R3"
    assert risk.category == "workspace"


def test_workspace_risk_fires_for_worktree_hint():
    risk = _detect_workspace_risk([], ["worktree isolation required"])
    assert risk is not None


def test_workspace_risk_case_insensitive():
    risk = _detect_workspace_risk([], ["Dogfood execution path"])
    assert risk is not None


def test_workspace_risk_no_fire_for_unrelated():
    risk = _detect_workspace_risk(["core/research_brief.py"], [])
    assert risk is None


# ---------------------------------------------------------------------------
# _detect_destructive_risk
# ---------------------------------------------------------------------------

def test_destructive_risk_fires_for_policy():
    risk = _detect_destructive_risk("require_human_for_destructive", [])
    assert risk is not None
    assert risk.id == "R4"
    assert risk.category == "approval"


def test_destructive_risk_fires_for_constraint():
    risk = _detect_destructive_risk("", ["no force push allowed"])
    assert risk is not None


def test_destructive_risk_no_fire_when_absent():
    risk = _detect_destructive_risk("auto", ["worktree isolation"])
    assert risk is None


# ---------------------------------------------------------------------------
# _detect_assumption_risks
# ---------------------------------------------------------------------------

def test_assumption_risk_fires_for_low_confidence():
    assumptions = [{"id": "A1", "statement": "API is stable", "confidence": "low"}]
    risks = _detect_assumption_risks(assumptions)
    assert len(risks) == 1
    assert risks[0].id == "R5"
    assert risks[0].category == "assumption"
    assert "API is stable" in risks[0].description


def test_assumption_risk_fires_for_unknown_confidence():
    assumptions = [{"id": "A2", "statement": "No side effects", "confidence": "unknown"}]
    risks = _detect_assumption_risks(assumptions)
    assert len(risks) == 1


def test_assumption_risk_fires_for_missing_confidence():
    assumptions = [{"id": "A3", "statement": "DB schema unchanged"}]
    risks = _detect_assumption_risks(assumptions)
    assert len(risks) == 1


def test_assumption_risk_skips_medium_confidence():
    assumptions = [{"id": "A4", "statement": "Tests pass", "confidence": "medium"}]
    assert _detect_assumption_risks(assumptions) == []


def test_assumption_risk_skips_high_confidence():
    assumptions = [{"id": "A5", "statement": "Stable", "confidence": "high"}]
    assert _detect_assumption_risks(assumptions) == []


def test_assumption_risks_counter_sequential():
    assumptions = [
        {"statement": "X", "confidence": "low"},
        {"statement": "Y", "confidence": "low"},
    ]
    risks = _detect_assumption_risks(assumptions)
    assert [r.id for r in risks] == ["R5", "R6"]


# ---------------------------------------------------------------------------
# _detect_gap_risks
# ---------------------------------------------------------------------------

def test_gap_risk_fires_for_each_gap():
    gaps = ["How does AF store state?", "What retry limit is safe?"]
    risks = _detect_gap_risks(gaps)
    assert len(risks) == 2
    assert risks[0].id == "R20"
    assert risks[1].id == "R21"
    assert risks[0].category == "research_gap"


def test_gap_risk_no_risks_for_empty():
    assert _detect_gap_risks([]) == []


def test_gap_risk_description_contains_question():
    risks = _detect_gap_risks(["retry policy"])
    assert "retry policy" in risks[0].description


# ---------------------------------------------------------------------------
# run_premortem — integration
# ---------------------------------------------------------------------------

def test_run_premortem_empty_spec_no_risks():
    spec = _spec()
    result = run_premortem(spec)
    assert not result.has_risks()
    assert result.spec_intent == "Add premortem module"


def test_run_premortem_core_py_triggers_r1_r2():
    spec = _spec(scope=["core/dogfood.py"])
    result = run_premortem(spec)
    ids = [r.id for r in result.risks]
    assert "R1" in ids  # blueprint sync
    assert "R2" in ids  # packaging


def test_run_premortem_dogfood_scope_triggers_r3():
    spec = _spec(scope=["core/dogfood.py"])
    result = run_premortem(spec)
    ids = [r.id for r in result.risks]
    assert "R3" in ids


def test_run_premortem_destructive_policy_triggers_r4():
    spec = _spec(approval_policy="require_human_for_destructive")
    result = run_premortem(spec)
    ids = [r.id for r in result.risks]
    assert "R4" in ids


def test_run_premortem_gaps_become_risks():
    spec = _spec(gaps=["retry budget", "packaging path"])
    result = run_premortem(spec)
    categories = [r.category for r in result.risks]
    assert categories.count("research_gap") == 2


def test_run_premortem_low_confidence_assumptions_become_risks():
    assumptions = [{"statement": "API stable", "confidence": "low"}]
    spec = _spec(assumptions=assumptions)
    result = run_premortem(spec)
    categories = [r.category for r in result.risks]
    assert "assumption" in categories


def test_run_premortem_to_dict_has_all_keys():
    spec = _spec(scope=["core/dogfood.py"])
    d = run_premortem(spec).to_dict()
    assert "spec_intent" in d
    assert "risks" in d
    assert isinstance(d["risks"], list)


def test_run_premortem_full_pipeline_no_duplicate_ids():
    """All risks in a full-trigger spec must have unique IDs."""
    spec = _spec(
        scope=["core/dogfood.py", "run_factory_cli.py"],
        risk_hints=["Blueprint sync for core/*.py"],
        approval_policy="require_human_for_destructive",
        assumptions=[
            {"statement": "A", "confidence": "low"},
            {"statement": "B", "confidence": "low"},
        ],
        gaps=["retry budget"],
    )
    result = run_premortem(spec)
    ids = [r.id for r in result.risks]
    assert len(ids) == len(set(ids)), f"Duplicate IDs: {ids}"


def test_run_premortem_no_duplicate_ids_with_many_assumptions():
    """16+ low-confidence assumptions must not collide with gap IDs."""
    assumptions = [
        {"statement": f"Assumption {i}", "confidence": "low"}
        for i in range(16)
    ]
    spec = _spec(assumptions=assumptions, gaps=["gap question"])
    result = run_premortem(spec)
    ids = [r.id for r in result.risks]
    assert len(ids) == len(set(ids)), f"Duplicate IDs: {ids}"


def test_gap_start_shifts_when_many_assumptions():
    """Gap counter must start above assumption counter when assumptions > 15."""
    from core.premortem import _detect_gap_risks
    risks = _detect_gap_risks(["q1", "q2"], start=21)
    assert [r.id for r in risks] == ["R21", "R22"]


# ---------------------------------------------------------------------------
# _detect_existing_pattern_risk
# ---------------------------------------------------------------------------

def test_pattern_risk_fires_on_scope_overlap():
    findings = [{"path": "core/utils.py", "content": "def foo(): ...", "kind": "file_snippet"}]
    risk = _detect_existing_pattern_risk(findings, scope=["core/utils.py"])
    assert risk is not None
    assert risk.id == "R10"
    assert risk.category == "pattern_consistency"
    assert "core/utils.py" in risk.description


def test_pattern_risk_skips_when_no_overlap():
    findings = [{"path": "core/utils.py", "content": "...", "kind": "file_snippet"}]
    risk = _detect_existing_pattern_risk(findings, scope=["core/other.py"])
    assert risk is None


def test_pattern_risk_skips_empty_findings():
    assert _detect_existing_pattern_risk([], scope=["core/utils.py"]) is None


def test_pattern_risk_skips_finding_without_path():
    findings = [{"content": "...", "kind": "web_ref"}]
    assert _detect_existing_pattern_risk(findings, scope=["core/utils.py"]) is None


def test_pattern_risk_has_two_verification_steps():
    findings = [{"path": "core/utils.py", "content": "...", "kind": "file_snippet"}]
    risk = _detect_existing_pattern_risk(findings, scope=["core/utils.py"])
    assert risk is not None
    assert len(risk.verification) == 2


def test_pattern_risk_id_r10_no_collision_with_assumptions():
    """R10 must not duplicate assumption risk IDs in run_premortem."""
    assumptions = [{"statement": f"A{i}", "confidence": "low"} for i in range(9)]
    spec = _spec(
        scope=["core/utils.py"],
        research_findings=[{"path": "core/utils.py", "content": "...", "kind": "file_snippet"}],
        assumptions=assumptions,
    )
    result = run_premortem(spec)
    ids = [r.id for r in result.risks]
    assert "R10" in ids
    assert len(ids) == len(set(ids)), f"Duplicate IDs: {ids}"


def test_run_premortem_with_research_findings_adds_r10():
    spec = _spec(
        scope=["core/utils.py"],
        research_findings=[{"path": "core/utils.py", "content": "def add(): ...", "kind": "file_snippet"}],
    )
    result = run_premortem(spec)
    categories = [r.category for r in result.risks]
    assert "pattern_consistency" in categories
    r10 = next(r for r in result.risks if r.id == "R10")
    assert "core/utils.py" in r10.description


# ---------------------------------------------------------------------------
# TestDetectScopeFileRisk
# ---------------------------------------------------------------------------

class TestDetectScopeFileRisk:
    def test_empty_scope_returns_empty(self):
        assert _detect_scope_file_risk([]) == []

    def test_all_existing_files_returns_empty(self, tmp_path):
        f = tmp_path / "real.py"
        f.write_text("# real")
        assert _detect_scope_file_risk([str(f)]) == []

    def test_missing_file_returns_single_r11_risk(self):
        result = _detect_scope_file_risk(["nonexistent/__typo__/path.py"])
        assert len(result) == 1
        assert result[0].id == "R11"

    def test_r11_category_is_scope_file(self):
        result = _detect_scope_file_risk(["nonexistent/__typo__/path.py"])
        assert result[0].category == "scope_file"

    def test_description_mentions_missing_path(self):
        result = _detect_scope_file_risk(["typo/__missing__.py"])
        assert "typo/__missing__.py" in result[0].description

    def test_multiple_missing_files_in_one_risk(self):
        result = _detect_scope_file_risk(["__a__/b.py", "__c__/d.py"])
        assert len(result) == 1
        assert "__a__/b.py" in result[0].description
        assert "__c__/d.py" in result[0].description

    def test_mixed_existing_and_missing_reports_only_missing(self, tmp_path):
        real = tmp_path / "real.py"
        real.write_text("")
        result = _detect_scope_file_risk([str(real), "__missing__/file.py"])
        assert len(result) == 1
        assert "__missing__/file.py" in result[0].description
        assert str(real) not in result[0].description

    def test_r11_has_verification_step(self):
        result = _detect_scope_file_risk(["__no_such_file__.py"])
        assert len(result[0].verification) >= 1

    def test_run_premortem_fires_r11_for_missing_scope_file(self):
        spec = _spec(scope=["__nonexistent_scope_file_xyz__.py"])
        result = run_premortem(spec)
        ids = [r.id for r in result.risks]
        assert "R11" in ids

    def test_run_premortem_no_r11_when_scope_empty(self):
        spec = _spec(scope=[])
        result = run_premortem(spec)
        ids = [r.id for r in result.risks]
        assert "R11" not in ids

    def test_no_id_collision_when_r11_fires_with_assumptions_and_gaps(self):
        spec = _spec(
            scope=["__nonexistent_scope_file_xyz__.py"],
            assumptions=[
                {"statement": f"A{i}", "confidence": "low"} for i in range(3)
            ],
            gaps=["some gap"],
        )
        result = run_premortem(spec)
        ids = [r.id for r in result.risks]
        assert "R11" in ids
        assert len(ids) == len(set(ids)), f"Duplicate IDs: {ids}"

    def test_assumption_ids_start_at_r18_not_r17(self):
        """Assumptions start at R18: R11=scope_file, R12=stale_test, R13=duplicate_function, R14=conflicting_import, R15=long_function, R16=complexity, R17=nesting_depth."""
        assumptions = [{"statement": "first", "confidence": "low"}]
        spec = _spec(assumptions=assumptions)
        result = run_premortem(spec)
        ids = [r.id for r in result.risks]
        assert "R18" in ids
        assert "R17" not in ids  # no deeply nested functions in empty scope
        assert "R16" not in ids  # no complex functions in empty scope
        assert "R14" not in ids
        assert "R13" not in ids
        assert "R12" not in ids
        assert "R11" not in ids


# ---------------------------------------------------------------------------
# TestDetectStaleTestRisk
# ---------------------------------------------------------------------------

class TestDetectStaleTestRisk:
    def test_empty_scope_returns_none(self):
        assert _detect_stale_test_risk([]) is None

    def test_non_py_files_ignored(self):
        assert _detect_stale_test_risk(["docs/foo.md", "README.rst"]) is None

    def test_test_files_in_scope_are_skipped(self):
        # test_ files are already tests — no recursive check expected
        assert _detect_stale_test_risk(["tests/test_foo.py"]) is None

    def test_existing_test_file_returns_none(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        tests_dir = tmp_path / "tests"
        tests_dir.mkdir()
        (tests_dir / "test_mymodule.py").write_text("")
        src = tmp_path / "mymodule.py"
        src.write_text("")
        assert _detect_stale_test_risk([str(src.relative_to(tmp_path))]) is None

    def test_missing_test_file_returns_r12(self):
        result = _detect_stale_test_risk(["core/__no_test_for_this_module__.py"])
        assert result is not None
        assert result.id == "R12"

    def test_r12_category_is_stale_test(self):
        result = _detect_stale_test_risk(["core/__no_test_for_this_module__.py"])
        assert result.category == "stale_test"

    def test_description_mentions_missing_file(self):
        result = _detect_stale_test_risk(["core/__orphan__.py"])
        assert "core/__orphan__.py" in result.description

    def test_multiple_missing_tests_in_one_risk(self):
        result = _detect_stale_test_risk(["core/__a__.py", "core/__b__.py"])
        assert result is not None
        assert "core/__a__.py" in result.description
        assert "core/__b__.py" in result.description

    def test_has_verification_step(self):
        result = _detect_stale_test_risk(["core/__no_test__.py"])
        assert len(result.verification) >= 1

    def test_mixed_py_and_non_py_only_checks_py(self):
        # only core/__no_test__.py is .py and missing test
        result = _detect_stale_test_risk(["core/__no_test__.py", "docs/spec.md"])
        assert result is not None
        assert "docs/spec.md" not in result.description

    def test_run_premortem_fires_r12_for_missing_test(self):
        spec = _spec(scope=["core/__no_test_for_this_xyz__.py"])
        result = run_premortem(spec)
        ids = [r.id for r in result.risks]
        assert "R12" in ids

    def test_run_premortem_no_r12_when_scope_empty(self):
        spec = _spec(scope=[])
        result = run_premortem(spec)
        ids = [r.id for r in result.risks]
        assert "R12" not in ids

    def test_no_id_collision_r12_with_r11_and_assumptions(self):
        spec = _spec(
            scope=["__nonexistent_scope__.py", "core/__no_test_xyz__.py"],
            assumptions=[{"statement": f"A{i}", "confidence": "low"} for i in range(3)],
            gaps=["some gap"],
        )
        result = run_premortem(spec)
        ids = [r.id for r in result.risks]
        assert len(ids) == len(set(ids)), f"Duplicate IDs: {ids}"


# ---------------------------------------------------------------------------
# TestDuplicateFunctionRisk
# ---------------------------------------------------------------------------

class TestDuplicateFunctionRisk:
    def test_empty_scope_returns_none(self):
        assert _detect_duplicate_function_risk("`foo()` should be added", []) is None

    def test_no_backtick_names_returns_none(self):
        assert _detect_duplicate_function_risk("add a helper function", ["core/utils.py"]) is None

    def test_no_duplicate_returns_none(self, tmp_path):
        f = tmp_path / "mymod.py"
        f.write_text("def bar(): pass\n")
        assert _detect_duplicate_function_risk("`foo()` should be added", [str(f)]) is None

    def test_duplicate_found_returns_r13(self, tmp_path):
        f = tmp_path / "mymod.py"
        f.write_text("def foo(): pass\n")
        result = _detect_duplicate_function_risk("`foo()` should be added", [str(f)])
        assert result is not None
        assert result.id == "R13"
        assert result.category == "duplicate_function"

    def test_description_mentions_function_and_file(self, tmp_path):
        f = tmp_path / "mymod.py"
        f.write_text("def foo(): pass\n")
        result = _detect_duplicate_function_risk("`foo()` should be added", [str(f)])
        assert "foo" in result.description
        assert str(f) in result.description

    def test_multiple_duplicates_in_one_risk(self, tmp_path):
        f = tmp_path / "mymod.py"
        f.write_text("def foo(): pass\ndef bar(): pass\n")
        result = _detect_duplicate_function_risk("`foo()` and `bar()` to add", [str(f)])
        assert result is not None
        assert "foo" in result.description
        assert "bar" in result.description

    def test_non_py_scope_files_ignored(self, tmp_path):
        f = tmp_path / "config.yaml"
        f.write_text("foo: bar\n")
        assert _detect_duplicate_function_risk("`foo()` to add", [str(f)]) is None

    def test_run_premortem_fires_r13_for_duplicate(self, tmp_path):
        f = tmp_path / "mymod.py"
        f.write_text("def percentile(): pass\n")
        spec = _spec(
            intent="Add `percentile()` function",
            scope=[str(f)],
        )
        result = run_premortem(spec)
        ids = [r.id for r in result.risks]
        assert "R13" in ids

    def test_run_premortem_no_r13_when_no_duplicate(self, tmp_path):
        f = tmp_path / "mymod.py"
        f.write_text("def other(): pass\n")
        spec = _spec(
            intent="Add `percentile()` function",
            scope=[str(f)],
        )
        result = run_premortem(spec)
        ids = [r.id for r in result.risks]
        assert "R13" not in ids

    def test_assumption_ids_start_at_r18_not_r17(self):
        """Assumptions start at R18: R11=scope_file, R12=stale_test, R13=duplicate_function, R14=conflicting_import, R15=long_function, R16=complexity, R17=nesting_depth."""
        assumptions = [{"statement": "first", "confidence": "low"}]
        spec = _spec(assumptions=assumptions)
        result = run_premortem(spec)
        ids = [r.id for r in result.risks]
        assert "R18" in ids
        assert "R17" not in ids  # no deeply nested functions in empty scope
        assert "R16" not in ids  # no complex functions in empty scope
        assert "R14" not in ids
        assert "R13" not in ids

    def test_no_id_collision_with_all_detectors(self, tmp_path):
        f = tmp_path / "mymod.py"
        f.write_text("def percentile(): pass\n")
        spec = _spec(
            intent="Add `percentile()` function",
            scope=[str(f), "__nonexistent__.py", "core/__no_test_xyz__.py"],
            assumptions=[{"statement": f"A{i}", "confidence": "low"} for i in range(3)],
            gaps=["some gap"],
        )
        result = run_premortem(spec)
        ids = [r.id for r in result.risks]
        assert "R13" in ids
        assert len(ids) == len(set(ids)), f"Duplicate IDs: {ids}"


# ---------------------------------------------------------------------------
# TestConflictingImportRisk
# ---------------------------------------------------------------------------

class TestConflictingImportRisk:
    def test_no_backtick_names_returns_none(self):
        assert _detect_conflicting_import_risk("add a helper function", ["core/utils.py"]) is None

    def test_empty_scope_returns_none(self):
        assert _detect_conflicting_import_risk("`foo()` to add", []) is None

    def test_no_conflict_returns_none(self, tmp_path):
        f = tmp_path / "mymod.py"
        f.write_text("import os\n")
        assert _detect_conflicting_import_risk("`foo()` to add", [str(f)]) is None

    def test_direct_import_conflict_returns_r14(self, tmp_path):
        f = tmp_path / "mymod.py"
        f.write_text("import foo\n")
        result = _detect_conflicting_import_risk("`foo()` to add", [str(f)])
        assert result is not None
        assert result.id == "R14"
        assert result.category == "conflicting_import"

    def test_from_import_conflict_returns_r14(self, tmp_path):
        f = tmp_path / "mymod.py"
        f.write_text("from mypackage import foo\n")
        result = _detect_conflicting_import_risk("`foo()` to add", [str(f)])
        assert result is not None
        assert result.id == "R14"

    def test_description_mentions_name_and_file(self, tmp_path):
        f = tmp_path / "mymod.py"
        f.write_text("import bar\n")
        result = _detect_conflicting_import_risk("`bar()` to add", [str(f)])
        assert "bar" in result.description
        assert str(f) in result.description

    def test_non_py_scope_files_ignored(self, tmp_path):
        f = tmp_path / "config.yaml"
        f.write_text("import foo\n")
        assert _detect_conflicting_import_risk("`foo()` to add", [str(f)]) is None

    def test_missing_scope_file_skipped(self):
        assert _detect_conflicting_import_risk("`foo()` to add", ["__nonexistent__.py"]) is None

    def test_run_premortem_fires_r14_for_conflict(self, tmp_path):
        f = tmp_path / "mymod.py"
        f.write_text("from os.path import join\n")
        spec = _spec(
            intent="Add `join()` function",
            scope=[str(f)],
        )
        result = run_premortem(spec)
        ids = [r.id for r in result.risks]
        assert "R14" in ids

    def test_run_premortem_no_r14_when_no_conflict(self, tmp_path):
        f = tmp_path / "mymod.py"
        f.write_text("import os\n")
        spec = _spec(
            intent="Add `join()` function",
            scope=[str(f)],
        )
        result = run_premortem(spec)
        ids = [r.id for r in result.risks]
        assert "R14" not in ids

    def test_no_id_collision_with_all_detectors(self, tmp_path):
        f = tmp_path / "mymod.py"
        f.write_text("from os import join\ndef join(): pass\n")
        spec = _spec(
            intent="Add `join()` function",
            scope=[str(f), "__nonexistent__.py", "core/__no_test_xyz__.py"],
            assumptions=[{"statement": f"A{i}", "confidence": "low"} for i in range(3)],
            gaps=["some gap"],
        )
        result = run_premortem(spec)
        ids = [r.id for r in result.risks]
        assert "R13" in ids
        assert "R14" in ids
        assert len(ids) == len(set(ids)), f"Duplicate IDs: {ids}"


class TestLongFunctionRisk:
    """Tests for _detect_long_function_risk (R15)."""

    def _make_long_func(self, tmp_path, name: str = "big_fn", lines: int = 51) -> str:
        body = "\n".join(f"    x{i} = {i}" for i in range(lines - 1))
        source = f"def {name}():\n{body}\n    return x0\n"
        f = tmp_path / "mod.py"
        f.write_text(source)
        return str(f)

    def test_empty_scope_returns_empty(self):
        assert _detect_long_function_risk([]) == []

    def test_non_py_files_ignored(self, tmp_path):
        f = tmp_path / "config.yaml"
        f.write_text("key: value\n")
        assert _detect_long_function_risk([str(f)]) == []

    def test_short_function_returns_empty(self, tmp_path):
        f = tmp_path / "mod.py"
        f.write_text("def small():\n    return 1\n")
        assert _detect_long_function_risk([str(f)]) == []

    def test_exactly_threshold_lines_returns_empty(self, tmp_path):
        # def line + (_LONG_FUNCTION_THRESHOLD - 1) body lines = _LONG_FUNCTION_THRESHOLD total
        body = "\n".join(f"    x{i} = {i}" for i in range(_LONG_FUNCTION_THRESHOLD - 1))
        source = f"def borderline():\n{body}\n"
        f = tmp_path / "mod.py"
        f.write_text(source)
        assert _detect_long_function_risk([str(f)]) == []

    def test_one_over_threshold_returns_r15(self, tmp_path):
        path = self._make_long_func(tmp_path, lines=_LONG_FUNCTION_THRESHOLD + 1)
        result = _detect_long_function_risk([path])
        assert len(result) == 1
        assert result[0].id == "R15"

    def test_category_is_long_function(self, tmp_path):
        path = self._make_long_func(tmp_path)
        result = _detect_long_function_risk([path])
        assert result[0].category == "long_function"

    def test_description_mentions_function_name_and_file(self, tmp_path):
        path = self._make_long_func(tmp_path, name="my_fn")
        result = _detect_long_function_risk([path])
        assert "my_fn" in result[0].description
        assert path in result[0].description

    def test_missing_scope_file_skipped(self):
        assert _detect_long_function_risk(["__nonexistent__.py"]) == []

    def test_syntax_error_file_skipped(self, tmp_path):
        f = tmp_path / "broken.py"
        f.write_text("def bad(:\n    pass\n")
        assert _detect_long_function_risk([str(f)]) == []

    def test_run_premortem_fires_r15_for_long_function(self, tmp_path):
        path = self._make_long_func(tmp_path)
        spec = _spec(intent="Add feature", scope=[path])
        result = run_premortem(spec)
        ids = [r.id for r in result.risks]
        assert "R15" in ids

    def test_run_premortem_no_r15_for_short_functions(self, tmp_path):
        f = tmp_path / "mod.py"
        f.write_text("def tiny():\n    return 1\n")
        spec = _spec(intent="Add feature", scope=[str(f)])
        result = run_premortem(spec)
        ids = [r.id for r in result.risks]
        assert "R15" not in ids

    def test_no_id_collision_r15_with_all_detectors(self, tmp_path):
        # _make_long_func writes to tmp_path/mod.py; use a different name for second file
        long_fn_path = self._make_long_func(tmp_path, name="join")
        conflict_path = tmp_path / "conflict.py"
        conflict_path.write_text("from os import join\ndef join(): pass\n")
        spec = _spec(
            intent="Add `join()` function",
            scope=[str(long_fn_path), str(conflict_path), "__nonexistent__.py"],
            assumptions=[{"statement": f"A{i}", "confidence": "low"} for i in range(3)],
            gaps=["some gap"],
        )
        result = run_premortem(spec)
        ids = [r.id for r in result.risks]
        assert "R15" in ids
        assert len(ids) == len(set(ids)), f"Duplicate IDs: {ids}"


# ---------------------------------------------------------------------------
# TestComplexityRisk
# ---------------------------------------------------------------------------

class TestComplexityRisk:
    """Tests for _detect_complexity_risk (R16)."""

    def _make_simple_func(self, tmp_path) -> str:
        source = "def simple():\n    return 1\n"
        f = tmp_path / "mod.py"
        f.write_text(source)
        return str(f)

    def _make_complex_func(self, tmp_path, name: str = "complex_fn", complexity: int = 12) -> str:
        """Build a function with enough if/for/while to exceed the threshold."""
        # complexity = 1 + number of If/For/While nodes
        branches = complexity - 1
        body_lines = []
        for i in range(branches):
            body_lines.append(f"    if x{i} > 0:")
            body_lines.append(f"        x{i} = 1")
        source = f"def {name}(x0=0, **kwargs):\n"
        for i in range(1, branches):
            source += f"    x{i} = {i}\n"
        source += "\n".join(body_lines) + "\n    return 0\n"
        f = tmp_path / "mod.py"
        f.write_text(source)
        return str(f)

    def test_empty_scope_returns_empty(self):
        from core.premortem import _detect_complexity_risk
        assert _detect_complexity_risk([]) == []

    def test_non_py_files_ignored(self, tmp_path):
        from core.premortem import _detect_complexity_risk
        f = tmp_path / "config.yaml"
        f.write_text("key: value\n")
        assert _detect_complexity_risk([str(f)]) == []

    def test_simple_function_returns_empty(self, tmp_path):
        from core.premortem import _detect_complexity_risk
        path = self._make_simple_func(tmp_path)
        assert _detect_complexity_risk([path]) == []

    def test_complex_function_returns_r16(self, tmp_path):
        from core.premortem import _detect_complexity_risk
        path = self._make_complex_func(tmp_path, complexity=12)
        result = _detect_complexity_risk([path])
        assert len(result) == 1
        assert result[0].id == "R16"
        assert result[0].category == "complexity"

    def test_exactly_threshold_returns_empty(self, tmp_path):
        """복잡도 == 10은 임계값 초과 아님 → 결과 없음."""
        from core.premortem import _detect_complexity_risk, _COMPLEXITY_THRESHOLD
        # 복잡도 10 = 1 + 9 branches
        branches = _COMPLEXITY_THRESHOLD - 1
        body = "\n".join(
            f"    if x{i} > 0:\n        x{i} = 1"
            for i in range(branches)
        )
        source = f"def borderline(**kwargs):\n"
        for i in range(branches):
            source += f"    x{i} = {i}\n"
        source += body + "\n    return 0\n"
        f = tmp_path / "mod.py"
        f.write_text(source)
        assert _detect_complexity_risk([str(f)]) == []

    def test_one_over_threshold_returns_r16(self, tmp_path):
        """복잡도 11 (> 10) → R16."""
        from core.premortem import _detect_complexity_risk, _COMPLEXITY_THRESHOLD
        path = self._make_complex_func(tmp_path, complexity=_COMPLEXITY_THRESHOLD + 1)
        result = _detect_complexity_risk([path])
        assert len(result) == 1
        assert result[0].id == "R16"

    def test_missing_scope_file_skipped(self):
        from core.premortem import _detect_complexity_risk
        assert _detect_complexity_risk(["__nonexistent__.py"]) == []

    def test_syntax_error_file_skipped(self, tmp_path):
        from core.premortem import _detect_complexity_risk
        f = tmp_path / "broken.py"
        f.write_text("def bad(:\n    pass\n")
        assert _detect_complexity_risk([str(f)]) == []

    def test_description_format(self, tmp_path):
        """description이 정해진 접두사/접미사 형식을 따른다."""
        from core.premortem import _detect_complexity_risk
        path = self._make_complex_func(tmp_path, name="my_fn", complexity=12)
        result = _detect_complexity_risk([path])
        assert result
        desc = result[0].description
        assert desc.startswith("Complex function(s) in scope: ")
        assert desc.endswith(". Consider refactoring before extending.")
        assert "`my_fn`" in desc
        assert "complexity" in desc

    def test_run_premortem_fires_r16_for_complex_function(self, tmp_path):
        from core.premortem import _COMPLEXITY_THRESHOLD
        path = self._make_complex_func(tmp_path, complexity=_COMPLEXITY_THRESHOLD + 2)
        spec = _spec(intent="Add feature", scope=[path])
        result = run_premortem(spec)
        ids = [r.id for r in result.risks]
        assert "R16" in ids

    def test_run_premortem_no_r16_for_simple_function(self, tmp_path):
        path = self._make_simple_func(tmp_path)
        spec = _spec(intent="Add feature", scope=[path])
        result = run_premortem(spec)
        ids = [r.id for r in result.risks]
        assert "R16" not in ids

    def test_assumption_start_at_r18_when_r16_fires(self, tmp_path):
        """R16 complexity + R18 assumption 공존 시나리오 — ID 충돌 없음.

        The complex fixture uses flat (non-nested) if statements, so R17
        (nesting_depth) does not fire; the assumption lands at R18.
        """
        path = self._make_complex_func(tmp_path, complexity=12)
        assumptions = [{"statement": "API stable", "confidence": "low"}]
        spec = _spec(intent="Add feature", scope=[path], assumptions=assumptions)
        result = run_premortem(spec)
        ids = [r.id for r in result.risks]
        assert "R16" in ids
        assert "R17" not in ids  # flat ifs are depth 1, not deeply nested
        assert "R18" in ids
        assert len(ids) == len(set(ids)), f"Duplicate IDs: {ids}"

    def test_no_id_collision_r16_with_all_detectors(self, tmp_path):
        path = self._make_complex_func(tmp_path, complexity=12)
        spec = _spec(
            intent="Add feature",
            scope=[path, "__nonexistent__.py"],
            assumptions=[{"statement": f"A{i}", "confidence": "low"} for i in range(3)],
            gaps=["some gap"],
        )
        result = run_premortem(spec)
        ids = [r.id for r in result.risks]
        assert "R16" in ids
        assert len(ids) == len(set(ids)), f"Duplicate IDs: {ids}"

    def test_nested_function_inner_branches_not_counted_in_outer(self, tmp_path):
        """Outer function complexity must NOT include branches from nested functions.

        Regression guard for the ast.walk() double-count bug: ast.walk flattens
        the entire subtree, so a plain 'continue' on the nested FunctionDef node
        skips that node but still yields all of its descendants (if/for/while),
        causing them to be counted in the outer function's complexity.

        The fix uses an explicit DFS stack that prunes nested FunctionDef
        subtrees entirely — children of a nested function are never enqueued.

        def outer():           # complexity 1
            if a: pass         # +1 → 2 (outer branch)
            if b: pass         # +1 → 3 (outer branch)
            def inner():       # separate function — NOT counted in outer
                if x: pass    # inner branch (must NOT appear in outer's count)
                if y: pass    # inner branch (must NOT appear in outer's count)

        Expected: outer complexity = 3, inner complexity = 10 (both within threshold>10).
        With the bug: outer complexity = 12 (inner's 9 branches wrongly included) → R16 fires.
        """
        from core.premortem import _detect_complexity_risk, _COMPLEXITY_THRESHOLD

        # outer has 2 own branches; inner has THRESHOLD-1 (9) branches so inner's
        # own complexity is exactly 10 (does NOT exceed threshold, which is >10).
        # But if the bug double-counts inner's branches into outer, outer becomes
        # 1+2+9 = 12 > 10 and wrongly fires R16 — so this fixture actively catches
        # the regression rather than passing regardless of the bug.
        inner_branches = "\n".join(
            f"        if y{i}: pass" for i in range(_COMPLEXITY_THRESHOLD - 1)
        )
        source = (
            "def outer():\n"
            "    if a: pass\n"
            "    if b: pass\n"
            "    def inner():\n"
            f"{inner_branches}\n"
            "        return 1\n"
            "    return 0\n"
        )
        f = tmp_path / "nested.py"
        f.write_text(source, encoding="utf-8")

        # Fixed: outer=3, inner=10 — neither exceeds threshold(>10) → no R16.
        # Buggy: inner's 9 branches counted in outer → outer=12 → R16 fires → non-empty.
        assert _detect_complexity_risk([str(f)]) == [], (
            "outer(2 own branches) must NOT include inner's 9 branches; "
            "if R16 fires here, inner's branches are being double-counted in outer"
        )

    def test_nested_function_outer_independently_exceeds_threshold(self, tmp_path):
        """Outer function that genuinely exceeds threshold must still fire R16.

        Ensures the pruning fix doesn't suppress legitimate outer findings.
        """
        from core.premortem import _detect_complexity_risk, _COMPLEXITY_THRESHOLD

        # outer: 1 + 11 branches = 12 → exceeds threshold(10) → R16
        # inner: 1 branch = 2 → does not exceed
        outer_branches = "\n".join(
            f"    if x{i} > 0: pass" for i in range(_COMPLEXITY_THRESHOLD + 1)
        )
        source = (
            f"def outer():\n"
            f"{outer_branches}\n"
            f"    def inner():\n"
            f"        if z: pass\n"
            f"        return 1\n"
            f"    return 0\n"
        )
        f = tmp_path / "nested_exceeds.py"
        f.write_text(source, encoding="utf-8")

        result = _detect_complexity_risk([str(f)])
        # outer must fire R16; inner must not
        assert len(result) == 1, (
            f"Expected exactly 1 R16 finding (outer), got {len(result)}"
        )
        assert result[0].id == "R16"
        assert "outer" in result[0].description

    def test_nested_function_inner_independently_exceeds_threshold(self, tmp_path):
        """Inner function that genuinely exceeds threshold is counted as its own entry.

        ast.walk(tree) visits inner as a separate FunctionDef node, so it gets
        its own complexity count.  This test confirms that behaviour is preserved.
        """
        from core.premortem import _detect_complexity_risk, _COMPLEXITY_THRESHOLD

        # outer: 1 branch = 2 → does not exceed
        # inner: 1 + 11 branches = 12 → exceeds threshold(10) → R16
        inner_branches = "\n".join(
            f"        if x{i} > 0: pass" for i in range(_COMPLEXITY_THRESHOLD + 1)
        )
        source = (
            f"def outer():\n"
            f"    if a: pass\n"
            f"    def inner():\n"
            f"{inner_branches}\n"
            f"        return 1\n"
            f"    return 0\n"
        )
        f = tmp_path / "nested_inner_exceeds.py"
        f.write_text(source, encoding="utf-8")

        result = _detect_complexity_risk([str(f)])
        # inner must fire R16; outer must not (outer has only 1 branch)
        assert len(result) == 1, (
            f"Expected exactly 1 R16 finding (inner), got {len(result)}"
        )
        assert result[0].id == "R16"
        assert "inner" in result[0].description


# ---------------------------------------------------------------------------
# TestNestingDepthRisk
# ---------------------------------------------------------------------------

class TestNestingDepthRisk:
    """Tests for _detect_nesting_depth_risk (R17)."""

    def _make_nested_func(self, tmp_path, name: str = "nested_fn", depth: int = 5) -> str:
        """Build a function whose deepest control-flow nesting equals *depth*."""
        lines = [f"def {name}():"]
        for level in range(depth):
            lines.append("    " * (level + 1) + f"if x{level}:")
        lines.append("    " * (depth + 1) + "pass")
        f = tmp_path / "mod.py"
        f.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return str(f)

    def test_empty_scope_returns_empty(self):
        from core.premortem import _detect_nesting_depth_risk
        assert _detect_nesting_depth_risk([]) == []

    def test_non_py_file_skipped(self, tmp_path):
        from core.premortem import _detect_nesting_depth_risk
        f = tmp_path / "notes.txt"
        f.write_text("if a:\n  if b:\n    if c:\n      pass\n")
        assert _detect_nesting_depth_risk([str(f)]) == []

    def test_flat_function_returns_empty(self, tmp_path):
        """Sequential (non-nested) if statements stay at depth 1 → no R17."""
        from core.premortem import _detect_nesting_depth_risk
        source = "def flat():\n" + "".join(
            f"    if x{i}: pass\n" for i in range(8)
        )
        f = tmp_path / "mod.py"
        f.write_text(source, encoding="utf-8")
        assert _detect_nesting_depth_risk([str(f)]) == []

    def test_deeply_nested_fires_r17(self, tmp_path):
        from core.premortem import _detect_nesting_depth_risk
        path = self._make_nested_func(tmp_path, depth=5)
        result = _detect_nesting_depth_risk([path])
        assert len(result) == 1
        assert result[0].id == "R17"
        assert result[0].category == "nesting_depth"

    def test_depth_at_threshold_returns_empty(self, tmp_path):
        """Depth exactly at the threshold does not fire (strictly greater than)."""
        from core.premortem import _detect_nesting_depth_risk, _NESTING_DEPTH_THRESHOLD
        path = self._make_nested_func(tmp_path, depth=_NESTING_DEPTH_THRESHOLD)
        assert _detect_nesting_depth_risk([path]) == []

    def test_depth_above_threshold_fires(self, tmp_path):
        from core.premortem import _detect_nesting_depth_risk, _NESTING_DEPTH_THRESHOLD
        path = self._make_nested_func(tmp_path, depth=_NESTING_DEPTH_THRESHOLD + 1)
        result = _detect_nesting_depth_risk([path])
        assert len(result) == 1
        assert result[0].id == "R17"

    def test_missing_file_returns_empty(self):
        from core.premortem import _detect_nesting_depth_risk
        assert _detect_nesting_depth_risk(["__nonexistent__.py"]) == []

    def test_syntax_error_skipped(self, tmp_path):
        from core.premortem import _detect_nesting_depth_risk
        f = tmp_path / "broken.py"
        f.write_text("def (:\n", encoding="utf-8")
        assert _detect_nesting_depth_risk([str(f)]) == []

    def test_description_and_verification_mention_function(self, tmp_path):
        from core.premortem import _detect_nesting_depth_risk
        path = self._make_nested_func(tmp_path, name="deep_fn", depth=6)
        result = _detect_nesting_depth_risk([path])
        assert "deep_fn" in result[0].description
        assert "nested" in result[0].description.lower()
        assert any("deep_fn" in v.command for v in result[0].verification)

    def test_nested_function_inner_depth_not_counted_in_outer(self, tmp_path):
        """A deeply nested inner def must not inflate the outer function's depth.

        The outer body only contains the inner def at depth 0; the inner def's
        own deep nesting is measured separately when ast.walk visits it.
        """
        from core.premortem import _detect_nesting_depth_risk, _NESTING_DEPTH_THRESHOLD
        inner_lines = []
        for level in range(_NESTING_DEPTH_THRESHOLD + 2):
            inner_lines.append("        " + "    " * level + f"if y{level}:")
        inner_lines.append("        " + "    " * (_NESTING_DEPTH_THRESHOLD + 2) + "pass")
        source = (
            "def outer():\n"
            "    def inner():\n"
            + "\n".join(inner_lines)
            + "\n        return 1\n"
            "    return 0\n"
        )
        f = tmp_path / "nested.py"
        f.write_text(source, encoding="utf-8")
        result = _detect_nesting_depth_risk([str(f)])
        # Only inner is deeply nested; outer (just holds a def) must not fire.
        assert len(result) == 1, f"Expected only inner to fire, got {len(result)}"
        assert "inner" in result[0].description
        assert "outer" not in result[0].description

    def test_elif_chain_counts_toward_depth(self, tmp_path):
        """Documented behaviour: a long elif chain is parsed as nested If nodes,
        so it accumulates depth and can fire R17 even though it reads as flat.

        This locks the intentional convention (see _max_block_depth docstring) so
        a future refactor that special-cases orelse is a deliberate change, not a
        silent regression.
        """
        from core.premortem import _detect_nesting_depth_risk, _NESTING_DEPTH_THRESHOLD
        branches = _NESTING_DEPTH_THRESHOLD + 2  # exceed threshold via elif chain
        lines = ["def dispatch(x):", "    if x == 0: pass"]
        lines += [f"    elif x == {i}: pass" for i in range(1, branches)]
        f = tmp_path / "mod.py"
        f.write_text("\n".join(lines) + "\n", encoding="utf-8")
        result = _detect_nesting_depth_risk([str(f)])
        assert len(result) == 1
        assert result[0].id == "R17"

    def test_run_premortem_fires_r17_for_deeply_nested(self, tmp_path):
        path = self._make_nested_func(tmp_path, depth=6)
        spec = _spec(intent="Add feature", scope=[path])
        result = run_premortem(spec)
        ids = [r.id for r in result.risks]
        assert "R17" in ids

    def test_run_premortem_no_r17_for_flat_function(self, tmp_path):
        source = "def flat():\n" + "".join(f"    if x{i}: pass\n" for i in range(8))
        f = tmp_path / "mod.py"
        f.write_text(source, encoding="utf-8")
        spec = _spec(intent="Add feature", scope=[str(f)])
        result = run_premortem(spec)
        ids = [r.id for r in result.risks]
        assert "R17" not in ids

    def test_no_id_collision_r17_with_assumptions_and_gaps(self, tmp_path):
        path = self._make_nested_func(tmp_path, depth=6)
        spec = _spec(
            intent="Add feature",
            scope=[path],
            assumptions=[{"statement": f"A{i}", "confidence": "low"} for i in range(3)],
            gaps=["some gap"],
        )
        result = run_premortem(spec)
        ids = [r.id for r in result.risks]
        assert "R17" in ids
        assert len(ids) == len(set(ids)), f"Duplicate IDs: {ids}"
