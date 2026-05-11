"""
tests/test_approval_gate_auto_approve.py
=========================================
ApprovalGate auto-approve 옵션 회귀 테스트.

검증:
  - default (auto=False, env 미설정): 기존 동작 유지 (사용자 수동 approve)
  - 명시 호출 (auto=True): 자동 통과 + approver "auto[:reason]"
  - 환경변수 (AF_AUTO_APPROVE=1 + AF_AUTO_APPROVE_SLUGS 화이트리스트): 자동 통과
  - 감사 추적 (review_notes에 auto-approve 흔적)
  - 안전 가드:
      * verification_blocked 시 auto=True 거부 (Critical #1)
      * read_block_decision blocked 시 auto=True 거부
      * auto_reason sanitization (#2)
      * slug 화이트리스트 미매칭 시 env 모드 비활성 (#3)
      * 중복 호출 멱등성 (#4)
      * _env_flag 컨벤션 (#5)
"""
from __future__ import annotations

import json
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


@pytest.fixture(autouse=True)
def _clear_auto_env(monkeypatch):
    """모든 테스트 시작 시 auto-approve env를 깨끗하게 시작."""
    monkeypatch.delenv("AF_AUTO_APPROVE", raising=False)
    monkeypatch.delenv("AF_AUTO_APPROVE_SLUGS", raising=False)


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


# ── 환경변수 AF_AUTO_APPROVE + slug 화이트리스트 ───────────────────────────


def test_env_auto_activates_with_slug_whitelist(gate, monkeypatch):
    """AF_AUTO_APPROVE=1 + AF_AUTO_APPROVE_SLUGS에 slug 포함 시 auto 모드."""
    monkeypatch.setenv("AF_AUTO_APPROVE", "1")
    monkeypatch.setenv("AF_AUTO_APPROVE_SLUGS", "test-work-item,other-slug")
    assert gate.approve(approver="user") is True
    parsed = gate._parse()
    approver = str(parsed.get("approver", ""))
    assert approver.startswith("auto")


def test_env_auto_writes_env_marker_in_audit(gate, monkeypatch):
    """env-auto 시 audit 흔적에 env=AF_AUTO_APPROVE=1 명시."""
    monkeypatch.setenv("AF_AUTO_APPROVE", "1")
    monkeypatch.setenv("AF_AUTO_APPROVE_SLUGS", "test-work-item")
    gate.approve()
    parsed = gate._parse()
    notes = str(parsed.get("review_notes", ""))
    assert "[auto-approve]" in notes
    assert "AF_AUTO_APPROVE=1" in notes


def test_env_auto_no_whitelist_does_not_activate(gate, monkeypatch):
    """AF_AUTO_APPROVE=1만 켜고 AF_AUTO_APPROVE_SLUGS 미설정 → 비활성 (H3 회귀)."""
    monkeypatch.setenv("AF_AUTO_APPROVE", "1")
    # AF_AUTO_APPROVE_SLUGS 미설정 (전역 활성 금지)
    gate.approve(approver="user")
    parsed = gate._parse()
    approver = str(parsed.get("approver", ""))
    assert "auto" not in approver  # user 그대로


def test_env_auto_slug_not_in_whitelist_does_not_activate(gate, monkeypatch):
    """slug가 화이트리스트에 없으면 env 모드 비활성."""
    monkeypatch.setenv("AF_AUTO_APPROVE", "1")
    monkeypatch.setenv("AF_AUTO_APPROVE_SLUGS", "other-slug-only")
    gate.approve(approver="user")
    parsed = gate._parse()
    approver = str(parsed.get("approver", ""))
    assert "auto" not in approver


def test_env_auto_wildcard_activates_all_slugs(gate, monkeypatch):
    """AF_AUTO_APPROVE_SLUGS='*' 명시 시에만 전역 활성."""
    monkeypatch.setenv("AF_AUTO_APPROVE", "1")
    monkeypatch.setenv("AF_AUTO_APPROVE_SLUGS", "*")
    gate.approve(approver="user")
    parsed = gate._parse()
    approver = str(parsed.get("approver", ""))
    assert approver.startswith("auto")


