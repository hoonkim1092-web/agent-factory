"""
tests/test_approval_gate_auto_approve.py
=========================================
ApprovalGate auto-approve 옵션 회귀 테스트.

검증:
  - default (auto=False, env 미설정): 기존 동작 유지 (사용자 수동 approve)
  - 명시 호출 (auto=True): 자동 통과 + approver "auto[:reason]"
  - 환경변수 (AF_AUTO_APPROVE=1): 자동 통과
  - 감사 추적 (review_notes에 auto-approve 흔적)
"""
from __future__ import annotations

import os

import pytest

from core.approval_gate import ApprovalGate


@pytest.fixture
def gate(tmp_path):
    """초기화된 ApprovalGate (execution_open: false)."""
    workspace = tmp_path
    slug = "test-work-item"
    g = ApprovalGate(str(workspace), slug)
    g.initialize(work_item_id="WI-001", run_id="run-test")
    return g


# ── default 동작 (기존 호환성 유지) ─────────────────────────────────────────


def test_default_approve_user_label(gate, monkeypatch):
    """default approve() — approver='user' (기존 호환)."""
    monkeypatch.delenv("AF_AUTO_APPROVE", raising=False)
    assert gate.approve(approver="user") is True
    parsed = gate._parse()
    assert "user" in str(parsed.get("approver", ""))


def test_default_no_auto_marker_in_review_notes(gate, monkeypatch):
    """default 호출 시 review_notes에 auto-approve 흔적 없음."""
    monkeypatch.delenv("AF_AUTO_APPROVE", raising=False)
    gate.approve(approver="user")
    parsed = gate._parse()
    notes = str(parsed.get("review_notes", ""))
    assert "[auto-approve]" not in notes


# ── auto=True 명시 호출 ──────────────────────────────────────────────────────


def test_explicit_auto_true_marks_approver_auto(gate, monkeypatch):
    """auto=True 호출 시 approver='auto' 라벨."""
    monkeypatch.delenv("AF_AUTO_APPROVE", raising=False)
    assert gate.approve(auto=True) is True
    parsed = gate._parse()
    approver = str(parsed.get("approver", ""))
    assert approver.startswith("auto")


def test_explicit_auto_with_reason(gate, monkeypatch):
    """auto=True + auto_reason 호출 시 approver='auto:{reason}' 라벨."""
    monkeypatch.delenv("AF_AUTO_APPROVE", raising=False)
    assert gate.approve(auto=True, auto_reason="trivial-bugfix") is True
    parsed = gate._parse()
    approver = str(parsed.get("approver", ""))
    assert "auto:trivial-bugfix" in approver


def test_explicit_auto_writes_audit_line(gate, monkeypatch):
    """auto=True 호출 시 review_notes에 audit 흔적 prepend."""
    monkeypatch.delenv("AF_AUTO_APPROVE", raising=False)
    gate.approve(auto=True, auto_reason="test")
    parsed = gate._parse()
    notes = str(parsed.get("review_notes", ""))
    assert "[auto-approve]" in notes
    assert "explicit auto=True" in notes
    assert "test" in notes


def test_explicit_auto_opens_execution(gate, monkeypatch):
    """auto=True 호출 시 execution_open=True (실제 게이트 통과)."""
    monkeypatch.delenv("AF_AUTO_APPROVE", raising=False)
    assert gate.is_execution_open() is False  # 초기 false
    gate.approve(auto=True)
    # is_execution_open은 실제로 검증
    # (해시 검증 등은 별도이지만 execution_open 필드는 true)
    parsed = gate._parse()
    assert parsed.get("execution_open") is True or str(parsed.get("execution_open")).lower() == "true"


# ── 환경변수 AF_AUTO_APPROVE=1 ──────────────────────────────────────────────


def test_env_auto_approve_activates(gate, monkeypatch):
    """AF_AUTO_APPROVE=1 환경변수 설정 시 auto 모드."""
    monkeypatch.setenv("AF_AUTO_APPROVE", "1")
    assert gate.approve(approver="user") is True  # approver 무시됨
    parsed = gate._parse()
    approver = str(parsed.get("approver", ""))
    assert approver.startswith("auto")


def test_env_auto_writes_env_marker_in_audit(gate, monkeypatch):
    """env-auto 시 audit 흔적에 env=AF_AUTO_APPROVE=1 명시."""
    monkeypatch.setenv("AF_AUTO_APPROVE", "1")
    gate.approve()
    parsed = gate._parse()
    notes = str(parsed.get("review_notes", ""))
    assert "[auto-approve]" in notes
    assert "AF_AUTO_APPROVE=1" in notes


def test_env_value_other_than_1_does_not_activate(gate, monkeypatch):
    """AF_AUTO_APPROVE=0 또는 다른 값은 비활성."""
    monkeypatch.setenv("AF_AUTO_APPROVE", "0")
    gate.approve(approver="user")
    parsed = gate._parse()
    approver = str(parsed.get("approver", ""))
    assert "auto" not in approver  # user 그대로


def test_env_unset_default_inactive(gate, monkeypatch):
    """환경변수 미설정 시 default user 동작."""
    monkeypatch.delenv("AF_AUTO_APPROVE", raising=False)
    gate.approve(approver="user")
    parsed = gate._parse()
    notes = str(parsed.get("review_notes", ""))
    assert "[auto-approve]" not in notes


# ── 우선순위 / 호환성 ────────────────────────────────────────────────────────


def test_explicit_auto_overrides_when_env_off(gate, monkeypatch):
    """env 꺼져 있어도 explicit auto=True가 우선."""
    monkeypatch.delenv("AF_AUTO_APPROVE", raising=False)
    gate.approve(auto=True, auto_reason="override")
    parsed = gate._parse()
    notes = str(parsed.get("review_notes", ""))
    assert "explicit auto=True" in notes


def test_no_gate_path_returns_false(tmp_path, monkeypatch):
    """gate_path 없으면 False — auto 무관."""
    monkeypatch.setenv("AF_AUTO_APPROVE", "1")
    g = ApprovalGate(str(tmp_path), "no-such-slug")
    # initialize 안 했으므로 gate_path 없음
    assert g.approve() is False
