"""tests/test_skill_quality_gate.py — SkillQualityGate shadow delta 게이트 INV-1~7.

설계: docs/2026-06-10-skill-evolution-fitness-gate-design.md §10
"""
from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest

from core.skill_quality_gate import SkillQualityGate


# ── 헬퍼 ──────────────────────────────────────────────────────────────────────

def _shadow(*, wins=0, losses=0, ties=0, total_cases=0, delta=0.0):
    from core.skill_eval_harness import ShadowEvalSummary
    return ShadowEvalSummary(
        total_cases=total_cases, wins=wins, losses=losses, ties=ties, delta=delta,
    )


def _report(*, pass_rate=1.0, total_contract_cases=5, shadow=None):
    from core.skill_eval_harness import ShadowEvalSummary
    shadow = shadow or ShadowEvalSummary()
    contract = MagicMock()
    contract.total_cases = total_contract_cases
    contract.pass_rate = pass_rate
    contract.details = []
    r = MagicMock()
    r.contract_eval = contract
    r.shadow_eval = shadow
    r.static_gate = {"ok": True}
    r.recommended_stage = "active"
    r.report_path = ""
    return r


def _make_gate(report):
    """harness mock이 report를 반환하는 SkillQualityGate."""
    mock_harness = MagicMock()
    mock_harness.evaluate.return_value = report
    with patch("core.skill_eval_harness.SkillEvalHarness", return_value=mock_harness):
        gate = SkillQualityGate(registry=MagicMock())
    return gate


def _skill_dir(tmp_path, name="skill"):
    d = tmp_path / name
    d.mkdir()
    (d / "skill.py").write_text("def run(inputs): return inputs")
    return d


# ── INV-1~7 ───────────────────────────────────────────────────────────────────

def test_inv1_delta_positive_passes(tmp_path):
    """INV-1: baseline 有 + shadow ≥ MIN + delta>0 → PASS."""
    skill_dir = _skill_dir(tmp_path)
    report = _report(
        shadow=_shadow(total_cases=SkillQualityGate.MIN_SHADOW_CASES, wins=2, losses=1, delta=0.33),
    )
    gate = _make_gate(report)
    result = gate.validate(str(skill_dir))
    assert result.passed is True


def test_inv2_delta_negative_rejected(tmp_path):
    """INV-2: baseline 有 + shadow ≥ MIN + delta<0 → REJECTED."""
    skill_dir = _skill_dir(tmp_path)
    report = _report(
        shadow=_shadow(total_cases=SkillQualityGate.MIN_SHADOW_CASES, wins=1, losses=2, delta=-0.33),
    )
    gate = _make_gate(report)
    result = gate.validate(str(skill_dir))
    assert result.passed is False
    assert any("shadow regression" in r for r in result.failure_reasons)


def test_inv2b_delta_zero_rejected(tmp_path):
    """INV-2b: delta==0 → REJECTED (무변화 비채택 — selection 압력)."""
    skill_dir = _skill_dir(tmp_path)
    report = _report(
        shadow=_shadow(total_cases=SkillQualityGate.MIN_SHADOW_CASES, wins=1, losses=1, delta=0.0),
    )
    gate = _make_gate(report)
    result = gate.validate(str(skill_dir))
    assert result.passed is False


def test_inv3_no_baseline_passes_contract_only(tmp_path):
    """INV-3: baseline 無(total_cases=0) → contract만 판단, 하위호환 PASS."""
    skill_dir = _skill_dir(tmp_path)
    report = _report(shadow=_shadow(total_cases=0))
    gate = _make_gate(report)
    result = gate.validate(str(skill_dir))
    assert result.passed is True  # contract pass_rate=1.0


def test_inv4_small_sample_not_blocked(tmp_path):
    """INV-4: total_cases < MIN → delta 무관 차단 안 함 (소표본 무차단)."""
    skill_dir = _skill_dir(tmp_path)
    small = SkillQualityGate.MIN_SHADOW_CASES - 1
    report = _report(
        shadow=_shadow(total_cases=small, wins=0, losses=small, delta=-1.0),
    )
    gate = _make_gate(report)
    result = gate.validate(str(skill_dir))
    assert result.passed is True  # 소표본이라 delta 게이트 미적용


def test_inv5_quality_delta_filled(tmp_path):
    """INV-5: GateResult.quality_delta == report.shadow_eval.delta."""
    skill_dir = _skill_dir(tmp_path)
    expected_delta = 0.67
    report = _report(
        shadow=_shadow(total_cases=SkillQualityGate.MIN_SHADOW_CASES, wins=2, delta=expected_delta),
    )
    gate = _make_gate(report)
    result = gate.validate(str(skill_dir))
    assert result.quality_delta == expected_delta


def test_inv5b_quality_delta_none_when_no_baseline(tmp_path):
    """INV-5b: total_cases=0 → quality_delta=None."""
    skill_dir = _skill_dir(tmp_path)
    report = _report(shadow=_shadow(total_cases=0))
    gate = _make_gate(report)
    result = gate.validate(str(skill_dir))
    assert result.quality_delta is None


def test_inv6_baseline_dir_normalized_to_file_path(tmp_path):
    """INV-6: baseline 디렉터리 → skill.py 파일 경로로 정규화 후 harness 전달.

    경로 정규화 없으면 importlib.spec_from_file_location(디렉터리)=None
    → baseline_callable=None → total_cases=0 → delta 게이트 무력화.
    """
    baseline_dir = _skill_dir(tmp_path, "baseline")
    candidate_dir = _skill_dir(tmp_path, "candidate")

    captured: dict = {}

    def capture_evaluate(skill_py, *, baseline_skill_path=None, **kwargs):
        captured["baseline"] = baseline_skill_path
        return _report(shadow=_shadow(total_cases=3, wins=2, delta=0.33))

    mock_harness = MagicMock()
    mock_harness.evaluate.side_effect = capture_evaluate
    with patch("core.skill_eval_harness.SkillEvalHarness", return_value=mock_harness):
        gate = SkillQualityGate(registry=MagicMock())

    gate.validate(str(candidate_dir), baseline_skill_path=str(baseline_dir))

    # 디렉터리가 아닌 파일 경로로 정규화됐는지 검증
    assert captured.get("baseline") is not None, "baseline이 harness에 전달되지 않음"
    assert captured["baseline"].endswith("skill.py"), (
        f"baseline이 파일 경로여야 하는데 디렉터리: {captured['baseline']}"
    )
    assert os.path.isfile(captured["baseline"]), "정규화된 경로가 실제 파일이어야 함"


def test_inv7_knowledge_skill_passes_without_harness(tmp_path):
    """INV-7: knowledge 스킬(skill.py 없음) → PASS, harness 호출 없음."""
    skill_dir = tmp_path / "knowledge_skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text("# Knowledge Skill")

    mock_harness = MagicMock()
    with patch("core.skill_eval_harness.SkillEvalHarness", return_value=mock_harness):
        gate = SkillQualityGate(registry=MagicMock())

    result = gate.validate(str(skill_dir), auto_register=False)
    assert result.passed is True
    mock_harness.evaluate.assert_not_called()
