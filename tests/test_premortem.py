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
    _detect_gap_risks,
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
) -> CompiledSpec:
    return CompiledSpec(
        intent=intent,
        scope=scope or [],
        risk_hints=risk_hints or [],
        constraints=constraints or [],
        approval_policy=approval_policy,
        assumptions=assumptions or [],
        gaps=gaps or [],
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
