"""Tests for core.triad — 正反合 Triad orchestration (§17 Step 15)."""
from __future__ import annotations

import warnings
from unittest.mock import patch

import pytest

import core.triad as triad_mod
from core.triad import (
    VALID_EVIDENCE_TYPES,
    TriadBlockedError,
    TriadCriticFinding,
    TriadCriticReport,
    TriadDecision,
    TriadResult,
    _coerce_verdict,
    _validate_findings,
    run_triad,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _finding(
    severity: str = "High",
    title: str = "Missing test coverage",
    evidence_type: str = "test_gap",
    evidence: str = "tests/test_triad.py missing",
    step: str = "S1",
) -> TriadCriticFinding:
    return TriadCriticFinding(
        severity=severity,
        title=title,
        evidence_type=evidence_type,
        evidence=evidence,
        affected_plan_step=step,
        why_it_breaks="CI will fail without coverage",
        required_fix="Add tests/test_triad.py",
    )


def _critical() -> TriadCriticFinding:
    return _finding(
        severity="Critical",
        title="core.triad missing from af.spec",
        evidence_type="packaging",
        evidence="af.spec:33 hiddenimports — core.triad absent",
        step="S1",
    )


# ---------------------------------------------------------------------------
# TriadCriticFinding — serialisation
# ---------------------------------------------------------------------------

def test_finding_to_dict_keys():
    f = _finding()
    d = f.to_dict()
    assert set(d.keys()) == {
        "severity", "title", "evidence_type", "evidence",
        "affected_plan_step", "why_it_breaks", "required_fix",
    }


def test_finding_from_dict_roundtrip():
    f = _finding(severity="Critical", evidence_type="file_line")
    restored = TriadCriticFinding.from_dict(f.to_dict())
    assert restored.severity == "Critical"
    assert restored.evidence_type == "file_line"


# ---------------------------------------------------------------------------
# TriadCriticReport — serialisation + helpers
# ---------------------------------------------------------------------------

def test_report_has_critical_true():
    report = TriadCriticReport(verdict="BLOCK", findings=[_critical()])
    assert report.has_critical()


def test_report_has_critical_false():
    report = TriadCriticReport(verdict="WARN", findings=[_finding(severity="High")])
    assert not report.has_critical()


def test_report_critical_findings_filter():
    report = TriadCriticReport(
        verdict="BLOCK",
        findings=[_critical(), _finding(severity="High")],
    )
    assert len(report.critical_findings()) == 1
    assert report.critical_findings()[0].severity == "Critical"


def test_report_from_dict_roundtrip():
    report = TriadCriticReport(verdict="WARN", findings=[_finding()])
    restored = TriadCriticReport.from_dict(report.to_dict())
    assert restored.verdict == "WARN"
    assert len(restored.findings) == 1


# ---------------------------------------------------------------------------
# _validate_findings — evidence contract enforcement
# ---------------------------------------------------------------------------

def test_validate_drops_invalid_evidence_type():
    f = _finding(evidence_type="vague_feeling")
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        result = _validate_findings([f])
    assert len(result) == 0
    assert any("invalid evidence_type" in str(warning.message) for warning in w)


def test_validate_drops_empty_evidence():
    f = _finding(evidence="")
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        result = _validate_findings([f])
    assert len(result) == 0
    assert any("evidence is empty" in str(warning.message) for warning in w)


def test_validate_keeps_valid_finding():
    f = _finding(evidence_type="file_line", evidence="core/triad.py:42")
    result = _validate_findings([f])
    assert len(result) == 1


def test_validate_coerces_unknown_severity():
    f = _finding(evidence_type="git_diff", evidence="diff output", severity="Critical+")
    with warnings.catch_warnings(record=True):
        warnings.simplefilter("always")
        result = _validate_findings([f])
    assert result[0].severity == "Low"


def test_validate_all_evidence_types_accepted():
    for et in VALID_EVIDENCE_TYPES:
        f = _finding(evidence_type=et, evidence="some evidence")
        result = _validate_findings([f])
        assert len(result) == 1, f"evidence_type '{et}' should be valid"


# ---------------------------------------------------------------------------
# _coerce_verdict — Critical → BLOCK enforcement
# ---------------------------------------------------------------------------

def test_coerce_verdict_critical_forces_block():
    report = TriadCriticReport(verdict="PASS", findings=[_critical()])
    _coerce_verdict(report)
    assert report.verdict == "BLOCK"


def test_coerce_verdict_no_critical_unchanged():
    report = TriadCriticReport(verdict="PASS", findings=[_finding(severity="High")])
    _coerce_verdict(report)
    assert report.verdict == "PASS"


def test_coerce_verdict_unknown_becomes_warn():
    report = TriadCriticReport(verdict="MAYBE", findings=[])
    _coerce_verdict(report)
    assert report.verdict == "WARN"


# ---------------------------------------------------------------------------
# TriadDecision — serialisation
# ---------------------------------------------------------------------------

def test_decision_to_dict_roundtrip():
    d = TriadDecision(
        finding_title="Missing af.spec entry",
        verdict="REJECT",
        reason="core.triad added to af.spec:101",
        blueprint_section="§0",
        adr_ref="",
    )
    restored = TriadDecision.from_dict(d.to_dict())
    assert restored.verdict == "REJECT"
    assert restored.blueprint_section == "§0"


# ---------------------------------------------------------------------------
# run_triad — happy path (PASS stub)
# ---------------------------------------------------------------------------

def test_run_triad_pass_returns_result():
    plan = {"steps": [{"id": "S1", "description": "do thing", "commands": []}]}
    result = run_triad(plan, {})
    assert isinstance(result, TriadResult)
    assert result.approved
    assert result.final_plan == plan


def test_run_triad_pass_no_findings():
    plan = {"steps": []}
    result = run_triad(plan, {})
    assert result.critic_report.verdict == "PASS"
    assert result.critic_report.findings == []


# ---------------------------------------------------------------------------
# run_triad — injectable critic with findings
# ---------------------------------------------------------------------------

def _critic_with_high(plan_dict, context):
    return TriadCriticReport(
        verdict="WARN",
        findings=[_finding(severity="High")],
    )


def test_run_triad_high_finding_approved():
    plan = {"steps": []}
    result = run_triad(plan, {}, _critic_fn=_critic_with_high)
    assert result.approved  # High alone doesn't block


def _critic_with_critical(plan_dict, context):
    return TriadCriticReport(
        verdict="BLOCK",
        findings=[_critical()],
    )


def test_run_triad_critical_raises_blocked_error():
    plan = {"steps": []}
    with pytest.raises(TriadBlockedError, match="unresolved Critical"):
        run_triad(plan, {}, _critic_fn=_critic_with_critical)


def test_run_triad_critical_architect_rejects_approved():
    """When Architect REJECTs a Critical finding it is considered resolved."""
    def _architect(plan_dict, critic_report, context):
        decisions = [
            TriadDecision(
                finding_title=f.title,
                verdict="REJECT",
                reason="Architect resolved: added core.triad to af.spec",
                blueprint_section="§0",
            )
            for f in critic_report.findings
        ]
        return plan_dict, decisions

    plan = {"steps": []}
    result = run_triad(plan, {}, _critic_fn=_critic_with_critical, _architect_fn=_architect)
    assert result.approved


def test_run_triad_critical_architect_hold_still_blocked():
    """HOLD on a Critical finding does NOT count as resolved → still blocked."""
    def _architect(plan_dict, critic_report, context):
        decisions = [
            TriadDecision(finding_title=f.title, verdict="HOLD", reason="needs user input")
            for f in critic_report.findings
        ]
        return plan_dict, decisions

    plan = {"steps": []}
    with pytest.raises(TriadBlockedError):
        run_triad(plan, {}, _critic_fn=_critic_with_critical, _architect_fn=_architect)


def test_run_triad_critical_architect_accept_still_blocked():
    """ACCEPT on a Critical finding also does NOT count as resolved → still blocked.

    Only REJECT signals 'Architect has addressed and overridden this finding'.
    ACCEPT means Architect agrees with the Critic — the problem stands.
    """
    def _architect(plan_dict, critic_report, context):
        decisions = [
            TriadDecision(finding_title=f.title, verdict="ACCEPT", reason="critic is right")
            for f in critic_report.findings
        ]
        return plan_dict, decisions

    plan = {"steps": []}
    with pytest.raises(TriadBlockedError):
        run_triad(plan, {}, _critic_fn=_critic_with_critical, _architect_fn=_architect)


# ---------------------------------------------------------------------------
# run_triad — evidence validation inside run_triad
# ---------------------------------------------------------------------------

def test_run_triad_strips_evidence_free_findings():
    """Findings without evidence are stripped before Architect sees them."""
    def _bad_critic(plan_dict, context):
        return TriadCriticReport(
            verdict="BLOCK",
            findings=[
                TriadCriticFinding(
                    severity="Critical",
                    title="vague concern",
                    evidence_type="file_line",
                    evidence="",  # empty — invalid
                    affected_plan_step="S1",
                    why_it_breaks="...",
                    required_fix="...",
                )
            ],
        )

    plan = {"steps": []}
    with warnings.catch_warnings(record=True):
        warnings.simplefilter("always")
        # After stripping, no Critical remains → should not raise
        result = run_triad(plan, {}, _critic_fn=_bad_critic)
    assert result.approved


# ---------------------------------------------------------------------------
# run_triad — module-level injectable executor
# ---------------------------------------------------------------------------

def test_run_triad_uses_module_executor():
    custom_called = {"n": 0}

    def _custom(plan_dict, context):
        custom_called["n"] += 1
        return TriadCriticReport(verdict="PASS", findings=[])

    with patch.object(triad_mod, "_critic_executor", side_effect=_custom):
        run_triad({"steps": []}, {})

    assert custom_called["n"] == 1


# ---------------------------------------------------------------------------
# TriadResult — serialisation
# ---------------------------------------------------------------------------

def test_triad_result_to_dict_keys():
    plan = {"steps": []}
    result = run_triad(plan, {})
    d = result.to_dict()
    assert set(d.keys()) == {
        "initial_plan", "critic_report", "decisions",
        "final_plan", "approved", "block_reason",
    }
