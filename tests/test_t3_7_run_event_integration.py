"""
T3-7 — Audit/Cost/Approval → RunEvent 통합 테스트.

검증 항목:
  1. RunBudget: 80% 마일스톤에 COST_INCURRED RunEvent 방출
  2. RunBudget: exhausted 마일스톤에 COST_INCURRED RunEvent 방출
  3. RunBudget: run_id 없으면 이벤트 방출 안 함
  4. ApprovalGate.initialize(): APPROVAL_REQUESTED RunEvent 방출
  5. ApprovalGate.approve(): APPROVAL_GRANTED RunEvent 방출
  6. ApprovalGate.approve(): run_id 없으면 이벤트 방출 안 함
  7. W3: is_execution_open() — 문서 변경 시 자동 invalidate + False 반환
  8. W3: is_execution_open() — 문서 미변경 시 True 반환
"""
from __future__ import annotations

import os
import tempfile
from unittest.mock import MagicMock, patch

import pytest

from core.events.run_event import RunEvent, RunEventType
from core.run_budget import RunBudget, set_run_budget


# ── 헬퍼 ────────────────────────────────────────────────────


class _CapturingStore:
    """RunEvent를 메모리에 캡처하는 인메모리 store."""

    def __init__(self):
        self.events: list[RunEvent] = []

    def append(self, event: RunEvent) -> None:
        self.events.append(event)

    def list_events(self, run_id: str) -> list[RunEvent]:
        return [e for e in self.events if e.run_id == run_id]


# ── 1~3. RunBudget COST_INCURRED 방출 ─────────────────────


class TestRunBudgetCostEvent:
    def _make_budget(self, max_tokens: int, run_id: str = "run_test") -> tuple[RunBudget, _CapturingStore]:
        store = _CapturingStore()
        b = RunBudget(max_tokens=max_tokens, run_id=run_id, project_id="proj_test")
        return b, store

    def test_80pct_milestone_emits_cost_event(self):
        store = _CapturingStore()
        b = RunBudget(max_tokens=10, run_id="r1", project_id="p1")
        with patch("core.events.run_event.get_default_store", return_value=store):
            b.record("a" * 32)  # 8 tokens → 80% of 10
        cost_events = [e for e in store.events if e.event_type == RunEventType.COST_INCURRED]
        assert len(cost_events) == 1
        assert cost_events[0].payload["milestone"] == "80_pct"
        assert cost_events[0].run_id == "r1"
        assert cost_events[0].project_id == "p1"

    def test_exhausted_milestone_emits_cost_event(self):
        store = _CapturingStore()
        b = RunBudget(max_tokens=4, run_id="r2", project_id="p2")
        with patch("core.events.run_event.get_default_store", return_value=store):
            b.record("a" * 16)  # 4 tokens → 100% exhausted
        milestones = [e.payload["milestone"] for e in store.events if e.event_type == RunEventType.COST_INCURRED]
        assert "exhausted" in milestones

    def test_no_run_id_no_event(self):
        store = _CapturingStore()
        b = RunBudget(max_tokens=4, run_id="")
        with patch("core.events.run_event.get_default_store", return_value=store):
            b.record("a" * 20)  # triggers both 80% and exhausted
        assert store.events == []

    def test_unlimited_budget_no_event(self):
        store = _CapturingStore()
        b = RunBudget(max_tokens=0, run_id="r3")
        with patch("core.events.run_event.get_default_store", return_value=store):
            b.record("a" * 10_000)
        assert store.events == []

    def test_set_run_budget_accepts_run_id(self):
        b = set_run_budget(100, run_id="run_abc", project_id="proj_xyz")
        assert b.run_id == "run_abc"
        assert b.project_id == "proj_xyz"
        set_run_budget(0)  # reset


# ── 4~6. ApprovalGate RunEvent 방출 ───────────────────────


def _make_gate(tmp_dir: str, slug: str = "test-slug"):
    from core.approval_gate import ApprovalGate
    return ApprovalGate(workspace=tmp_dir, slug=slug)


