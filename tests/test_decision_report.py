"""tests/test_decision_report.py — §9.4 케이스 (3)."""
from __future__ import annotations

import json
import os
import tempfile

from core.escalation_evaluator import EscalationDecision, RunDecision
from core.escalation_decision_report import write_decision_report, write_error_decision


def _make_run_decision(block: bool = True, rule_id: str = "e2e_command_missing") -> RunDecision:
    d = EscalationDecision(
        block=block, severity="block" if block else "warn",
        reason="threshold_met" if block else "no_active_blocks_in_run",
        rule_id=rule_id, activate_at="P2",
    )
    return RunDecision(
        block=block,
        blocking_rules=[rule_id] if block else [],
        rule_decisions=[d],
        reason=f"blocked_by:{rule_id}" if block else "no_active_blocks_in_run",
        activate_phase="P2",
        summary_snapshot={"project_slug": "test-slug", "last_updated": "2026-05-10T00:00:00+09:00"},
    )


def test_write_decision_report_creates_files():
    """#11: write_decision_report → _decision.md + _decision.json 원자 작성."""
    with tempfile.TemporaryDirectory() as slug_dir:
        decision = _make_run_decision(block=True)
        write_decision_report(decision, slug_dir, summary_last_updated="2026-05-10T00:00:00+09:00")

        assert os.path.isfile(os.path.join(slug_dir, "_decision.json"))
        assert os.path.isfile(os.path.join(slug_dir, "_decision.md"))

        with open(os.path.join(slug_dir, "_decision.json"), encoding="utf-8") as fh:
            d = json.load(fh)
        assert d["block"] is True
        assert d["blocking_rules"] == ["e2e_command_missing"]


def test_write_decision_report_required_keys():
    """#12: _decision.json에 3 필수 키(decision_schema_version / generated_from_summary_last_updated / escalation_phase) 존재."""
    with tempfile.TemporaryDirectory() as slug_dir:
        decision = _make_run_decision(block=False)
        ts = "2026-05-10T01:00:00+09:00"
        write_decision_report(decision, slug_dir, summary_last_updated=ts)

        with open(os.path.join(slug_dir, "_decision.json"), encoding="utf-8") as fh:
            d = json.load(fh)
        assert d["decision_schema_version"] == 1
        assert d["generated_from_summary_last_updated"] == ts
        assert "escalation_phase" in d


def test_write_error_decision():
    """#13: write_error_decision → block=True, reason="evaluator_error"."""
    with tempfile.TemporaryDirectory() as slug_dir:
        write_error_decision(
            slug_dir,
            project_slug="test-slug",
            summary_last_updated="2026-05-10T00:00:00+09:00",
            error_repr="SomeError('oops')",
        )

        assert os.path.isfile(os.path.join(slug_dir, "_decision.json"))
        with open(os.path.join(slug_dir, "_decision.json"), encoding="utf-8") as fh:
            d = json.load(fh)
        assert d["block"] is True
        assert d["reason"] == "evaluator_error"