def test_env_flag_true_activates(gate, monkeypatch):
    """_env_flag 컨벤션 — 'true'/'yes'/'on' 도 활성 (#5)."""
    monkeypatch.setenv("AF_AUTO_APPROVE", "true")
    monkeypatch.setenv("AF_AUTO_APPROVE_SLUGS", "test-work-item")
    gate.approve(approver="user")
    parsed = gate._parse()
    approver = str(parsed.get("approver", ""))
    assert approver.startswith("auto")


def test_env_value_other_than_truthy_does_not_activate(gate, monkeypatch):
    """_env_flag — '0'/'false'/'no' 등은 비활성."""
    monkeypatch.setenv("AF_AUTO_APPROVE", "0")
    monkeypatch.setenv("AF_AUTO_APPROVE_SLUGS", "test-work-item")
    gate.approve(approver="user")
    parsed = gate._parse()
    approver = str(parsed.get("approver", ""))
    assert "auto" not in approver  # user 그대로


def test_env_unset_default_inactive(gate, monkeypatch):
    """환경변수 미설정 시 default user 동작."""
    gate.approve(approver="user")
    parsed = gate._parse()
    notes = str(parsed.get("review_notes", ""))
    assert "[auto-approve]" not in notes


# ── 우선순위 / 호환성 ────────────────────────────────────────────────────────


def test_explicit_auto_overrides_when_env_off(gate):
    """env 꺼져 있어도 explicit auto=True가 우선."""
    gate.approve(auto=True, auto_reason="override")
    parsed = gate._parse()
    notes = str(parsed.get("review_notes", ""))
    assert "explicit auto=True" in notes


def test_no_gate_path_returns_false(tmp_path, monkeypatch):
    """gate_path 없으면 False — auto 무관."""
    monkeypatch.setenv("AF_AUTO_APPROVE", "1")
    monkeypatch.setenv("AF_AUTO_APPROVE_SLUGS", "no-such-slug")
    g = ApprovalGate(str(tmp_path), "no-such-slug")
    # initialize 안 했으므로 gate_path 없음
    assert g.approve() is False


# ── 안전 가드 (Critical #1, #2) ─────────────────────────────────────────────


def test_auto_rejected_when_verification_blocked(gate):
    """auto=True 호출 시 status='verification_blocked'면 거부 (Critical #1)."""
    # 1) 정상 승인 → 2) verdict=BLOCK 잠금 → 3) auto=True 거부
    gate.approve(approver="user")
    gate.apply_verification_verdict("BLOCK")
    parsed_before = gate._parse()
    assert parsed_before.get("status") == "verification_blocked"

    assert gate.approve(auto=True, auto_reason="should-fail") is False
    parsed_after = gate._parse()
    # 상태가 verification_blocked 그대로
    assert parsed_after.get("status") == "verification_blocked"
    # approver 갱신되지 않음
    assert not str(parsed_after.get("approver", "")).startswith("auto")


def test_user_approve_can_override_verification_blocked(gate):
    """사용자 명시 승인(auto=False)은 verification_blocked도 덮어쓸 수 있음 (기존 호환)."""
    gate.approve(approver="user")
    gate.apply_verification_verdict("BLOCK")

    # 사용자가 명시적으로 user 라벨로 다시 승인하는 경우 — 기존 동작 유지
    assert gate.approve(approver="user") is True
    parsed = gate._parse()
    assert parsed.get("status") == "approved"