class TestApprovalGateRunEvent:
    def test_initialize_emits_approval_requested(self, tmp_path):
        store = _CapturingStore()
        gate = _make_gate(str(tmp_path))
        with patch("core.events.run_event.get_default_store", return_value=store):
            gate.initialize(run_id="run_init")
        events = [e for e in store.events if e.event_type == RunEventType.APPROVAL_REQUESTED]
        assert len(events) == 1
        assert events[0].run_id == "run_init"
        assert events[0].payload["slug"] == "test-slug"

    def test_approve_emits_approval_granted(self, tmp_path):
        store = _CapturingStore()
        gate = _make_gate(str(tmp_path))
        gate.initialize()
        with patch("core.events.run_event.get_default_store", return_value=store):
            gate.approve(approver="hoon", run_id="run_approve")
        events = [e for e in store.events if e.event_type == RunEventType.APPROVAL_GRANTED]
        assert len(events) == 1
        assert events[0].run_id == "run_approve"
        assert events[0].payload["approver"] == "hoon"

    def test_no_run_id_no_event(self, tmp_path):
        store = _CapturingStore()
        gate = _make_gate(str(tmp_path))
        gate.initialize()
        with patch("core.events.run_event.get_default_store", return_value=store):
            gate.approve(run_id="")
        approval_events = [e for e in store.events if e.event_type == RunEventType.APPROVAL_GRANTED]
        assert approval_events == []

    def test_approve_missing_gate_no_event(self, tmp_path):
        """gate_path 없으면 approve()가 False + 이벤트 없음."""
        store = _CapturingStore()
        gate = _make_gate(str(tmp_path))
        # initialize() 호출 없이 approve() 시도
        with patch("core.events.run_event.get_default_store", return_value=store):
            result = gate.approve(run_id="run_missing")
        assert result is False
        assert store.events == []


# ── 7~8. W3: is_execution_open() check_validity 통합 ──────


def _write_doc(path: str, content: str = "dummy content") -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


class TestW3IsExecutionOpen:
    def test_open_with_unchanged_docs_returns_true(self, tmp_path):
        gate = _make_gate(str(tmp_path))
        gate.initialize()
        # approve() — 현재 파일 없음 → 빈 해시 스냅샷
        gate.approve()
        # 빈 스냅샷 + 빈 디렉터리 → check_validity() True
        assert gate.is_execution_open() is True

    def test_open_with_changed_docs_auto_invalidates(self, tmp_path):
        """승인 후 문서 변경 → is_execution_open() False + 자동 invalidate."""
        gate = _make_gate(str(tmp_path))
        gate.initialize()
        # 문서 한 개 생성하고 approve (해시 스냅샷 저장)
        feat_plan = os.path.join(str(tmp_path), "docs", "work-items", "test-slug", "feature-plan.md")
        _write_doc(feat_plan, "original content")
        gate.approve()
        assert gate.get_status()["execution_open"] is True

        # 문서 변경
        _write_doc(feat_plan, "modified content — different hash")
        # W3: is_execution_open() 내부에서 check_validity() 실행 → invalidate
        result = gate.is_execution_open()
        assert result is False
        # 자동 invalidate 확인
        status = gate.get_status()
        assert status["execution_open"] is False

    def test_not_open_when_file_missing(self, tmp_path):
        gate = _make_gate(str(tmp_path))
        assert gate.is_execution_open() is False

    def test_not_open_when_status_review_pending(self, tmp_path):
        gate = _make_gate(str(tmp_path))
        gate.initialize()
        assert gate.is_execution_open() is False

    def test_new_doc_added_after_approval_detected(self, tmp_path):
        """승인 당시 없던 문서가 사후 추가되면 check_validity가 False를 반환한다."""
        gate = _make_gate(str(tmp_path))
        gate.initialize()
        gate.approve()  # 문서 없음 → 빈 해시 스냅샷

        # 승인 후 새 문서 추가
        feat_plan = os.path.join(str(tmp_path), "docs", "work-items", "test-slug", "feature-plan.md")
        _write_doc(feat_plan, "brand new content")

        valid, changed = gate.check_validity()
        assert valid is False
        assert "feature-plan.md" in changed
