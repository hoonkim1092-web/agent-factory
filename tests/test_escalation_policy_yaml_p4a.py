"""tests/test_escalation_policy_yaml_p4a.py — P4a §8.3 케이스 (2건)."""
from __future__ import annotations

import pytest

from core.escalation_evaluator import _PolicyRule, load_policy, read_current_phase


def test_yaml_v1_loads_current_phase_and_modes():
    """case 9: 실제 config/escalation_policy.yaml 로드 → v1 schema 검증."""
    policy = load_policy()
    assert policy.get("version") == 1
    assert read_current_phase(policy) == "P4"

    rules_by_id = {r["rule_id"]: r for r in policy.get("rules", []) if isinstance(r, dict)}

    owner = rules_by_id.get("owner_role_mismatch", {})
    assert owner.get("mode") == "observation"

    evidence = rules_by_id.get("evidence_quality_warn", {})
    assert evidence.get("mode") == "observation"

    e2e = rules_by_id.get("e2e_command_missing", {})
    assert e2e.get("mode") == "enforce"


def test_yaml_invalid_mode_raises():
    """case 10: mode='garbage' → _PolicyRule.from_dict 에서 ValueError."""
    with pytest.raises(ValueError, match="mode must be enforce"):
        _PolicyRule.from_dict(
            {
                "rule_id": "bad_rule",
                "activate_at": "P2",
                "mode": "garbage",
            }
        )
