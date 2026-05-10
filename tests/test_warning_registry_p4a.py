"""tests/test_warning_registry_p4a.py — P4a §8.2 케이스 (3건)."""
from __future__ import annotations

import json
from unittest.mock import patch

from core.warning_registry import WarningRegistry


_POLICY_P4 = {
    "version": 1,
    "current_phase": "P4",
    "rules": [
        {
            "rule_id": "e2e_command_missing",
            "activate_at": "P2",
            "mode": "enforce",
            "block_when": {
                "affected_phase_in": ["build", "integrate", "code_review", "cross_validate", "verify"],
                "count_per_run_min": 1,
            },
            "exempt_when": {"affected_phase_in": ["scope"]},
        },
        {
            "rule_id": "owner_role_mismatch",
            "activate_at": "P4",
            "mode": "observation",
            "block_when": {"repeat_count_min": 3},
        },
    ],
}

_POLICY_NO_PHASE = {
    "version": 1,
    "rules": [
        {
            "rule_id": "e2e_command_missing",
            "activate_at": "P2",
            "block_when": {"count_per_run_min": 999999},
        },
    ],
}


def test_summarize_writes_escalation_phase_from_yaml(tmp_path):
    """case 6: yaml current_phase=P4 → _summary.json + _decision.json 양쪽 escalation_phase=="P4"."""
    wr = WarningRegistry(workspace=str(tmp_path))
    # 레코드 없는 상태로 summarize (empty summary, no BLOCK)
    with patch("core.escalation_evaluator.load_policy", return_value=_POLICY_P4):
        summary = wr.summarize(project_slug="proj")

    assert summary["escalation_phase"] == "P4"

    slug_dir = tmp_path / "runtime" / "warnings" / "proj"
    with open(slug_dir / "_summary.json", encoding="utf-8") as fh:
        s = json.load(fh)
    assert s["escalation_phase"] == "P4"

    with open(slug_dir / "_decision.json", encoding="utf-8") as fh:
        d = json.load(fh)
    assert d["escalation_phase"] == "P4"


def test_summarize_falls_back_to_p2_when_yaml_missing_phase(tmp_path):
    """case 7: yaml current_phase 부재 → _summary.json + _decision.json 양쪽 "P2"."""
    wr = WarningRegistry(workspace=str(tmp_path))
    with patch("core.escalation_evaluator.load_policy", return_value=_POLICY_NO_PHASE):
        summary = wr.summarize(project_slug="proj")

    assert summary["escalation_phase"] == "P2"

    slug_dir = tmp_path / "runtime" / "warnings" / "proj"
    with open(slug_dir / "_summary.json", encoding="utf-8") as fh:
        s = json.load(fh)
    assert s["escalation_phase"] == "P2"

    with open(slug_dir / "_decision.json", encoding="utf-8") as fh:
        d = json.load(fh)
    assert d["escalation_phase"] == "P2"


def test_write_error_decision_uses_dynamic_phase(tmp_path):
    """case 8: yaml P4 로드 성공 + _build_summary 강제 예외 → _decision.json escalation_phase=="P4" (error path 동적화)."""
    wr = WarningRegistry(workspace=str(tmp_path))
    slug_dir = tmp_path / "runtime" / "warnings" / "proj"
    slug_dir.mkdir(parents=True, exist_ok=True)

    with patch("core.escalation_evaluator.load_policy", return_value=_POLICY_P4), \
         patch("core.warning_registry._build_summary", side_effect=RuntimeError("forced")):
        try:
            wr.summarize(project_slug="proj")
        except RuntimeError:
            pass

    decision_path = slug_dir / "_decision.json"
    assert decision_path.exists(), "_decision.json must be written even on _build_summary failure"
    with open(decision_path, encoding="utf-8") as fh:
        d = json.load(fh)
    assert d["escalation_phase"] == "P4"
    assert d["block"] is True
    assert d["reason"] == "evaluator_error"
