"""tests/test_escalation_evaluator_p4a.py — P4a §8.1 케이스 (7건)."""
from __future__ import annotations

from core.escalation_evaluator import (
    evaluate,
    read_current_phase,
)
from core.warning_registry import WarningRecord


def _make_record(
    rule_id: str = "owner_role_mismatch",
    phase: str = "build",
    count: int = 1,
    repeat_count: int = 1,
    false_positive_override: bool = False,
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


_POLICY_OBSERVATION = {
    "version": 1,
    "current_phase": "P4",
    "rules": [
        {
            "rule_id": "owner_role_mismatch",
            "activate_at": "P4",
            "mode": "observation",
            "block_when": {"repeat_count_min": 3},
        }
    ],
}

_POLICY_OFF = {
    "version": 1,
    "current_phase": "P4",
    "rules": [
        {
            "rule_id": "owner_role_mismatch",
            "activate_at": "P4",
            "mode": "off",
            "block_when": {"repeat_count_min": 3},
        }
    ],
}

_POLICY_ENFORCE_NO_MODE = {
    "version": 1,
    "current_phase": "P2",
    "rules": [
        {
            "rule_id": "e2e_command_missing",
            "activate_at": "P2",
            # mode 키 없음 → enforce default
            "block_when": {
                "affected_phase_in": ["build"],
                "count_per_run_min": 1,
            },
        }
    ],
}

_POLICY_V1_FULL = {
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


def test_evaluate_observation_below_threshold_returns_warn():
    """case 1: observation mode, repeat_count < min → warn/observation_below_threshold."""
    record = _make_record(repeat_count=1)
    d = evaluate(record, policy=_POLICY_OBSERVATION, current_phase="P4")
    assert d.block is False
    assert d.severity == "warn"
    assert d.reason == "observation_below_threshold"


def test_evaluate_observation_threshold_met_returns_block_candidate():
    """case 2: observation mode, repeat_count ≥ min → block_candidate/observation_threshold_met."""
    record = _make_record(repeat_count=5)
    d = evaluate(record, policy=_POLICY_OBSERVATION, current_phase="P4")
    assert d.block is False
    assert d.severity == "block_candidate"
    assert d.reason == "observation_threshold_met"


def test_evaluate_off_mode_skips_threshold():
    """case 3: off mode, repeat_count=999 → warn/mode_off (threshold 평가 없음)."""
    record = _make_record(repeat_count=999)
    d = evaluate(record, policy=_POLICY_OFF, current_phase="P4")
    assert d.block is False
    assert d.severity == "warn"
    assert d.reason == "mode_off"


def test_evaluate_enforce_mode_default_when_field_missing():
    """case 4: mode 키 없음 → enforce default → threshold 도달 시 block=True."""
    record = _make_record(rule_id="e2e_command_missing", phase="build", count=1)
    d = evaluate(record, policy=_POLICY_ENFORCE_NO_MODE, current_phase="P2")
    assert d.block is True
    assert d.severity == "block"
    assert d.reason == "threshold_met"


def test_read_current_phase_fallback_p2_when_missing_or_invalid():
    """case 5: current_phase 부재/invalid → "P2" fallback."""
    assert read_current_phase({}) == "P2"
    assert read_current_phase({"current_phase": "P9"}) == "P2"
    assert read_current_phase({"current_phase": "never"}) == "P2"
    assert read_current_phase({"current_phase": "P4"}) == "P4"


def test_observation_respects_false_positive_override():
    """case 6 (F5 회귀): override=True → mode 무관 warn/false_positive_override (override 우선)."""
    record = _make_record(repeat_count=999, false_positive_override=True)
    d = evaluate(record, policy=_POLICY_OBSERVATION, current_phase="P4")
    assert d.block is False
    assert d.severity == "warn"
    assert d.reason == "false_positive_override"


def test_e2e_command_missing_blocks_under_p4_current_phase():
    """case 7 (F7 회귀): P4 current_phase에서 e2e_command_missing(enforce) 여전히 BLOCK."""
    record = _make_record(rule_id="e2e_command_missing", phase="build", count=1)
    d = evaluate(record, policy=_POLICY_V1_FULL, current_phase="P4")
    assert d.block is True
    assert d.severity == "block"
    assert d.reason == "threshold_met"
