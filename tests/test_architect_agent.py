"""Tests for core.architect_agent — Triad 合 Architect executor (§17 Step 19)."""
from __future__ import annotations

import copy
from pathlib import Path
from unittest.mock import patch

import pytest

from core.architect_agent import (
    _adr_matches,
    _extract_section,
    _load_accepted_adrs,
    _load_blueprint_text,
    _patch_final_plan,
    _resolve_finding,
    _section_for_step,
    architect_fn,
)
from core.triad import (
    TriadCriticFinding,
    TriadCriticReport,
    TriadDecision,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _finding(
    severity: str = "High",
    title: str = "Missing packaging entry",
    evidence_type: str = "packaging",
    evidence: str = "af.spec:105 hiddenimports — core.architect_agent absent",
    step: str = "S2-implement",
    required_fix: str = "Add core.architect_agent to af.spec hiddenimports",
) -> TriadCriticFinding:
    return TriadCriticFinding(
        severity=severity,
        title=title,
        evidence_type=evidence_type,
        evidence=evidence,
        affected_plan_step=step,
        why_it_breaks="Frozen build will fail to import module",
        required_fix=required_fix,
    )


def _plan() -> dict:
    return {
        "intent": "Implement architect_agent",
        "steps": [{"id": "S1", "action": "create", "target": "core/architect_agent.py"}],
        "unresolved_risks": [],
        "completion_criteria": [],
        "approval_points": [],
        "verification_requirements": [],
    }


SAMPLE_BLUEPRINT = """
# Master Blueprint

## §0 Quick Reference

| File | Description |
|------|-------------|
| core/triad.py | Triad orchestration |

## §3 Subsystems

### §3.1 Dogfood Pipeline

The dogfood pipeline runs in an isolated worktree.

## §17 Deep Interview Pipeline

Step 19 is the Architect agent.
"""

SAMPLE_ADR_ACCEPTED = """
# ADR: Agent Model Routing Defaults and Escalation

Status: Accepted
Date: 2026-05-15

## Context

Routing models to agent tasks...

## Decision

Use Sonnet for af-critic and af-cross-review.
"""

SAMPLE_ADR_DRAFT = """
# ADR: Experimental Feature

Status: Draft
Date: 2026-05-20

## Context

An experimental routing idea.
"""


# ---------------------------------------------------------------------------
# _load_blueprint_text
# ---------------------------------------------------------------------------

class TestLoadBlueprintText:
    def test_returns_empty_on_missing_file(self, tmp_path):
        result = _load_blueprint_text(tmp_path / "nonexistent.md")
        assert result == ""

    def test_reads_existing_file(self, tmp_path):
        p = tmp_path / "bp.md"
        p.write_text("# Blueprint\n§3 stuff", encoding="utf-8")
        result = _load_blueprint_text(p)
        assert "§3 stuff" in result


# ---------------------------------------------------------------------------
# _extract_section
# ---------------------------------------------------------------------------

class TestExtractSection:
    def test_extracts_known_section(self):
        text = SAMPLE_BLUEPRINT
        result = _extract_section(text, "§3")
        assert "§3" in result
        assert "Subsystems" in result

    def test_returns_empty_for_unknown_section(self):
        result = _extract_section(SAMPLE_BLUEPRINT, "§99")
        assert result == ""

    def test_extracts_subsection(self):
        result = _extract_section(SAMPLE_BLUEPRINT, "§3.1")
        assert "Dogfood" in result

    def test_does_not_prefix_match_subsection(self):
        # §3 must NOT match §3.1 — prefix false match regression (af-cross-review BLOCK fix)
        bp = "## §3 Subsystems\n\nTop level content.\n\n### §3.1 Dogfood\n\nSub content.\n"
        result_3 = _extract_section(bp, "§3")
        result_31 = _extract_section(bp, "§3.1")
        assert "Top level content" in result_3
        assert "Sub content" in result_31
        # §3 result must NOT bleed into §3.1 heading unexpectedly claim §3.1 is §3
        assert "§3.1" not in result_3.split("§3 Subsystems", 1)[0]

    def test_section_absent_returns_empty_not_subsection(self):
        # Blueprint only has §3.1; searching §3 should return empty (no heading matches)
        bp = "### §3.1 Dogfood Pipeline\n\nContent only in subsection.\n"
        result = _extract_section(bp, "§3")
        assert result == ""


# ---------------------------------------------------------------------------
# _section_for_step
# ---------------------------------------------------------------------------

class TestSectionForStep:
    def test_finds_section_by_explicit_ref(self):
        ref, text = _section_for_step("§3.1 worktree isolation", SAMPLE_BLUEPRINT)
        assert ref == "§3.1"
        assert "Dogfood" in text

    def test_finds_section_by_keyword(self):
        ref, text = _section_for_step("dogfood pipeline workspace", SAMPLE_BLUEPRINT)
        # Should find §3 or §3.1 via keyword match
        assert ref != "" or text != ""  # some match found

    def test_returns_empty_for_unrelated_step(self):
        ref, text = _section_for_step("completely unrelated xyz987", SAMPLE_BLUEPRINT)
        assert ref == "" and text == ""


# ---------------------------------------------------------------------------
# _load_accepted_adrs
# ---------------------------------------------------------------------------

class TestLoadAcceptedAdrs:
    def test_loads_accepted_only(self, tmp_path):
        (tmp_path / "ADR-20260515-114000-model-routing.md").write_text(
            SAMPLE_ADR_ACCEPTED, encoding="utf-8"
        )
        (tmp_path / "ADR-20260520-000000-experimental.md").write_text(
            SAMPLE_ADR_DRAFT, encoding="utf-8"
        )
        results = _load_accepted_adrs(tmp_path)
        assert len(results) == 1
        assert "Model Routing" in results[0]["title"]

    def test_returns_empty_when_dir_missing(self, tmp_path):
        result = _load_accepted_adrs(tmp_path / "nonexistent")
        assert result == []

    def test_skips_non_adr_files(self, tmp_path):
        (tmp_path / "README.md").write_text("Status: Accepted\n", encoding="utf-8")
        (tmp_path / "ADR-20260515-000000-valid.md").write_text(
            SAMPLE_ADR_ACCEPTED, encoding="utf-8"
        )
        results = _load_accepted_adrs(tmp_path)
        assert len(results) == 1


# ---------------------------------------------------------------------------
# _adr_matches
# ---------------------------------------------------------------------------

class TestAdrMatches:
    def _adr(self) -> dict:
        return {
            "filename": "ADR-20260515-114000-model-routing.md",
            "title": "Agent Model Routing",
            "body": SAMPLE_ADR_ACCEPTED,
        }

    def test_matches_when_keywords_overlap(self):
        f = _finding(
            title="Agent model routing escalation missing",
            evidence="af-critic escalation to Sonnet not implemented",
        )
        assert _adr_matches(self._adr(), f) is True

    def test_no_match_for_unrelated_finding(self):
        f = _finding(
            title="Blueprint sync hook broken",
            evidence="pre-commit hook fails on packaging step",
        )
        assert _adr_matches(self._adr(), f) is False


# ---------------------------------------------------------------------------
# _resolve_finding
# ---------------------------------------------------------------------------

class TestResolveFinding:
    def test_reject_when_blueprint_evidence_with_matching_section(self):
        f = _finding(
            evidence_type="blueprint",
            step="§3.1 worktree isolation",
            evidence="§3.1 missing worktree details",
        )
        decision = _resolve_finding(f, SAMPLE_BLUEPRINT, [])
        assert decision.verdict == "REJECT"
        assert decision.blueprint_section != ""

    def test_reject_when_accepted_adr_matches(self, tmp_path):
        adr = {
            "filename": "ADR-routing.md",
            "title": "Agent Model Routing",
            "body": SAMPLE_ADR_ACCEPTED,
        }
        f = _finding(
            title="Agent model routing escalation missing",
            evidence="Sonnet not configured for agent routing tasks",
            evidence_type="file_line",
        )
        decision = _resolve_finding(f, "", [adr])
        assert decision.verdict == "REJECT"
        assert decision.adr_ref == "ADR-routing.md"

    def test_accept_when_no_context_matches(self):
        f = _finding(
            title="core.architect_agent missing from af.spec",
            evidence="af.spec:105 hiddenimports absent",
            evidence_type="packaging",
            step="S2-packaging",
        )
        decision = _resolve_finding(f, "", [])
        assert decision.verdict == "ACCEPT"
        assert "required_fix" in decision.reason.lower() or "valid" in decision.reason.lower()

    def test_accept_preserves_severity(self):
        f = _finding(severity="Critical")
        decision = _resolve_finding(f, "", [])
        assert decision.finding_title == f.title
        assert "Critical" in decision.reason


# ---------------------------------------------------------------------------
# _patch_final_plan
# ---------------------------------------------------------------------------

class TestPatchFinalPlan:
    def test_accept_appends_to_unresolved_risks(self):
        f = _finding(title="Missing entry", required_fix="Add hiddenimport")
        d = TriadDecision(
            finding_title="Missing entry",
            verdict="ACCEPT",
            reason="Valid finding",
        )
        result = _patch_final_plan(_plan(), [f], [d])
        assert any("ACCEPT" in r for r in result["unresolved_risks"])

    def test_hold_appends_human_review_marker(self):
        f = _finding(title="Uncertain risk")
        d = TriadDecision(
            finding_title="Uncertain risk",
            verdict="HOLD",
            reason="Cannot determine from context",
        )
        result = _patch_final_plan(_plan(), [f], [d])
        assert any("HOLD" in r and "human review" in r for r in result["unresolved_risks"])

    def test_reject_does_not_add_to_risks(self):
        f = _finding(title="Blueprint concern")
        d = TriadDecision(
            finding_title="Blueprint concern",
            verdict="REJECT",
            reason="Blueprint already handles it",
            blueprint_section="§3",
        )
        result = _patch_final_plan(_plan(), [f], [d])
        assert result["unresolved_risks"] == []

    def test_does_not_duplicate_risk_entries(self):
        f = _finding(title="Dup risk")
        d = TriadDecision(finding_title="Dup risk", verdict="ACCEPT", reason="ok")
        plan_with_existing = _plan()
        # Simulate first pass already adding the entry
        first = _patch_final_plan(plan_with_existing, [f], [d])
        second = _patch_final_plan(first, [f], [d])
        accept_count = sum(1 for r in second["unresolved_risks"] if "Dup risk" in r)
        assert accept_count == 1

    def test_original_plan_not_mutated(self):
        f = _finding()
        d = TriadDecision(finding_title=f.title, verdict="ACCEPT", reason="ok")
        original = _plan()
        _patch_final_plan(original, [f], [d])
        assert original["unresolved_risks"] == []


# ---------------------------------------------------------------------------
# architect_fn — integration
# ---------------------------------------------------------------------------

class TestArchitectFn:
    def test_returns_tuple_of_plan_and_decisions(self, tmp_path):
        bp = tmp_path / "bp.md"
        bp.write_text(SAMPLE_BLUEPRINT, encoding="utf-8")

        report = TriadCriticReport(
            verdict="WARN",
            findings=[_finding()],
        )
        final_plan, decisions = architect_fn(
            _plan(), report, {}, _blueprint_path=bp, _adr_dir=tmp_path
        )
        assert isinstance(final_plan, dict)
        assert isinstance(decisions, list)
        assert len(decisions) == 1

    def test_empty_findings_returns_original_plan(self, tmp_path):
        report = TriadCriticReport(verdict="PASS", findings=[])
        final_plan, decisions = architect_fn(
            _plan(), report, {}, _blueprint_path=tmp_path / "none.md", _adr_dir=tmp_path
        )
        assert decisions == []
        assert final_plan["intent"] == "Implement architect_agent"

    def test_accept_finding_surfaces_in_unresolved_risks(self, tmp_path):
        report = TriadCriticReport(
            verdict="BLOCK",
            findings=[_finding(title="Packaging gap", evidence_type="packaging")],
        )
        final_plan, decisions = architect_fn(
            _plan(), report, {}, _blueprint_path=tmp_path / "none.md", _adr_dir=tmp_path
        )
        assert any("Packaging gap" in r for r in final_plan["unresolved_risks"])

    def test_blueprint_reject_does_not_pollute_risks(self, tmp_path):
        bp = tmp_path / "bp.md"
        bp.write_text(SAMPLE_BLUEPRINT, encoding="utf-8")
        report = TriadCriticReport(
            verdict="WARN",
            findings=[
                _finding(
                    evidence_type="blueprint",
                    step="§3.1 dogfood",
                    evidence="§3.1 something",
                )
            ],
        )
        final_plan, decisions = architect_fn(
            _plan(), report, {}, _blueprint_path=bp, _adr_dir=tmp_path
        )
        assert decisions[0].verdict == "REJECT"
        assert final_plan["unresolved_risks"] == []

    def test_accepted_adr_triggers_reject(self, tmp_path):
        (tmp_path / "ADR-20260515-114000-model-routing.md").write_text(
            SAMPLE_ADR_ACCEPTED, encoding="utf-8"
        )
        report = TriadCriticReport(
            verdict="WARN",
            findings=[
                _finding(
                    title="Agent model routing escalation unspecified",
                    evidence="Sonnet escalation for agent routing not in code",
                    evidence_type="file_line",
                    step="S3-routing",
                )
            ],
        )
        final_plan, decisions = architect_fn(
            _plan(), report, {}, _blueprint_path=tmp_path / "none.md", _adr_dir=tmp_path
        )
        assert decisions[0].verdict == "REJECT"
        assert "ADR" in decisions[0].reason

    def test_multiple_findings_all_decided(self, tmp_path):
        findings = [
            _finding(title=f"Issue {i}", evidence=f"evidence_{i}.py:10 line ref")
            for i in range(3)
        ]
        report = TriadCriticReport(verdict="WARN", findings=findings)
        _, decisions = architect_fn(
            _plan(), report, {}, _blueprint_path=tmp_path / "none.md", _adr_dir=tmp_path
        )
        assert len(decisions) == 3
        assert all(d.verdict in {"ACCEPT", "REJECT", "HOLD"} for d in decisions)

    def test_missing_blueprint_does_not_raise(self, tmp_path):
        report = TriadCriticReport(verdict="WARN", findings=[_finding()])
        # Should not raise even if blueprint file is absent
        final_plan, decisions = architect_fn(
            _plan(), report, {}, _blueprint_path=tmp_path / "missing.md", _adr_dir=tmp_path
        )
        assert len(decisions) == 1

    def test_context_workspace_passed_through(self, tmp_path):
        """architect_fn accepts and ignores context without error."""
        report = TriadCriticReport(verdict="PASS", findings=[])
        ctx = {"workspace": str(tmp_path), "spec": {}, "premortem": {}}
        final_plan, decisions = architect_fn(
            _plan(), report, ctx, _blueprint_path=tmp_path / "none.md", _adr_dir=tmp_path
        )
        assert isinstance(final_plan, dict)
