"""tests/test_escalation_evaluator.py — §9.1 + §9.2 케이스."""
from __future__ import annotations

import pytest

from core.escalation_evaluator import (
    EscalationDecision,
    RunDecision,
    _is_phase_active,
    compute_run_decision,
    evaluate,
    load_policy,
)
from core.warning_registry import WarningRecord


def _make_record(
    rule_id: str = "e2e_command_missing",
    phase: str = "build",
    count: int = 1,
    repeat_count: int = 1,
    false_positive_override: bool = False,
    activate_at: str = "P2",
) -> WarningRecord:
    return WarningRecord(
        rule_id=rule_id,
        severity="warn",
        project_slug="test-slug",
        ts="2026-05-10T00:00:00+09:00",
        record_id="test:x:abc12345",
        affected_phase=phase,
        count=count,
        repeat_count=repeat_count,
        false_positive_override=false_positive_override,
    )


_POLICY_P2 = {
    "version": 1,
    "rules": [
        {
            "rule_id": "e2e_command_missing",
            "activate_at": "P2",
            "block_when": {
                "affected_phase_in": ["build", "integrate", "code_review", "cross_validate", "verify"],
                "count_per_run_min": 1,
            },
            "exempt_when": {"affected_phase_in": ["scope"]},
        }
    ],
}

_POLICY_NEVER = {
    "version": 1,
    "rules": [{"rule_id": "never_rule", "activate_at": "never"}],
}

_POLICY_P4 = {
    "version": 1,
    "rules": [{"rule_id": "e2e_command_missing", "activate_at": "P4"}],
}


# §9.1 — evaluate (6 케이스)

def test_evaluate_rule_not_active_never(monkeypatch):
    """#1: rule activate_at=never → rule_not_active."""
    monkeypatch.setattr("core.escalation_evaluator.load_policy", lambda: _POLICY_NEVER)
    r = _make_record(rule_id="never_rule")
    d = evaluate(r)
    assert d.block is False
    assert d.reason == "rule_not_active"


def test_evaluate_inactive_phase_p4(monkeypatch):
    """#2: activate_at=P4, current=P2 → inactive_phase."""
    monkeypatch.setattr("core.escalation_evaluator.load_policy", lambda: _POLICY_P4)
    r = _make_record(rule_id="e2e_command_missing", phase="build", count=5)
    d = evaluate(r)
    assert d.block is False
    assert d.reason == "inactive_phase"


def test_evaluate_exempt_scope(monkeypatch):
    """#3: scope phase → exempt_phase:scope."""
    monkeypatch.setattr("core.escalation_evaluator.load_policy", lambda: _POLICY_P2)
    r = _make_record(phase="scope", count=3)
    d = evaluate(r)
    assert d.block is False
    assert "exempt_phase:scope" in d.reason


def test_evaluate_threshold_met_build(monkeypatch):
    """#4: build phase, count=1 → block=True, threshold_met."""
    monkeypatch.setattr("core.escalation_evaluator.load_policy", lambda: _POLICY_P2)
    r = _make_record(phase="build", count=1)
    d = evaluate(r)
    assert d.block is True
    assert d.reason == "threshold_met"


def test_evaluate_below_threshold_count_zero(monkeypatch):
    """#5: build phase, count=0 → block=False, below_threshold."""
    monkeypatch.setattr("core.escalation_evaluator.load_policy", lambda: _POLICY_P2)
    r = _make_record(phase="build", count=0)
    d = evaluate(r)
    assert d.block is False
    assert d.reason == "below_threshold"


def test_evaluate_false_positive_override(monkeypatch):
    """#6: false_positive_override=True → block=False, false_positive_override."""
    monkeypatch.setattr("core.escalation_evaluator.load_policy", lambda: _POLICY_P2)
    r = _make_record(phase="build", count=14, false_positive_override=True)
    d = evaluate(r)
    assert d.block is False
    assert d.reason == "false_positive_override"


# §9.2 — compute_run_decision (3 케이스)

def test_compute_run_decision_no_active_rules():
    """#7: 빈 summary → RunDecision(block=False, blocking_rules=[])."""
    summary = {"project_slug": "s", "last_updated": "t", "by_rule": {}}
    rd = compute_run_decision(summary, _POLICY_NEVER)
    assert rd.block is False
    assert rd.blocking_rules == []


def test_compute_run_decision_blocked(monkeypatch):
    """#8: build 14건 + scope 3건 → block=True, blocking_rules=['e2e_command_missing']."""
    monkeypatch.setattr("core.escalation_evaluator.load_policy", lambda: _POLICY_P2)
    summary = {
        "project_slug": "s",
        "last_updated": "t",
        "by_rule": {
            "e2e_command_missing": {
                "count": 17,
                "severity": "warn",
                "last_ts": "t",
                "first_ts": "t",
                "by_phase": {"build": 14, "scope": 3},
                "repeat_count_max": 1,
                "any_override": False,
            }
        },
    }
    rd = compute_run_decision(summary, _POLICY_P2)
    assert rd.block is True
    assert "e2e_command_missing" in rd.blocking_rules
    rule_reasons = [d.reason for d in rd.rule_decisions]
    assert "threshold_met" in rule_reasons
    assert any("exempt_phase:scope" in r for r in rule_reasons)


def test_compute_run_decision_override(monkeypatch):
    """#9: any_override=true → block=False."""
    monkeypatch.setattr("core.escalation_evaluator.load_policy", lambda: _POLICY_P2)
    summary = {
        "project_slug": "s",
        "last_updated": "t",
        "by_rule": {
            "e2e_command_missing": {
                "count": 14,
                "severity": "warn",
                "last_ts": "t",
                "first_ts": "t",
                "by_phase": {"build": 14},
                "repeat_count_max": 1,
                "any_override": True,
            }
        },
    }
    rd = compute_run_decision(summary, _POLICY_P2)
    assert rd.block is False


def test_is_phase_active():
    assert _is_phase_active("P2", "P2") is True
    assert _is_phase_active("P1", "P2") is True
    assert _is_phase_active("P3", "P2") is False
    assert _is_phase_active("never", "P2") is False