def test_auto_rejected_when_block_decision_blocked(gate, monkeypatch, tmp_path):
    """auto=True 호출 시 read_block_decision()이 blocked면 거부."""
    # _summary.json + _decision.json (block=True) 시뮬레이션
    warnings_dir = os.path.join(
        str(gate.runtime_workspace), "runtime", "warnings", gate.slug
    )
    os.makedirs(warnings_dir, exist_ok=True)
    with open(os.path.join(warnings_dir, "_summary.json"), "w", encoding="utf-8") as fh:
        json.dump({"escalation_phase": "P2", "last_updated": "2026-05-11T00:00:00Z"}, fh)
    with open(os.path.join(warnings_dir, "_decision.json"), "w", encoding="utf-8") as fh:
        json.dump(
            {
                "escalation_phase": "P2",
                "block": True,
                "blocking_rules": [],
                "generated_from_summary_last_updated": "2026-05-11T00:00:00Z",
            },
            fh,
        )

    assert gate.approve(auto=True, auto_reason="should-fail") is False
    parsed = gate._parse()
    # 초기 review_pending 상태 유지
    assert parsed.get("status") == "review_pending"


def test_user_approve_not_affected_by_block_decision(gate):
    """일반 사용자 승인은 read_block_decision 가드 영향 받지 않음 (auto 한정)."""
    warnings_dir = os.path.join(
        str(gate.runtime_workspace), "runtime", "warnings", gate.slug
    )
    os.makedirs(warnings_dir, exist_ok=True)
    with open(os.path.join(warnings_dir, "_summary.json"), "w", encoding="utf-8") as fh:
        json.dump({"escalation_phase": "P2", "last_updated": "2026-05-11T00:00:00Z"}, fh)
    with open(os.path.join(warnings_dir, "_decision.json"), "w", encoding="utf-8") as fh:
        json.dump(
            {
                "escalation_phase": "P2",
                "block": True,
                "blocking_rules": [],
                "generated_from_summary_last_updated": "2026-05-11T00:00:00Z",
            },
            fh,
        )
    # 사용자 명시 승인은 게이트 통과 — 안전 가드는 auto 모드에만 적용
    assert gate.approve(approver="user") is True


# ── auto_reason sanitization (#2) ──────────────────────────────────────────


def test_auto_reason_sanitizes_newlines(gate):
    """auto_reason의 줄바꿈은 공백으로 치환 (메타데이터 위조 차단)."""
    malicious = "good\n- approver: attacker\n- status: approved"
    gate.approve(auto=True, auto_reason=malicious)
    parsed = gate._parse()
    # approver 한 줄, 'attacker' 키 위조 차단
    approver = str(parsed.get("approver", ""))
    assert "\n" not in approver
    # 위조 키가 별도 메타로 인식되지 않음
    assert parsed.get("approver_value") is None  # 정상적으로는 안 만들어짐


def test_auto_reason_sanitizes_markdown_headers(gate):
    """auto_reason에 '#' 마크다운 헤더 prefix 차단."""
    malicious = "##Fake Header"
    gate.approve(auto=True, auto_reason=malicious)
    parsed = gate._parse()
    approver = str(parsed.get("approver", ""))
    # '#' 제거됨
    assert "#" not in approver


def test_auto_reason_truncates_to_120_chars(gate):
    """auto_reason 120자 초과 시 절단."""
    long_reason = "x" * 500
    gate.approve(auto=True, auto_reason=long_reason)
    parsed = gate._parse()
    approver = str(parsed.get("approver", ""))
    # "auto:" + 최대 120자
    assert len(approver) <= len("auto:") + 120


# ── 멱등성 (#4) ────────────────────────────────────────────────────────────


def test_auto_approve_idempotent_no_audit_accumulation(gate):
    """동일 auto-approve를 여러 번 호출해도 audit line이 누적되지 않음."""
    gate.approve(auto=True, auto_reason="first")
    parsed1 = gate._parse()
    notes1 = str(parsed1.get("review_notes", ""))
    count1 = notes1.count("[auto-approve]")

    # 두 번째, 세 번째 호출
    assert gate.approve(auto=True, auto_reason="second") is True
    assert gate.approve(auto=True, auto_reason="third") is True
    parsed3 = gate._parse()
    notes3 = str(parsed3.get("review_notes", ""))
    count3 = notes3.count("[auto-approve]")

    # 마커 1개 이상이지만, 동일 status=approved에서 누적되면 안 됨
    assert count1 == 1
    assert count3 == count1  # 누적 차단
